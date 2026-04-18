import httpx
import logging
from abc import ABC, abstractmethod
from app.models.llm_model import LLMModel

logger = logging.getLogger(__name__)


class LLMException(Exception):
    """Bazowa klasa dla błędów związanych z LLM."""
    pass


class LLMConnectionError(LLMException):
    """Błąd połączenia z serwerem (np. serwer nie działa)."""
    pass


class LLMTimeoutError(LLMException):
    """Przekroczono czas oczekiwania na odpowiedź."""
    pass


class LLMAPIError(LLMException):
    """Serwer zwrócił błąd HTTP (np. 400 Bad Request, 500 Internal Server Error)."""
    def __init__(self, message: str, status_code: int, response_body: str):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class BaseLLMClient(ABC):
    def __init__(self, model_config: LLMModel):
        self.model_config = model_config
        self.base_url = model_config.api_base_url.rstrip("/")
        self.model_name = model_config.model_identifier
        self.timeout = httpx.Timeout(300.0, connect=10.0)

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        pass

    async def _safe_post(self, url: str, **kwargs) -> httpx.Response:
        """Wewnętrzna metoda do bezpiecznego wysyłania zapytań z inteligentną obsługą błędów."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, **kwargs)
                if response.status_code >= 400:
                    error_detail = response.text
                    try:
                        error_json = response.json()
                        if "error" in error_json and isinstance(error_json["error"], dict) and "message" in error_json["error"]:
                            error_detail = error_json["error"]["message"]
                        elif "error" in error_json and isinstance(error_json["error"], str):
                            error_detail = error_json["error"]
                    except ValueError:
                        pass

                    logger.error(
                        f"Błąd API LLM ({response.status_code}) dla {self.model_name}. "
                        f"Szczegóły: {error_detail}"
                    )

                    raise LLMAPIError(
                        message=f"API Error {response.status_code}: {error_detail}",
                        status_code=response.status_code,
                        response_body=response.text
                    )
                return response

        except httpx.TimeoutException as e:
            logger.error(f"Timeout ({self.timeout}s) podczas łączenia z {url}")
            raise LLMTimeoutError(f"Przekroczono czas oczekiwania na odpowiedź modelu {self.model_name}") from e
        except httpx.RequestError as e:
            logger.error(f"Błąd połączenia z {url}: {str(e)}")
            raise LLMConnectionError(f"Nie udało się połączyć z modelem {self.model_name} ({self.base_url})") from e


class OpenAICompatibleClient(BaseLLMClient):
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {"Content-Type": "application/json"}
        if self.model_config.api_key:
            headers["Authorization"] = f"Bearer {self.model_config.api_key}"

        payload = {
            "model": self.model_name,
            "messages": messages,
            **self.model_config.parameters
        }

        response = await self._safe_post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            headers=headers
        )

        try:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except (KeyError, ValueError) as e:
            logger.error(f"Nieoczekiwana struktura odpowiedzi OpenAI dla {self.model_name}: {response.text}")
            raise LLMException(f"Błąd parsowania odpowiedzi: {str(e)}")


class OllamaClient(BaseLLMClient):
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": self.model_config.parameters
        }
        if system_prompt:
            payload["system"] = system_prompt

        response = await self._safe_post(
            f"{self.base_url}/api/generate",
            json=payload
        )

        try:
            data = response.json()
            return data["response"]
        except (KeyError, ValueError) as e:
            logger.error(f"Nieoczekiwana struktura odpowiedzi Ollama dla {self.model_name}: {response.text}")
            raise LLMException(f"Błąd parsowania odpowiedzi: {str(e)}")


class LLMClientFactory:
    @staticmethod
    def get_client(model_config: LLMModel) -> BaseLLMClient:
        provider = model_config.provider.lower()
        if provider == "ollama":
            return OllamaClient(model_config)
        elif provider in ["vllm", "llama.cpp", "openai"]:
            return OpenAICompatibleClient(model_config)
        else:
            raise ValueError(f"Nieobsługiwany provider LLM: {model_config.provider}")
