from django.db import models


class Thing(models.Model):
    name = models.CharField(max_length=64)

    class Meta:
        app_label = "django_app"
