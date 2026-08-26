from typing import Any
from database.connection import run_query


def build_delivery_tools(customer_email: str):
    """Build delivery-lookup tools bound to one authenticated customer's email."""

    def get_delivery_status(order_id: int) -> dict[str, Any]:
        """
        Look up delivery/tracking status for one of the current customer's
        own orders. Use when they ask where their delivery is or courier progress.

        Args:
            order_id: The order's numeric ID.
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

    return [get_delivery_status]
