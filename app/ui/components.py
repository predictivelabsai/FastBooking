"""Shared FastHTML components: layout shell, nav, cards, badges."""

from __future__ import annotations

from fasthtml.common import *


# ── Layout shell ─────────────────────────────────────────────────────────
def layout(*children, title: str = "FoodAngels"):
    return (
        Title(title),
        Html(
            Head(
                Meta(charset="utf-8"),
                Meta(name="viewport", content="width=device-width, initial-scale=1"),
                Script(src="https://cdn.tailwindcss.com"),
                Script(src="https://unpkg.com/htmx.org@2.0.4"),
                Title(title),
            ),
            Body(
                cls="bg-gray-50 min-h-screen flex flex-col",
            )(
                nav_bar(),
                Main(cls="flex-1 container mx-auto px-4 py-6 max-w-6xl")(*children),
                footer(),
            ),
        ),
    )


def nav_bar():
    return Header(cls="bg-white shadow-sm sticky top-0 z-50")(
        Nav(cls="container mx-auto px-4 py-3 max-w-6xl flex items-center justify-between")(
            A(href="/", cls="text-xl font-bold text-orange-600")("FoodAngels"),
            Div(cls="flex items-center gap-4")(
                A(href="/", cls="text-gray-600 hover:text-orange-600 text-sm font-medium")(
                    "Restaurants"
                ),
                A(
                    href="/cart",
                    cls="text-gray-600 hover:text-orange-600 text-sm font-medium",
                )("Cart"),
                A(
                    href="/orders",
                    cls="text-gray-600 hover:text-orange-600 text-sm font-medium",
                )("Orders"),
                A(
                    href="/admin",
                    cls="text-gray-600 hover:text-orange-600 text-sm font-medium",
                )("Admin"),
            ),
        ),
    )


def footer():
    return Footer(cls="bg-white border-t mt-auto")(
        Div(cls="container mx-auto px-4 py-4 max-w-6xl text-center text-gray-400 text-sm")(
            "FoodAngels — save food, save money"
        ),
    )


# ── Cards ────────────────────────────────────────────────────────────────
def restaurant_card(r: dict):
    avail_badge = (
        Span(cls="inline-block px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700")(
            "Open"
        )
        if r.get("available")
        else Span(
            cls="inline-block px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700"
        )("Closed")
    )
    return A(
        href=f"/restaurants/{r['id']}",
        cls="block bg-white rounded-lg shadow-sm hover:shadow-md transition p-4",
    )(
        Div(cls="flex items-center justify-between mb-2")(
            H3(cls="font-semibold text-gray-800 text-lg")(r["name"]),
            avail_badge,
        ),
        P(cls="text-gray-500 text-sm")(r.get("address", "")),
        P(cls="text-gray-400 text-xs mt-1")(
            f'{r.get("city", "")} {r.get("zipcode", "")}'.strip()
        ),
    )


def product_card(p: dict, show_add: bool = True):
    discount = p.get("discount_pct", 0)
    price_display = Div(cls="flex items-center gap-2")(
        Span(cls="text-orange-600 font-bold")(f'{p["current_price"]} EUR'),
        (
            Span(cls="text-gray-400 line-through text-sm")(f'{p["old_price"]} EUR')
            if discount
            else ""
        ),
        (
            Span(cls="bg-orange-100 text-orange-700 text-xs px-1.5 py-0.5 rounded")(
                f"-{discount}%"
            )
            if discount
            else ""
        ),
    )
    add_btn = ""
    if show_add:
        btn_id = f"add-btn-{p['id']}"
        add_btn = Div(id=btn_id, cls="mt-2")(
            Button(
                hx_post=f"/cart/add/{p['id']}",
                hx_target=f"#{btn_id}",
                hx_swap="innerHTML",
                cls="bg-orange-500 hover:bg-orange-600 text-white text-sm px-3 py-1 rounded",
            )("Add to Cart"),
        )

    return Div(cls="bg-white rounded-lg shadow-sm p-4")(
        H4(cls="font-medium text-gray-800")(p["name"]),
        P(cls="text-gray-500 text-sm mt-1 line-clamp-2")(p.get("description", "")),
        Div(cls="mt-2")(price_display),
        diet_badges(p),
        add_btn,
    )


def diet_badges(p: dict):
    badges = []
    for key, label, color in [
        ("vegetarian", "Vegetarian", "green"),
        ("vegan", "Vegan", "emerald"),
        ("gluten_free", "Gluten Free", "blue"),
        ("lactose_free", "Lactose Free", "purple"),
    ]:
        if p.get(key):
            badges.append(
                Span(
                    cls=f"inline-block px-1.5 py-0.5 text-xs rounded bg-{color}-100 text-{color}-700"
                )(label)
            )
    if not badges:
        return ""
    return Div(cls="flex flex-wrap gap-1 mt-2")(*badges)


def status_badge(status: str):
    colors = {
        "new": "bg-blue-100 text-blue-700",
        "accepted": "bg-green-100 text-green-700",
        "refused": "bg-red-100 text-red-700",
        "done": "bg-gray-100 text-gray-700",
        "pending": "bg-yellow-100 text-yellow-700",
        "paid": "bg-indigo-100 text-indigo-700",
        "canceled": "bg-red-100 text-red-700",
    }
    cls = colors.get(status, "bg-gray-100 text-gray-700")
    return Span(cls=f"inline-block px-2 py-0.5 text-xs rounded-full {cls}")(status.title())


def order_card(o: dict):
    return Div(cls="bg-white rounded-lg shadow-sm p-4")(
        Div(cls="flex items-center justify-between mb-2")(
            Span(cls="font-semibold text-gray-800")(
                f'Order #{o.get("number_order", o["id"])}'
            ),
            status_badge(o.get("status", "new")),
        ),
        P(cls="text-gray-500 text-sm")(f'Total: {o.get("final_price", "0")} EUR'),
        P(cls="text-gray-400 text-xs")(o.get("date", "")),
        A(
            href=f'/orders/{o["id"]}',
            cls="text-orange-600 text-sm mt-2 inline-block hover:underline",
        )("View details"),
    )
