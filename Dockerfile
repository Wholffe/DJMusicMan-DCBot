FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y ffmpeg curl unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"
RUN curl -fsSL https://deno.land/x/install/install.sh | sh

RUN python -m pip install --upgrade pip

COPY requirements.txt main.py ./
COPY music_bot/ ./music_bot/

RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir /data

VOLUME ["/data"]

ENV MAX_CACHE_FILES=100
ENV IDLE_TIMER=180
ENV UPDATE_ON_RESTART=true
ENV STARTUP_CHANNEL_ID=0

CMD ["sh", "-c", "if [ \"$UPDATE_ON_RESTART\" = \"true\" ]; then pip install --no-cache-dir --upgrade -r requirements.txt; fi && python3 /app/main.py"]