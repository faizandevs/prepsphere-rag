ARCHITECTURE.md
System Architecture Overview
Problem Statement
Render has strict memory and CPU limits. A monolithic RAG application with Pinecone client, LangChain, embeddings, and Gemini API exceeded these constraints, causing deployment failures.
Solution: Microservice Architecture
Split the application into two services:
┌──────────────────┐
│ User/Client │
└────────┬─────────┘
│ HTTP Request
▼
┌──────────────────────────────────┐
│ THIN FORWARDER (Render) │
│ - FastAPI (minimal deps) │
│ - Request validation │
│ - Token authentication │
│ - Proxy to EC2 │
└────────┬─────────────────────────┘
│ Forward request
▼
┌──────────────────────────────────┐
│ HEAVY BACKEND (AWS EC2) │
│ - Pinecone vector DB │
│ - LangChain RAG chain │
│ - Sentence Transformers │
│ - Gemini 2.5 Flash LLM │
│ - Complex inference │
└────────┬─────────────────────────┘
│ Return response
▼
┌──────────────────────────────────┐
│ Response to User │
└──────────────────────────────────┘
Data Pipeline
Raw PDFs (6-7 books, 800+ pages)
│
▼
┌──────────────────────────────┐
│ PDF Extraction Pipeline │
│ - PDFPlumber (text extraction)
│ - PyPDF2 (metadata) │
│ - OCR (for scanned PDFs) │
│ - Manual text refinement │
└──────────────────────────────┘
│
▼
Extracted Text Files (6-7 TXT files)
│
▼
┌──────────────────────────────┐
│ Text Processing │
│ - Chunking (overlap strategy)│
│ - Cleaning (normalize text) │
└──────────────────────────────┘
│
▼
┌──────────────────────────────┐
│ Embedding Generation │
│ Model: sentence-transformers │
│ (all-MiniLM-L6-v2) │
└──────────────────────────────┘
│
▼
Pinecone Vector Database
(Stores embeddings + metadata)
Service Details
Thin Forwarder (Render)
Purpose: Lightweight API gateway
Technology:

FastAPI (minimal framework)
Python 3.11
Requirements: ~100MB

Responsibilities:

Receive user requests
Validate input format
Authentication (bearer token)
Forward to EC2
Return responses

Deployment:

Platform: Render.com
Auto-deploy from GitHub push
Free/Starter tier possible

Endpoint:
POST /chat
Content-Type: application/json
{
"question": "user query"
}
Heavy Backend (AWS EC2)
Purpose: RAG processing and inference
Technology:

FastAPI
LangChain (RAG chains)
Pinecone (vector DB client)
Sentence Transformers (embeddings)
Google Generative AI (Gemini)
Python 3.11

Responsibilities:

Vector similarity search in Pinecone
RAG chain orchestration
LLM inference with Gemini
Context retrieval and augmentation
Complex prompt engineering

Deployment:

Platform: AWS EC2 (t3.medium or larger)
OS: Ubuntu 22.04
Process Manager: systemd
Auto-start on reboot: Yes

Endpoint:
POST /chat
Authorization: Bearer <token>
Content-Type: application/json
{
"question": "user query"
}
Why This Architecture Works
AspectThin ForwarderHeavy BackendMemory~50MB~500MB+CPUMinimalHigh (inference)Latency<100ms2-5s (Gemini)CostFree/cheapSmall EC2 instanceScalingAuto-scale on RenderManual EC2 sizingCold Start30-50sN/A (always on)
Authentication Flow
Client Request
│
├─→ Bearer Token Check (Thin Forwarder)
│
├─→ Forward to EC2
│
├─→ FORWARDER_TOKEN Check (EC2)
│
├─→ Process with RAG
│
└─→ Return Response
Data Security

API keys in .env (never committed)
Bearer tokens for inter-service auth
No sensitive data in logs
Pinecone API key secured on EC2

Performance Metrics

Thin Forwarder Response: <500ms (with network)
Heavy Backend Processing: 2-5s (includes Gemini API call)
Vector Retrieval: <200ms (Pinecone)
Total End-to-End: 3-6s per query
