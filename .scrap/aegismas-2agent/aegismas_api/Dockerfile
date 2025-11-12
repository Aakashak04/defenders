FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application - maintain package structure
COPY . /app/aegismas_api

# Create models directory
RUN mkdir -p /app/aegismas_api/models

# Set PYTHONPATH to include /app so we can import aegismas_api
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Run application - use the module path that matches the file structure
CMD ["python", "-m", "uvicorn", "aegismas_api.main:app", "--host", "0.0.0.0", "--port", "8080"]

