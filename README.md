# FastAPI Microservices RAG System

A microservices-based application for document processing with RAG (Retrieval-Augmented Generation), featuring JWT authentication and role-based access control.

## Architecture

```
┌────────────┐     ┌────────────┐     ┌────────────┐
│            │     │            │     │            │
│  NGINX     │────▶│    Auth    │◀───▶│   Users    │
│  Gateway   │     │  Service   │     │  Service   │
│            │     │            │     │            │
└─────┬──────┘     └────────────┘     └────────────┘
      │
      │
      ▼
┌────────────┐
│            │
│    RAG     │
│  Service   │
│            │
└────────────┘
```

## RAG Pipeline

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│          │    │          │    │          │    │          │
│ Document │───▶│  Split   │───▶│ Vectorize│───▶│  Store   │
│  Upload  │    │  Text    │    │          │    │          │
│          │    │          │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                      │
                                                      ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│          │    │          │    │          │    │          │
│  Return  │◀───│ Generate │◀───│ Retrieve │◀───│  Query   │
│  Answer  │    │  Answer  │    │ Context  │    │          │
│          │    │          │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

## Services

- **Auth** (8000): Authentication & JWT management
- **Users** (8001): User profiles with Casbin RBAC
- **RAG** (8002): Document processing & retrieval

## Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.9+

### Quick Start
```bash
# Run with Docker
docker-compose up --build

# API endpoints available at:
# http://localhost:8000/api/...
```

## Documentation

- Swagger UI: `http://localhost:8000/docs`
- API endpoints:
  - `/api/auth/...`: Authentication
  - `/api/users/...`: User management
  - `/api/rag/...`: Document operations

## Environment

Key environment variables in `.env` files:
- `DATABASE_URL`: SQLite connection string
- `SECRET_KEY`: JWT signing key
- `AUTH_SERVICE_URL`: Auth service location
- `GROQ_API_KEY`: For RAG service

## Deployment

Configuration for Azure Container Apps included in `azure-deploy.yml`.

## License

MIT
