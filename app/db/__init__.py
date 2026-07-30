"""Database model registry."""

# Import model modules so Base.metadata always contains the complete schema.
from app.db import models as commerce_models  # noqa: F401
from app.db import platform_models as platform_models  # noqa: F401
