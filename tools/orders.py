from typing import Any
from database.connection import run_query


def build_order_tools(customer_email: str):
    """
    Build order-lookup tools bound to one authenticated customer's email.
    The model never supplies or sees the email -- it's fixed server-side
    from the verified Supabase token, so there's no way for the model
    (or a malicious prompt) to fetch another customer's orders.
    """

    def get_order_status(order_id: int) -> dict[str, Any]:
        """
        Look up the status of one of the current customer's own orders.
        Use when they ask "where is my order", "is order 42 confirmed", etc.

        Args:
            order_id: The order's numeric ID, as given by the customer.
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
            return {"found": False, "message": "No matching order was found on your account."}

        order = rows[0]
        items = run_query(
            "SELECT product_name, quantity, status FROM order_items WHERE order_id = %(order_id)s",
            {"order_id": order_id},
        )
        order["items"] = items
        return {"found": True, "order": order}

    def list_recent_orders(limit: int = 5) -> dict[str, Any]:
        """
        List the current customer's most recent orders (id + status only).
        Use when they ask "what are my orders" without a specific order ID.

        Args:
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

    return [get_order_status, list_recent_orders]
