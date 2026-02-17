-- FoodAngels database schema
-- Target: PostgreSQL 14+
-- All tables live in the "foodangels" schema within the "finespresso_db" database.

CREATE SCHEMA IF NOT EXISTS foodangels;

-- Atomic order numbering
CREATE SEQUENCE IF NOT EXISTS foodangels.order_number_seq;

-- ── Users ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS foodangels.users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    username        VARCHAR(300) NOT NULL DEFAULT '',
    password_hash   VARCHAR(255) NOT NULL DEFAULT '',
    role            VARCHAR(50)  NOT NULL DEFAULT 'user',   -- 'user' | 'restaurant'
    phone_number    VARCHAR(30)  NOT NULL DEFAULT '',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    is_admin        BOOLEAN      NOT NULL DEFAULT FALSE,
    registered      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ── Restaurants ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS foodangels.restaurants (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES foodangels.users(id),
    name            VARCHAR(200) NOT NULL DEFAULT '',
    address         VARCHAR(255) NOT NULL DEFAULT '',
    latitude        NUMERIC(10,7),
    longitude       NUMERIC(10,7),
    about           TEXT         NOT NULL DEFAULT '',
    phone_number    VARCHAR(30)  NOT NULL DEFAULT '',
    available       BOOLEAN      NOT NULL DEFAULT TRUE,
    city            VARCHAR(100) NOT NULL DEFAULT '',
    country         VARCHAR(100) NOT NULL DEFAULT '',
    zipcode         VARCHAR(30)  NOT NULL DEFAULT '',
    logo            VARCHAR(500),
    back_image      VARCHAR(500),
    email           VARCHAR(255),
    site            VARCHAR(500)
);

-- ── Restaurant Hours ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS foodangels.restaurant_hours (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER NOT NULL REFERENCES foodangels.restaurants(id),
    week_day        SMALLINT NOT NULL,          -- 0=Mon … 6=Sun
    from_hour       TIME,
    to_hour         TIME,
    work            BOOLEAN NOT NULL DEFAULT FALSE
);

-- ── Products ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS foodangels.products (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER NOT NULL REFERENCES foodangels.restaurants(id),
    name            VARCHAR(200) NOT NULL,
    description     TEXT         NOT NULL DEFAULT '',
    image           VARCHAR(500),
    current_price   NUMERIC(10,2) NOT NULL,
    old_price       NUMERIC(10,2) NOT NULL,
    quantity        INTEGER       NOT NULL,
    meals           BOOLEAN NOT NULL DEFAULT FALSE,
    pastries        BOOLEAN NOT NULL DEFAULT FALSE,
    drinks          BOOLEAN NOT NULL DEFAULT FALSE,
    bread           BOOLEAN NOT NULL DEFAULT FALSE,
    groceries       BOOLEAN NOT NULL DEFAULT FALSE,
    vegetarian      BOOLEAN NOT NULL DEFAULT FALSE,
    vegan           BOOLEAN NOT NULL DEFAULT FALSE,
    lactose_free    BOOLEAN NOT NULL DEFAULT FALSE,
    gluten_free     BOOLEAN NOT NULL DEFAULT FALSE,
    allergen        TEXT    NOT NULL DEFAULT ''
);

-- ── Orders ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS foodangels.orders (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES foodangels.users(id),
    restaurant_id    INTEGER REFERENCES foodangels.restaurants(id),
    number_order     INTEGER UNIQUE DEFAULT nextval('foodangels.order_number_seq'),
    amount           NUMERIC(10,2),
    final_price      NUMERIC(10,2) DEFAULT 0,
    status           VARCHAR(20) NOT NULL DEFAULT 'new',
    date             TIMESTAMPTZ NOT NULL DEFAULT now(),
    to_hour          TIMESTAMPTZ,
    commission       SMALLINT,
    pickup_time      VARCHAR(200),
    customer_message VARCHAR(200)
);

-- ── Order Products ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS foodangels.order_products (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES foodangels.orders(id),
    product_id      INTEGER REFERENCES foodangels.products(id),
    product_name    VARCHAR(200) NOT NULL,
    quantity        INTEGER      NOT NULL,
    old_price       NUMERIC(10,2) NOT NULL,
    current_price   NUMERIC(10,2) NOT NULL
);

-- ── Codes (discount / promo) ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS foodangels.codes (
    id               SERIAL PRIMARY KEY,
    name             VARCHAR(50)  NOT NULL,
    code             VARCHAR(10)  NOT NULL UNIQUE,
    start_date       TIMESTAMPTZ,
    end_date         TIMESTAMPTZ,
    discount         INTEGER      NOT NULL DEFAULT 0,
    discount_amount  NUMERIC(10,2) NOT NULL DEFAULT 0,
    free_delivery    BOOLEAN      NOT NULL DEFAULT FALSE,
    quantity         SMALLINT     DEFAULT 1,
    used_by          TEXT         NOT NULL DEFAULT ''
);

-- ── User Carts ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS foodangels.user_carts (
    id       SERIAL PRIMARY KEY,
    user_id  INTEGER NOT NULL UNIQUE REFERENCES foodangels.users(id),
    data     JSONB   NOT NULL DEFAULT '[]'::jsonb
);

-- ── User Favorite Restaurants ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS foodangels.user_favorite_restaurants (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES foodangels.users(id),
    restaurant_id   INTEGER NOT NULL REFERENCES foodangels.restaurants(id),
    UNIQUE (user_id, restaurant_id)
);

-- ── Contact Us ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS foodangels.contact_us (
    id     SERIAL PRIMARY KEY,
    email  VARCHAR(255) NOT NULL DEFAULT '',
    phone  VARCHAR(20)  NOT NULL DEFAULT ''
);

-- ── User Agreements ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS foodangels.user_agreements (
    id         SERIAL PRIMARY KEY,
    text       TEXT     NOT NULL DEFAULT '',
    commission SMALLINT NOT NULL DEFAULT 0
);

-- ── Privacy Policies ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS foodangels.privacy_policies (
    id   SERIAL PRIMARY KEY,
    text TEXT NOT NULL DEFAULT ''
);

-- ── Useful views ─────────────────────────────────────────────────────────────

-- Restaurant overview with product count
CREATE OR REPLACE VIEW foodangels.v_restaurant_overview AS
SELECT
    r.id,
    r.name,
    r.city,
    r.available,
    COUNT(p.id) AS product_count,
    MIN(p.current_price) AS min_price,
    MAX(p.current_price) AS max_price
FROM foodangels.restaurants r
LEFT JOIN foodangels.products p ON p.restaurant_id = r.id
GROUP BY r.id, r.name, r.city, r.available
ORDER BY r.name;

-- Order summary with item count and restaurant name
CREATE OR REPLACE VIEW foodangels.v_order_summary AS
SELECT
    o.id AS order_id,
    o.number_order,
    o.status,
    o.final_price,
    o.date,
    u.email AS customer_email,
    r.name AS restaurant_name,
    COUNT(op.id) AS item_count
FROM foodangels.orders o
JOIN foodangels.users u ON u.id = o.user_id
LEFT JOIN foodangels.restaurants r ON r.id = o.restaurant_id
LEFT JOIN foodangels.order_products op ON op.order_id = o.id
GROUP BY o.id, o.number_order, o.status, o.final_price, o.date,
         u.email, r.name
ORDER BY o.date DESC;

-- Daily revenue per restaurant
CREATE OR REPLACE VIEW foodangels.v_daily_revenue AS
SELECT
    r.name AS restaurant_name,
    DATE(o.date) AS order_date,
    COUNT(o.id) AS order_count,
    SUM(o.final_price) AS total_revenue
FROM foodangels.orders o
JOIN foodangels.restaurants r ON r.id = o.restaurant_id
WHERE o.status NOT IN ('refused', 'canceled', 'abandoned')
GROUP BY r.name, DATE(o.date)
ORDER BY order_date DESC, restaurant_name;
