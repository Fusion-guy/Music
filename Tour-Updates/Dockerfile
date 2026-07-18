FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Data-map voor de SQLite dedup-database (wordt gemount als volume).
RUN mkdir -p /app/data

CMD ["python", "main.py"]
