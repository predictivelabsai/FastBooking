"""Home page — restaurant listing with search."""

from __future__ import annotations

from fasthtml.common import *

from app.ui.components import layout, restaurant_card


def register_routes(app, client):
    @app.get("/marketplace")
    async def home(request):
        restaurants = await client.list_restaurants()
        return layout(
            Div(cls="mb-6")(
                H1(cls="text-2xl font-bold text-gray-800 mb-1")("Welcome to Food Angels!"),
                P(cls="text-gray-500 mb-4")("A simple way to do good for the environment, and your wallet!"),
                Div(cls="relative")(
                    Input(
                        type="search",
                        name="q",
                        placeholder="Search restaurants...",
                        hx_get="/marketplace/search",
                        hx_trigger="input changed delay:300ms, search",
                        hx_target="#restaurant-grid",
                        hx_swap="innerHTML",
                        cls="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none",
                    ),
                ),
            ),
            Div(id="restaurant-grid", cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4")(
                *[restaurant_card(r) for r in restaurants]
            ),
            title="FoodAngels — Home",
        )

    @app.get("/marketplace/search")
    async def search(request, q: str = ""):
        restaurants = await client.list_restaurants(q=q)
        return Div(id="restaurant-grid")(
            *[restaurant_card(r) for r in restaurants]
        ) if restaurants else Div(id="restaurant-grid")(
            P(cls="text-gray-500 col-span-full text-center py-8")(
                "No restaurants found"
            )
        )
