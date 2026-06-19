import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import auth, webhooks, dashboard

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

@app.on_event("startup")
async def on_startup():
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

@app.get("/health")
def health_check():
    logger.debug("Healthcheck endpoint called")
    return {"status": "healthy", "service": "ReplyOne Backend API"}

@app.get("/")
def read_root():
    return {"message": "Welcome to ReplyOne API"}
