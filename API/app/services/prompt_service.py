import asyncio
import logging
from typing import Optional, List, Tuple

from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.services.file_processing_service import FileProcessingService
from app.services.qdrant_service import qdrant_service

logger = logging.getLogger("BenchmarkWorker")

RAG_PROMPT_TEMPLATE = """Kontekst z bazy wiedzy:
{context}

Pytanie: {question}

Odpowiedz na pytanie korzystając wyłącznie z podanego kontekstu. Jeśli odpowiedź nie znajduje się w kontekście, napisz "Brak odpowiedzi w dostępnym kontekście"."""


class PromptService:
    """Service for preparing prompts (RAG, files)"""

    @staticmethod
    async def prepare_rag_prompt(
        test_case: TestCase,
        test_suite: TestSuite
    ) -> Tuple[str, Optional[List]]:
        """
        Prepare RAG prompt with context from Qdrant.
        Returns (prompt, images_list).
        """
        logger.info(f"Tryb RAG: wyszukiwanie w kolekcji '{test_suite.qdrant_collection}'")
        relevant_chunks = await qdrant_service.search_relevant_chunks(
            collection_name=test_suite.qdrant_collection,  # type: ignore
            query=test_case.input_text or "",
            model_id=str(test_suite.embedding_model_id) if test_suite.embedding_model_id else None,
            limit=5
        )

        context_parts = []
        for chunk_data in relevant_chunks:
            text, page_num, filename = chunk_data
            if page_num and filename:
                context_parts.append(f"[Plik: {filename}, Strona: {page_num}]\n{text}")
            else:
                context_parts.append(text)
        context = "\n\n".join(context_parts) if context_parts else "Brak kontekstu."
        combined_prompt = RAG_PROMPT_TEMPLATE.format(
            context=context,
            question=test_case.input_text or ""
        )
        return combined_prompt, None

    @staticmethod
    async def prepare_standard_prompt(
        test_case: TestCase
    ) -> Tuple[str, List]:
        """
        Prepare standard prompt with file contents.
        Returns (prompt, images_list).
        """
        combined_prompt = test_case.input_text or ""
        images_list = []

        if test_case.files:
            file_contents_list = []
            for file_asset in test_case.files:
                file_data = await asyncio.to_thread(
                    FileProcessingService.get_file_content, file_asset
                )

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

        return combined_prompt, images_list
