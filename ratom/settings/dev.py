# flake8: noqa
import os
import sys

from ratom.settings.base import *  # noqa

DEBUG = True

USE_DEBUG_TOOLBAR = os.getenv("USE_DEBUG_TOOLBAR", False)

INSTALLED_APPS += (
    "corsheaders",
)

MIDDLEWARE += (
    "corsheaders.middleware.CorsMiddleware",
)


if USE_DEBUG_TOOLBAR:
    INSTALLED_APPS += (
        "debug_toolbar",
    )

    MIDDLEWARE += (
     "debug_toolbar.middleware.DebugToolbarMiddleware",
    )

CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-version-requested",
]

INTERNAL_IPS = ("127.0.0.1",)

#: Don't send emails, just print them on stdout
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

#: Run celery tasks synchronously
CELERY_TASK_ALWAYS_EAGER = True

#: Tell us when a synchronous celery task fails
CELERY_TASK_EAGER_PROPAGATES = True

SECRET_KEY = os.environ.get(
    "SECRET_KEY", "#bd9o-0&)wpy=uhy*#zc7ppe05h8b^f68+&hv7dzs5qf&t@gq6"
)

# Special test settings
if "test" in sys.argv:
    PASSWORD_HASHERS = (
        "django.contrib.auth.hashers.SHA1PasswordHasher",
        "django.contrib.auth.hashers.MD5PasswordHasher",
    )

    LOGGING["root"]["handlers"] = []

if os.getenv("DATABASE_URL"):
    import dj_database_url

    db_from_env = dj_database_url.config(
        conn_max_age=500,
        ssl_require=os.getenv("DATABASE_SSL", False),
    )
    DATABASES["default"].update(db_from_env)

RATOM_SAMPLE_DATA_ENABLED = True
