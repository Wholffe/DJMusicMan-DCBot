FROM python:latest

WORKDIR /app

RUN python -m pip install --upgrade pip

RUN apt-get update && \
    apt-get install -y \
    ca-certificates \
    libssl-dev \
    curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY .env .
COPY music_bot .
COPY main .

CMD ["python", "main.py"]