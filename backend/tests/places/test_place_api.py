import pytest
from rest_framework import status

from apps.geohub.models import GeoCoverage, PlaceType
from apps.places.models import Place


@pytest.fixture
def place_type(db):
    return PlaceType.objects.create(code="city", name="Город", radius_meters_default=250)


@pytest.mark.django_db
def test_create_place(api_client, regular_user, place_type):
    api_client.force_authenticate(user=regular_user)
    payload = {
        "name": "Новое место",
        "description": "Описание",
        "place_type": place_type.id,
        "country": "RU",
    }
    resp = api_client.post("/api/places/places/", payload, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    place = Place.objects.get(id=resp.data["id"])
    assert place.created_by_id == regular_user.id
    assert place.place_type_id == place_type.id


@pytest.mark.django_db
def test_place_coverages(api_client, regular_user, place_type):
    api_client.force_authenticate(user=regular_user)
    coverage = GeoCoverage.objects.create(
        name="Точка",
        latitude=10,
        longitude=20,
        place_type=place_type,
        radius_meters=100,
    )
    resp = api_client.post(
        "/api/places/places/",
        {
            "name": "Место с покрытием",
            "coverage_ids": [coverage.id],
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    resp_detail = api_client.get(f"/api/places/places/{resp.data['id']}/")
    assert resp_detail.status_code == status.HTTP_200_OK
    assert resp_detail.data["coverages"][0]["coverage"]["id"] == coverage.id
