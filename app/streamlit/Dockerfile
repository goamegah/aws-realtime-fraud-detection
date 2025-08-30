# Dockerfile
FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Exposed port
EXPOSE 8501

# Launch app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]