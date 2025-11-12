FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY gateway/proxy.py /app/gateway/proxy.py
COPY gateway/__init__.py /app/gateway/__init__.py

ENV DEFENDER_URL=http://defender:8080/v1/decide
ENV ORIGIN=http://host.docker.internal:8000

EXPOSE 8085

CMD ["python", "gateway/proxy.py"]

