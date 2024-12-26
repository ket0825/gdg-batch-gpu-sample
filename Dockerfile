FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY bert_inference.py .

CMD ["python3", "bert_inference.py"]