"""Admin pages — dashboard, products CRUD, orders management."""

from __future__ import annotations

from decimal import Decimal

from fasthtml.common import *

from app.ui.components import layout, product_card, status_badge


def register_routes(app, client, get_admin_user_id):
    # ── Dashboard ────────────────────────────────────────────────────────
    @app.get("/admin")
    async def admin_dashboard(request):
        user_id = await get_admin_user_id()
        rest = await client.admin_get_restaurant(user_id)
        if not rest:
            return layout(
                H1(cls="text-2xl font-bold text-gray-800 mb-4")("Admin Dashboard"),
                P(cls="text-gray-500 py-8 text-center")(
                    "No restaurant linked to this account."
                ),
                title="Admin — FoodAngels",
            )

        avail_cls = "bg-green-500" if rest.get("available") else "bg-red-500"
        avail_text = "Open" if rest.get("available") else "Closed"

        return layout(
            H1(cls="text-2xl font-bold text-gray-800 mb-4")("Admin Dashboard"),
            Div(cls="bg-white rounded-lg shadow-sm p-6 mb-6")(
                H2(cls="text-xl font-semibold text-gray-800 mb-2")(rest["name"]),
                P(cls="text-gray-500")(rest.get("address", "")),
                Div(cls="flex items-center gap-3 mt-4")(
                    Span(cls=f"px-3 py-1 text-white rounded-full text-sm {avail_cls}")(
                        avail_text
                    ),
                    Button(
                        hx_put="/admin/toggle-availability",
                        hx_target="body",
                        cls="text-sm text-orange-600 hover:text-orange-800 underline",
                    )("Toggle availability"),
                ),
            ),
            Div(cls="grid grid-cols-1 md:grid-cols-3 gap-4")(
                A(
                    href="/admin/products",
                    cls="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition text-center",
                )(
                    H3(cls="font-semibold text-gray-800")("Products"),
                    P(cls="text-gray-500 text-sm mt-1")("Manage your menu"),
                ),
                A(
                    href="/admin/orders",
                    cls="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition text-center",
                )(
                    H3(cls="font-semibold text-gray-800")("Orders"),
                    P(cls="text-gray-500 text-sm mt-1")("View and manage orders"),
                ),
            ),
            title="Admin — FoodAngels",
        )

    @app.put("/admin/toggle-availability")
    async def toggle_avail(request):
        user_id = await get_admin_user_id()
        await client.admin_toggle_availability(user_id)
        return RedirectResponse("/admin", status_code=303)

    # ── Products ─────────────────────────────────────────────────────────
    @app.get("/admin/products")
    async def admin_products(request):
        user_id = await get_admin_user_id()
        products = await client.admin_list_products(user_id)

        rows = []
        for p in products:
            rows.append(
                Tr()(
                    Td(cls="px-4 py-2 text-gray-800")(p["name"]),
                    Td(cls="px-4 py-2 text-gray-600")(f'{p["current_price"]} EUR'),
                    Td(cls="px-4 py-2 text-gray-600")(f'{p["old_price"]} EUR'),
                    Td(cls="px-4 py-2 text-gray-600")(str(p["quantity"])),
                    Td(cls="px-4 py-2")(
                        Button(
                            hx_delete=f'/admin/products/{p["id"]}/delete',
                            hx_target="body",
                            hx_confirm="Delete this product?",
                            cls="text-red-500 hover:text-red-700 text-sm",
                        )("Delete")
                    ),
                )
            )

        return layout(
            Div(cls="flex items-center justify-between mb-4")(
                H1(cls="text-2xl font-bold text-gray-800")("Products"),
                A(
                    href="/admin",
                    cls="text-orange-600 hover:underline text-sm",
                )("Back to dashboard"),
            ),
            # Add product form
            Div(cls="bg-white rounded-lg shadow-sm p-4 mb-6")(
                H3(cls="font-semibold text-gray-700 mb-3")("Add Product"),
                Form(hx_post="/admin/products/add", hx_target="body", cls="space-y-3")(
                    Div(cls="grid grid-cols-1 md:grid-cols-2 gap-3")(
                        Input(
                            type="text",
                            name="name",
                            placeholder="Product name",
                            required=True,
                            cls="px-3 py-2 border border-gray-300 rounded text-sm",
                        ),
                        Input(
                            type="text",
                            name="description",
                            placeholder="Description",
                            cls="px-3 py-2 border border-gray-300 rounded text-sm",
                        ),
                        Input(
                            type="number",
                            name="current_price",
                            placeholder="Current price",
                            step="0.01",
                            required=True,
                            cls="px-3 py-2 border border-gray-300 rounded text-sm",
                        ),
                        Input(
                            type="number",
                            name="old_price",
                            placeholder="Old price",
                            step="0.01",
                            required=True,
                            cls="px-3 py-2 border border-gray-300 rounded text-sm",
                        ),
                        Input(
                            type="number",
                            name="quantity",
                            placeholder="Quantity",
                            value="1",
                            cls="px-3 py-2 border border-gray-300 rounded text-sm",
                        ),
                    ),
                    Div(cls="flex flex-wrap gap-3")(
                        Label(cls="flex items-center gap-1 text-sm")(
                            Input(type="checkbox", name="meals"), "Meals"
                        ),
                        Label(cls="flex items-center gap-1 text-sm")(
                            Input(type="checkbox", name="pastries"), "Pastries"
                        ),
                        Label(cls="flex items-center gap-1 text-sm")(
                            Input(type="checkbox", name="drinks"), "Drinks"
                        ),
                        Label(cls="flex items-center gap-1 text-sm")(
                            Input(type="checkbox", name="vegetarian"), "Vegetarian"
                        ),
                        Label(cls="flex items-center gap-1 text-sm")(
                            Input(type="checkbox", name="vegan"), "Vegan"
                        ),
                    ),
                    Button(
                        type="submit",
                        cls="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded text-sm",
                    )("Add Product"),
                ),
            ),
            # Products table
            Div(cls="bg-white rounded-lg shadow-sm overflow-hidden")(
                Table(cls="w-full")(
                    Thead(cls="bg-gray-50")(
                        Tr()(
                            Th(cls="px-4 py-2 text-left text-gray-600 text-sm")("Name"),
                            Th(cls="px-4 py-2 text-left text-gray-600 text-sm")("Price"),
                            Th(cls="px-4 py-2 text-left text-gray-600 text-sm")("Old Price"),
                            Th(cls="px-4 py-2 text-left text-gray-600 text-sm")("Qty"),
                            Th(cls="px-4 py-2 text-left text-gray-600 text-sm")("Actions"),
                        ),
                    ),
                    Tbody()(*rows) if rows else Tbody()(
                        Tr()(
                            Td(colspan="5", cls="px-4 py-8 text-center text-gray-500")(
                                "No products yet"
                            )
                        )
                    ),
                ),
            ),
            title="Products — Admin — FoodAngels",
        )

    @app.post("/admin/products/add")
    async def add_product(request):
        user_id = await get_admin_user_id()
        form = await request.form()
        data = {
            "name": form.get("name", ""),
            "description": form.get("description", ""),
            "current_price": str(form.get("current_price", "0")),
            "old_price": str(form.get("old_price", "0")),
            "quantity": int(form.get("quantity", 1)),
            "meals": "meals" in form,
            "pastries": "pastries" in form,
            "drinks": "drinks" in form,
            "vegetarian": "vegetarian" in form,
            "vegan": "vegan" in form,
        }
        await client.admin_create_product(user_id, data)
        return RedirectResponse("/admin/products", status_code=303)

    @app.delete("/admin/products/{product_id}/delete")
    async def delete_product(request, product_id: int):
        user_id = await get_admin_user_id()
        await client.admin_delete_product(user_id, product_id)
        return RedirectResponse("/admin/products", status_code=303)

    # ── Orders ───────────────────────────────────────────────────────────
    @app.get("/admin/orders")
    async def admin_orders(request):
        user_id = await get_admin_user_id()
        orders = await client.admin_list_orders(user_id)

        cards = []
        for o in orders:
            action_buttons = []
            if o.get("status") in ("new", "pending"):
                action_buttons.extend([
                    Button(
                        hx_put=f'/admin/orders/{o["id"]}/accept',
                        hx_target="body",
                        cls="bg-green-500 hover:bg-green-600 text-white text-sm px-3 py-1 rounded",
                    )("Accept"),
                    Button(
                        hx_put=f'/admin/orders/{o["id"]}/refuse',
                        hx_target="body",
                        cls="bg-red-500 hover:bg-red-600 text-white text-sm px-3 py-1 rounded",
                    )("Refuse"),
                ])
            elif o.get("status") == "accepted":
                action_buttons.append(
                    Button(
                        hx_put=f'/admin/orders/{o["id"]}/done',
                        hx_target="body",
                        cls="bg-blue-500 hover:bg-blue-600 text-white text-sm px-3 py-1 rounded",
                    )("Mark Done")
                )

            product_list = Ul(cls="mt-2 text-sm text-gray-600")(
                *[
                    Li()(f'{p["product_name"]} x{p["quantity"]} — {p["current_price"]} EUR')
                    for p in o.get("products", [])
                ]
            )

            cards.append(
                Div(cls="bg-white rounded-lg shadow-sm p-4")(
                    Div(cls="flex items-center justify-between mb-2")(
                        Span(cls="font-semibold text-gray-800")(
                            f'Order #{o.get("number_order", o["id"])}'
                        ),
                        status_badge(o.get("status", "new")),
                    ),
                    P(cls="text-gray-500 text-sm")(
                        f'Total: {o.get("final_price", "0")} EUR'
                    ),
                    product_list,
                    (
                        P(cls="text-gray-400 text-xs mt-1")(
                            f'Message: {o["customer_message"]}'
                        )
                        if o.get("customer_message")
                        else ""
                    ),
                    Div(cls="flex gap-2 mt-3")(*action_buttons) if action_buttons else "",
                )
            )

        return layout(
            Div(cls="flex items-center justify-between mb-4")(
                H1(cls="text-2xl font-bold text-gray-800")("Orders"),
                A(href="/admin", cls="text-orange-600 hover:underline text-sm")(
                    "Back to dashboard"
                ),
            ),
            Div(
                cls="grid grid-cols-1 md:grid-cols-2 gap-4",
                hx_get="/admin/orders",
                hx_trigger="every 15s",
                hx_target="body",
                hx_swap="innerHTML",
            )(
                *cards if cards else [P(cls="text-gray-500 col-span-full text-center py-8")("No orders yet")]
            ),
            title="Orders — Admin — FoodAngels",
        )

    @app.put("/admin/orders/{order_id}/accept")
    async def accept_order(request, order_id: int):
        user_id = await get_admin_user_id()
        await client.admin_update_order_status(user_id, order_id, "accepted")
        return RedirectResponse("/admin/orders", status_code=303)

    @app.put("/admin/orders/{order_id}/refuse")
    async def refuse_order(request, order_id: int):
        user_id = await get_admin_user_id()
        await client.admin_update_order_status(user_id, order_id, "refused")
        return RedirectResponse("/admin/orders", status_code=303)

    @app.put("/admin/orders/{order_id}/done")
    async def done_order(request, order_id: int):
        user_id = await get_admin_user_id()
        await client.admin_update_order_status(user_id, order_id, "done")
        return RedirectResponse("/admin/orders", status_code=303)
