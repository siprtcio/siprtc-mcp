FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY test_app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY test_app /app/test_app
COPY .chainlit /app/.chainlit
COPY public /app/public

RUN useradd --system --uid 10001 --create-home --shell /usr/sbin/nologin app \
    && chown -R app /app
USER 10001

CMD ["chainlit", "run", "test_app/chainlit_app.py", "--host", "0.0.0.0", "--port", "8501"]
