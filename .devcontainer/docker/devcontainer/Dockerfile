
FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04


RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get update -y \
    && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git \
    make \
    libc6-dev \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    python3-numpy

RUN cd /usr/local/src && \
    curl -L -O https://go.dev/dl/go1.24.3.linux-amd64.tar.gz && \
    rm -rf /usr/local/go && tar -C /usr/local -xzf go1.24.3.linux-amd64.tar.gz && \
    rm go1.24.3.linux-amd64.tar.gz

ENV PATH="/usr/local/go/bin:/usr/local/src/cfssl/bin:$PATH"

RUN cd /usr/local/src && \
    git clone https://github.com/cloudflare/cfssl.git && \
    cd cfssl && \
    make && \
    make install

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

USER vscode