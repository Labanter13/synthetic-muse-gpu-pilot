# Experimental GPU container: must be validated on a real RTX 4090 before production.
FROM nvidia/cuda:13.0.2-devel-ubuntu24.04
ENV DEBIAN_FRONTEND=noninteractive KANDINSKY_HOME=/workspace/cache UV_PYTHON=3.13
RUN apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates ffmpeg python3 python3-venv python3-pip build-essential pkg-config && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && curl -fsSL https://github.com/casey/just/releases/download/1.43.1/just-1.43.1-x86_64-unknown-linux-musl.tar.gz | tar -xz -C /usr/local/bin just
ENV PATH=/root/.local/bin:$PATH
WORKDIR /opt
RUN git clone --depth=1 https://github.com/kandinskylab/kandinsky-6.git
WORKDIR /opt/kandinsky-6
COPY scripts /opt/synthetic/scripts
COPY service /opt/synthetic/service
RUN chmod +x /opt/synthetic/scripts/*.sh
EXPOSE 8000
ENTRYPOINT ["/opt/synthetic/scripts/entrypoint.sh"]
