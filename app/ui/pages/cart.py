"""Cart page — items grouped by restaurant, place order."""

from __future__ import annotations

from fasthtml.common import *

from app.ui.components import layout, status_badge


def register_routes(app, client, get_user_id):
    @app.get("/cart")
    async def cart_page(request):
        user_id = await get_user_id()
        items = await client.get_cart(user_id)
        if not items:
            return layout(
                H1(cls="text-2xl font-bold text-gray-800 mb-4")("Your Cart"),
                P(cls="text-gray-500 py-8 text-center")("Your cart is empty."),
                A(href="/", cls="text-green-600 hover:underline")("Browse restaurants"),
                title="Cart — FoodAngels",
            )

        # Group items by restaurant
        by_restaurant: dict[int, list[dict]] = {}
        for item in items:
            rid = item.get("restaurant_id", 0)
            by_restaurant.setdefault(rid, []).append(item)

        sections = []
        for rid, cart_items in by_restaurant.items():
            restaurant = await client.get_restaurant(rid) if rid else None
            r_name = restaurant["name"] if restaurant else f"Restaurant #{rid}"

            rows = []
            total = 0.0
            for ci in cart_items:
                product = await client.get_product(ci.get("product_id", 0))
                if product:
                    price = float(product["current_price"]) * ci.get("quantity", 1)
                    total += price
                    rows.append(
                        Div(cls="flex items-center justify-between py-2 border-b border-gray-100")(
                            Div()(
                                Span(cls="text-gray-800")(product["name"]),
                                Span(cls="text-gray-400 text-sm ml-2")(
                                    f'x{ci.get("quantity", 1)}'
                                ),
                            ),
                            Span(cls="text-gray-700 font-medium")(f"{price:.2f} EUR"),
                        )
                    )

            sections.append(
                Div(cls="bg-white rounded-lg shadow-sm p-4 mb-4")(
                    H3(cls="font-semibold text-gray-800 mb-3")(r_name),
                    *rows,
                    Div(cls="flex justify-between mt-3 pt-3 border-t border-gray-200")(
                        Span(cls="font-semibold text-gray-700")("Subtotal"),
                        Span(cls="font-bold text-green-700")(f"{total:.2f} EUR"),
                    ),
                    Form(
                        hx_post=f"/cart/order/{rid}",
                        hx_target="#cart-result",
                        hx_swap="innerHTML",
                        cls="mt-3",
                    )(
                        Input(
                            type="text",
                            name="customer_message",
                            placeholder="Add a message (optional)",
                            cls="w-full px-3 py-2 border border-gray-300 rounded-lg mb-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none",
                        ),
                        Button(
                            type="submit",
                            cls="w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded-full font-semibold",
                        )("Place Order"),
                    ),
                )
            )

        return layout(
            H1(cls="text-2xl font-bold text-gray-800 mb-4")("Your Cart"),
            Div(id="cart-result")(),
            *sections,
            Div(cls="mt-4")(
                Button(
                    hx_delete="/cart/clear",
                    hx_target="body",
                    cls="text-red-500 hover:text-red-700 text-sm",
                )("Clear entire cart"),
            ),
            title="Cart — FoodAngels",
        )

    @app.post("/cart/add/{product_id}")
    async def add_to_cart(request, product_id: int):
        user_id = await get_user_id()
        product = await client.get_product(product_id)
        if not product:
            return Span(cls="text-red-500 text-sm")("Product not found")

        items = await client.get_cart(user_id)
        # check if already in cart
        found = False
        for item in items:
            if item.get("product_id") == product_id:
                item["quantity"] = item.get("quantity", 1) + 1
                found = True
                break
        if not found:
            items.append(
                {
                    "restaurant_id": product["restaurant_id"],
                    "product_id": product_id,
                    "quantity": 1,
                }
            )
        await client.update_cart(user_id, items)
        return Span(cls="text-green-600 text-sm")("Added!")

    @app.post("/cart/order/{restaurant_id}")
    async def place_order(request, restaurant_id: int):
        user_id = await get_user_id()
        form = await request.form()
        message = form.get("customer_message", "")

        items = await client.get_cart(user_id)
        order_items = [
            {"product_id": i["product_id"], "quantity": i.get("quantity", 1)}
            for i in items
            if i.get("restaurant_id") == restaurant_id
        ]

        if not order_items:
            return Div(cls="bg-red-50 text-red-700 p-3 rounded mb-4")(
                "No items for this restaurant in cart."
            )

        order = await client.create_order(
            user_id,
            {
                "restaurant_id": restaurant_id,
                "products": order_items,
                "customer_message": message or None,
            },
        )

        # remove ordered items from cart
        remaining = [i for i in items if i.get("restaurant_id") != restaurant_id]
        await client.update_cart(user_id, remaining)

        return Div(cls="bg-green-50 text-green-700 p-3 rounded mb-4")(
            f'Order #{order.get("number_order", order["id"])} placed successfully! ',
            A(
                href=f'/orders/{order["id"]}',
                cls="text-green-800 underline font-medium",
            )("View order"),
        )

    @app.delete("/cart/clear")
    async def clear_cart_page(request):
        user_id = await get_user_id()
        await client.clear_cart(user_id)
        return RedirectResponse("/cart", status_code=303)
