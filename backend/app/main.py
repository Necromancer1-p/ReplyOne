import logging
import asyncio
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import auth, webhooks, dashboard
from app.core.websocket import router as ws_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("replyone.main")
logger.info("Starting ReplyOne API Application...")

app = FastAPI(
    title="ReplyOne Core API", 
    version="1.0.0",
    description="Backend API for ReplyOne Multi-Tenant AI Customer Support Aggregator"
)

api_app = app # Alias to prevent shadowing from 'app' package imports

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to dashboard and widget domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(ws_router, tags=["WebSocket"])

from fastapi.staticfiles import StaticFiles
import os

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
async def on_startup():
    # Initialize Redis check
    from app.core.websocket import init_redis
    await init_redis()

    logger.info("Running database startup checks...")
    try:
        from app.db.session import engine, Base
        import app.models # Ensure all models are registered on Base
        async with engine.begin() as conn:
            logger.info("Initializing database tables if not existing...")
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.critical(f"Database startup failed: {e}", exc_info=True)

    # Start Redis Pub/Sub listener
    logger.info("Starting Redis Pub/Sub listener...")
    from app.core.websocket import redis_pubsub_listener
    api_app.state.redis_listener = asyncio.create_task(redis_pubsub_listener())

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down background tasks...")
    if hasattr(api_app.state, "redis_listener"):
        api_app.state.redis_listener.cancel()
        try:
            await api_app.state.redis_listener
        except asyncio.CancelledError:
            logger.info("Redis Pub/Sub listener successfully stopped.")


@app.get("/health")
def health_check():
    logger.debug("Healthcheck endpoint called")
    return {"status": "healthy", "service": "ReplyOne Backend API"}

@app.get("/")
def read_root():
    return {"message": "Welcome to ReplyOne API"}
