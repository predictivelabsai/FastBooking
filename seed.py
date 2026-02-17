"""Seed script — populates sample restaurants, products, and users."""

from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import text

from app.config import settings
from app.db.base import Base
from app.db.engine import engine, async_session_factory
from app.db.models import (
    ContactUs,
    Order,
    OrderProduct,
    PrivacyPolicy,
    Product,
    Restaurant,
    RestaurantHours,
    User,
    UserAgreement,
    UserCart,
)


async def seed():
    # create schema + tables
    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}"))
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # ── Users ────────────────────────────────────────────────────────
        customer = User(
            email="customer@demo.com",
            username="DemoCustomer",
            role="user",
            phone_number="+1234567890",
            is_active=True,
            password_hash="not-a-real-hash",
        )
        owner1 = User(
            email="owner1@demo.com",
            username="GreenBowlOwner",
            role="restaurant",
            phone_number="+1234567891",
            is_active=True,
            password_hash="not-a-real-hash",
        )
        owner2 = User(
            email="owner2@demo.com",
            username="BakerStreetOwner",
            role="restaurant",
            phone_number="+1234567892",
            is_active=True,
            password_hash="not-a-real-hash",
        )
        owner3 = User(
            email="owner3@demo.com",
            username="PizzaPalaceOwner",
            role="restaurant",
            phone_number="+1234567893",
            is_active=True,
            password_hash="not-a-real-hash",
        )
        db.add_all([customer, owner1, owner2, owner3])
        await db.flush()

        # ── Restaurants ──────────────────────────────────────────────────
        r1 = Restaurant(
            user_id=owner1.id,
            name="Green Bowl",
            address="123 Health Street",
            city="Copenhagen",
            country="Denmark",
            zipcode="1000",
            latitude=55.6761,
            longitude=12.5683,
            about="Fresh salads, smoothie bowls, and healthy wraps. All ingredients locally sourced.",
            phone_number="+4512345678",
            available=True,
        )
        r2 = Restaurant(
            user_id=owner2.id,
            name="Baker Street Bakery",
            address="221B Baker Street",
            city="Copenhagen",
            country="Denmark",
            zipcode="1050",
            latitude=55.6802,
            longitude=12.5722,
            about="Artisan breads, pastries, and cakes. Freshly baked every morning.",
            phone_number="+4512345679",
            available=True,
        )
        r3 = Restaurant(
            user_id=owner3.id,
            name="Pizza Palace",
            address="45 Margherita Lane",
            city="Copenhagen",
            country="Denmark",
            zipcode="1100",
            latitude=55.6739,
            longitude=12.5614,
            about="Authentic Neapolitan pizza with a modern twist. Wood-fired oven, organic toppings.",
            phone_number="+4512345680",
            available=True,
        )
        db.add_all([r1, r2, r3])
        await db.flush()

        # ── Restaurant Hours ─────────────────────────────────────────────
        import datetime

        for rest in [r1, r2, r3]:
            for day in range(7):
                work = day < 6  # closed Sunday for r1/r2/r3 variety
                db.add(
                    RestaurantHours(
                        restaurant_id=rest.id,
                        week_day=day,
                        from_hour=datetime.time(8, 0) if work else None,
                        to_hour=datetime.time(20, 0) if work else None,
                        work=work,
                    )
                )

        # ── Products ─────────────────────────────────────────────────────
        products_data = [
            # Green Bowl products
            (r1.id, "Quinoa Power Bowl", "Quinoa, avocado, chickpeas, cherry tomatoes, tahini dressing", Decimal("11.50"), Decimal("14.00"), 10, True, False, False, False, False, True, True, True, True),
            (r1.id, "Berry Smoothie Bowl", "Acai, blueberries, banana, granola, coconut flakes", Decimal("9.00"), Decimal("12.00"), 15, True, False, False, False, False, True, True, True, False),
            (r1.id, "Grilled Chicken Wrap", "Grilled chicken, mixed greens, hummus, whole wheat tortilla", Decimal("10.00"), Decimal("12.50"), 8, True, False, False, False, False, False, False, False, False),
            (r1.id, "Green Detox Juice", "Kale, celery, apple, ginger, lemon", Decimal("5.50"), Decimal("7.00"), 20, False, False, True, False, False, True, True, True, True),
            # Baker Street products
            (r2.id, "Sourdough Loaf", "Traditional 24-hour fermented sourdough bread", Decimal("4.50"), Decimal("6.00"), 20, False, False, False, True, False, False, True, False, False),
            (r2.id, "Croissant", "Butter croissant, flaky and golden", Decimal("2.50"), Decimal("3.50"), 30, False, True, False, False, False, False, False, False, False),
            (r2.id, "Cinnamon Roll", "Soft roll with cinnamon sugar and cream cheese frosting", Decimal("3.50"), Decimal("4.50"), 15, False, True, False, False, False, False, False, False, False),
            (r2.id, "Almond Danish", "Puff pastry with almond cream and sliced almonds", Decimal("3.00"), Decimal("4.00"), 12, False, True, False, False, False, False, False, False, False),
            (r2.id, "Rye Bread", "Dense Danish rye bread with seeds", Decimal("3.50"), Decimal("5.00"), 10, False, False, False, True, False, False, True, False, False),
            # Pizza Palace products
            (r3.id, "Margherita", "San Marzano tomatoes, fresh mozzarella, basil", Decimal("10.00"), Decimal("13.00"), 25, True, False, False, False, False, False, False, False, False),
            (r3.id, "Quattro Formaggi", "Mozzarella, gorgonzola, parmesan, fontina", Decimal("12.00"), Decimal("15.00"), 15, True, False, False, False, False, False, False, False, False),
            (r3.id, "Veggie Supreme", "Mushrooms, peppers, olives, artichokes, onions", Decimal("11.50"), Decimal("14.50"), 12, True, False, False, False, False, True, True, False, False),
            (r3.id, "Tiramisu", "Classic Italian tiramisu with espresso and mascarpone", Decimal("6.00"), Decimal("8.00"), 10, False, True, False, False, False, False, False, False, False),
            (r3.id, "Sparkling Lemonade", "House-made lemonade with sparkling water", Decimal("3.50"), Decimal("4.50"), 30, False, False, True, False, False, True, True, True, True),
        ]
        for row in products_data:
            db.add(
                Product(
                    restaurant_id=row[0],
                    name=row[1],
                    description=row[2],
                    current_price=row[3],
                    old_price=row[4],
                    quantity=row[5],
                    meals=row[6],
                    pastries=row[7],
                    drinks=row[8],
                    bread=row[9],
                    groceries=row[10],
                    vegetarian=row[11],
                    vegan=row[12],
                    lactose_free=row[13],
                    gluten_free=row[14],
                )
            )

        # ── Cart for demo customer ───────────────────────────────────────
        db.add(UserCart(user_id=customer.id, data=[]))

        # ── Info records ─────────────────────────────────────────────────
        db.add(ContactUs(email="support@foodangels.org", phone="+4500000000"))
        db.add(UserAgreement(text="By using FoodAngels you agree to our terms of service.", commission=5))
        db.add(PrivacyPolicy(text="We respect your privacy. Read our full policy at foodangels.org/privacy."))

        # ── Sample order ─────────────────────────────────────────────────
        order = Order(
            user_id=customer.id,
            restaurant_id=r1.id,
            amount=Decimal("20.50"),
            final_price=Decimal("20.50"),
            status="done",
            pickup_time="12:30",
            customer_message="No onions please",
        )
        db.add(order)
        await db.flush()

        db.add(OrderProduct(order_id=order.id, product_name="Quinoa Power Bowl", quantity=1, old_price=Decimal("14.00"), current_price=Decimal("11.50")))
        db.add(OrderProduct(order_id=order.id, product_name="Berry Smoothie Bowl", quantity=1, old_price=Decimal("12.00"), current_price=Decimal("9.00")))

        await db.commit()
        print("Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
