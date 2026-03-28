from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_ollama import OllamaLLM

router = APIRouter()

# TODO: Później te wartości będą pobierane z bazy/konfiguracji GUI
OLLAMA_BASE_URL = "http://192.168.0.109:11434"
MODEL_NAME = "qwen3:8b"


class PromptRequest(BaseModel):
    prompt: str


class PromptResponse(BaseModel):
    response: str


@router.post("/generate", response_model=PromptResponse)
async def generate_response(request: PromptRequest):
    try:
        llm = OllamaLLM(
            base_url=OLLAMA_BASE_URL,
            model=MODEL_NAME
        )
        response = llm.invoke(request.prompt)
        return PromptResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd podczas komunikacji z LLM: {str(e)}")
