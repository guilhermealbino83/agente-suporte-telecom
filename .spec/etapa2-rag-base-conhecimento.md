# Etapa 2 — Base de Conhecimento Local (RAG)

## Pré-requisito

Etapa 1 concluída e aprovada no code review.

## Objetivo

Carregar arquivos locais da pasta `docs/` e disponibilizá-los como base de conhecimento pesquisável por similaridade semântica (RAG = Retrieval-Augmented Generation).

---

## Conceito: como RAG funciona

```
INGESTÃO (roda uma vez na inicialização)
  arquivo.txt → [Document Loader] → texto bruto
  texto bruto → [Text Splitter]  → chunks (pedaços menores)
  chunks      → [Embeddings]     → vetores numéricos
  vetores     → [FAISS]          → índice pesquisável

RETRIEVAL (roda a cada pergunta)
  pergunta → [Embeddings]  → vetor da pergunta
  vetor    → [FAISS.search] → N chunks mais parecidos semanticamente
  chunks   → contexto para o LLM responder
```

**Por que dividir em chunks?** LLMs têm limite de contexto. Um PDF de 50 páginas não cabe inteiro no prompt. Você busca só as 3-5 partes mais relevantes para a pergunta.

---

## Passo 1 — Instalar dependências adicionais

Adicione ao `requirements.txt`:

```
faiss-cpu
langchain-community
langchain-huggingface
sentence-transformers
pypdf
```

- `faiss-cpu` — vector store local (busca por similaridade)
- `langchain-community` — document loaders (TextLoader, PyPDFLoader, CSVLoader)
- `langchain-huggingface` — integração com modelos de embedding locais
- `sentence-transformers` — modelo de embedding que roda na sua máquina, **sem API key**
- `pypdf` — leitura de PDFs

```bash
pip install faiss-cpu langchain-community langchain-huggingface sentence-transformers pypdf
```

> **Por que HuggingFace para embeddings?** Anthropic não oferece API de embeddings — apenas modelos de chat. A alternativa mais simples é usar modelos locais via `sentence-transformers`, que baixam o modelo uma vez (~90MB) e rodam offline. Para produção, você poderia usar Cohere ou Voyage AI, mas para o projeto de estudo o modelo local é suficiente e gratuito.

---

## Passo 2 — Criar arquivos fictícios de conhecimento

Crie arquivos na pasta `docs/` com conteúdo fictício de uma operadora. Esses arquivos simulam a base de conhecimento do chatbot.

**`docs/planos.txt`** — exemplo de conteúdo:

```
PLANO FAMÍLIA CONECTA
Valor: R$ 149,90/mês
Inclui: 4 linhas com 20GB cada, ligações ilimitadas entre as linhas do plano.
Benefícios: 1 app de streaming incluído, Wi-Fi Calling, portabilidade gratuita.
Fidelidade: 12 meses. Após fidelidade, sem multa de cancelamento.

PLANO INDIVIDUAL TURBO
Valor: R$ 69,90/mês
Inclui: 30GB de dados, ligações ilimitadas para qualquer operadora.
Benefícios: Sem fidelidade, chip eSIM disponível.
```

**`docs/faq.txt`** — exemplo de conteúdo:

```
COMO FAZER PORTABILIDADE?
Para trazer seu número para nossa operadora: acesse o app, vá em "Portabilidade",
insira seu número atual e aguarde até 3 dias úteis. Serviço gratuito.

COMO VERIFICAR MEU CONSUMO?
Acesse o app na seção "Meu Plano" ou disque *100# e tecle call.

O QUE FAZER SE A INTERNET PAROU?
1. Verifique se os dados móveis estão ativados nas configurações do celular.
2. Reinicie o dispositivo.
3. Se persistir, ligue 1056 (suporte técnico 24h).
```

> Crie pelo menos 2 arquivos `.txt`. PDFs e CSVs funcionam também mas exigem mais configuração — comece com TXT.

---

## Passo 3 — Criar o módulo `app/kb.py`

Este módulo é responsável por carregar os arquivos e construir o índice FAISS.

### 3.1 — Importações

```python
from pathlib import Path
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
```

### 3.2 — Carregar todos os TXTs da pasta `docs/`

```python
DOCS_DIR = Path(__file__).parent.parent / "docs"

def load_documents():
    loader = DirectoryLoader(
        str(DOCS_DIR),
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    return loader.load()
```

> `DirectoryLoader` lê todos os arquivos que casam com o `glob`. Para adicionar PDFs depois, basta mudar o `glob` para `**/*.pdf` e o `loader_cls` para `PyPDFLoader`.

### 3.3 — Dividir em chunks

```python
def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,       # máximo de caracteres por chunk
        chunk_overlap=50,     # sobreposição entre chunks contíguos
    )
    return splitter.split_documents(documents)
```

**Por que `chunk_overlap`?** Evita que uma informação seja cortada no meio e perdida. Um overlap de 50 caracteres garante que os chunks vizinhos compartilhem contexto.

### 3.4 — Criar o índice FAISS

```python
def build_vectorstore(chunks):
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    return FAISS.from_documents(chunks, embeddings)
```

> Na primeira execução, o modelo `all-MiniLM-L6-v2` (~90MB) é baixado automaticamente e salvo em cache local. Nas execuções seguintes, carrega do cache sem internet.

### 3.5 — Função principal que inicializa tudo

```python
def create_retriever():
    documents = load_documents()
    chunks = split_documents(documents)
    vectorstore = build_vectorstore(chunks)
    return vectorstore.as_retriever(search_kwargs={"k": 3})
```

`k=3` significa "retorna os 3 chunks mais similares à pergunta".

---

## Passo 4 — Inicializar o retriever junto com o servidor

No `app/main.py`, inicialize o retriever uma única vez ao subir o servidor. Use os **lifespan events** do FastAPI:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.kb import create_retriever

retriever = None  # variável global

@asynccontextmanager
async def lifespan(app: FastAPI):
    global retriever
    print("Carregando base de conhecimento...")
    retriever = create_retriever()
    print("Base carregada!")
    yield  # servidor fica rodando aqui
    # limpeza ao desligar (se necessário)

app = FastAPI(lifespan=lifespan)
```

> **Por que lifespan?** É a forma moderna do FastAPI de rodar código na inicialização. O `retriever` é carregado uma vez e fica em memória — eficiente para múltiplas requisições.

---

## Passo 5 — Testar o retriever isoladamente

Antes de integrá-lo ao chat, teste se está funcionando com um script simples:

Crie `tests/test_kb.py` (ou rode no terminal Python interativo):

```python
import os
from dotenv import load_dotenv
load_dotenv()

from app.kb import create_retriever

retriever = create_retriever()
results = retriever.invoke("plano família")

for doc in results:
    print("---")
    print(doc.page_content[:200])
```

Se retornar trechos dos seus arquivos `.txt` sobre "plano família", o RAG está funcionando.

---

## Critério de conclusão

- [ ] `create_retriever()` executa sem erros ao subir o servidor
- [ ] `retriever.invoke("alguma pergunta")` retorna chunks relevantes dos seus arquivos
- [ ] Servidor ainda responde no `/chat` normalmente (a integração com o chat fica na Etapa 3)

Quando esses pontos estiverem prontos, avise para o code review da Etapa 2.
