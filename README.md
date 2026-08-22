# Agente de Suporte Telecom

Projeto prático vinculado à vaga **[Job-30157] Senior AI Developer — Telecom**.

**Contexto simulado:** chatbot de atendimento ao cliente de uma operadora de telecom que mantém histórico de conversa por sessão e consulta uma base de conhecimento local (planos, FAQ, tarifas) para responder perguntas.

---

## Arquitetura

```
POST /chat  { session_id, message } → { response }

FastAPI
  └── Agent ReAct (LangChain)
        ├── ConversationBufferMemory  (keyed por session_id)
        └── Tool: consultar_base_conhecimento → FAISS retriever

Knowledge Base (carregada na inicialização)
  docs/*.txt / *.pdf / *.csv → chunks → embeddings → FAISS
```

## Estrutura de Diretórios

```
agente-suporte-telecom/
├── app/
│   ├── main.py      # FastAPI + endpoint /chat
│   ├── agent.py     # Agente ReAct + memory store por session_id
│   ├── tools.py     # Tool: consultar_base_conhecimento
│   └── kb.py        # Carrega docs/ → FAISS vector store
├── docs/            # Base de conhecimento RAG (TXT, PDF, CSV)
├── .spec/           # Guias de implementação por etapa (mentoria)
├── requirements.txt
└── README.md
```

---

## Plano de Etapas

| # | Etapa | Foco |
|---|-------|------|
| 1 | FastAPI + LangChain com Memória | Chain simples com `ConversationBufferMemory` por sessão |
| 2 | Base de Conhecimento Local (RAG) | Document loaders → FAISS vector store |
| 3 | Agente ReAct + Tool de Consulta | Agente decide quando consultar os arquivos |
| 4 | Prompt Engineering — Persona Telecom | System prompt, restrições de domínio, tom de voz |
| 5 | Observabilidade com Langfuse | Traces, latência por step, avaliação de qualidade |

---

## Stack

- Python 3.11+
- FastAPI + Uvicorn
- LangChain (chains, agents, memory, document loaders)
- FAISS (vector store in-memory)
- Anthropic Claude (via LangChain)
- Langfuse (Etapa 5)
