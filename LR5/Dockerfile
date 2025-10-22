FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY glossary.proto .
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. glossary.proto

COPY server.py .
COPY rest_server.py .
COPY client.py .
COPY glossary_data.json .

EXPOSE 50051
EXPOSE 5000

CMD ["python", "rest_server.py"]