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

# # Clear any existing empty directories to allow bind mounts to work
# if [ -d "/etc/traefik/dynamic" ] && [ -z "$(ls -A /etc/traefik/dynamic)" ]; then
#     rmdir /etc/traefik/dynamic
# fi
# if [ -d "/etc/traefik/static" ] && [ -z "$(ls -A /etc/traefik/static)" ]; then
#     rmdir /etc/traefik/static
# fi

exec "$@"