# tools/delivery.py
from typing import Any
from database.connection import run_query


def get_delivery_status(order_id: int, customer_email: str) -> dict[str, Any]:
    """
    Look up delivery/tracking status for a specific order.
    Use when a customer asks where their delivery is or courier progress.
    Requires order ID + email verification, same as get_order_status.

    Args:
        order_id: The order's numeric ID.
        customer_email: Email on the customer's account.
    """
    rows = run_query(
        """
        SELECT d.status, d.pickup_location, d.delivery_location,
               d.last_location_name, d.picked_at, d.delivered_at, d.failure_reason
        FROM delivery_orders d
        JOIN orders o ON o.id = d.order_id
        JOIN users u ON u.id = o.customer_id
        WHERE o.id = %(order_id)s AND u.email = %(email)s
        ORDER BY d.created_at DESC
        LIMIT 1
        """,
        {"order_id": order_id, "email": customer_email},
    )
    if not rows:
        return {"found": False, "message": "No delivery information was found for that order."}
    return {"found": True, "delivery": rows[0]}