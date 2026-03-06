# Prepsphere RAG Chatbot

A production-grade RAG (Retrieval Augmented Generation) chatbot system using Google Gemini, deployed across AWS EC2 and Render for my Final Year Project which was an android app. 

## System Architecture

```
User → Render (Thin Forwarder) → AWS EC2 (Heavy Backend) → Gemini API
```

- **Thin Forwarder** (Render): Lightweight API gateway for user requests
- **Heavy Backend** (EC2): RAG processing with Pinecone vector DB
- **Data Pipeline**: PDF extraction with OCR + text processing

## Quick Start

### For Development

1. See `heavy_backend/README.md` for EC2 setup
2. See `thin_forwarder/README.md` for Render setup
3. See `docs/ARCHITECTURE.md` for system overview

### For Deployment

- Heavy Backend: EC2 instance + `bootstrap.sh`
- Thin Forwarder: Render + GitHub integration
- Data: Extract texts using `data/extraction_scripts/pdf_extraction.py`

## Tech Stack

- **LLM**: Google Gemini 2.5 Flash
- **Vector DB**: Pinecone
- **Framework**: FastAPI + LangChain
- **Embeddings**: Sentence Transformers
- **Hosting**: AWS EC2 + Render
- **Data Processing**: PDFPlumber, PyPDF2, OCR

## File Structure

```
heavy_backend/     - RAG logic, vector retrieval (EC2)
thin_forwarder/    - API gateway, request forwarding (Render)
data/              - PDFs, extracted texts, extraction scripts
docs/              - Architecture & deployment guides
```

## Key Features

✅ Distributed architecture (heavy lifting on EC2, API on Render)
✅ RAG with 800+ pages of English books
✅ Automated PDF text extraction with OCR
✅ Vector similarity search with Pinecone
✅ Production-ready with systemd service management

## Resume Highlights

- Designed microservice architecture to overcome Render memory limits
- Implemented PDF extraction pipeline with OCR for scanned documents
- Built scalable RAG system with 800+ pages of learning material
- Deployed across AWS EC2 and Render with CI/CD via GitHub

---

For detailed deployment instructions, see respective README files.
