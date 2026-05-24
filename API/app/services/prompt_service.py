import asyncio
import copy
import logging
from typing import Optional, List, Tuple

from app.core.llm_clients import BaseLLMClient
from app.core.utils import clean_llm_response
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.services.file_processing_service import FileProcessingService
from app.services.qdrant_service import qdrant_service

logger = logging.getLogger("BenchmarkWorker")

RAG_PROMPT_TEMPLATE = """Kontekst z bazy wiedzy:
{context}

##############################################################

Pytanie: {question}

##############################################################

Odpowiedz na pytanie korzystając wyłącznie z podanego kontekstu. Jeśli odpowiedź nie znajduje się w kontekście, napisz "Brak odpowiedzi w dostępnym kontekście"."""  # noqa


class PromptService:
    """Service for preparing prompts (RAG, files)"""

    @staticmethod
    async def prepare_rag_prompt(
        test_case: TestCase,
        test_suite: TestSuite,
        client: BaseLLMClient
    ) -> Tuple[str, Optional[List]]:
        """
        Prepare RAG prompt using Multi-Query generation via the tested LLM.
        """
        original_query = test_case.input_text or ""

        mq_system_prompt = (
            "Jesteś ekspertem prawnym. Przekształć zapytanie użytkownika w 3 bardzo krótkie, uderzające w sedno warianty wyszukiwania dla bazy wektorowej. "  # noqa
            "1. Wariant używający stricte formalnych pojęć z kodeksów (max 5-8 słów).\n"
            "2. Wariant skupiony na rdzeniu problemu/czynności prawnej (max 5-8 słów).\n"
            "3. Wariant redukujący zapytanie do najważniejszych słów kluczowych (np. ustawa, artykuł, kluczowe pojęcie).\n"
            "Zasady:\n"
            "- Nie zadawaj pytań. Zwróć tylko skondensowane frazy.\n"
            "- Każda fraza musi znajdować się w nowej linii.\n"
            "- Absolutny zakaz używania numeracji, punktorów, myślników oraz tekstu wstępnego."
        )

        try:
            client_copy = copy.deepcopy(client)
            client_copy.model_config.parameters["thinking_budget_tokens"] = 512
            mq_response, _, _ = await client_copy.generate(
                prompt=original_query,
                system_prompt=mq_system_prompt
            )
            cleaned_mq_response = clean_llm_response(mq_response)
            generated_queries = [q.strip() for q in cleaned_mq_response.split('\n') if q.strip()]
            queries = [original_query] + generated_queries[:3]
            logger.info(f"Wygenerowano warianty Multi-Query: {generated_queries[:3]}")
        except Exception as e:
            logger.warning(f"Błąd generowania wariantów Multi-Query: {e}. Używam tylko oryginału.")
            queries = [original_query]

        logger.info(f"Tryb RAG: wyszukiwanie w '{test_suite.qdrant_collection}' dla {len(queries)} zapytań")
        relevant_chunks = await qdrant_service.search_relevant_chunks_multiquery(
            collection_name=test_suite.qdrant_collection,  # type: ignore
            queries=queries,
            model_id=str(test_suite.embedding_model_id) if test_suite.embedding_model_id else None,
            limit=10
        )

        context_parts = []
        for chunk_data in relevant_chunks:
            text, page_num, filename = chunk_data
            if page_num and filename:
                context_parts.append(f"[Plik: {filename}, Strona: {page_num}]\n{text}")
            else:
                context_parts.append(text)

        logger.info(f"Znaleziono {len(relevant_chunks)} istotnych fragmentów dla zapytań Multi-Query.")

        context = "\n#########\n".join(context_parts) if context_parts else "Brak kontekstu."
        combined_prompt = RAG_PROMPT_TEMPLATE.format(
            context=context,
            question=original_query
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
