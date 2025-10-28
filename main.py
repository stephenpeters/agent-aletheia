"""Aletheia - Idea Discovery Agent for Mnemosyne."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agent_sdk.utils import setup_logger
from agent_aletheia.routes.ideas import router as ideas_router
from agent_aletheia.routes.chat import router as chat_router

logger = setup_logger("aletheia.main")

app = FastAPI(
    title="Aletheia - Idea Discovery Agent",
    description="Content discovery, evaluation, and conversational ideation agent for the Mnemosyne system",
    version="0.2.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ideas_router)
app.include_router(chat_router)


@app.get("/healthz")
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "agent": "aletheia",
        "version": "0.1.0",
    }


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("Aletheia agent starting up")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Aletheia agent shutting down")
