FROM node:22-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN python3 -m venv /opt/venv \
    && pip install --no-cache-dir -r requirements.txt

COPY node-service/package.json node-service/package-lock.json ./node-service/
RUN npm ci --prefix node-service --omit=dev

COPY . .
RUN SECRET_KEY=container-build-only DEBUG=False DATABASE_URL=sqlite:////tmp/unwind-build.sqlite3 \
    python manage.py collectstatic --noinput

EXPOSE 10000
CMD ["node", "node-service/src/launch.js"]
