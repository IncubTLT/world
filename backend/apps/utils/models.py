from django.db import models
from django.utils.translation import gettext_lazy as _


class Create(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("Создано"))

    class Meta:
        abstract = True
        ordering = ('-created_at',)


class CreateUpdater(Create):
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Обновлено"))

    class Meta(Create.Meta):
        abstract = True
        ordering = ('-updated_at',)
