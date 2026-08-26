"""
Core Gemini chat logic for the Soko-Link customer service agent.

Extracted from the original main.py CLI so it can be reused by both the
local CLI (main.py) and the HTTP API (api.py). Tools are now passed in per
call instead of being a fixed global list, since the API needs different
tools per request depending on whether the customer is authenticated.
"""
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError

from knowledge.retrieve_knowledge import retrieve_knowledge

load_dotenv()

logger = logging.getLogger(__name__)

MODEL_FALLBACK_LIST = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-1.5-flash"]

NON_TEXT_FINISH_REASONS = {
    "SAFETY", "PROHIBITED_CONTENT", "RECITATION", "BLOCKLIST", "SPII", "OTHER",
}

FRIENDLY_FALLBACK = (
    "I'm sorry, I didn't quite catch that. Could you rephrase, or let me "
    "know if this is about a product, order, payment, delivery, or your account?"
)

BASE_DIR = Path(__file__).resolve().parent
SYSTEM_INSTRUCTION_FILE = BASE_DIR / "knowledge" / "system_instructions.md"

client = genai.Client(api_key=os.environ.get("GEMINIAI_API_KEY"))


def load_system_instructions() -> str:
    with open(SYSTEM_INSTRUCTION_FILE, "r", encoding="utf-8") as f:
        return f.read()


def build_system_instruction() -> str:
    system_instructions = load_system_instructions()
    company_information = retrieve_knowledge("company_information")
    return f"""{system_instructions}
            # COMPANY INFORMATION
            The following information describes Soko-Link.
            Use this information when answering customer questions.

            Do not invent information that is not contained in the
            company information or provided by an available tool.

            {company_information}
            """


def make_chat(model_name: str, system_instruction: str, tools: list, history=None):
    """Create a chat session for a given model + tool set.
    Does NOT verify the model actually works -- chats.create() never
    touches the network. Errors only surface once you send a message."""
    kwargs = dict(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
            tools=tools,
        ),
    )
    if history:
        kwargs["history"] = history
    return client.chats.create(**kwargs)


def create_agent_session(tools: list) -> dict:
    """Create a fresh chat session state dict, bound to the given tool set."""
    system_instruction = build_system_instruction()
    model_name = MODEL_FALLBACK_LIST[0]
    chat = make_chat(model_name, system_instruction, tools)
    return {
        "chat": chat,
        "model": model_name,
        "system_instruction": system_instruction,
        "tools": tools,
    }


def get_response_text(response) -> str | None:
    """
    Safely pull text out of a response. Returns None (not an exception)
    when the model produced no usable text -- e.g. a safety block.
    response.text raises ValueError in these cases.
    """
    try:
        candidates = getattr(response, "candidates", None)
        if not candidates:
            return None
        finish_reason = getattr(candidates[0], "finish_reason", None)
        finish_reason_name = getattr(finish_reason, "name", finish_reason)
        if finish_reason_name in NON_TEXT_FINISH_REASONS:
            logger.info("Non-text finish_reason from model: %s", finish_reason_name)
            return None
        text = response.text
        return text.strip() if text else None
    except ValueError:
        logger.info("response.text raised ValueError (no text part in response).")
        return None
    except Exception:
        logger.exception("Unexpected error while extracting response text.")
        return None


def send_message_with_fallback(state: dict, user_input: str, max_retries_per_model: int = 2) -> str:
    """
    Send a message, retrying transient errors, and failing over to the
    next model in MODEL_FALLBACK_LIST when one is unavailable -- carrying
    history and the same bound tools across the switch.
    """
    remaining_models = MODEL_FALLBACK_LIST[MODEL_FALLBACK_LIST.index(state["model"]):]

    for model_name in remaining_models:
        if model_name != state["model"]:
            try:
                history = state["chat"].get_history()
            except Exception:
                history = None
            state["chat"] = make_chat(model_name, state["system_instruction"], state["tools"], history=history)
            state["model"] = model_name
            logger.info("Switched to fallback model: %s", model_name)

        backoff = 1.0
        for attempt in range(max_retries_per_model):
            try:
                response = state["chat"].send_message(user_input)
                text = get_response_text(response)
                if text:
                    return text
                return FRIENDLY_FALLBACK

            except ServerError:
                logger.warning("ServerError on model %s (attempt %d/%d).", model_name, attempt + 1, max_retries_per_model)
                time.sleep(backoff)
                backoff *= 2
                continue

            except APIError as error:
                logger.warning("APIError on model %s: %r", model_name, error)
                break

            except Exception:
                logger.exception("Unexpected error sending message on model %s.", model_name)
                return (
                    "I'm sorry, something went wrong on my end. "
                    "Could you try again, or let me know if you'd like "
                    "to speak with a human agent?"
                )

    logger.error("All models in MODEL_FALLBACK_LIST failed for this message.")
    return (
        "I'm sorry, I'm having trouble processing requests right now. "
        "Please try again shortly, or contact human support if this continues."
    )
