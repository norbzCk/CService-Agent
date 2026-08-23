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

load_dotenv()

logger = logging.getLogger(__name__)

MODEL_FALLBACK_LIST = ["gemini-3.7-flash", "gemini-3.5-flash", "gemini-2.5-flash","gemini-1.5-flash"]

BASE_DIR = Path(__file__).resolve().parent
SYSTEM_INSTRUCTION_FILE = BASE_DIR / "knowledge" / "system_instructions.md"


client = genai.Client(api_key=os.environ.get("GEMINIAI_API_KEY"))


def print_time(label: str = "Current time") -> None:
    """Print the current local time in a simple, readable format."""
    now = datetime.now()
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
    print(f"{label}: {formatted_time}")


def load_system_instructions() -> str:
    """Load system instructions from the system_instructions.md file."""    
    with open(SYSTEM_INSTRUCTION_FILE, "r", encoding="utf-8") as f:
        return f.read()

def build_system_instruction() -> str:
    """
    Build the complete system instruction used by Gemini.
    The system instruction contains the agent's behavior and
    relevant company knowledge.
    """

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

## Create a support agent that uses the Gemini API to respond to user queries.
def create_support_agent():
    """ Create the customer service chat using the first
        available Gemini model from MODEL_FALLBACK_LIST.
        Models are tried in order from highest priority to
        lowest priority.
        Returns:
            tuple: (chat, active_model)

        Raises:
            RuntimeError:
               If all configured models are unavailable.
    """
    system_instruction = build_system_instruction()

    tools = [
            search_products,
            get_product,
        ]

    for model_name in MODEL_FALLBACK_LIST:
        try:
            logger.info("Trying Gemini model : %s", model_name)
            chat = client.chats.create(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    thinking_config=types.ThinkingConfig(
                        thinking_level="low",
                    ),
                    tools=tools,
                ),
            )
            return chat, model_name
        
        except (ServerError, APIError) as error:

            print(
                f"Model {model_name} unavailable."
            )
            print(
                "Trying next fallback model...\n"
            )

            continue

    raise RuntimeError(
        "All Gemini models in MODEL_FALLBACK_LIST "
        "are currently unavailable."
    )


#A function to start the customer service agent

def start_customer_service_agent():
    """Start the customer service agent and handle user queries."""
    try:
        chat, _active_model = create_support_agent()
    except Exception as error:
        print("\nFailed to initialize the customer service support agent.")
        print(f"Error: {error}")
        return

    print()
    print("="*80)
    print("SOKO-LINK CUSTOMER SERVICE AGENT")
    print_time("Session started")
    print("Welcome, I am Soko-Link's customer service agent. You can ask me questions about our products, services, and more about our company!")


    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in {"exit", "quit", "q"}:
            print(
                "\nAgent: You're very welcome! "
                "I'm always here to help you."
            )
            break
        if not user_input:
            continue

        try:
            response = chat.send_message(user_input)

            print(
                f"\nAgent: {response.text}\n"
            )

        except ServerError as error:

            print(
                "\nAgent: I'm sorry, I'm experiencing "
                "a temporary service issue. "
                "Please try again in a moment.\n"
            )
        except APIError as error:
            print(
                "\nAgent: I'm sorry, I couldn't process "
                "your request right now. Please try again.\n"
            )
        except Exception as error:
            logger.exception(
                "Unexpected error while processing customer message: %r",
                error,
            )
            print(
                "\nAgent: An unexpected error occurred. "
                "Please try again later.\n"
            )

if __name__ == "__main__":
    start_customer_service_agent()