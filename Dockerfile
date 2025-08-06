# Use a slim Python base image
FROM python:3.11-slim

# Install system deps (if any APIs need SSL / locale stuff)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Prepare workspace
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source
COPY . .

# Tell Fly.io which port the app listens on
EXPOSE 8080
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
