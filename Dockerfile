FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p uploads
EXPOSE 10000
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --timeout 120"]
