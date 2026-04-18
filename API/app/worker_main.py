import asyncio
import logging
import uuid
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.benchmark_execution import BenchmarkExecution, ExecutionStatus
from app.models.benchmark_run import BenchmarkRun, RunStatus  # noqa
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.models.llm_model import LLMModel
from app.core.llm_clients import LLMClientFactory, LLMException
from app.services.evaluation_service import EvaluationService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BenchmarkWorker")


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

            start_time = asyncio.get_event_loop().time()

            response_text = await client.generate(
                prompt=test_case.input_text,
                system_prompt=test_suite.system_prompt
            )
            end_time = asyncio.get_event_loop().time()
            latency_ms = int((end_time - start_time) * 1000)
            expected_text = test_case.expected_output or ""

            score, eval_details = await EvaluationService.evaluate(
                verification_method=test_suite.verification_method,
                expected=expected_text,
                actual=response_text
            )

            execution.response_text = response_text
            execution.score = score
            execution.latency_ms = latency_ms
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
