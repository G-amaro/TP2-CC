FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    iproute2 \
    net-tools \
    iputils-ping \
    vim \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
CMD ["tail", "-f", "/dev/null"]
