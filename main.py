from fastapi import FastAPI, UploadFile, File
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
import shutil
import os

app = FastAPI()

# Initialize lightweight local embeddings and Cloud LLM
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
# Ensure you set GOOGLE_API_KEY in your deployment environment variables
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash") 

vectorstore = None

@app.post("/index-portfolio")
async def index_portfolio(file: UploadFile = File(...)):
    global vectorstore
    
    with open(file.filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    loader = PyPDFLoader(file.filename)
    docs = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = text_splitter.split_documents(docs)
    
    # FAISS is entirely in-memory, perfect for lightweight free hosting
    vectorstore = FAISS.from_documents(documents=splits, embedding=embeddings)
    return {"message": "Portfolio indexed successfully."}

@app.get("/ask")
async def ask_question(query: str):
    if not vectorstore:
        return {"error": "System not initialized. Upload documents first."}
    
    retriever = vectorstore.as_retriever()
    
    # System prompt to restrict hallucination
    system_prompt = (
        "You are an AI assistant answering questions about a candidate's portfolio. "
        "Use the provided context to answer. If you don't know, say so. "
        "\n\n"
        "{context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    
    response = rag_chain.invoke({"input": query})
    return {"answer": response["answer"]}