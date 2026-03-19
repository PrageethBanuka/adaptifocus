FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory
RUN mkdir -p data/models

# Production defaults
ENV DEV_MODE=0
ENV PORT=8000

EXPOSE ${PORT}

CMD /bin/bash -c "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
