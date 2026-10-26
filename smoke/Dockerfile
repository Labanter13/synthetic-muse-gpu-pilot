FROM nvidia/cuda:13.0.2-base-ubuntu24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends python3 ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY smoke/server.py /app/server.py
EXPOSE 8000
CMD ["python3", "-u", "/app/server.py"]
