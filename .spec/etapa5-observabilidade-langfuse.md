# Etapa 5 — Observabilidade com Langfuse

## Pré-requisito

Etapas 1 a 4 concluídas e aprovadas no code review.

## Objetivo

Instrumentar o agente com Langfuse para visualizar traces de execução, latência por step e avaliações de qualidade — o diferencial mais raro e valorizado do [Job-30157](../../../../.vagas/senior-ai-developer-telecom-job30157.md).

---

## Conceito: o que você vai ver no dashboard

Cada chamada ao `/chat` vai gerar um **trace** com:

```
Trace: mensagem "quais planos vocês têm?"  (latência total: 2.3s)
  ├── Span: RunnableWithMessageHistory     (latência: 2.2s)
  │     ├── Span: AgentExecutor            (latência: 2.1s)
  │     │     ├── Generation: ChatOpenAI   (tokens: 312, latência: 1.8s, custo: $0.0004)
  │     │     ├── Span: consultar_base_conhecimento  (latência: 0.1s)
  │     │     └── Generation: ChatOpenAI   (tokens: 180, latência: 0.2s)
  │     └── ...
  └── Score: relevancia = 0.9 (adicionado manualmente)
```

Para telecom com requisito de <2s de latência em voz, esse nível de detalhe é essencial para identificar onde o tempo está sendo gasto.

---

## Passo 1 — Criar conta e projeto no Langfuse

1. Acesse [cloud.langfuse.com](https://cloud.langfuse.com) e crie uma conta gratuita
2. Crie um novo **projeto** (ex: `agente-suporte-telecom`)
3. Vá em **Settings → API Keys** e crie um par de chaves
4. Copie o `Public Key` e o `Secret Key`

---

## Passo 2 — Configurar as chaves

Adicione ao `.env`:

```
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

Adicione ao `requirements.txt`:

```
langfuse
```

```bash
pip install langfuse
```

---

## Passo 3 — Integrar o CallbackHandler no agente

A integração mais simples com LangChain usa o `CallbackHandler`, que instrumenta automaticamente toda a execução sem precisar modificar a lógica existente.

### 3.1 — Criar o handler em `app/agent.py`

```python
from langfuse.langchain import CallbackHandler

def get_langfuse_handler(session_id: str, user_id: str | None = None):
    return CallbackHandler(
        session_id=session_id,    # agrupa traces da mesma conversa
        user_id=user_id,          # opcional: identifica o usuário
    )
```

### 3.2 — Passar o handler na chamada

Modifique a função `chat()`:

```python
def chat(session_id: str, message: str) -> str:
    langfuse_handler = get_langfuse_handler(session_id)

    response = chain_with_memory.invoke(
        {"input": message},
        config={
            "configurable": {"session_id": session_id},
            "callbacks": [langfuse_handler],     # ← adicionar aqui
        },
    )
    return response["output"]
```

Só isso. Os traces aparecem automaticamente no dashboard.

---

## Passo 4 — Verificar os traces no dashboard

1. Faça algumas chamadas ao `/chat` com perguntas variadas
2. Acesse o projeto no [cloud.langfuse.com](https://cloud.langfuse.com)
3. Clique em **Traces** no menu lateral

Você deve ver uma lista de traces, um por chamada. Clique em qualquer um para ver os spans aninhados, o conteúdo do prompt e da resposta, os tokens usados e a latência.

**O que observar:**
- Qual step é mais lento? (geralmente a `Generation` do LLM)
- Qual a latência total de ponta a ponta?
- A tool foi chamada? Quantas vezes?
- Qual foi o prompt enviado ao LLM (com o histórico injetado)?

---

## Passo 5 — Adicionar scores de qualidade

Scores permitem avaliar a qualidade das respostas. Você pode adicioná-los via API após a chamada.

### 5.1 — Obter o trace_id

O `CallbackHandler` expõe o ID do trace após a execução:

```python
def chat(session_id: str, message: str) -> tuple[str, str]:
    langfuse_handler = get_langfuse_handler(session_id)

    response = chain_with_memory.invoke(
        {"input": message},
        config={
            "configurable": {"session_id": session_id},
            "callbacks": [langfuse_handler],
        },
    )

    trace_id = langfuse_handler.get_trace_id()
    return response["output"], trace_id
```

### 5.2 — Endpoint para avaliar respostas

Adicione em `main.py` um endpoint para receber avaliações:

```python
from langfuse import Langfuse

langfuse_client = Langfuse()

class ScoreRequest(BaseModel):
    trace_id: str
    score: float         # 0.0 a 1.0
    comment: str = ""

@app.post("/score")
def add_score(request: ScoreRequest):
    langfuse_client.create_score(
        trace_id=request.trace_id,
        name="relevancia_resposta",
        value=request.score,
        comment=request.comment,
    )
    return {"status": "ok"}
```

### 5.3 — Atualizar o response do `/chat` para retornar o trace_id

```python
class ChatResponse(BaseModel):
    response: str
    trace_id: str        # ← adicionar campo

@app.post("/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest) -> ChatResponse:
    resposta, trace_id = chat(request.session_id, request.message)
    return ChatResponse(response=resposta, trace_id=trace_id)
```

---

## Passo 6 — Testar o fluxo completo de observabilidade

### Chamada ao chat:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"obs1\", \"message\": \"quais planos voces tem?\"}" | jq .
```

Anote o `trace_id` retornado.

### Adicionar avaliação manual:

```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d "{\"trace_id\": \"<id-do-trace>\", \"score\": 0.9, \"comment\": \"Resposta correta e completa\"}"
```

### Verificar no dashboard:

No Langfuse, abra o trace e confirme que o score aparece vinculado.

---

## Exploração adicional no dashboard

Após alguns testes, explore:

- **Sessions** — veja o histórico completo de uma conversa
- **Models** — custo total por modelo e por sessão
- **Metrics** — latência média ao longo do tempo
- Filtre traces onde a tool foi chamada vs. não foi chamada

---

## Critério de conclusão

- [ ] Traces aparecem no dashboard do Langfuse após chamadas ao `/chat`
- [ ] É possível ver os spans internos (AgentExecutor, Generation, tool call)
- [ ] Latência total e por step estão visíveis
- [ ] Score adicionado via `/score` aparece vinculado ao trace correto
- [ ] Pelo menos 3 conversas com perfis diferentes avaliadas no dashboard

Avise quando concluir para o code review final da Etapa 5 — e parabéns por completar o projeto!
