# Etapa 1 — FastAPI + LangChain com Memória Conversacional

## Objetivo

Criar um endpoint HTTP que recebe mensagens e mantém o histórico da conversa por sessão — o bot "lembra" o que foi dito antes.

---

## Passo 0 — Preparar o ambiente

### Criar a estrutura de pastas

```
agente-suporte-telecom/
├── app/
│   ├── __init__.py      ← arquivo vazio, necessário para Python tratar como pacote
│   ├── main.py
│   └── agent.py
├── docs/                ← já existe (aqui estão esses guias)
├── requirements.txt
└── .env                 ← suas chaves de API (não commitar)
```

### Instalar dependências

Crie o `requirements.txt` com o conteúdo abaixo e depois instale:

```
fastapi
uvicorn[standard]
langchain
langchain-anthropic
python-dotenv
```

```bash
pip install -r requirements.txt
```

### Configurar variável de ambiente

Crie o arquivo `.env` na raiz do projeto:

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Passo 1 — Entender o que é uma Chain com Memória

Antes de codar, o fluxo conceitual é:

```
[mensagem do usuário]
        ↓
[histórico da sessão é recuperado do store]
        ↓
[prompt é montado: system + histórico + mensagem atual]
        ↓
[LLM processa e responde]
        ↓
[resposta + par pergunta/resposta é salvo no store]
        ↓
[resposta retorna para o usuário]
```

O `session_id` é a chave que identifica qual histórico usar. Sessões diferentes têm históricos independentes.

---

## Passo 2 — Criar o módulo de agente (`app/agent.py`)

Este arquivo tem duas responsabilidades:
1. Construir a chain (prompt → LLM)
2. Gerenciar o store de histórico por sessão

### 2.1 — Importações necessárias

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
```

### 2.2 — O store de sessões

Um dicionário Python simples indexado por `session_id`:

```python
# store global: session_id → histórico de mensagens
_store: dict[str, InMemoryChatMessageHistory] = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in _store:
        _store[session_id] = InMemoryChatMessageHistory()
    return _store[session_id]
```

> Cada vez que chega uma mensagem nova, chamamos `get_session_history(session_id)`. Se a sessão não existe, cria; se existe, retorna o histórico já acumulado.

### 2.3 — O prompt

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "Você é um assistente de suporte de uma operadora de telecom. Responda de forma clara e objetiva."),
    MessagesPlaceholder("history"),   # ← aqui vai o histórico injetado automaticamente
    ("human", "{input}"),             # ← aqui vai a mensagem atual
])
```

`MessagesPlaceholder("history")` é o "slot" onde o LangChain injeta automaticamente as mensagens anteriores da sessão.

### 2.4 — Montar a chain com histórico

```python
llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)

chain = prompt | llm

chain_with_memory = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)
```

### 2.5 — Função pública que `main.py` vai chamar

```python
def chat(session_id: str, message: str) -> str:
    response = chain_with_memory.invoke(
        {"input": message},
        config={"configurable": {"session_id": session_id}},
    )
    return response.content
```

---

## Passo 3 — Criar o endpoint FastAPI (`app/main.py`)

### 3.1 — Importações e inicialização

```python
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()  # carrega o .env com as chaves de API

from app.agent import chat

app = FastAPI()
```

> `load_dotenv()` deve ser chamado **antes** de importar os módulos que usam as variáveis de ambiente.

### 3.2 — Modelos de request/response

```python
class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
```

### 3.3 — O endpoint

```python
@app.post("/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest) -> ChatResponse:
    resposta = chat(request.session_id, request.message)
    return ChatResponse(response=resposta)
```

---

## Passo 4 — Rodar o servidor

```bash
uvicorn app.main:app --reload
```

O `--reload` reinicia automaticamente quando você salva um arquivo — útil durante o desenvolvimento.

Você verá algo como:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

---

## Passo 5 — Testar a memória

Abra outro terminal e execute as duas chamadas abaixo na ordem:

**Primeira mensagem:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"u1\", \"message\": \"meu nome e Joao\"}"
```

**Segunda mensagem (mesma sessão):**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"u1\", \"message\": \"qual e o meu nome?\"}"
```

A segunda resposta deve mencionar "João". Se mencionar, a memória está funcionando.

**Teste de isolamento de sessão:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"u2\", \"message\": \"qual e o meu nome?\"}"
```

Sessão diferente (`u2`) não deve saber o nome — deve responder que não tem essa informação.

---

## Possíveis erros

| Erro | Causa provável | Solução |
|---|---|---|
| `AuthenticationError` | Chave de API inválida ou ausente | Verificar o `.env` e se `load_dotenv()` está sendo chamado |
| `ModuleNotFoundError: app.agent` | `__init__.py` faltando em `app/` | Criar o arquivo vazio |
| `422 Unprocessable Entity` | Body do request com campo errado | Conferir os nomes dos campos no JSON (`session_id`, `message`) |
| `ImportError: langchain_anthropic` | Pacote não instalado | `pip install langchain-anthropic` |

---

## Critério de conclusão

- [ ] Servidor sobe sem erros
- [ ] Endpoint `/chat` responde com `{ "response": "..." }`
- [ ] Segunda mensagem da mesma sessão lembra informação da primeira
- [ ] Sessão diferente **não** compartilha histórico

Quando todos os pontos estiverem marcados, avise para o code review da Etapa 1.
