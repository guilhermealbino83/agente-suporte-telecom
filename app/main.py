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

app = FastAPI(lifespan=lifespan)

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest) -> ChatResponse:
    resposta = chat(request.session_id, request.message)
    return ChatResponse(response=resposta)
