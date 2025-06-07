FROM docker.io/alpine:3.20 AS etcd

ARG ETCD_VER
ENV ETCD_VER=3.5.15

ARG PROXY_DOMAIN
ENV PROXY_DOMAIN=${PROXY_DOMAIN:-herringbank.com}


RUN apk add --update ca-certificates openssl tar curl
RUN arch=$(arch | sed s/aarch64/arm64/ | sed s/x86_64/amd64/) && \
    curl -L https://github.com/etcd-io/etcd/releases/download/v${ETCD_VER}/etcd-v${ETCD_VER}-linux-${arch}.tar.gz -o /tmp/etcd.tar.gz && \
    mkdir -p /tmp/etcd-download && \
    tar xzvf /tmp/etcd.tar.gz -C /tmp/etcd-download --strip-components=1 --no-same-owner && \
    rm -Rf /tmp/etcd.tar.gz && \
    mv /tmp/etcd-download/etcd* /bin/ && \
    apk del --purge tar openssl && \
    rm -Rf /tmp/etcd-download /var/cache/apk/*

FROM docker.io/traefik:v3.1.6 AS dist

ARG USERNAME=traefik
ARG USER_UID=1001
ARG USER_GID=$USER_UID
# Install envsubst
RUN apk update && apk add --no-cache gettext shadow sudo \
    && groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

RUN apk add --no-cache libcap && \
    setcap 'cap_net_bind_service=+ep' /usr/local/bin/traefik

# Copy basicAuth - insecure
COPY --chown=$USERNAME:$USERNAME ./config/usersfile /etc/traefik/.htpasswd
# RUN chown -R $USERNAME:$USERNAME /etc/traefik/*.* /etc/traefik/.htpasswd

COPY --chown=$USERNAME:$USERNAME ./config/static/traefik.yml /etc/traefik/traefik.yaml
# COPY ./config/dynamic.yaml /etc/traefik/dynamic.yaml

# Should we do it this way? 
# Nope, but good enough for now

# Server certificates
COPY --chown=$USERNAME:$USERNAME ./certs/traefik/traefik-server.pem /etc/traefik/server.pem
COPY --chown=$USERNAME:$USERNAME ./certs/traefik/traefik-server-key.pem /etc/traefik/server-key.pem

COPY --chown=$USERNAME:$USERNAME ./certs/traefik/asterisk_fp.pem /etc/traefik/asterisk_fp.pem
COPY --chown=$USERNAME:$USERNAME ./certs/traefik/asterisk_fp-key.pem /etc/traefik/asterisk_fp-key.pem

COPY --chown=$USERNAME:$USERNAME ./certs/traefik/wildcard_herringbank.pem /etc/traefik/wildcard_herringbank.pem
COPY --chown=$USERNAME:$USERNAME ./certs/traefik/wildcard_herringbank-key.pem /etc/traefik/wildcard_herringbank-key.pem

# Client certificates
# COPY ./certs/traefik/traefik-etcd-client.pem /etc/traefik/etcd-client.pem
# COPY ./certs/traefik/traefik-etcd-client-key.pem /etc/traefik/etcd-client-key.pem

COPY --chown=$USERNAME:$USERNAME ./certs/ca.pem /etc/traefik/ca.pem

COPY --from=etcd /bin/etcd /bin/etcd
COPY --from=etcd /bin/etcdctl /bin/etcdctl

COPY --chown=traefik:traefik ./dockerfiles/traefik/traefik-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

RUN chmod 644 /etc/traefik/*.pem && \
    chmod 600 /etc/traefik/*-key.pem

VOLUME      /data
VOLUME      /logs

EXPOSE      2379 2380 4001 7001

RUN chown traefik -R /etc/traefik && \
    mkdir -p /logs && chown traefik -R /logs

# Add this after your existing COPY commands
COPY --chown=$USERNAME:$USERNAME ./config/dynamic/ /etc/traefik/dynamic/
COPY --chown=$USERNAME:$USERNAME ./config/static/ /etc/traefik/static/

USER $USERNAME


ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["traefik"]

