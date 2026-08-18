from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()  # carrega o .env com as chaves de API

from app.agent import chat

app = FastAPI()

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest) -> ChatResponse:
    resposta = chat(request.session_id, request.message)
    return ChatResponse(response=resposta)
