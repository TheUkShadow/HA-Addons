ARG BUILD_FROM=ghcr.io/home-assistant/base:latest
FROM $BUILD_FROM

EXPOSE 8100

# Install Python + required packages
RUN apk add --no-cache \
    python3 \
	py3-requests \
    py3-pyserial \
	py3-flask \
	py3-gunicorn

WORKDIR /app

# Copy data
COPY rootfs /

# Ensure all s6 scripts are executable
RUN chmod +x /etc/s6-overlay/s6-rc.d/*/run || true
RUN chmod +x /etc/s6-overlay/s6-rc.d/*/finish || true


