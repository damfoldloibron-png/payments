FROM python:3.13-slim
WORKDIR /payment_service

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONPATH=/payment_service/src
