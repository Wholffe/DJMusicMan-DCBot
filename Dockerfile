FROM python:latest

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg

RUN python -m pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY music_bot/ /app/music_bot/
COPY main.py /app/

RUN mkdir /data
VOLUME ["/data"]

ENV MAX_CACHE_FILES=100
ENV IDLE_TIMER=180

CMD ["python", "main.py"]