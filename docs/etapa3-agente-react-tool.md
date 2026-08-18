# Etapa 3 — Agente ReAct + Tool de Consulta

## Pré-requisito

Etapas 1 e 2 concluídas e aprovadas no code review.

## Objetivo

Substituir a chain simples da Etapa 1 por um **Agente ReAct**: um loop onde o LLM decide, turno a turno, se precisa consultar a base de conhecimento ou se consegue responder com o próprio conhecimento.

---

## Conceito: o padrão ReAct

ReAct = **Re**asoning + **Act**ing. O agente age em um loop:

```
[Pergunta do usuário]
        ↓
Thought: o LLM raciocina sobre o que precisa fazer
        ↓
Action: chama uma tool (ex: consultar_base_conhecimento)
        ↓
Observation: recebe o resultado da tool
        ↓
Thought: raciocina com base no resultado
        ↓
Final Answer: responde ao usuário
```

Se o LLM considerar que já sabe a resposta, pula direto para `Final Answer` sem chamar nenhuma tool.

---

## Passo 1 — Criar o módulo `app/tools.py`

Este módulo define a tool que o agente pode invocar.

### 1.1 — Importações

```python
from langchain_core.tools import tool
```

### 1.2 — Definir a tool

```python
from app.kb import create_retriever

_retriever = None

def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = create_retriever()
    return _retriever

@tool
def consultar_base_conhecimento(query: str) -> str:
    """
    Busca informações sobre planos, tarifas, FAQ e procedimentos da operadora.
    Use quando o usuário perguntar sobre planos, preços, portabilidade, consumo
    ou qualquer informação específica da operadora.
    """
    retriever = get_retriever()
    docs = retriever.invoke(query)
    if not docs:
        return "Nenhuma informação encontrada na base de conhecimento."
    return "\n\n".join(doc.page_content for doc in docs)
```

> **A descrição da tool é crítica.** O LLM usa esse texto para decidir *quando* chamar a tool. Seja específico: liste os casos de uso. Uma descrição vaga resulta em tool sendo ignorada ou chamada desnecessariamente.

---

## Passo 2 — Atualizar `app/agent.py` para usar agente ReAct

### 2.1 — Importações adicionais

```python
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain import hub
from app.tools import consultar_base_conhecimento
```

### 2.2 — O prompt do agente ReAct

O agente ReAct exige um formato de prompt específico com variáveis `{tools}`, `{tool_names}`, `{agent_scratchpad}`. A forma mais simples é usar o prompt padrão do LangChain Hub:

```python
react_prompt = hub.pull("hwchase17/react")
```

> **Se não quiser usar o hub** (requer internet toda vez), você pode baixar o template uma vez, salvar como string no código e usar `PromptTemplate.from_template(...)`. O hub é conveniente para começar.

### 2.3 — Criar o agente

```python
tools = [consultar_base_conhecimento]

agent = create_react_agent(llm, tools, react_prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,          # exibe o raciocínio no terminal — muito útil para debug
    handle_parsing_errors=True,  # evita crash por output malformado do LLM
    max_iterations=5,      # evita loop infinito
)
```

### 2.4 — Adaptar o `RunnableWithMessageHistory`

O `AgentExecutor` recebe `input` e `chat_history` (não mais `history`). Atualize a criação do chain com memória:

```python
chain_with_memory = RunnableWithMessageHistory(
    agent_executor,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",   # ← nome mudou
)
```

E a função `chat()`:

```python
def chat(session_id: str, message: str) -> str:
    response = chain_with_memory.invoke(
        {"input": message},
        config={"configurable": {"session_id": session_id}},
    )
    return response["output"]   # ← AgentExecutor retorna dict, não AIMessage
```

---

## Passo 3 — Inicialização no servidor

O `retriever` agora pode ser inicializado dentro do `tools.py` (lazy, na primeira chamada) ou via lifespan. Para garantir que o FAISS não seja recriado a cada requisição, pré-aqueça no lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.tools import get_retriever
    print("Pré-carregando base de conhecimento...")
    get_retriever()   # força inicialização antes de aceitar requisições
    print("Pronto.")
    yield
```

---

## Passo 4 — Testar os dois comportamentos do agente

### Cenário 1: pergunta sobre conteúdo dos arquivos (deve usar a tool)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"t1\", \"message\": \"quais planos voces tem?\"}"
```

No terminal do servidor (com `verbose=True`), você verá:

```
Thought: Preciso consultar a base de conhecimento para responder sobre planos.
Action: consultar_base_conhecimento
Action Input: planos disponíveis
Observation: PLANO FAMÍLIA CONECTA...
Thought: Tenho a informação. Posso responder.
Final Answer: Temos dois planos disponíveis...
```

### Cenário 2: pergunta genérica (não deve usar a tool)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"t2\", \"message\": \"oi, tudo bem?\"}"
```

O agente deve responder diretamente, sem invocar a tool.

### Cenário 3: memória + tool combinadas

```bash
# mensagem 1
curl -X POST http://localhost:8000/chat \
  -d "{\"session_id\": \"t3\", \"message\": \"me chamo Ana\"}"

# mensagem 2
curl -X POST http://localhost:8000/chat \
  -d "{\"session_id\": \"t3\", \"message\": \"qual plano voce recomenda para mim, Ana?\"}"
```

O agente deve lembrar o nome e buscar planos na base.

---

## Possíveis problemas

| Problema | Causa | Solução |
|---|---|---|
| Agente nunca chama a tool | Descrição da tool muito vaga | Reescrever a docstring com casos de uso específicos |
| `OutputParserException` | LLM gerou formato ReAct inválido | `handle_parsing_errors=True` já trata; se persistir, ajustar prompt |
| Agente chama a tool para tudo | Descrição muito ampla | Restringir a docstring a domínio específico (telecom) |
| `KeyError: 'output'` | `response` não é dict | Verificar se o `AgentExecutor` está sendo usado (não `chain`) |

---

## Critério de conclusão

- [ ] Pergunta sobre planos/tarifas → agente invoca `consultar_base_conhecimento`
- [ ] Saudação simples → agente responde sem invocar tool
- [ ] Agente ainda lembra contexto da sessão (memória da Etapa 1 preservada)
- [ ] `verbose=True` mostra o raciocínio no terminal

Avise quando concluir para o code review da Etapa 3.
