# Traefik Proxy setup

## Starting from zero

```bash
uv sync
source .venv/bin/activate
```

See all options:

```bash
./main.py --help
```

Generate initial config with services from `docker-compose.yml`

```bash
uv init-config -f ./tests/docker-compose.yml
```

Generate certificates for Traefik and services

```bash
uv generate-certs
uv generate-certs -b traefik
```

## Create usersfile

```bash
uv generate-usersfile -u admin -p admin
```

## Build dockerfiles

```bash
uv build-dockerfiles
```

## Run Traefik

```bash
docker-compose -f ./proxy/docker-compose.yml up -d
```


## Configuration

```bash