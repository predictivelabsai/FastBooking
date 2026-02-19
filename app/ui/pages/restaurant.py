"""Restaurant detail page — info header + product list."""

from __future__ import annotations

from fasthtml.common import *

from app.ui.components import layout, product_card


def register_routes(app, client):
    @app.get("/restaurants/{restaurant_id}")
    async def restaurant_detail(request, restaurant_id: int):
        r = await client.get_restaurant(restaurant_id)
        if not r:
            return layout(
                P(cls="text-center text-gray-500 py-8")("Restaurant not found"),
                title="Not Found",
            )

        # hours display
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        hours_rows = []
        for h in sorted(r.get("hours", []), key=lambda x: x["week_day"]):
            wd = h["week_day"]
            label = day_names[wd] if wd < len(day_names) else str(wd)
            if h["work"] and h.get("from_hour") and h.get("to_hour"):
                time_str = f'{h["from_hour"]} - {h["to_hour"]}'
            else:
                time_str = "Closed"
            hours_rows.append(
                Div(cls="flex justify-between text-sm")(
                    Span(cls="text-gray-600")(label),
                    Span(cls="text-gray-800")(time_str),
                )
            )

        avail = (
            Span(cls="bg-green-100 text-green-700 px-2 py-0.5 text-sm rounded-full")(
                "Open"
            )
            if r.get("available")
            else Span(cls="bg-red-100 text-red-700 px-2 py-0.5 text-sm rounded-full")(
                "Closed"
            )
        )

        products = r.get("products", [])
        categories = {}
        for p in products:
            for cat in ["meals", "pastries", "drinks", "bread", "groceries"]:
                if p.get(cat):
                    categories.setdefault(cat.title(), []).append(p)
            if not any(p.get(c) for c in ["meals", "pastries", "drinks", "bread", "groceries"]):
                categories.setdefault("Other", []).append(p)

        sections = []
        for cat_name, cat_products in categories.items():
            sections.append(
                Div(cls="mb-6")(
                    H3(cls="text-lg font-semibold text-green-700 mb-3")(cat_name),
                    Div(cls="grid grid-cols-1 md:grid-cols-2 gap-4")(
                        *[product_card(p) for p in cat_products]
                    ),
                )
            )

        return layout(
            Div(cls="mb-6")(
                Div(cls="flex items-center gap-3 mb-2")(
                    H1(cls="text-2xl font-bold text-gray-800")(r["name"]),
                    avail,
                ),
                P(cls="text-gray-500")(r.get("address", "")),
                P(cls="text-gray-400 text-sm")(r.get("about", "")),
                Div(cls="mt-4 bg-white rounded-xl p-4 shadow-sm max-w-xs border-t-4 border-green-500")(
                    H3(cls="font-semibold text-gray-700 mb-2")("Hours"),
                    *hours_rows if hours_rows else [P(cls="text-gray-400 text-sm")("No hours set")],
                ),
            ),
            Div(cls="mt-4")(
                H2(cls="text-xl font-bold text-gray-800 mb-4")("Menu"),
                *sections if sections else [P(cls="text-gray-500")("No products available")],
            ),
            title=f"{r['name']} — FoodAngels",
        )
