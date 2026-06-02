FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api.py demo.py ./

EXPOSE 5000

# gunicorn for a real server. Workers default to 2; the demo runs with 1 so its
# in-memory store stays consistent (see docker-compose.yml).
CMD ["sh", "-c", "gunicorn -w ${GUNICORN_WORKERS:-2} -b 0.0.0.0:5000 --timeout 60 api:app"]
