"""Dash support API.

Wires up FastAPI and delegates to the agent for everything else.
Run locally with: uvicorn api.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import chat, health

app = FastAPI(title="Dash support backend")

# Open CORS for local development. Lock this down before shipping.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
