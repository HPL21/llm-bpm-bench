from fastapi import FastAPI

app = FastAPI(title="LLM Benchmarker API")

@app.get("/")
async def root():
    return {"message": "API działa poprawnie!"}