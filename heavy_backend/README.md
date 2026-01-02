# Heavy Backend - RAG Processing

Runs on AWS EC2. Handles vector DB operations, LLM inference, and complex RAG logic.

## Setup

1. Launch EC2 instance (Ubuntu 22.04, t3.medium or larger)
2. Run bootstrap script:

```bash
   bash bootstrap.sh
```

3. Add `.env` with API keys
4. Service auto-starts: `systemctl status myrag`

## API Endpoint

POST `/chat` - RAG query processing

See main.py for full details.
