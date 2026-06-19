# ReplyOne

ReplyOne is a Multi-Tenant AI Customer Support Aggregator.

## Tech Stack

- **Frontend:** React, Vite, Tailwind CSS, Zustand, Socket.io-client, React Query
- **Backend:** FastAPI, MySQL (aiomysql), Redis, Celery, SQLAlchemy
- **Mock AI:** FastAPI

## Project Architecture & Folder Structure

- `backend/`: The core FastAPI application that handles routing, database interactions, background tasks (Celery), and core business logic.
- `frontend/`: The React-based frontend application built with Vite, providing the dashboard and UI.
- `mock-ai/`: A lightweight FastAPI service acting as a mock AI model to simulate intent classification, sentiment analysis, and response generation.

## Getting Started

### Prerequisites

Ensure you have the following installed on your machine:
- Docker & Docker Compose
- Node.js (v18+ recommended)
- Python 3.10+ (if running backend locally without Docker)

### Running the Services via Docker

You can easily start the backend, database, Redis cache, celery worker, and the Mock AI service using Docker Compose.

```bash
# From the root of the project:
docker-compose up -d --build
```

This will spin up:
- MySQL Database (`db`) at port 3306
- Redis Server (`redis`) at port 6379
- Mock AI Service (`mock-ai`) at `http://localhost:8008`
- Backend API (`api`) at `http://localhost:8000`
- Celery Worker (`worker`)

To verify the API is running, you can visit: `http://localhost:8000/docs`

### Running the Frontend Locally

```bash
cd frontend
npm install
npm run dev
```

This will start the Vite development server. You can visit the frontend at the local URL provided by Vite (typically `http://localhost:5173`).

## Environment Variables

For the docker-compose setup, default environment variables are already configured within `docker-compose.yml`. For local development outside of Docker, refer to the respective service environments (e.g., `DATABASE_URL`, `REDIS_URL`, `AI_SERVICE_URL`).
