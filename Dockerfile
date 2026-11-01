# CEFR-aligned placement test: Streamlit app with SQLite data on a volume.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml requirements.txt ./
COPY src ./src
RUN pip install -r requirements.txt
COPY . .

# data/ holds placement.db and secret.key. Mount a volume here or every
# container restart loses all sessions and the email-hashing key.
VOLUME ["/app/data/runtime"]
ENV PLACEMENT_DB=/app/data/runtime/placement.db \
    PLACEMENT_KEY=/app/data/runtime/secret.key

EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
