FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port
EXPOSE 3000

# Run Streamlit
CMD ["streamlit", "run", "main.py", "--server.port=3000", "--server.address=0.0.0.0", "--server.headless=true"]