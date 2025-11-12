FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn

# Copy application
COPY . /app/aegismas/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Run application
CMD ["python", "-m", "uvicorn", "aegismas.main:app", "--host", "0.0.0.0", "--port", "8080"]

