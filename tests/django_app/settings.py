SECRET_KEY = "unmagic-test"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}
INSTALLED_APPS = ["tests.django_app"]
USE_TZ = True
