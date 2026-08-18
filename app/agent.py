from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# store global: session_id → histórico de mensagens
_store: dict[str, InMemoryChatMessageHistory] = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in _store:
        _store[session_id] = InMemoryChatMessageHistory()
    return _store[session_id]

prompt = ChatPromptTemplate.from_messages([
    ("system", "Você é um assistente de suporte de uma operadora de telecom. Responda de forma clara e objetiva."),
    MessagesPlaceholder("history"),   # ← aqui vai o histórico injetado automaticamente
    ("human", "{input}"),             # ← aqui vai a mensagem atual
])

llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)

chain = prompt | llm

chain_with_memory = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)

def chat(session_id: str, message: str) -> str:
    response = chain_with_memory.invoke(
        {"input": message},
        config={"configurable": {"session_id": session_id}},
    )
    return response.content
