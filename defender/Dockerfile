FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY defender/main.py /app/defender/main.py
COPY defender/__init__.py /app/defender/__init__.py
COPY anomaly_detection /app/anomaly_detection

ENV DEFENDER_DB=/app/events.db
ENV ORIGIN=http://host.docker.internal:8000

EXPOSE 8080

CMD ["uvicorn", "defender.main:app", "--host", "0.0.0.0", "--port", "8080"]

