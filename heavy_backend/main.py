from fastapi import FastAPI, Request, HTTPException, status
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

# ============================
# 1️⃣ ENVIRONMENT / API KEYS
# ============================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("INDEX_NAME", "chatbot-rag")
FORWARDER_TOKEN = os.getenv("FORWARDER_TOKEN")  # Token for thin forwarder

if not GEMINI_API_KEY or not PINECONE_API_KEY or not INDEX_NAME:
    raise ValueError("❌ Missing environment variables.")

# ============================
# 2️⃣ LAZY INITIALIZATION (YOUR WORKING CODE)
# ============================

_qa_chain = None  # Global cache for QA chain

def get_qa_chain():
    """Initialize QA chain only on first request (lazy loading)"""
    global _qa_chain
    
    if _qa_chain is not None:
        return _qa_chain
    
    print("⏳ Initializing RAG chain on first request...")
    
    from pinecone import Pinecone
    from langchain_pinecone import Pinecone
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.chains import RetrievalQA
    
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
    os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
    
    # Initialize Pinecone
    
    
    # Initialize embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    
    # Initialize vector store
    vectorstore = Pinecone.from_existing_index(
    index_name=INDEX_NAME,
    embedding=embeddings,
    text_key="text"
)
    # Initialize LLM
    llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.1,
    api_key=GEMINI_API_KEY,
    convert_system_message_to_human=True,
    system_instruction="""You are Prepsphere AI, a helpful academic assistant.
Use only the information retrieved from the context to answer questions. 
If the context does not contain enough information, reply: "I don't know."
If the user asks anything unrelated to studies, academics, exams, or general knowledge, reply:
"I'm not trained to answer this type of question."
Keep responses clear."""
)
    
    # Create QA chain
    _qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 4})
    )
    
    print("✅ RAG chain initialized!")
    return _qa_chain

# ============================
# 3️⃣ FASTAPI APP
# ============================

app = FastAPI(title="Prepsphere AI - Heavy Backend")

class ChatInput(BaseModel):
    question: str

@app.get("/")
def home():
    return {"status": "ok", "message": "Prepsphere AI - RAG API Ready"}

@app.get("/health")
def health_check():
    """Health check endpoint (doesn't initialize RAG)"""
    return {"status": "healthy"}

def check_forwarder_token(request: Request):
    """Optional bearer token check for thin forwarder"""
    if not FORWARDER_TOKEN:
        return  # Token checking disabled if not set
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    if token != FORWARDER_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

@app.post("/chat")
async def chat(request: Request, data: ChatInput):
    """Chat endpoint - initializes RAG on first request"""
    # Verify token if set
    try:
        check_forwarder_token(request)
    except HTTPException as exc:
        raise exc
    
    try:
        qa = get_qa_chain()  # Lazy load on first request
        response = qa.invoke(data.question)
        return {"answer": response["result"]}
    except Exception as e:
        return {"error": str(e), "answer": "An error occurred processing your question."}