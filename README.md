# FastAPI Microservices with Casbin RBAC for Azure

This project implements a set of microservices for user management and document processing with Retrieval-Augmented Generation (RAG). It uses FastAPI, SQLAlchemy, JWT authentication, and Casbin for role-based access control.

## Microservices

The application is split into three microservices:

1. **Auth Service** (Port 8000): Handles user authentication and JWT management
2. **Users Service** (Port 8001): Manages user profiles with Casbin RBAC
3. **RAG Service** (Port 8002): Provides document processing and retrieval functionality

## Key Features

- **JWT-based Authentication**: Secure token-based authentication system
- **Casbin RBAC**: Fine-grained role-based access control
- **Document Processing**: Upload, process, and retrieve documents
- **Microservices Architecture**: Each service operates independently
- **Azure Deployment Ready**: Configuration for deploying to Azure Container Apps

## Local Development

### Prerequisites

- Docker and Docker Compose
- Python 3.9+

### Running Locally with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Access services at:
# - Auth Service: http://localhost:8000
# - Users Service: http://localhost:8001
# - RAG Service: http://localhost:8002
```

### Running Individual Services

```bash
# Auth Service
cd auth-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Users Service
cd users-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001

# RAG Service
cd rag-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

## API Documentation

Each service provides its own Swagger documentation:

- Auth Service: http://localhost:8000/docs
- Users Service: http://localhost:8001/docs
- RAG Service: http://localhost:8002/docs

## Azure Deployment

This project includes Azure deployment configuration using Azure Container Apps.

### Deployment Steps

1. Create Azure Container Registry
2. Set up GitHub Secrets for the deployment workflow
3. Run the GitHub Action workflow
4. Configure API Gateway in Azure to route requests to the appropriate services

See the `azure-deploy.yml` file for detailed deployment configuration.

## Environment Variables

### Auth Service
- `DATABASE_URL`: Database connection string
- `SECRET_KEY`: Secret key for JWT signing

### Users Service
- `DATABASE_URL`: Database connection string
- `AUTH_SERVICE_URL`: URL of the Auth Service

### RAG Service
- `DATABASE_URL`: Database connection string
- `AUTH_SERVICE_URL`: URL of the Auth Service

## License

MIT
