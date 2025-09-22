FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Create data directory for database and make it writable
RUN mkdir -p /app/data && chmod 777 /app/data

# Copy app source
COPY . .

# Persist database directory
VOLUME ["/app/data"]

# Default command
CMD ["python", "src/app.py"]