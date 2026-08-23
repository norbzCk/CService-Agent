import logging
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError

from knowledge.retrieve_knowledge import retrieve_knowledge
from tools.products import search_products, get_product
from tools.orders import get_order_status, list_recent_orders
from tools.delivery import get_delivery_status
from tools.payment import get_payment_status

load_dotenv()

logger = logging.getLogger(__name__)

MODEL_FALLBACK_LIST = [ "gemini-3.5-flash", "gemini-2.5-flash", "gemini-1.5-flash"]

# finish_reason values that mean "there is no usable text, but this is not a bug"
NON_TEXT_FINISH_REASONS = {
    "SAFETY",
    "PROHIBITED_CONTENT",
    "RECITATION",
    "BLOCKLIST",
    "SPII",
    "OTHER",
}

FRIENDLY_FALLBACK = (
    "I'm sorry, I didn't quite catch that. Could you rephrase, or let me "
    "know if this is about a product, order, payment, delivery, or your account?"
)

BASE_DIR = Path(__file__).resolve().parent
SYSTEM_INSTRUCTION_FILE = BASE_DIR / "knowledge" / "system_instructions.md"

client = genai.Client(
    api_key=os.environ.get("GEMINIAI_API_KEY")
)


def print_time(label: str = "Current time") -> None:
    now = datetime.now()
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
    print(f"{label}: {formatted_time}")


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


def _make_chat(model_name: str, system_instruction: str, history=None):
    """Create a chat session for a given model. Does NOT verify the model
    actually works -- chats.create() never touches the network. Errors only
    surface once you send a message, which is why creation succeeding
    doesn't mean the model is usable."""
    tools = [
        search_products,
        get_product,
        get_order_status,
        list_recent_orders,
        get_delivery_status,
        get_payment_status,
    ]
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


def create_support_agent():
    """Create the first chat session using the highest-priority model.
    Actual failover to the next model happens in send_message_with_fallback,
    since we can't know a model is broken until we try to use it."""
    system_instruction = build_system_instruction()
    model_name = MODEL_FALLBACK_LIST[0]
    chat = _make_chat(model_name, system_instruction)
    return chat, model_name, system_instruction


def get_response_text(response) -> str | None:
    """
    Safely pull text out of a response. Returns None (not an exception)
    when the model produced no usable text -- e.g. a safety block, an
    empty candidate, or an odd finish_reason. response.text raises
    ValueError in these cases, and that used to bubble up as a generic
    "unexpected error" for the customer.
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
    Send a message, retrying transient errors, and actually failing over
    to the next model in MODEL_FALLBACK_LIST when one is unavailable --
    carrying the conversation history across so context isn't lost.
    """
    remaining_models = MODEL_FALLBACK_LIST[MODEL_FALLBACK_LIST.index(state["model"]):]

    for model_index, model_name in enumerate(remaining_models):
        if model_name != state["model"]:
            # Switching models: rebuild the chat with prior history so
            # the conversation continues naturally.
            try:
                history = state["chat"].get_history()
            except Exception:
                history = None
            state["chat"] = _make_chat(model_name, state["system_instruction"], history=history)
            state["model"] = model_name
            logger.info("Switched to fallback model: %s", model_name)

        backoff = 1.0
        for attempt in range(max_retries_per_model):
            try:
                response = state["chat"].send_message(user_input)
                text = get_response_text(response)
                if text:
                    return text
                # No usable text but no exception either (e.g. safety block,
                # empty tool loop). This is a legitimate outcome, not a
                # reason to fail over models or retry.
                return FRIENDLY_FALLBACK

            except ServerError:
                logger.warning(
                    "ServerError on model %s (attempt %d/%d).",
                    model_name, attempt + 1, max_retries_per_model,
                )
                time.sleep(backoff)
                backoff *= 2
                continue

            except APIError as error:
                logger.warning("APIError on model %s: %r", model_name, error)
                break  # stop retrying this model, move to the next one

            except Exception:
                logger.exception("Unexpected error sending message on model %s.", model_name)
                return (
                    "I'm sorry, something went wrong on my end. "
                    "Could you try again, or let me know if you'd like "
                    "to speak with a human agent?"
                )

        # This model exhausted its retries or hard-failed; try the next one.

    logger.error("All models in MODEL_FALLBACK_LIST failed for this message.")
    return (
        "I'm sorry, I'm having trouble processing requests right now. "
        "Please try again shortly, or contact human support if this continues."
    )


def start_customer_service_agent():
    try:
        chat, active_model, system_instruction = create_support_agent()
    except Exception as error:
        print("\nFailed to initialize the customer service support agent.")
        print(f"Error: {error}")
        return

    state = {"chat": chat, "model": active_model, "system_instruction": system_instruction}

    print()
    print("=" * 80)
    print("SOKO-LINK CUSTOMER SERVICE AGENT")
    print_time("Session started")
    print("Welcome, I am Soko-Link's customer service agent. You can ask me questions about our products, services, and more about our company!")

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in {"exit", "quit", "q"}:
            print("\nAgent: You're very welcome! I'm always here to help you.")
            break
        if not user_input:
            continue

        reply = send_message_with_fallback(state, user_input)
        print(f"\nAgent: {reply}\n")


if __name__ == "__main__":
    start_customer_service_agent()