from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from app.kb import create_retriever

load_dotenv()  # carrega o .env com as chaves de API

from app.agent import chat

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.tools import get_retriever
    print("Pré-carregando base de conhecimento...")
    get_retriever()   # força inicialização antes de aceitar requisições
    print("Pronto.")
    yield

from langfuse import Langfuse

langfuse_client = Langfuse()

class ScoreRequest(BaseModel):
    trace_id: str
    score: float         # 0.0 a 1.0
    comment: str = ""

app = FastAPI(lifespan=lifespan)

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    trace_id: str

@app.post("/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest) -> ChatResponse:
    resposta = chat(request.session_id, request.message)
    return ChatResponse(response=resposta)

@app.post("/score")
def add_score(request: ScoreRequest):
    langfuse_client.create_score(
        trace_id=request.trace_id,
        name="relevancia_resposta",
        value=request.score,
        comment=request.comment,
    )
    return {"status": "ok"}