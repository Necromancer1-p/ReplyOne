# 🤖 ReplyOne: Multi-Tenant AI Customer Support Aggregator

ReplyOne is a next-generation, enterprise-ready multi-tenant customer support aggregator. It consolidates inbound communications from various channels (such as WhatsApp, Instagram, and web-based chat widgets) into a unified agent inbox, leveraging AI to automatically draft replies or directly respond to customers based on knowledge base profiles and product catalogs.

---

## ✨ Features

- **🛡️ Robust Multi-Tenancy**: Complete isolation of configurations, user rosters (`owner`, `agent`, `viewer`), customers, products, and chat transcripts per tenant.
- **📥 Omnichannel Messaging Support**: Native support for WhatsApp, Instagram, and Custom Web Widgets with webhook logging and deduplication.
- **🧠 Contextual AI Copilot**: Uses a custom inference engine powered by tenant-specific knowledge bases, FAQs, business hours, and active product specifications.
- **💬 Real-Time Unified Agent Inbox**: Modern, reactive chat panel built with WebSockets, offering split screen viewing, agent handoffs, manual overrides, and AI-suggested responses.
- **📊 Performance & Analytics Dashboard**: Built-in visual analytics capturing metrics such as average response times, AI deflection rates, customer satisfaction trends, and intent analysis.
- **⚙️ Celery Async Worker Queue**: Heavy processing tasks (like webhook decryption, AI agent reasoning, and state sync) are handled asynchronously via Celery and Redis.

---

## 🏗️ System Architecture

ReplyOne follows a modern, distributed architecture to handle high throughput and ensure horizontal scalability:

```mermaid
graph TD
    Client[Customer (WhatsApp, Insta, Web)] -->|Webhook / API| API[FastAPI Core Server :8000]
    API -->|Pub/Sub & Tasks| Redis[(Redis Broker :6379)]
    Redis --> Celery[Celery Async Workers]
    Celery -->|Infer intent / reply| MockAI[Mock AI Inference Service :8008]
    API -->|Relational Storage| DB[(MySQL 8.0 / SQLite)]
    Agent[Agent Console] -->|WebSockets / REST| API
    Agent -->|UI Views| Frontend[React + Vite + Tailwind :5173]
```

### Tech Stack Details

- **Frontend**: [React 18](https://react.dev/), [Vite](https://vite.dev/), [TypeScript](https://www.typescriptlang.org/), [Tailwind CSS](https://tailwindcss.com/) for fluid grid layout, [Lucide React](https://lucide.dev/) for crisp vector iconography.
- **Backend API**: [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Asyncio), [Pydantic v2](https://docs.pydantic.dev/) for schema validation.
- **Asynchronous Processing**: [Celery](https://docs.celeryq.dev/) for task queueing, with [Redis](https://redis.io/) acting as both the message broker and WebSocket Pub/Sub coordinator.
- **Mock AI Service**: A helper FastAPI application simulating neural text classification, semantic knowledge-base scanning, and product availability checks.
- **Database**: [MySQL 8.0](https://www.mysql.com/) for containerized environments, [SQLite](https://sqlite.org/) for quick local bootstrapping.

---

## 📁 Repository Structure

```text
ReplyOne/
├── backend/               # FastAPI core, database schemas, API routers, and Celery workers
│   ├── app/
│   │   ├── api/           # Auth, Webhooks, Dashboard, and WebSockets endpoints
│   │   ├── core/          # Security, token management, and WebSocket connection managers
│   │   ├── db/            # SQLAlchemy session configurations and engines
│   │   ├── models/        # SQLAlchemy tables (Tenant, User, Channel, Message, etc.)
│   │   ├── schemas/       # Pydantic models for validation and response serialization
│   │   ├── services/      # Encryption utilities, AI orchestration logic
│   │   └── main.py        # App entry point, middleware registration, startup/shutdown tasks
│   └── Dockerfile
├── frontend/              # React, TypeScript, and Tailwind dashboard client
│   ├── src/
│   │   ├── components/    # InboxView, AnalyticsView, OnboardingWizard, SettingsView, etc.
│   │   ├── store/         # Zustand global states (auth, inbox, sockets)
│   │   ├── utils/         # API request wrappers and date formatting helpers
│   │   └── App.tsx        # Shell navigation and page routing
│   └── package.json
├── mock-ai/               # FastAPI mock service simulating NLP/LLM responses
│   └── app.py
├── docker-compose.yml     # Multi-container local orchestration manifest
└── replyone.db            # SQLite development database file
```

---

## 🚀 Getting Started

### Prerequisites

Make sure you have the following installed on your machine:
- [Docker](https://www.docker.com/products/docker-desktop/) & Docker Compose
- [Node.js](https://nodejs.org/) (v18+) & `npm` (if running frontend outside docker)
- [Python 3.10+](https://www.python.org/) (if running backend outside docker)

---

### Method A: Quickstart via Docker Compose (Recommended)

To boot up the entire ecosystem (Database, Redis, AI model, Backend, and Celery Workers) in a fully orchestrated mesh:

1. Navigate to the `ReplyOne` directory:
   ```bash
   cd ReplyOne
   ```
2. Build and start all services:
   ```bash
   docker compose up --build -d
   ```
3. Verify all services are healthy and running:
   ```bash
   docker compose ps
   ```

#### Exposed Endpoints:
- **Core API Server**: [http://localhost:8000](http://localhost:8000) (Interactive Swagger Docs at `/docs`)
- **Mock AI inference**: [http://localhost:8008](http://localhost:8008)
- **MySQL DB Port**: `3306`
- **Redis Port**: `6379`

To stop the cluster and retain volume persistence:
```bash
docker compose down
```

---

### Method B: Local Development Setup

#### 1. Setup Backend
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the development server (uses SQLite by default if no `DATABASE_URL` env var is specified):
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

#### 2. Setup Mock AI Service
1. In a new terminal, navigate to the `mock-ai` directory:
   ```bash
   cd mock-ai
   ```
2. Install its small dependency set and run the server:
   ```bash
   pip install -r requirements.txt
   python app.py
   ```

#### 3. Setup Frontend
1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install node dependencies:
   ```bash
   npm install
   ```
3. Start the Vite React development server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to the address outputted by Vite (typically [http://localhost:5173](http://localhost:5173)).

---

## 🔒 Security & Encryption

- **Double-Envelope Webhook Protection**: Channels encrypt external credentials dynamically using 256-bit AES symmetric keys configured on the host server.
- **Multi-Tenant Scoping**: Every database transaction is scoped at the query level using `tenant_id` validation.
- **JWT Authorization**: User authentication utilizes secure JSON Web Tokens with auto-rotating sessions.