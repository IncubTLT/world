from django.db import migrations, models
import django.db.models.deletion


def ensure_place_types(apps, schema_editor):
    PlaceType = apps.get_model("geohub", "PlaceType")
    defaults = [
        ("city", "Город", "Городская среда", 250),
        ("forest", "Лес", "Лесная или труднопроходимая зона", 2000),
        ("plain", "Равнина", "Равнина/открытая местность", 1000),
        ("water", "Вода", "Озёра/реки/прибрежная зона", 5000),
        ("park", "Парк", "Парки, зелёные зоны в городе", 600),
        ("mountain", "Горы", "Горная местность", 3000),
    ]
    for code, name, desc, radius in defaults:
        PlaceType.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "description": desc,
                "radius_meters_default": radius,
                "is_active": True,
            },
        )


def map_coverages(apps, schema_editor):
    GeoCoverage = apps.get_model("geohub", "GeoCoverage")
    PlaceType = apps.get_model("geohub", "PlaceType")

    code_map = {
        "city": "city",
        "forest": "forest",
        "plain": "plain",
        "water": "water",
    }

    for coverage in GeoCoverage.objects.all():
        code = code_map.get(getattr(coverage, "environment", None)) or "city"
        place_type = PlaceType.objects.filter(code=code).first() or PlaceType.objects.first()
        coverage.place_type_id = place_type.id if place_type else None
        if coverage.radius_meters is None and place_type:
            coverage.radius_meters = place_type.radius_meters_default
        coverage.save(update_fields=["place_type", "radius_meters"])


class Migration(migrations.Migration):

    dependencies = [
        ("geohub", "0002_placetype"),
    ]

    operations = [
        migrations.AddField(
            model_name="placetype",
            name="radius_meters_default",
            field=models.PositiveIntegerField(default=1000, help_text="Будет подставлен в точку покрытия, если не указан вручную.", verbose_name="Радиус по умолчанию, м"),
        ),
        migrations.AddField(
            model_name="geocoverage",
            name="place_type",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="coverages", to="geohub.placetype", verbose_name="Тип местности", help_text="Определяет радиус по умолчанию и тип среды (город, лес и т.д.)."),
        ),
        migrations.RunPython(ensure_place_types, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(map_coverages, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="geocoverage",
            name="environment",
        ),
        migrations.AlterField(
            model_name="geocoverage",
            name="place_type",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="coverages", to="geohub.placetype", verbose_name="Тип местности", help_text="Определяет радиус по умолчанию и тип среды (город, лес и т.д.)."),
        ),
    ]
