# Youth Permission Tracker – Test Environment Setup

This repository supports running a **test environment** consisting of:

* **FastAPI backend** (SQLite, persistent)
* **Static website frontend** (nginx)
* **Traefik reverse proxy** for hostname-based routing

## Hostnames

* Website: `youth.lthome.com`
* API: `youth-api.lthome.com`

---

## Architecture Overview

```
Internet / Browser
        |
     Traefik
   (port 80/443)
     /        \
youth.lthome.com     youth-api.lthome.com
     |                     |
   nginx               FastAPI
 (static site)        (SQLite DB)
```

* Traefik routes traffic by **Host header**
* SQLite DB persists on the host filesystem
* Containers communicate via a shared Docker network

---

## Environment Variables

Both services use:

```env
ENV=test
BASE_URL=localhost
```

API-only:

```env
DB_PATH=/data/data.sqlite3
```

---

## Persistent SQLite Storage

* Host path: `./data/sqlite/data.sqlite3`
* Container path: `/data/data.sqlite3`
* Data persists across container restarts and removal

---

# OPTION A — Using docker-compose (Recommended)

## 1. Create required folders

```bash
mkdir -p data/sqlite
```

## 2. docker-compose.yml

```yaml
services:
  traefik:
    image: traefik:v2.11
    container_name: youth_traefik_test
    command:
      - --api.dashboard=true
      - --providers.docker=true
      - --providers.docker.exposedbydefault=false
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
    ports:
      - "80:80"
      - "443:443"
      - "8081:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - youth_net

  api:
    build:
      context: .
      dockerfile: new-api-dockerfile
    container_name: youth_api_test
    environment:
      ENV: "test"
      BASE_URL: "localhost"
      DB_PATH: "/data/data.sqlite3"
    volumes:
      - ./data/sqlite:/data
    networks:
      - youth_net
    labels:
      - traefik.enable=true
      - traefik.http.routers.youth-api.rule=Host(`youth-api.lthome.com`)
      - traefik.http.routers.youth-api.entrypoints=web
      - traefik.http.services.youth-api.loadbalancer.server.port=8000

  web:
    build:
      context: .
      dockerfile: new-web-dockerfile
    container_name: youth_web_test
    environment:
      ENV: "test"
      BASE_URL: "localhost"
    depends_on:
      - api
    networks:
      - youth_net
    labels:
      - traefik.enable=true
      - traefik.http.routers.youth-web.rule=Host(`youth.lthome.com`)
      - traefik.http.routers.youth-web.entrypoints=web
      - traefik.http.services.youth-web.loadbalancer.server.port=80

networks:
  youth_net:
    driver: bridge
```

## 3. Start the environment

```bash
docker compose up --build
```

## 4. Access

* Website: [http://youth.lthome.com](http://youth.lthome.com)
* API: [http://youth-api.lthome.com](http://youth-api.lthome.com)
* Traefik dashboard: [http://localhost:8081](http://localhost:8081)

Stop (data preserved):

```bash
docker compose down
```

---

# OPTION B — Without docker-compose (Manual Docker)

## 1. Create network and DB folder

```bash
docker network create youth_net
mkdir -p data/sqlite
```

## 2. Build images

```bash
docker build -f new-api-dockerfile -t youth-api:local .
docker build -f new-web-dockerfile -t youth-web:local .
```

## 3. Start Traefik

```bash
docker run -d \
  --name youth_traefik_test \
  --network youth_net \
  -p 80:80 \
  -p 443:443 \
  -p 8081:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  traefik:v2.11 \
  --api.dashboard=true \
  --providers.docker=true \
  --providers.docker.exposedbydefault=false \
  --entrypoints.web.address=:80 \
  --entrypoints.websecure.address=:443
```

## 4. Start API container

```bash
docker run -d \
  --name youth_api_test \
  --network youth_net \
  -e ENV=test \
  -e BASE_URL=localhost \
  -e DB_PATH=/data/data.sqlite3 \
  -v "$(pwd)/data/sqlite:/data" \
  -l traefik.enable=true \
  -l 'traefik.http.routers.youth-api.rule=Host(`youth-api.lthome.com`)' \
  -l traefik.http.routers.youth-api.entrypoints=web \
  -l traefik.http.services.youth-api.loadbalancer.server.port=8000 \
  youth-api:local
```

## 5. Start web container

```bash
docker run -d \
  --name youth_web_test \
  --network youth_net \
  -e ENV=test \
  -e BASE_URL=localhost \
  -l traefik.enable=true \
  -l 'traefik.http.routers.youth-web.rule=Host(`youth.lthome.com`)' \
  -l traefik.http.routers.youth-web.entrypoints=web \
  -l traefik.http.services.youth-web.loadbalancer.server.port=80 \
  youth-web:local
```

---

## Logs

```bash
docker logs -f youth_traefik_test
docker logs -f youth_api_test
docker logs -f youth_web_test
```

---

## Stop & Cleanup (DB preserved)

```bash
docker stop youth_web_test youth_api_test youth_traefik_test
docker rm youth_web_test youth_api_test youth_traefik_test
```

---

## Hostname Resolution

### Local testing

Add to hosts file:

**Windows**

```
C:\Windows\System32\drivers\etc\hosts
```

**macOS/Linux**

```
/etc/hosts
```

Add:

```
127.0.0.1 youth.lthome.com
127.0.0.1 youth-api.lthome.com
```

### External access

* DNS A/AAAA records must point to your server’s public IP
* Router must forward ports **80/443** to the Docker host

---

## Frontend → API Notes

* Browser-based JavaScript must call:

  * `http://youth-api.lthome.com`
* Docker-internal names (e.g. `api:8000`) are not accessible from browsers
* Traefik handles routing cleanly without CORS issues

---

## Summary

* Persistent SQLite storage
* Hostname-based routing
* Works with or without docker-compose
* Test environment mirrors production topology
