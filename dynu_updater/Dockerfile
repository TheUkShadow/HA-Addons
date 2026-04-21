ARG BUILD_ARCH
FROM ghcr.io/home-assistant/${BUILD_ARCH}-base-debian:trixie-2026.03.1

ARG ACME_VERSION=3.3.0
ARG CERTBOT_DNS_MULTI_VERSION=4.33.0
ARG CERTBOT_VERSION=3.3.0
ARG CRYPTOGRAPHY_VERSION=44.0.2
ARG FLASK_VERSION=3.0.2
ARG GUNICORN_VERSION=21.2.0
ARG REQUESTS_VERSION=2.31.0

# Allow pip to install packages system-wide on Debian
ENV PIP_BREAK_SYSTEM_PACKAGES=1

ARG \
    BUILD_ARCH \
    ACME_VERSION \
    CERTBOT_DNS_MULTI_VERSION \
    CERTBOT_VERSION \
    CRYPTOGRAPHY_VERSION

RUN \
    set -x \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        cargo \
        golang \
        libffi8 \
        libffi-dev \
        libssl-dev \
        openssl \
        python3 \
        python3-dev \
        python3-pip \
        rustc \
		mosquitto-clients \
    && pip3 install --no-cache-dir \
        acme==${ACME_VERSION} \
        certbot==${CERTBOT_VERSION} \
        certbot-dns-multi==${CERTBOT_DNS_MULTI_VERSION} \
        cryptography==${CRYPTOGRAPHY_VERSION} \
    && apt-get purge -y --auto-remove \
        build-essential \
        cargo \
        golang \
        libffi-dev \
        libssl-dev \
        python3-dev \
        python3-pip \
        rustc \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /root/.cache

# Copy data
COPY rootfs /

# Ensure all s6 scripts are executable
RUN chmod +x /etc/s6-overlay/s6-rc.d/*/up || true
RUN chmod +x /etc/s6-overlay/s6-rc.d/*/down || true
RUN chmod +x /etc/s6-overlay/s6-rc.d/*/run || true
RUN chmod +x /etc/s6-overlay/s6-rc.d/*/finish || true
