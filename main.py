"""
Local CLI for testing the agent directly, without the HTTP layer.
The real deployed entry point is api.py (run via uvicorn).
"""
from datetime import datetime

from agent_core import create_agent_session, send_message_with_fallback
from tools.products import search_products, get_product
from tools.orders import build_order_tools
from tools.delivery import build_delivery_tools
from tools.payment import build_payment_tools
from knowledge.retrieve_knowledge import retrieve_knowledge


def print_time(label: str = "Current time") -> None:
    now = datetime.now()
    print(f"{label}: {now.strftime('%Y-%m-%d %H:%M:%S')}")


def start_customer_service_agent():
    # For local CLI testing, optionally simulate a logged-in customer by
    # setting a test email here -- leave as None to test guest mode.
    test_customer_email = None  # e.g. "someone@example.com"

    tools = [search_products, get_product, retrieve_knowledge]
    if test_customer_email:
        tools += build_order_tools(test_customer_email)
        tools += build_delivery_tools(test_customer_email)
        tools += build_payment_tools(test_customer_email)

    try:
        state = create_agent_session(tools)
    except Exception as error:
        print("\nFailed to initialize the customer service support agent.")
        print(f"Error: {error}")
        return

    print()
    print("=" * 80)
    print("SOKO-LINK CUSTOMER SERVICE AGENT (local CLI)")
    print_time("Session started")
    mode = f"authenticated as {test_customer_email}" if test_customer_email else "guest mode"
    print(f"Welcome! Running in {mode}.")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nAgent: Goodbye! Have a great day.")
            break

        if user_input.lower() in {"exit", "quit", "q"}:
            print("\nAgent: You're very welcome! I'm always here to help you.")
            break
        if not user_input:
            continue

        reply = send_message_with_fallback(state, user_input)
        print(f"\nAgent: {reply}\n")


if __name__ == "__main__":
    start_customer_service_agent()
