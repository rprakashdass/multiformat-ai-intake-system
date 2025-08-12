# Dockerized FastAPI + Redis Deployment

A robust containerized architecture for running a **FastAPI** backend with **Redis** caching, designed for scalability, easy deployment, and persistent data storage.

This setup uses **Docker** and **Docker Compose** to manage services, networking, and volumes — ensuring reproducibility and isolation.

---

## 1️⃣ High-Level Overview

We run two main services inside Docker:

### **1. FastAPI Application Container**

* Runs the Python **FastAPI** backend with **Uvicorn**.
* Uses environment variables from `.env`.
* Connects to Redis for caching, session management, or quick data lookups.

### **2. Redis Container**

* Uses **Redis 7-alpine** (lightweight, fast).
* Stores its data in a Docker volume so it survives container restarts.

Both containers communicate via a **private Docker network** for security and isolation.

---

## 2️⃣ Architecture Diagram

```

                                            🌐 Browser / Client                                            
                                                     │                                                    
                                                     ▼                                                    
                                    http://13.201.57.209:8000/static/index.html                            
                                                     │                                                    
                                                     ▼                                                    
                                           AWS EC2 (Ubuntu Host)                                          
                                                     │                                                    
                                            ┌────────┴─────────┐                                         
                                            │  Docker Engine   │                                         
                                            └──────────────────┘                                         
                                                     │                                                    
                                       ┌──────────────────────────────┐                                     
                                       │  Internal Docker Network     │  (bridge: app_network)             
                                       └──────────────────────────────┘                                     
                                         │                        │                                      
                                         ▼                        ▼                                      
                                ┌────────────────────┐   ┌──────────────────────┐                       
                                │   app container    │   │   redis container    │                       
                                │  (FastAPI + code)  │   │ (Redis 7 - Alpine)   │                       
                                │ Runs:              │   │ Listens on 6379      │                       
                                │ uvicorn main:app   │   │ Data stored in /data │                       
                                │ host=0.0.0.0:8000  │   │ Persistent Volumes   │                       
                                └─────────┬──────────┘   └─────────┬────────────┘                       
                                          │                        │                                      
                                          └──────────────┬─────────┘                                      
                                                         │                                                
                                                DNS inside Docker:                                        
                                                - `app` ↔ `redis`                                         
                                                         │                                                
                                                Volumes (Persistent Data)                                 
                                                         │                                                
                                                 redis_data:/data                                         
                                        (stored on host, survives container restarts)                                     


```

## 3️⃣ Docker Components

### **Dockerfile** (FastAPI app)

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
* Exposes port **8000** inside the container.
* Runs the FastAPI app with Uvicorn.

---

### **docker-compose.yml**

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

* `app` service is built from your local Dockerfile.
* `redis` service uses the official Redis 7-alpine image.
* Both share the same **app\_network** for communication.
* `redis_data` volume stores Redis data persistently.
* `depends_on` ensures Redis starts before the app.

---

## 4️⃣ Networking

* **Network Type:** bridge
* **Container DNS:** Inside `app_network`, containers can reach each other by name:

  * `redis:6379` → Redis container
  * `app:8000` → FastAPI container
* **Host Access:**

  * `http://13.201.57.209:8000` → FastAPI app
  * `13.201.57.209:6379` → Redis server

---

## 5️⃣ Persistent Data

Redis data is stored in `/data` inside the container, mapped to the Docker volume `redis_data:/data`.

* **Benefits:**

  * Data survives container restarts.
  * Clearing the volume resets the database.

---

## 6️⃣ Running the Services

**Build and Start:**

```bash
docker-compose up --build
```

**Stop:**

```bash
docker-compose down
```

**Stop and Remove Volumes (Clear Redis Data):**

```bash
docker-compose down -v
```

---

## 7️⃣ Why This Setup Works Well

* **Isolation:** Each service runs in its own container with its own dependencies.
* **Port Mapping:** Only required ports are exposed to the host.
* **Networking:** Containers communicate over a secure internal network.
* **Persistence:** Redis data survives restarts.
* **Lightweight:** Redis 7-alpine keeps the image size small and fast.
