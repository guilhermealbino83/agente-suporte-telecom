from pathlib import Path
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

DOCS_DIR = Path(__file__).parent.parent / "docs"

def load_documents():
    loader = DirectoryLoader(
        str(DOCS_DIR),
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    return loader.load()

def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,       # máximo de caracteres por chunk
        chunk_overlap=50,     # sobreposição entre chunks contíguos
    )
    return splitter.split_documents(documents)

def build_vectorstore(chunks):
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    return FAISS.from_documents(chunks, embeddings)

def create_retriever():
    documents = load_documents()
    chunks = split_documents(documents)
    vectorstore = build_vectorstore(chunks)
    return vectorstore.as_retriever(search_kwargs={"k": 3})

