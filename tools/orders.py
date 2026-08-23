# tools/orders.py  (in CService-Agent, standalone)
from typing import Any
from database.connection import run_query


def get_order_status(order_id: int, customer_email: str) -> dict[str, Any]:
    """
    Look up the status of a specific order.
    Use when a customer asks about an order's status, e.g. "where is my
    order", "is order 42 confirmed". Requires the customer to confirm
    both the order ID and the email on their account -- never look up
    an order without both, so customers can't see each other's orders.

    Args:
        order_id: The order's numeric ID.
        customer_email: Email on the customer's account, to verify ownership.
    """
    rows = run_query(
        """
        SELECT o.id, o.status, o.status_reason, o.total_amount, o.item_count,
               o.delivery_method, o.created_at, o.updated_at
        FROM orders o
        JOIN users u ON u.id = o.customer_id
        WHERE o.id = %(order_id)s AND u.email = %(email)s
        """,
        {"order_id": order_id, "email": customer_email},
    )
    if not rows:
        return {"found": False, "message": "No matching order was found for that order ID and email."}

    order = rows[0]
    items = run_query(
        "SELECT product_name, quantity, status FROM order_items WHERE order_id = %(order_id)s",
        {"order_id": order_id},
    )
    order["items"] = items
    return {"found": True, "order": order}


def list_recent_orders(customer_email: str, limit: int = 5) -> dict[str, Any]:
    """
    List a customer's most recent orders (id + status only).
    Use when they ask "what are my orders" without a specific order ID.

    Args:
        customer_email: Email on the customer's account.
        limit: Max orders to return (default 5, max 10).
    """
    limit = max(1, min(limit, 10))
    rows = run_query(
        """
        SELECT o.id, o.status, o.total_amount, o.created_at
        FROM orders o
        JOIN users u ON u.id = o.customer_id
        WHERE u.email = %(email)s
        ORDER BY o.created_at DESC
        LIMIT %(limit)s
        """,
        {"email": customer_email, "limit": limit},
    )
    return {"orders": rows}