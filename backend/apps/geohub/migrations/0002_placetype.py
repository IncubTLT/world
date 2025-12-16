from django.db import migrations, models


def seed_place_types(apps, schema_editor):
    PlaceType = apps.get_model("geohub", "PlaceType")
    defaults = [
        ("beach", "Пляж", "Пляжное место или береговая линия"),
        ("city", "Город", "Городское место"),
        ("sight", "Достопримечательность", "Любой интересный объект"),
        ("trek", "Маршрут", "Пешеходный/трекинговый маршрут"),
    ]
    for code, name, desc in defaults:
        PlaceType.objects.get_or_create(
            code=code,
            defaults={"name": name, "description": desc},
        )


def unseed_place_types(apps, schema_editor):
    PlaceType = apps.get_model("geohub", "PlaceType")
    PlaceType.objects.filter(code__in=["beach", "city", "sight", "trek"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("geohub", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlaceType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("code", models.SlugField(help_text="Уникальный код типа, используется на фронтенде и при импорте.", max_length=32, unique=True, verbose_name="Код")),
                ("name", models.CharField(max_length=100, verbose_name="Название")),
                ("description", models.CharField(blank=True, max_length=255, verbose_name="Описание")),
                ("is_active", models.BooleanField(default=True, help_text="Неактивные типы скрываются из списка.", verbose_name="Активен")),
            ],
            options={
                "verbose_name": "Тип места",
                "verbose_name_plural": "Типы мест",
                "ordering": ("name",),
            },
        ),
        migrations.RunPython(seed_place_types, reverse_code=unseed_place_types),
    ]
