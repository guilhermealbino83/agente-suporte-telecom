import os
from dotenv import load_dotenv
load_dotenv()

from app.kb import create_retriever

retriever = create_retriever()
results = retriever.invoke("plano família")

for doc in results:
    print("---")
    print(doc.page_content[:200])