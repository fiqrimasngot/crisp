FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    HOST=0.0.0.0

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py inference.py project_model_best.keras ./
COPY templates ./templates

USER 65532:65532
EXPOSE 5000
CMD ["python", "app.py"]