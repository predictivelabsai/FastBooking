"""Seed script — populates sample restaurants, products, and users."""

from __future__ import annotations

import asyncio
import datetime
import hashlib
from decimal import Decimal

from sqlalchemy import text

from app.config import settings
from app.db.base import Base
from app.db.engine import async_session_factory, engine
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
from app.db.platform_models import (
    Booking,
    ClinicConnector,
    Guest,
    HotelRoomType,
    Location,
    Membership,
    MembershipPlan,
    Offering,
    PaymentTransaction,
    RecreationProgramme,
    Resource,
    ScheduledEvent,
    Tenant,
    TenantModule,
    TicketType,
)


async def seed():
    # create schema + tables
    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}"))
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # ── Tenant and admin-configurable modules ────────────────────────
        now = datetime.datetime.now(datetime.timezone.utc)
        tenant = Tenant(
            slug="fastbooking-demo",
            name="FastBooking Demo",
            status="active",
            timezone="Pacific/Auckland",
            currency="NZD",
            locale="en-NZ",
        )
        db.add(tenant)
        await db.flush()
        for module in ("restaurant", "hotel", "clinic", "events", "recreation"):
            db.add(TenantModule(tenant_id=tenant.id, module=module, enabled=True))

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
        db.add_all(
            [
                Membership(tenant_id=tenant.id, user_id=owner1.id, role="admin"),
                Membership(tenant_id=tenant.id, user_id=owner2.id, role="staff"),
                Membership(tenant_id=tenant.id, user_id=owner3.id, role="viewer"),
            ]
        )

        # ── Restaurants ──────────────────────────────────────────────────
        locations = [
            Location(
                tenant_id=tenant.id,
                slug="green-bowl",
                name="Green Bowl",
                address="123 Health Street",
                city="Copenhagen",
                country="Denmark",
                timezone="Europe/Copenhagen",
            ),
            Location(
                tenant_id=tenant.id,
                slug="baker-street",
                name="Baker Street Bakery",
                address="221B Baker Street",
                city="Copenhagen",
                country="Denmark",
                timezone="Europe/Copenhagen",
            ),
            Location(
                tenant_id=tenant.id,
                slug="pizza-palace",
                name="Pizza Palace",
                address="45 Margherita Lane",
                city="Copenhagen",
                country="Denmark",
                timezone="Europe/Copenhagen",
            ),
            Location(
                tenant_id=tenant.id,
                slug="harbour-hotel",
                name="Harbour Hotel",
                address="8 Marina Way",
                city="Tallinn",
                country="Estonia",
                timezone="Europe/Tallinn",
            ),
            Location(
                tenant_id=tenant.id,
                slug="city-clinic",
                name="City Private Clinic",
                address="21 Health Avenue",
                city="Tallinn",
                country="Estonia",
                timezone="Europe/Tallinn",
            ),
            Location(
                tenant_id=tenant.id,
                slug="north-arena",
                name="North Arena",
                address="1 Concert Square",
                city="Tallinn",
                country="Estonia",
                timezone="Europe/Tallinn",
            ),
            Location(
                tenant_id=tenant.id,
                slug="queenstown-events-centre",
                name="Queenstown Events Centre",
                address="Joe O'Connell Drive",
                city="Queenstown",
                country="New Zealand",
                timezone="Pacific/Auckland",
            ),
        ]
        db.add_all(locations)
        await db.flush()
        r1 = Restaurant(
            tenant_id=tenant.id,
            location_id=locations[0].id,
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
            tenant_id=tenant.id,
            location_id=locations[1].id,
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
            tenant_id=tenant.id,
            location_id=locations[2].id,
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

        # ── Shared booking inventory for all enabled modules ─────────────
        for restaurant, location in zip([r1, r2, r3], locations[:3], strict=True):
            for number, capacity in enumerate((2, 4, 4, 6), 1):
                db.add(
                    Resource(
                        tenant_id=tenant.id,
                        location_id=location.id,
                        module="restaurant",
                        slug=f"table-{number}",
                        name=f"Table {number}",
                        resource_type="table",
                        capacity=capacity,
                    )
                )

        hotel_offering = Offering(
            tenant_id=tenant.id,
            location_id=locations[3].id,
            module="hotel",
            slug="standard-room",
            name="Standard harbour room",
            description="A bright double room with breakfast.",
            capacity=2,
            price=Decimal("119.00"),
        )
        clinic_offering = Offering(
            tenant_id=tenant.id,
            location_id=locations[4].id,
            module="clinic",
            slug="initial-consultation",
            name="Initial consultation",
            description="Scheduling only; clinical records remain in FastClinic.",
            duration_minutes=30,
            price=Decimal("75.00"),
            settings_json={"external_id": "initial-consultation"},
        )
        event_offering = Offering(
            tenant_id=tenant.id,
            location_id=locations[5].id,
            module="events",
            slug="summer-sessions",
            name="Summer Sessions",
            description="An evening of live music at North Arena.",
            capacity=800,
            price=Decimal("39.00"),
        )
        db.add_all([hotel_offering, clinic_offering, event_offering])
        await db.flush()
        db.add(
            HotelRoomType(
                tenant_id=tenant.id,
                location_id=locations[3].id,
                offering_id=hotel_offering.id,
                code="STANDARD",
                name="Standard room",
                occupancy=2,
                units=20,
                nightly_rate=Decimal("119.00"),
            )
        )
        db.add(
            Resource(
                tenant_id=tenant.id,
                location_id=locations[4].id,
                module="clinic",
                slug="practitioner-1",
                name="Dr Demo",
                resource_type="practitioner",
                capacity=1,
                external_id="1",
            )
        )
        db.add(
            ClinicConnector(
                tenant_id=tenant.id,
                location_id=locations[4].id,
                base_url="https://clinic.fastsme.com",
                secret_env_name="FASTCLINIC_API_TOKEN",
            )
        )
        scheduled_event = ScheduledEvent(
            tenant_id=tenant.id,
            location_id=locations[5].id,
            offering_id=event_offering.id,
            slug="summer-sessions-2026",
            name="Summer Sessions 2026",
            starts_at=datetime.datetime(
                2026, 9, 15, 19, 0, tzinfo=datetime.timezone.utc
            ),
            ends_at=datetime.datetime(
                2026, 9, 15, 23, 0, tzinfo=datetime.timezone.utc
            ),
            sales_open_at=now,
            sales_close_at=datetime.datetime(
                2026, 9, 15, 18, 0, tzinfo=datetime.timezone.utc
            ),
            status="published",
        )
        db.add(scheduled_event)
        await db.flush()
        db.add_all(
            [
                TicketType(
                    tenant_id=tenant.id,
                    event_id=scheduled_event.id,
                    code="GENERAL",
                    name="General admission",
                    price=Decimal("39.00"),
                    capacity=700,
                ),
                TicketType(
                    tenant_id=tenant.id,
                    event_id=scheduled_event.id,
                    code="VIP",
                    name="VIP",
                    price=Decimal("99.00"),
                    capacity=100,
                    max_per_booking=6,
                ),
            ]
        )

        recreation_offerings = [
            Offering(
                tenant_id=tenant.id,
                location_id=locations[6].id,
                module="recreation",
                slug="learn-to-swim-kea-2",
                name="Learn to Swim · Kea 2",
                description="Term-based learn-to-swim programme.",
                capacity=8,
                price=Decimal("145.00"),
            ),
            Offering(
                tenant_id=tenant.id,
                location_id=locations[6].id,
                module="recreation",
                slug="court-hire",
                name="Indoor court hire",
                description="Casual or club court booking.",
                duration_minutes=60,
                capacity=1,
                price=Decimal("48.00"),
            ),
        ]
        db.add_all(recreation_offerings)
        await db.flush()
        teaching_pool = Resource(
            tenant_id=tenant.id,
            location_id=locations[6].id,
            module="recreation",
            slug="teaching-pool",
            name="Teaching pool",
            resource_type="pool",
            capacity=2,
            attributes={"lanes": 2, "accessible": True},
        )
        courts = [
            Resource(
                tenant_id=tenant.id,
                location_id=locations[6].id,
                module="recreation",
                slug=f"court-{number}",
                name=f"Indoor court {number}",
                resource_type="court",
                capacity=1,
            )
            for number in range(1, 3)
        ]
        db.add_all([teaching_pool, *courts])
        await db.flush()
        db.add(
            RecreationProgramme(
                tenant_id=tenant.id,
                location_id=locations[6].id,
                offering_id=recreation_offerings[0].id,
                resource_id=teaching_pool.id,
                code="LTS-KEA2-T3",
                name="Learn to Swim · Kea 2 · Term 3",
                category="learn_to_swim",
                starts_at=now + datetime.timedelta(days=7),
                ends_at=now + datetime.timedelta(days=77),
                enrolment_opens_at=now - datetime.timedelta(days=14),
                enrolment_closes_at=now + datetime.timedelta(days=6),
                capacity=8,
                status="published",
                schedule_json={"week_day": 2, "time": "09:00", "sessions": 10},
            )
        )
        db.add_all(
            [
                MembershipPlan(
                    tenant_id=tenant.id,
                    location_id=locations[6].id,
                    code="GYM-MONTHLY",
                    name="Gym monthly",
                    description="Monthly gym and group fitness access.",
                    billing_interval="month",
                    price=Decimal("69.00"),
                    access_rules={"areas": ["gym", "group_fitness"]},
                ),
                MembershipPlan(
                    tenant_id=tenant.id,
                    location_id=locations[6].id,
                    code="POOL-10",
                    name="Ten-swim pass",
                    description="Ten casual aquatic visits.",
                    billing_interval="visit",
                    price=Decimal("62.00"),
                    duration_days=180,
                    included_visits=10,
                    access_rules={"areas": ["aquatics"]},
                ),
            ]
        )

        # ── Representative dashboard activity ──────────────────────────
        recreation_guest = Guest(
            tenant_id=tenant.id,
            name="Aroha Thompson",
            email="aroha@example.nz",
            phone="+64 21 555 0142",
        )
        event_guest = Guest(
            tenant_id=tenant.id,
            name="Noah Williams",
            email="noah@example.nz",
        )
        db.add_all([recreation_guest, event_guest])
        await db.flush()
        sample_bookings = [
            Booking(
                tenant_id=tenant.id,
                location_id=locations[6].id,
                guest_id=recreation_guest.id,
                offering_id=recreation_offerings[0].id,
                module="recreation",
                public_reference="FB-DEMO-LTS",
                status="confirmed",
                starts_at=now + datetime.timedelta(days=7),
                ends_at=now + datetime.timedelta(days=77),
                quantity=1,
                currency="NZD",
                subtotal=Decimal("145.00"),
                total=Decimal("145.00"),
                manage_token_hash=hashlib.sha256(b"seed-lts").hexdigest(),
                booking_metadata={"programme": "LTS-KEA2-T3"},
            ),
            Booking(
                tenant_id=tenant.id,
                location_id=locations[6].id,
                guest_id=recreation_guest.id,
                offering_id=recreation_offerings[1].id,
                module="recreation",
                public_reference="FB-DEMO-COURT",
                status="confirmed",
                starts_at=now + datetime.timedelta(days=1, hours=2),
                ends_at=now + datetime.timedelta(days=1, hours=3),
                quantity=1,
                currency="NZD",
                subtotal=Decimal("48.00"),
                total=Decimal("48.00"),
                manage_token_hash=hashlib.sha256(b"seed-court").hexdigest(),
                booking_metadata={"resource": "court-1"},
            ),
            Booking(
                tenant_id=tenant.id,
                location_id=locations[5].id,
                guest_id=event_guest.id,
                offering_id=event_offering.id,
                module="events",
                public_reference="FB-DEMO-EVENT",
                status="pending",
                starts_at=scheduled_event.starts_at,
                ends_at=scheduled_event.ends_at,
                quantity=2,
                currency="NZD",
                subtotal=Decimal("78.00"),
                total=Decimal("78.00"),
                manage_token_hash=hashlib.sha256(b"seed-event").hexdigest(),
                booking_metadata={"event": scheduled_event.slug},
            ),
        ]
        db.add_all(sample_bookings)
        await db.flush()
        db.add_all(
            [
                PaymentTransaction(
                    tenant_id=tenant.id,
                    guest_id=recreation_guest.id,
                    booking_id=sample_bookings[0].id,
                    provider="onsite",
                    external_id="seed-payment-lts",
                    status="paid",
                    amount=Decimal("145.00"),
                    currency="NZD",
                    payment_method="eftpos",
                ),
                PaymentTransaction(
                    tenant_id=tenant.id,
                    guest_id=recreation_guest.id,
                    booking_id=sample_bookings[1].id,
                    provider="onsite",
                    external_id="seed-payment-court",
                    status="refunded",
                    amount=Decimal("48.00"),
                    refunded_amount=Decimal("48.00"),
                    currency="NZD",
                    payment_method="card",
                ),
            ]
        )

        # ── Restaurant Hours ─────────────────────────────────────────────
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
                    tenant_id=tenant.id,
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
        db.add(UserCart(tenant_id=tenant.id, user_id=customer.id, data=[]))

        # ── Info records ─────────────────────────────────────────────────
        db.add(ContactUs(email="support@foodangels.org", phone="+4500000000"))
        db.add(UserAgreement(text="By using FastBooking you agree to our terms of service.", commission=5))
        db.add(PrivacyPolicy(text="We respect your privacy. Read our full policy at foodangels.org/privacy."))

        # ── Sample order ─────────────────────────────────────────────────
        order = Order(
            tenant_id=tenant.id,
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
