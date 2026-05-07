import asyncio
import logging

from app.services.worker_service import WorkerService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BenchmarkWorker")

worker_service = WorkerService()

if __name__ == "__main__":
    asyncio.run(worker_service.worker_loop())
