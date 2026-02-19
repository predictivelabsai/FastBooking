"""Orders page — order history + detail."""

from __future__ import annotations

from fasthtml.common import *

from app.ui.components import layout, order_card, status_badge


def register_routes(app, client, get_user_id):
    @app.get("/orders")
    async def orders_page(request):
        user_id = await get_user_id()
        orders = await client.list_orders(user_id)

        if not orders:
            return layout(
                H1(cls="text-2xl font-bold text-gray-800 mb-4")("Your Orders"),
                P(cls="text-gray-500 py-8 text-center")("No orders yet."),
                A(href="/", cls="text-green-600 hover:underline")("Browse restaurants"),
                title="Orders — FoodAngels",
            )

        return layout(
            H1(cls="text-2xl font-bold text-gray-800 mb-4")("Your Orders"),
            Div(cls="grid grid-cols-1 md:grid-cols-2 gap-4")(
                *[order_card(o) for o in orders]
            ),
            title="Orders — FoodAngels",
        )

    @app.get("/orders/{order_id}")
    async def order_detail(request, order_id: int):
        user_id = await get_user_id()
        o = await client.get_order(user_id, order_id)
        if not o:
            return layout(
                P(cls="text-center text-gray-500 py-8")("Order not found"),
                title="Not Found",
            )

        product_rows = []
        for p in o.get("products", []):
            product_rows.append(
                Div(cls="flex items-center justify-between py-2 border-b border-gray-100")(
                    Div()(
                        Span(cls="text-gray-800")(p["product_name"]),
                        Span(cls="text-gray-400 text-sm ml-2")(f'x{p["quantity"]}'),
                    ),
                    Div(cls="text-right")(
                        Span(cls="text-gray-700")(f'{p["current_price"]} EUR'),
                        (
                            Span(cls="text-gray-400 line-through text-sm ml-2")(
                                f'{p["old_price"]} EUR'
                            )
                            if p["old_price"] != p["current_price"]
                            else ""
                        ),
                    ),
                )
            )

        return layout(
            Div(cls="max-w-2xl mx-auto")(
                Div(cls="flex items-center justify-between mb-4")(
                    H1(cls="text-2xl font-bold text-gray-800")(
                        f'Order #{o.get("number_order", o["id"])}'
                    ),
                    status_badge(o.get("status", "new")),
                ),
                Div(
                    cls="bg-white rounded-lg shadow-sm p-4",
                    hx_get=f"/orders/{order_id}/status",
                    hx_trigger="every 10s",
                    hx_target="#order-status",
                    hx_swap="innerHTML",
                )(
                    Div(id="order-status", cls="mb-4")(
                        P(cls="text-gray-600 text-sm")(
                            "Status: ",
                            status_badge(o.get("status", "new")),
                        ),
                    ),
                    H3(cls="font-semibold text-gray-700 mb-2")("Items"),
                    *product_rows,
                    Div(cls="flex justify-between mt-3 pt-3 border-t border-gray-200")(
                        Span(cls="font-semibold text-gray-700")("Total"),
                        Span(cls="font-bold text-green-700")(
                            f'{o.get("final_price", "0")} EUR'
                        ),
                    ),
                    (
                        Div(cls="mt-3")(
                            P(cls="text-gray-500 text-sm")(
                                f'Message: {o["customer_message"]}'
                            )
                        )
                        if o.get("customer_message")
                        else ""
                    ),
                    (
                        Div(cls="mt-2")(
                            P(cls="text-gray-500 text-sm")(
                                f'Pickup: {o["pickup_time"]}'
                            )
                        )
                        if o.get("pickup_time")
                        else ""
                    ),
                ),
                Div(cls="mt-4")(
                    A(href="/orders", cls="text-green-600 hover:underline text-sm")(
                        "Back to orders"
                    ),
                ),
            ),
            title=f'Order #{o.get("number_order", o["id"])} — FoodAngels',
        )

    @app.get("/orders/{order_id}/status")
    async def order_status_poll(request, order_id: int):
        user_id = await get_user_id()
        o = await client.get_order(user_id, order_id)
        if not o:
            return P(cls="text-gray-400")("Unknown")
        return P(cls="text-gray-600 text-sm")(
            "Status: ", status_badge(o.get("status", "new"))
        )
