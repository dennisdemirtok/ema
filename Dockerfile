# Multi-stage build: Node.js + Python for area processor
FROM node:20-slim AS base

# Install Python and system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY area-processor/requirements.txt ./area-processor/requirements.txt
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -r area-processor/requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

# Install Node.js dependencies
COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts

# Copy all source files
COPY . .

# Build Next.js
RUN npm run build

# Expose port
EXPOSE 3000

ENV NODE_ENV=production
ENV PORT=3000

CMD ["npm", "start"]
