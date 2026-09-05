FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py README.md ./
COPY templates templates
COPY static static

RUN useradd --create-home --uid 10001 appuser \
    && mkdir /data \
    && chown appuser:appuser /data

USER appuser
ENV PASTEBIN_DATABASE=/data/pastes.db
EXPOSE 5000

CMD ["python", "app.py"]
