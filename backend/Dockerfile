FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data for tokenization
RUN python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/uploads 

EXPOSE 5000

CMD ["python", "-m", "flask", "--app", "app:create_app", "run", "--host", "0.0.0.0", "--port", "5000"]

