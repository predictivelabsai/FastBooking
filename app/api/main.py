from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
    admin,
    cart,
    favorites,
    info,
    orders,
    platform,
    products,
    restaurants,
)


def create_api_app() -> FastAPI:
    api = FastAPI(title="FoodAngels API", version="0.1.0")

    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api.include_router(restaurants.router, prefix="/v0/restaurants", tags=["restaurants"])
    api.include_router(products.router, prefix="/v0/products", tags=["products"])
    api.include_router(orders.router, prefix="/v0/orders", tags=["orders"])
    api.include_router(cart.router, prefix="/v0/cart", tags=["cart"])
    api.include_router(favorites.router, prefix="/v0/favorites", tags=["favorites"])
    api.include_router(admin.router, prefix="/v0/admin", tags=["admin"])
    api.include_router(info.router, prefix="/v0/info", tags=["info"])
    api.include_router(platform.router, prefix="/v1", tags=["platform"])

    return api
