FROM python:latest

WORKDIR /app

RUN python -m pip install --upgrade pip

RUN apt-get update

RUN apt-get install -y \
    ca-certificates \
    libssl-dev \
    curl

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY .env .
COPY main.py .
COPY musicbot.py .

CMD ["python", "main.py"]