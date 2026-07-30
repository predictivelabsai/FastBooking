"""Shared FastHTML components: layout shell, nav, cards, badges."""

from __future__ import annotations

from fasthtml.common import *

# ── Logo SVG ────────────────────────────────────────────────────────────
LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" class="w-8 h-8">
  <path d="M20 36 C10 28 2 22 2 14 A10 10 0 0 1 20 8 A10 10 0 0 1 38 14 C38 22 30 28 20 36Z" fill="#16a34a"/>
  <path d="M20 8 C20 8 22 2 26 2 C28 2 30 4 28 7" fill="#15803d" stroke="#15803d" stroke-width="1.5" stroke-linecap="round"/>
  <path d="M20 8 C20 8 18 3 15 4 C13 5 13 7 15 8" fill="#22c55e" stroke="#22c55e" stroke-width="1" stroke-linecap="round"/>
</svg>"""


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
                Link(rel="preconnect", href="https://fonts.googleapis.com"),
                Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
                Link(
                    rel="stylesheet",
                    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
                ),
                Style("body { font-family: 'Inter', system-ui, sans-serif; }"),
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
            A(href="/", cls="flex items-center gap-2 text-xl font-bold text-green-600")(
                NotStr(LOGO_SVG),
                "Food Angels",
            ),
            Div(cls="flex items-center gap-4")(
                A(href="/", cls="text-gray-600 hover:text-green-600 text-sm font-medium")(
                    "Restaurants"
                ),
                A(
                    href="/cart",
                    cls="text-gray-600 hover:text-green-600 text-sm font-medium",
                )("Cart"),
                A(
                    href="/orders",
                    cls="text-gray-600 hover:text-green-600 text-sm font-medium",
                )("Orders"),
                A(
                    href="/admin",
                    cls="text-gray-600 hover:text-green-600 text-sm font-medium",
                )("Admin"),
            ),
        ),
    )


def footer():
    return Footer(cls="bg-white border-t mt-auto")(
        Div(cls="container mx-auto px-4 py-4 max-w-6xl text-center text-gray-400 text-sm")(
            "Food Angels — A simple way to do good for the environment, and your wallet!"
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
        cls="block bg-white rounded-xl shadow-sm hover:shadow-md transition p-5",
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
    quantity = p.get("quantity", 0)

    price_display = Div(cls="flex items-center gap-2")(
        Span(cls="text-green-700 font-bold")(f'{p["current_price"]} EUR'),
        (
            Span(cls="text-gray-400 line-through text-sm")(f'{p["old_price"]} EUR')
            if discount
            else ""
        ),
        (
            Span(cls="bg-green-100 text-green-700 text-xs px-1.5 py-0.5 rounded")(
                f"-{discount}%"
            )
            if discount
            else ""
        ),
    )

    quantity_badge = ""
    if quantity and quantity > 0:
        quantity_badge = Span(
            cls="bg-green-600 text-white text-xs px-2 py-0.5 rounded-full"
        )(f"{quantity} left")

    add_btn = ""
    if show_add:
        btn_id = f"add-btn-{p['id']}"
        add_btn = Div(id=btn_id, cls="mt-2")(
            Button(
                hx_post=f"/cart/add/{p['id']}",
                hx_target=f"#{btn_id}",
                hx_swap="innerHTML",
                cls="bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-1.5 rounded-full",
            )("Add to Cart"),
        )

    return Div(cls="bg-white rounded-xl shadow-sm p-5")(
        Div(cls="flex items-center justify-between")(
            H4(cls="font-medium text-gray-800")(p["name"]),
            quantity_badge,
        ),
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
        "new": "bg-green-50 text-green-700 border border-green-200",
        "accepted": "bg-green-50 text-green-700",
        "refused": "bg-red-50 text-red-600",
        "done": "bg-green-50 text-green-700",
        "pending": "bg-green-50 text-green-700 border border-green-200",
        "paid": "bg-green-50 text-green-700",
        "canceled": "bg-red-50 text-red-600",
    }
    prefixes = {
        "accepted": "\u2713 ",
        "done": "\u2713 ",
        "paid": "\u2713 ",
    }
    cls = colors.get(status, "bg-gray-100 text-gray-700")
    prefix = prefixes.get(status, "")
    return Span(cls=f"inline-block px-2 py-0.5 text-xs rounded-full {cls}")(
        f"{prefix}{status.title()}"
    )


def order_card(o: dict):
    return Div(cls="bg-white rounded-xl shadow-sm p-5")(
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
            cls="text-green-600 text-sm mt-2 inline-block hover:underline",
        )("View details"),
    )
