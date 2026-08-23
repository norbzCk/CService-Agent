from typing import Any

DEMO_PRODUCTS = [
    {
        "id": 1,
        "name": "Leather Belt",
        "description": "Classic genuine leather belt.",
        "price": 3500,
        "category": "Fashion",
        "seller": "Demo Fashion Store",
        "stock": 12,
    },
    {
        "id": 2,
        "name": "Casual Belt",
        "description": "Adjustable casual belt for everyday use.",
        "price": 2800,
        "category": "Fashion",
        "seller": "Demo Fashion Store",
        "stock": 25,
    },
    {
        "id": 3,
        "name": "Samsung Galaxy A55",
        "description": "Samsung Galaxy A55 smartphone.",
        "price": 850000,
        "category": "Phones",
        "seller": "Demo Electronics",
        "stock": 7,
    },
    {
        "id": 4,
        "name": "Cement 50kg",
        "description": "50kg bag of construction cement.",
        "price": 18500,
        "category": "Construction",
        "seller": "Demo Building Supplies",
        "stock": 100,
    },
]


def search_products(
    query: str,
    max_price: float | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    """
    Search products currently listed on Soko-Link.
    Use this tool when a customer asks to:
    - Find a product
    - Search for a product
    - Check whether a product is available
    - Find products within a maximum price
    - Find products in a specific category

    Do not use this tool for:
    - Order status
    - Delivery status
    - Account information
    - Seller verification

    Args:
        query:
            The product name or keywords the customer is
            looking for.

        max_price:
            Optional maximum price the customer wants to pay.

        category:
            Optional product category.

    Returns:
        A structured result containing matching products.
    """
    search_term = query.strip().lower()

    if not search_term:
        return {
            "success": False,
            "message": "A product search term is required.",
            "products": [],
        }

    results = []

    for product in DEMO_PRODUCTS:
        searchable_text = " ".join(
            [
                product["name"],
                product["description"],
                product["category"],
            ]
        ).lower()

        if search_term not in searchable_text:
            continue

        if max_price is not None and product["price"] > max_price:
            continue

        if (
            category is not None
            and product["category"].lower() != category.strip().lower()
        ):
            continue

        results.append(product)

    if not results:
        return {
            "success": True,
            "found": False,
            "message": f"No products matching '{query}' were found.",
            "products": [],
        }

    return {
        "success": True,
        "found": True,
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
    for product in DEMO_PRODUCTS:
        if product["id"] == product_id:
            return {
                "success": True,
                "found": True,
                "product": product,
            }

    return {
        "success": True,
        "found": False,
        "message": "Product not found.",
        "product": None,
    }

