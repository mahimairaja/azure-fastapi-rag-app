FROM python:3.10-slim

WORKDIR /app

# Fix the GPG key issue by using trusted keyring approach
RUN apt-get update -y || true && \
    apt-get install -y --no-install-recommends curl gnupg && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/trusted.gpg.d/nodesource.gpg && \
    apt-get update -y || true && \
    apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    gcc \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

# Create directories for data, storage, and logs
RUN mkdir -p data storage/documents storage/embeddings storage/chroma_db

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"] 