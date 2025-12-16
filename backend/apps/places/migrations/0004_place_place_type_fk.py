from django.db import migrations, models
import django.db.models.deletion


def set_default_place_type(apps, schema_editor):
    Place = apps.get_model("places", "Place")
    PlaceType = apps.get_model("geohub", "PlaceType")
    default_type = PlaceType.objects.filter(code="other").first() or PlaceType.objects.first()
    if not default_type:
        return
    Place.objects.filter(place_type__isnull=True).update(place_type=default_type)


class Migration(migrations.Migration):

    dependencies = [
        ("geohub", "0002_placetype"),
        ("places", "0003_remove_placemedia_place_alter_place_options_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="place",
            name="place_type",
        ),
        migrations.AddField(
            model_name="place",
            name="place_type",
            field=models.ForeignKey(blank=True, help_text="Выбирается из справочника типов мест.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="places", to="geohub.placetype", verbose_name="Тип места"),
        ),
        migrations.RunPython(set_default_place_type, reverse_code=migrations.RunPython.noop),
    ]
