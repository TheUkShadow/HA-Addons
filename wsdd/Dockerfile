ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache wsdd

COPY rootfs /

# Ensure all s6 scripts are executable
RUN chmod +x /etc/s6-overlay/s6-rc.d/*/run || true
RUN chmod +x /etc/s6-overlay/s6-rc.d/*/finish || true