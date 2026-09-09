# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build essentials if compiling native dependencies (like uvloop)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies into a local directory
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime environment
FROM python:3.11-slim AS runner

WORKDIR /app

# Create a non-root user for security best practices
RUN useradd -u 1000 fixuser && chown -R fixuser:fixuser /app
USER fixuser

# Copy installed python packages from builder stage
COPY --from=builder /root/.local /home/fixuser/.local
ENV PATH=/home/fixuser/.local/bin:$PATH

# Copy application source code
COPY --chown=fixuser:fixuser . .

# Expose the FIX gateway TCP port (e.g., 9801)
EXPOSE 9801

# Run the gateway application entry point
CMD ["python", "main.py"]
