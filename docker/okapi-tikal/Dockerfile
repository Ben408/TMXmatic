# LDW Okapi tikal — Temurin 17 JRE + official Linux okapi-apps (gtk2) distribution.
# Build: scripts\build_okapi_tikal_image.ps1

FROM eclipse-temurin:17-jre-jammy

ARG OKAPI_VERSION=1.48.0
ARG OKAPI_ZIP=okapi-apps_gtk2-linux-x86_64_1.48.0.zip
ENV OKAPI_HOME=/opt/okapi

RUN apt-get update \
    && apt-get install -y --no-install-recommends unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY ${OKAPI_ZIP} /tmp/okapi.zip

RUN mkdir -p "${OKAPI_HOME}" \
    && unzip -q /tmp/okapi.zip -d "${OKAPI_HOME}" \
    && rm /tmp/okapi.zip \
    && printf '#!/bin/bash\nexec "%s/tikal.sh" "$@"\n' "${OKAPI_HOME}" > /usr/local/bin/tikal \
    && chmod +x /usr/local/bin/tikal "${OKAPI_HOME}/tikal.sh"

WORKDIR /work
