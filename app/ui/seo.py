"""Search metadata, structured data, sitemap, and crawler policy."""

from __future__ import annotations

import json

from fasthtml.common import Link, Meta, NotStr, Script
from starlette.responses import Response

PRODUCT = "FastBooking"
BASE_URL = "https://booking.fastsme.com"
DESCRIPTION = (
    "Multi-tenant restaurant, hotel, private-clinic, and event booking software."
)
KEYWORDS = (
    "FastBooking",
    "restaurant reservations",
    "hotel booking software",
    "clinic appointment scheduling",
    "event ticketing",
    "multi-tenant booking platform",
    "FastSME",
    "open source business software",
)
FEATURES = (
    "Restaurant ordering and table reservations",
    "Hotel room inventory",
    "FastClinic-connected appointments",
    "Event and concert ticketing",
)
SITEMAP_PATHS = ("/", "/developers")


def seo_meta(
    *,
    path: str = "/",
    title: str | None = None,
    description: str | None = None,
):
    canonical = BASE_URL + (path if path != "/" else "")
    page_title = title or "FastBooking · Configurable bookings for service businesses"
    page_description = description or DESCRIPTION
    structured = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": PRODUCT,
        "url": canonical,
        "description": page_description,
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "isAccessibleForFree": True,
        "license": "https://opensource.org/license/mit",
        "featureList": list(FEATURES),
        "publisher": {
            "@type": "Organization",
            "name": "FastSME",
            "url": "https://fastsme.com",
        },
    }
    return (
        Link(rel="canonical", href=canonical),
        Meta(
            name="robots",
            content=(
                "index,follow,max-image-preview:large,"
                "max-snippet:-1,max-video-preview:-1"
            ),
        ),
        Meta(name="keywords", content=", ".join(KEYWORDS)),
        Meta(property="og:type", content="website"),
        Meta(property="og:site_name", content="FastSME"),
        Meta(property="og:title", content=page_title),
        Meta(property="og:description", content=page_description),
        Meta(property="og:url", content=canonical),
        Meta(name="twitter:card", content="summary"),
        Meta(name="twitter:title", content=page_title),
        Meta(name="twitter:description", content=page_description),
        Script(
            NotStr(json.dumps(structured, separators=(",", ":"))),
            type="application/ld+json",
        ),
    )


async def sitemap():
    urls = "\n".join(
        (
            f"  <url><loc>{BASE_URL}{path}</loc>"
            f"<changefreq>{'weekly' if path == '/' else 'monthly'}</changefreq>"
            f"<priority>{'1.0' if path == '/' else '0.6'}</priority></url>"
        )
        for path in SITEMAP_PATHS
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n"
    )
    return Response(xml, media_type="application/xml")


async def robots():
    body = f"""User-agent: *
Allow: /
Disallow: /admin
Disallow: /app
Disallow: /auth/
Disallow: /book/
Disallow: /manage/
Disallow: /api/

Sitemap: {BASE_URL}/sitemap.xml
"""
    return Response(body, media_type="text/plain")


def register_seo_routes(app):
    app.get("/sitemap.xml")(sitemap)
    app.routes.insert(0, app.routes.pop())
    app.get("/robots.txt")(robots)
    app.routes.insert(0, app.routes.pop())
