# Docker Implementation for FastAPI + Redis

This document explains the Docker setup for running a **FastAPI application** alongside **Redis** in a containerized environment, including networking, volumes, and service orchestration.

---

## 1. Overview

We are running two main services:

1. **FastAPI Application Container**

   * Runs the Python FastAPI app with Uvicorn.
   * Connects to Redis for data storage and caching.

2. **Redis Container**

   * Runs Redis version `7-alpine` (lightweight build).
   * Persists its data in a Docker volume so it survives restarts.

Both services run on the same **Docker network** so they can communicate via container names.

---

## 2. Architecture Diagram

```
              ┌───────────────────────────────┐
              │         Your Machine          │
              │      (Host: localhost)        │
              └───────────────────────────────┘
                           │
             Port 8000     │     Port 6379
         ┌─────────────────┴─────────────────┐
         │                                   │
   ┌────────────────────┐              ┌──────────────────────┐
   │   app container    │              │   redis container    │
   │  (FastAPI + code)  │              │ (Redis 7 - Alpine)   │
   │                    │              │                      │
   │ Runs:              │              │ Listens on 6379      │
   │ uvicorn main:app   │              │ Data stored in /data │
   │ host=0.0.0.0:8000  │              │                      │
   └─────────┬──────────┘              └─────────┬────────────┘
             │                                      │
             │  Internal Docker Network             │
             └───────────── app_network ────────────┘
                         (bridge driver)
                               │
                   DNS inside Docker:
                   - `app` ↔ `redis`
                               │
                   Volumes (Persistent Data)
                               │
                      redis_data:/data
        (stored on host, survives container restarts)
```

---

## 3. Docker Components

### **3.1 Dockerfile (FastAPI app)**

The `Dockerfile` builds an image for the FastAPI application.

```dockerfile
FROM python:3.11-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Explanation:**

* Uses a lightweight Python 3.11 image.
* Installs dependencies from `requirements.txt`.
* Copies project files into `/app`.
* Exposes port `8000` inside the container.
* Runs the FastAPI app using Uvicorn.

---

### **3.2 docker-compose.yml**

Defines both the app and Redis services.

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - ./.env
    depends_on:
      - redis
    networks:
      - app_network

  redis:
    image: "redis:7-alpine"
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - app_network

volumes:
  redis_data:

networks:
  app_network:
    driver: bridge
```

**Key Points:**

* **`app`**\*\* service\*\* is built from your local Dockerfile.
* **`redis`**\*\* service\*\* uses the official Redis image (`7-alpine`).
* Both share the same **`app_network`** so they can communicate.
* `redis_data` volume stores Redis data persistently.
* `depends_on` ensures Redis starts before the app.

---

## 4. Networking

* **Network Type**: `bridge`
* **Container DNS**: Inside the `app_network`, containers can reach each other by name:

  * `redis:6379` → Redis container
  * `app:8000` → FastAPI container
* **Host Access**:

  * `localhost:8000` → FastAPI app
  * `localhost:6379` → Redis server

---

## 5. Persistent Data

Redis data is stored in:

```
/data  (inside container)
```

This path is mapped to the Docker volume:

```
redis_data:/data
```

Which means:

* Data survives container restarts.
* Clearing the volume will reset the database.

---

## 6. Running the Services

### Build and Start

```bash
docker-compose up --build
```

### Stop

```bash
docker-compose down
```

### Stop and Remove Volumes (Clear Redis Data)

```bash
docker-compose down -v
```

---

## 7. Why This Setup Works Well

* **Isolation**: Each service runs in its own container with its own dependencies.
* **Port Mapping**: Only the needed ports are exposed to the host.
* **Networking**: Containers talk over an internal, secure network.
* **Persistence**: Redis keeps data even if its container restarts.
* **Lightweight**: `7-alpine` image keeps Redis container small and fast.
