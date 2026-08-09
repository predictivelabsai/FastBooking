"""Search metadata, structured data, sitemap, and crawler policy."""

from __future__ import annotations

import json

from fasthtml.common import Link, Meta, NotStr, Script
from starlette.responses import Response

PRODUCT = "FastBooking"
BASE_URL = "https://booking.fastsme.com"
DESCRIPTION = (
    "Recreation management software for aquatics, programmes, memberships, "
    "facilities, customer self-service, payments, and reporting."
)
KEYWORDS = (
    "FastBooking",
    "restaurant reservations",
    "hotel booking software",
    "clinic appointment scheduling",
    "event ticketing",
    "sports facility booking software",
    "swim school management software",
    "restaurant reservation software",
    "clinic appointment booking",
    "multi-tenant booking platform",
    "recreation management software",
    "aquatic facility bookings",
    "swimming lesson management",
    "FastSME",
    "open source business software",
)
FEATURES = (
    "Swimming lessons and recreation programmes",
    "Aquatic facilities and lane allocation",
    "Memberships, visits, and attendance",
    "Facility, court, stadium, and room bookings",
    "Restaurant ordering and table reservations",
    "Hotel room inventory",
    "FastClinic-connected appointments",
    "Event and concert ticketing",
)
SITEMAP_ENTRIES = (
    ("/", "weekly", "1.0"),
    ("/features", "weekly", "0.9"),
    ("/industries", "weekly", "0.9"),
    ("/industries/sport-recreation", "weekly", "0.8"),
    ("/industries/aquatics-swim-schools", "weekly", "0.8"),
    ("/industries/restaurants", "weekly", "0.8"),
    ("/industries/hotels", "weekly", "0.8"),
    ("/industries/clinics", "weekly", "0.8"),
    ("/industries/events-venues", "weekly", "0.8"),
    ("/tour", "weekly", "0.8"),
    ("/integrations", "monthly", "0.7"),
    ("/partners", "monthly", "0.7"),
    ("/compare", "weekly", "0.8"),
    ("/developers", "monthly", "0.6"),
)
SITEMAP_PATHS = tuple(path for path, _frequency, _priority in SITEMAP_ENTRIES)


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
            f"<changefreq>{frequency}</changefreq>"
            f"<priority>{priority}</priority></url>"
        )
        for path, frequency, priority in SITEMAP_ENTRIES
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n"
    )
    return Response(xml, media_type="application/xml")


async def llms():
    body = f"""# FastBooking

> Open-source recreation and multi-service booking software for facilities, programmes, memberships, customer self-service, payments, and reporting.

## Public pages

- [Home]({BASE_URL}/): Recreation management overview and animated product tour.
- [Features]({BASE_URL}/features): Complete capability map.
- [Industries]({BASE_URL}/industries): Detailed booking workflows by industry.
- [Product tour]({BASE_URL}/tour): Animated platform walkthrough.
- [Integrations]({BASE_URL}/integrations): Fast* product boundaries and hand-offs.
- [Partners]({BASE_URL}/partners): FastSME integration partners.
- [How we compare]({BASE_URL}/compare): Source-linked recreation software comparison.
- [Developers]({BASE_URL}/developers): API resources and interactive documentation.

## Key facts

- FastBooking is MIT-licensed: https://github.com/predictivelabsai/FastBooking
- Customer relationship workflows can connect to FastCRM while FastBooking remains the booking and availability source.
- Clinical records remain in FastClinic; FastBooking stores appointment allocation references only.
- Product configuration is restricted to the tenant admin role.
"""
    return Response(body, media_type="text/plain")


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
    for path, handler in (
        ("/sitemap.xml", sitemap),
        ("/robots.txt", robots),
        ("/llms.txt", llms),
    ):
        app.get(path)(handler)
        app.routes.insert(0, app.routes.pop())
