import pytest
from rest_framework import status

from apps.places.models import Place
from apps.trips.models import Trip, TripPoint


@pytest.fixture
def place(db, regular_user):
    return Place.objects.create(name="Test place", created_by=regular_user)


@pytest.mark.django_db
def test_create_trip(api_client, regular_user):
    api_client.force_authenticate(user=regular_user)
    payload = {"title": "Мой маршрут", "short_description": "Коротко", "description": "Полностью"}
    resp = api_client.post("/api/trips/trips/", payload, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    trip_id = resp.data["id"]
    trip = Trip.objects.get(id=trip_id)
    assert trip.owner_id == regular_user.id
    assert trip.title == payload["title"]


@pytest.mark.django_db
def test_trip_points_tree(api_client, regular_user, place):
    api_client.force_authenticate(user=regular_user)
    trip = Trip.objects.create(owner=regular_user, title="Маршрут")

    root = TripPoint.add_root(trip=trip, place=place, note="Корень")
    child = root.add_child(trip=trip, note="Дочерний")

    resp = api_client.get(f"/api/trips/trips/{trip.id}/")
    assert resp.status_code == status.HTTP_200_OK
    points = resp.data["points"]
    assert len(points) == 1
    assert points[0]["id"] == root.id
    assert points[0]["children"][0]["id"] == child.id


@pytest.mark.django_db
def test_trip_point_create_requires_owner(api_client, regular_user):
    other = Trip.objects.create(owner=regular_user, title="Чужой")  # owner same as user, used below
    api_client.force_authenticate(user=regular_user)
    resp = api_client.post(
        "/api/trips/trip-points/",
        {"trip": other.id, "note": "Новая точка"},
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_trip_point_forbid_wrong_owner(api_client, regular_user, staff_user):
    trip = Trip.objects.create(owner=staff_user, title="Не мой маршрут")
    api_client.force_authenticate(user=regular_user)
    resp = api_client.post(
        "/api/trips/trip-points/",
        {"trip": trip.id, "note": "Пытаюсь добавить"},
        format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
