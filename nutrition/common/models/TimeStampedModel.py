from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """Абстрактная модель с полями даты создания и обновления."""

    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
        help_text=_("Date when the object was created"),
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        auto_now=True,
        help_text=_("Date when the object was last updated"),
    )

    class Meta:
        abstract = True
