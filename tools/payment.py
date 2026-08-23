# tools/payments.py
from typing import Any
from database.connection import run_query


def get_payment_status(order_id: int, customer_email: str) -> dict[str, Any]:
    """
    Look up payment status (paid/pending/failed/refunded) for a specific order.
    Use when a customer asks whether a payment went through or about a refund.
    Requires order ID + email verification, same as get_order_status.

    Args:
        order_id: The order's numeric ID.
        customer_email: Email on the customer's account.
    """
    rows = run_query(
        """
        SELECT p.status, p.amount, p.payment_method, p.provider, p.message, p.confirmed_at
        FROM payment_transactions p
        JOIN orders o ON o.id = p.order_id
        JOIN users u ON u.id = o.customer_id
        WHERE o.id = %(order_id)s AND u.email = %(email)s
        ORDER BY p.created_at DESC
        LIMIT 1
        """,
        {"order_id": order_id, "email": customer_email},
    )
    if not rows:
        return {"found": False, "message": "No payment record was found for that order."}
    return {"found": True, "payment": rows[0]}