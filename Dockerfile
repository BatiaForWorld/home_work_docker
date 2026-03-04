FROM python:3.13.5

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DATABASE_URL=postgres://user:password@host:port/dbname \
    SECRET_KEY=mysecretkey \
    DEBUG=False

EXPOSE 8000
