import asyncio
import logging
import uuid

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.benchmark_execution import BenchmarkExecution, ExecutionStatus
from app.models.benchmark_run import BenchmarkRun, RunStatus  # noqa
from app.models.llm_model import LLMModel
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.core.config import settings
from app.core.llm_clients import BaseLLMClient, LLMClientFactory, LLMException
from app.core.utils import clean_llm_response
from app.services.evaluation_service import EvaluationService, EvaluationException
from app.services.prompt_service import PromptService

logger = logging.getLogger("BenchmarkWorker")


class WorkerService:
    """Service encapsulating worker logic for better testability"""

    def __init__(self):
        self.prompt_service = PromptService()

    async def _fetch_execution_data(self, db, execution_id: uuid.UUID) -> tuple:
        """Fetch execution, model, test_case, test_suite from database"""
        stmt = select(BenchmarkExecution).where(BenchmarkExecution.id == execution_id)
        execution = (await db.execute(stmt)).scalar_one()
        model_stmt = select(LLMModel).where(LLMModel.id == execution.llm_model_id)
        llm_model = (await db.execute(model_stmt)).scalar_one()
        tc_stmt = select(TestCase).where(TestCase.id == execution.test_case_id)
        test_case = (await db.execute(tc_stmt)).scalar_one()
        suite_stmt = select(TestSuite).where(TestSuite.id == test_case.suite_id)
        test_suite = (await db.execute(suite_stmt)).scalar_one()
        return execution, llm_model, test_case, test_suite

    async def _prepare_prompt_and_images(
        self,
        test_case: TestCase,
        test_suite: TestSuite,
        client: BaseLLMClient
    ) -> tuple:
        """Prepare prompt and list of images"""
        if test_suite.qdrant_collection:
            return await self.prompt_service.prepare_rag_prompt(test_case, test_suite, client)
        else:
            return await self.prompt_service.prepare_standard_prompt(test_case)

    async def _execute_llm_and_process(
        self,
        client: BaseLLMClient,
        prompt: str,
        system_prompt: str,
        images: list,
        verification_method: str,
        expected_text: str,
        judge_client: BaseLLMClient | None = None,
        eval_prompt: str | None = None,
        question: str | None = None
    ) -> tuple:
        """
        Execute LLM and evaluate response.
        Returns (cleaned_response_text, score, eval_details, latency_ms, prompt_tokens, completion_tokens)
        """
        start_time = asyncio.get_event_loop().time()

        response_text, prompt_tokens, completion_tokens = await client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            images=images if images else None
        )

        end_time = asyncio.get_event_loop().time()
        latency_ms = int((end_time - start_time) * 1000)

        cleaned_response_text = clean_llm_response(response_text, verification_method)

        score, eval_details = await EvaluationService.evaluate(
            verification_method=verification_method,
            expected=expected_text,
            actual=cleaned_response_text,
            judge_client=judge_client,
            system_prompt=eval_prompt,
            question=question
        )

        return cleaned_response_text, score, eval_details, latency_ms, prompt_tokens, completion_tokens

    async def _save_results(
        self,
        execution: BenchmarkExecution,
        db,
        cleaned_response_text: str,
        score,
        latency_ms: int,
        prompt_tokens: int,
        completion_tokens: int,
        eval_details: dict
    ):
        """Save results to database"""
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

        await db.commit()

    async def process_single_execution(self, execution_id: uuid.UUID):
        """
        Pobiera dane wykonania, wywołuje LLM i ewaluację, a następnie zapisuje wyniki.
        """
        execution = None
        cleaned_response_text = None
        latency_ms = None
        prompt_tokens = None
        completion_tokens = None
        score = None
        question = None
        eval_details = {}

        async with AsyncSessionLocal() as db:
            try:
                execution, llm_model, test_case, test_suite = await self._fetch_execution_data(db, execution_id)

                logger.info(f"Procesowanie [{execution_id}]: Model='{llm_model.name}', TestCase='{test_case.id}'")
                base_parameters = llm_model.parameters or {}
                suite_parameters = test_suite.parameters or {}
                merged_parameters = {**base_parameters, **suite_parameters}
                temp_llm_model = LLMModel(
                    id=llm_model.id,
                    name=llm_model.name,
                    provider=llm_model.provider,
                    api_base_url=llm_model.api_base_url,
                    model_identifier=llm_model.model_identifier,
                    api_key=llm_model.api_key,
                    parameters=merged_parameters,
                    is_active=llm_model.is_active
                )
                client = LLMClientFactory.get_client(temp_llm_model)

                combined_prompt, images_list = await self._prepare_prompt_and_images(test_case, test_suite, client)

                expected_text = test_case.expected_output or ""

                judge_client = None
                if test_suite.verification_method == "LLM_EVAL":
                    judge_model_name = settings.JUDGE_MODEL_NAME

                    if not judge_model_name:
                        raise Exception("Brak zmiennej JUDGE_MODEL_NAME w pliku .env (lub ma pustą wartość)!")

                    judge_stmt = select(LLMModel).where(LLMModel.name == judge_model_name)
                    judge_result = await db.execute(judge_stmt)
                    judge_model = judge_result.scalar_one_or_none()

                    if not judge_model:
                        raise Exception(f"Nie znaleziono modelu sędziego '{judge_model_name}' w bazie danych!")

                    judge_client = LLMClientFactory.get_client(judge_model)

                    question = test_case.input_text if test_suite.qdrant_collection else None

                cleaned_response_text, score, eval_details, latency_ms, prompt_tokens, completion_tokens = await self._execute_llm_and_process(  # noqa
                    client=client,
                    prompt=combined_prompt,
                    system_prompt=test_suite.system_prompt,
                    images=images_list,
                    verification_method=test_suite.verification_method,
                    expected_text=expected_text,
                    judge_client=judge_client,
                    eval_prompt=test_suite.eval_prompt,
                    question=question
                 )

                await self._save_results(
                    execution=execution,
                    db=db,
                    cleaned_response_text=cleaned_response_text,
                    score=score,
                    latency_ms=latency_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    eval_details=eval_details
                )

                logger.info(f"Zakończono sukcesem [{execution_id}]. Wynik ewaluacji ({test_suite.verification_method}): {score}")

            except LLMException as e:
                logger.error(f"Błąd klienta LLM dla [{execution_id}]: {str(e)}")
                if execution:
                    execution.status = ExecutionStatus.FAILED
                    execution.error_message = str(e)
                    await db.commit()

            except EvaluationException as e:
                logger.error(f"Błąd weryfikacji odpowiedzi [{execution_id}]: {str(e)}")
                if execution:
                    execution.response_text = cleaned_response_text
                    execution.latency_ms = latency_ms
                    execution.prompt_tokens = prompt_tokens
                    execution.completion_tokens = completion_tokens
                    execution.status = ExecutionStatus.FAILED
                    execution.error_message = str(e)
                    await db.commit()

            except Exception as e:
                logger.error(f"Nieoczekiwany błąd procesowania [{execution_id}]: {str(e)}", exc_info=True)
                if execution:
                    execution.status = ExecutionStatus.FAILED
                    execution.error_message = f"Błąd wewnętrzny workera: {str(e)}"
                    await db.commit()

    async def worker_loop(self):
        """Main worker loop that processes pending executions"""
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
                    await self.process_single_execution(execution_id)
                else:
                    await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Błąd krytyczny w pętli workera: {str(e)}")
                await asyncio.sleep(60)
