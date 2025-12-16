import pytest
from django.urls import reverse
from rest_framework import status

from apps.geohub.models import GeoCoverage, PlaceType


@pytest.mark.django_db
def test_place_type_crud(api_client, regular_user):
    api_client.force_authenticate(user=regular_user)
    url = "/api/geohub/place-types/"

    payload = {
        "code": "desert",
        "name": "Пустыня",
        "description": "Открытая песчаная местность",
        "radius_meters_default": 3000,
        "is_active": True,
    }
    create_resp = api_client.post(url, payload, format="json")
    assert create_resp.status_code == status.HTTP_201_CREATED
    place_type_id = create_resp.data["id"]

    detail_url = f"{url}{place_type_id}/"
    get_resp = api_client.get(detail_url)
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.data["name"] == payload["name"]
    assert get_resp.data["radius_meters_default"] == payload["radius_meters_default"]

    patch_resp = api_client.patch(detail_url, {"radius_meters_default": 3500}, format="json")
    assert patch_resp.status_code == status.HTTP_200_OK
    assert patch_resp.data["radius_meters_default"] == 3500

    delete_resp = api_client.delete(detail_url)
    assert delete_resp.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_place_type_list_filters_inactive(api_client):
    active = PlaceType.objects.create(code="active", name="Активный", radius_meters_default=500, is_active=True)
    PlaceType.objects.create(code="inactive", name="Неактивный", radius_meters_default=500, is_active=False)

    resp = api_client.get("/api/geohub/place-types/")
    assert resp.status_code == status.HTTP_200_OK
    codes = [item["code"] for item in resp.data["results"]]
    assert active.code in codes
    assert "inactive" not in codes


@pytest.mark.django_db
def test_geo_coverage_uses_place_type_default_radius(api_client, regular_user):
    api_client.force_authenticate(user=regular_user)
    place_type, _ = PlaceType.objects.get_or_create(
        code="city",
        defaults={
            "name": "Город",
            "radius_meters_default": 250,
            "is_active": True,
        },
    )

    resp = api_client.post(
        "/api/geohub/coverages/",
        {
            "name": "Точка в городе",
            "latitude": "55.7558",
            "longitude": "37.6173",
            "place_type": place_type.id,
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    coverage_id = resp.data["id"]
    coverage = GeoCoverage.objects.get(id=coverage_id)
    assert coverage.radius_meters == place_type.radius_meters_default
    assert resp.data["place_type_detail"]["code"] == place_type.code
