import asyncio
import io
import logging
import uuid
import os
import tempfile
import base64
import pymupdf4llm

from sqlalchemy import select
from PIL import Image
from app.core.database import AsyncSessionLocal
from app.models.benchmark_execution import BenchmarkExecution, ExecutionStatus
from app.models.benchmark_run import BenchmarkRun, RunStatus  # noqa
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.models.llm_model import LLMModel
from app.models.file_asset import FileAsset
from app.core.llm_clients import LLMClientFactory, LLMException
from app.core.utils import clean_llm_response
from app.services.evaluation_service import EvaluationService, EvaluationException
from app.services.storage_service import storage_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BenchmarkWorker")

MAX_IMAGE_SIZE = (1024, 1024)


def get_file_content(file_asset: FileAsset) -> dict:
    """
    Pobiera plik z MinIO i przygotowuje jego zawartość na podstawie formatu.
    Dla PDF - ekstrakcja tekstu. Dla obrazów - optymalizacja, resize i konwersja do Base64.
    Funkcja synchroniczna (blokująca), powinna być wywoływana w osobnym wątku.
    """
    try:
        response = storage_service.client.get_object(
            storage_service.bucket_name,
            file_asset.minio_path
        )
        file_bytes = response.read()
    except Exception as e:
        logger.error(f"Nie udało się pobrać pliku {file_asset.filename} z MinIO: {e}")
        return {"type": "error", "content": f"[Błąd pobierania pliku: {file_asset.filename}]"}
    finally:
        if 'response' in locals():
            response.close()
            response.release_conn()

    ext = os.path.splitext(file_asset.filename)[1].lower()

    if ext == ".pdf":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            logger.info(f"Ekstrakcja tekstu z pliku PDF: {file_asset.filename}")
            md_text = pymupdf4llm.to_markdown(tmp_path)
            return {"type": "text", "content": md_text}
        except Exception as e:
            logger.error(f"Błąd podczas parsowania pliku PDF {file_asset.filename}: {e}")
            return {"type": "error", "content": f"[Błąd przetwarzania pliku PDF: {file_asset.filename}]"}
        finally:
            os.remove(tmp_path)

    elif ext in [".jpg", ".jpeg", ".png"]:
        logger.info(f"Przygotowanie i optymalizacja obrazu {file_asset.filename} do wysłania.")
        try:
            img = Image.open(io.BytesIO(file_bytes))
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                alpha_mask = img.convert("RGBA").split()[3]
                background.paste(img, mask=alpha_mask)
                img = background
                ext = ".jpg"
            elif img.mode != "RGB":
                img = img.convert("RGB")
            img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            save_format = "PNG" if ext == ".png" else "JPEG"
            save_kwargs = {"format": save_format}
            if save_format == "JPEG":
                save_kwargs["quality"] = 85  # type: ignore
                save_kwargs["optimize"] = True  # type: ignore
            img.save(buffer, **save_kwargs)
            processed_bytes = buffer.getvalue()
            b64_img = base64.b64encode(processed_bytes).decode("utf-8")
            mime = "image/png" if ext == ".png" else "image/jpeg"
            return {"type": "image", "content": b64_img, "mime_type": mime}
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania obrazu {file_asset.filename}: {e}")
            return {"type": "error", "content": f"[Błąd przetwarzania obrazu: {file_asset.filename}]"}

    else:
        logger.warning(f"Nieobsługiwany format pliku: {ext} ({file_asset.filename})")
        return {"type": "error", "content": f"[Pominięto nieobsługiwany format pliku: {file_asset.filename}]"}


async def process_single_execution(execution_id: uuid.UUID):
    """
    Pobiera dane wykonania, wywołuje LLM i ewaluację, a następnie zapisuje wyniki.
    Używamy nowej sesji do procesowania, aby zachować czystość transakcji.
    """
    async with AsyncSessionLocal() as db:
        try:
            stmt = select(BenchmarkExecution).where(BenchmarkExecution.id == execution_id)
            execution = (await db.execute(stmt)).scalar_one()
            model_stmt = select(LLMModel).where(LLMModel.id == execution.llm_model_id)
            llm_model = (await db.execute(model_stmt)).scalar_one()
            tc_stmt = select(TestCase).where(TestCase.id == execution.test_case_id)
            test_case = (await db.execute(tc_stmt)).scalar_one()
            suite_stmt = select(TestSuite).where(TestSuite.id == test_case.suite_id)
            test_suite = (await db.execute(suite_stmt)).scalar_one()

            logger.info(f"Procesowanie [{execution_id}]: Model='{llm_model.name}', TestCase='{test_case.id}'")
            client = LLMClientFactory.get_client(llm_model)

            combined_prompt = test_case.input_text or ""
            images_list = []

            if test_case.files:
                file_contents_list = []
                for file_asset in test_case.files:
                    file_data = await asyncio.to_thread(get_file_content, file_asset)

                    if file_data["type"] == "text" or file_data["type"] == "error":
                        file_contents_list.append(
                            f"--- Początek zawartości pliku: {file_asset.filename} ---\n"
                            f"{file_data['content']}\n"
                            f"--- Koniec zawartości pliku: {file_asset.filename} ---"
                        )
                    elif file_data["type"] == "image":
                        images_list.append(file_data)

                if file_contents_list:
                    files_block = "\n\n".join(file_contents_list)
                    if combined_prompt:
                        combined_prompt = f"{combined_prompt}\n\n{files_block}"
                    else:
                        combined_prompt = files_block

            start_time = asyncio.get_event_loop().time()

            response_text, prompt_tokens, completion_tokens = await client.generate(
                prompt=combined_prompt,
                system_prompt=test_suite.system_prompt,
                images=images_list if images_list else None
            )

            end_time = asyncio.get_event_loop().time()
            latency_ms = int((end_time - start_time) * 1000)
            expected_text = test_case.expected_output or ""
            cleaned_response_text = clean_llm_response(response_text, test_suite.verification_method)

            score, eval_details = await EvaluationService.evaluate(
                verification_method=test_suite.verification_method,
                expected=expected_text,
                actual=cleaned_response_text
            )

            execution.response_text = cleaned_response_text
            execution.score = score
            execution.latency_ms = latency_ms
            execution.prompt_tokens = prompt_tokens
            execution.completion_tokens = completion_tokens
            execution.status = ExecutionStatus.COMPLETED

            if "reason" in eval_details:
                execution.error_message = f"Uzasadnienie sędziego: {eval_details['reason']}"
            elif "error" in eval_details:
                execution.error_message = eval_details["error"]

            logger.info(f"Zakończono sukcesem [{execution_id}]. Wynik ewaluacji ({test_suite.verification_method}): {score}")

            await db.commit()

        except LLMException as e:
            logger.error(f"Błąd klienta LLM dla [{execution_id}]: {str(e)}")
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            await db.commit()

        except EvaluationException as e:
            logger.error(f"Błąd weryfikacji odpowiedzi [{execution_id}]: {str(e)}")
            execution.response_text = cleaned_response_text
            execution.latency_ms = latency_ms
            execution.prompt_tokens = prompt_tokens
            execution.completion_tokens = completion_tokens
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            await db.commit()

        except Exception as e:
            logger.error(f"Nieoczekiwany błąd procesowania [{execution_id}]: {str(e)}", exc_info=True)
            execution.status = ExecutionStatus.FAILED
            execution.error_message = f"Błąd wewnętrzny workera: {str(e)}"
            await db.commit()


async def worker_loop():
    logger.info("Uruchamianie serwisu workera Benchmarków...")
    while True:
        try:
            async with AsyncSessionLocal() as db:
                stmt = (
                    select(BenchmarkExecution.id)
                    .where(BenchmarkExecution.status == ExecutionStatus.PENDING)
                    .order_by(BenchmarkExecution.created_at.asc(), BenchmarkExecution.id.asc())
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )

                result = await db.execute(stmt)
                execution_id = result.scalar_one_or_none()

                if execution_id:
                    update_stmt = select(BenchmarkExecution).where(BenchmarkExecution.id == execution_id)
                    exec_obj = (await db.execute(update_stmt)).scalar_one()
                    exec_obj.status = ExecutionStatus.PROCESSING
                    await db.commit()

            if execution_id:
                await process_single_execution(execution_id)
            else:
                await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Błąd krytyczny w pętli workera: {str(e)}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(worker_loop())
