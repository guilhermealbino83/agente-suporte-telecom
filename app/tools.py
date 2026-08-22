from langchain_core.tools import tool
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
