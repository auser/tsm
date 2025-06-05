#!/bin/sh
set -e

# Print environment variables for debugging
echo "PROXY_DOMAIN: ${PROXY_DOMAIN}"
echo "MAIL_FROM: ${MAIL_FROM}"

# Replace environment variables in the Traefik configuration
# envsubst < /etc/traefik/traefik.yaml > /etc/traefik/traefik_replaced.yaml
# mv /etc/traefik/traefik_replaced.yaml /etc/traefik/traefik.yaml

# Replace environment variables in the dynamic configuration
# envsubst < /etc/traefik/dynamic.yaml > /etc/traefik/dynamic_replaced.yaml
# mv /etc/traefik/dynamic_replaced.yaml /etc/traefik/dynamic.yaml

exec "$@"