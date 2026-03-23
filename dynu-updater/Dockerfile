ARG BUILD_FROM
FROM $BUILD_FROM

# Allow pip to install packages system-wide on Debian
ENV PIP_BREAK_SYSTEM_PACKAGES=1

# setup base
# certbot-dns-multi replaces most individual DNS plugins using lego

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
RUN chmod +x /etc/s6-overlay/s6-rc.d/*/run || true
RUN chmod +x /etc/s6-overlay/s6-rc.d/*/finish || true
