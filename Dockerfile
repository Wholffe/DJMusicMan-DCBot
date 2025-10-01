FROM python:3.11-slim-bullseye

WORKDIR /app

RUN apt-get update \
    && apt-get install -y ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip

COPY requirements.txt main.py ./
COPY music_bot/ ./music_bot/

RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir /data

VOLUME ["/data"]

ENV MAX_CACHE_FILES=100
ENV IDLE_TIMER=180

CMD ["python3", "/app/main.py"]