from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

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
from app.config import settings


def create_api_app() -> FastAPI:
    api = FastAPI(title="FastBooking API", version="1.0.0")

    api.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.PUBLIC_URL.rstrip("/")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    api.add_middleware(
        SessionMiddleware,
        secret_key=settings.SESSION_SECRET,
        session_cookie="session_",
        same_site="lax",
        https_only=settings.ENVIRONMENT == "production",
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
