from typing import Any
from database.connection import run_query


def build_payment_tools(customer_email: str):
    """Build payment-lookup tools bound to one authenticated customer's email."""

    def get_payment_status(order_id: int) -> dict[str, Any]:
        """
        Look up payment status (paid/pending/failed/refunded) for one of the
        current customer's own orders. Use when they ask whether a payment
        went through or about a refund.

        Args:
            order_id: The order's numeric ID.
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

    return [get_payment_status]
