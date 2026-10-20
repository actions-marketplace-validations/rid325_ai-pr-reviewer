FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY reviewbot/ /app/reviewbot/
COPY scripts/ /app/scripts/
RUN useradd --create-home --uid 10001 reviewbot && chown -R reviewbot:reviewbot /app

ENTRYPOINT ["python", "-m", "reviewbot.container_entrypoint"]
