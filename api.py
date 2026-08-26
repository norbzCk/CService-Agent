"""
HTTP API for the Soko-Link customer service agent.

Deployed as its own Render web service, independent of the main website
backend -- so a website outage doesn't take the agent down, and vice versa.
The frontend calls this service directly.
"""
import logging
import os
import uuid

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent_core import create_agent_session, send_message_with_fallback
from auth import get_customer_email
from session_store import get_session, set_session, active_session_count
from tools.products import search_products, get_product
from tools.orders import build_order_tools
from tools.delivery import build_delivery_tools
from tools.payment import build_payment_tools
from knowledge.retrieve_knowledge import retrieve_knowledge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Soko-Link Customer Service Agent")

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    authenticated: bool


def _build_tools(customer_email: str | None) -> list:
    tools = [search_products, get_product, retrieve_knowledge]
    if customer_email:
        tools += build_order_tools(customer_email)
        tools += build_delivery_tools(customer_email)
        tools += build_payment_tools(customer_email)
    return tools


@app.get("/healthz")
def healthz():
    return {"status": "ok", "active_sessions": active_session_count()}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, authorization: str | None = Header(default=None)):
    if not request.session_id or len(request.session_id) > 100:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    customer_email = get_customer_email(authorization)

    state = get_session(request.session_id)

    # (Re)build the session if it's new, OR if the auth status changed
    # since the last message (e.g. the user logged in mid-conversation) --
    # so tool access upgrades/downgrades correctly without a stale session
    # silently keeping old permissions.
    session_is_stale = state is not None and state.get("customer_email") != customer_email

    if state is None or session_is_stale:
        tools = _build_tools(customer_email)
        state = create_agent_session(tools)
        state["customer_email"] = customer_email

    try:
        reply = send_message_with_fallback(state, request.message)
    except Exception:
        logger.exception("Unhandled error in send_message_with_fallback")
        reply = (
            "I'm sorry, something went wrong on my end. "
            "Please try again in a moment."
        )

    set_session(request.session_id, state)

    return ChatResponse(
        reply=reply,
        session_id=request.session_id,
        authenticated=customer_email is not None,
    )


@app.post("/session/new")
def new_session():
    """Convenience endpoint for the frontend to mint a fresh session_id."""
    return {"session_id": str(uuid.uuid4())}
