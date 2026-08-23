from typing import Any, Literal

from database.connection import run_query

VALID_SORT = {
    "relevance": "p.rating_avg DESC, p.id DESC",
    "price_low": "p.price ASC, p.id DESC",
    "price_high": "p.price DESC, p.id DESC",
    "rating": "p.rating_avg DESC, p.rating_count DESC",
    "newest": "p.id DESC",
}


def search_products(
    query: str,
    min_price: float | None = None,
    max_price: float | None = None,
    category: str | None = None,
    in_stock_only: bool = True,
    sort_by: Literal["relevance", "price_low", "price_high", "rating", "newest"] = "relevance",
    limit: int = 8,
) -> dict[str, Any]:
    """
    Search products currently listed on Soko-Link.
    Use this tool when a customer asks to:
    - Find a product
    - Search for a product
    - Check whether a product is available
    - Find products within a price range
    - Find products in a specific category
    - Compare or browse products by price or rating

    Do not use this tool for:
    - Order status
    - Delivery status
    - Payment status
    - Account information
    - Seller verification

    Args:
        query:
            The product name or keywords the customer is looking for.
        min_price:
            Optional minimum price the customer wants to pay.
        max_price:
            Optional maximum price the customer wants to pay.
        category:
            Optional product category to filter by.
        in_stock_only:
            If true (default), only return products currently in stock.
            Set false if the customer explicitly asks to see out-of-stock items.
        sort_by:
            How to order results: "relevance" (default), "price_low",
            "price_high", "rating", or "newest".
        limit:
            Max results to return (default 8, capped at 20).

    Returns:
        A structured result containing matching products.
    """
    search_term = query.strip()

    if not search_term:
        return {
            "success": False,
            "message": "A product search term is required.",
            "products": [],
        }

    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = max_price, min_price

    limit = max(1, min(limit, 20))
    order_clause = VALID_SORT.get(sort_by, VALID_SORT["relevance"])

    conditions = [
        "p.is_active = TRUE",
        "(p.name ILIKE %(term)s OR p.description ILIKE %(term)s OR p.category ILIKE %(term)s)",
    ]
    params: dict[str, Any] = {"term": f"%{search_term}%", "limit": limit}

    if min_price is not None:
        conditions.append("p.price >= %(min_price)s")
        params["min_price"] = min_price

    if max_price is not None:
        conditions.append("p.price <= %(max_price)s")
        params["max_price"] = max_price

    if category is not None and category.strip():
        conditions.append("p.category ILIKE %(category)s")
        params["category"] = category.strip()

    if in_stock_only:
        conditions.append("p.stock > 0")

    sql = f"""
        SELECT p.id, p.name, p.description, p.price, p.category, p.stock,
               p.rating_avg, p.rating_count,
               b.business_name AS seller
        FROM products p
        LEFT JOIN business_users b ON b.id = p.seller_id
        WHERE {' AND '.join(conditions)}
        ORDER BY {order_clause}
        LIMIT %(limit)s
    """

    try:
        results = run_query(sql, params)
    except Exception:
        return {
            "success": False,
            "message": "I couldn't search products right now due to a system issue. Please try again shortly.",
            "products": [],
        }

    if not results:
        return {
            "success": True,
            "found": False,
            "message": f"No products matching '{query}' were found with those filters.",
            "products": [],
        }

    return {
        "success": True,
        "found": True,
        "count": len(results),
        "products": results,
    }


def get_product(
    product_id: int,
) -> dict[str, Any]:
    """
    Get detailed information about a specific product.

    Use this tool when a customer asks about a specific
    product and provides its product ID.

    Args:
        product_id:
            The unique ID of the product.

    Returns:
        A structured result containing the product,
        or a not-found result.
    """
    try:
        rows = run_query(
            """
            SELECT p.id, p.name, p.description, p.price, p.category, p.stock,
                   p.rating_avg, p.rating_count,
                   b.business_name AS seller
            FROM products p
            LEFT JOIN business_users b ON b.id = p.seller_id
            WHERE p.id = %(product_id)s AND p.is_active = TRUE
            """,
            {"product_id": product_id},
        )
    except Exception:
        return {
            "success": False,
            "message": "I couldn't look up that product right now due to a system issue. Please try again shortly.",
            "product": None,
        }

    if not rows:
        return {
            "success": True,
            "found": False,
            "message": "Product not found.",
            "product": None,
        }

    return {
        "success": True,
        "found": True,
        "product": rows[0],
    }