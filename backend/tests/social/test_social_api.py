import pytest
from rest_framework import status

from apps.social.models import Activity, Follow
from apps.trips.models import Trip
from apps.reviews.models import Review
from apps.places.models import Place
from apps.geohub.models import PlaceType


@pytest.fixture
def place(db, regular_user):
    pt = PlaceType.objects.create(code="city", name="Город", radius_meters_default=250)
    return Place.objects.create(name="Place", place_type=pt, created_by=regular_user)


@pytest.mark.django_db
def test_follow_create_and_list(api_client, regular_user, staff_user):
    api_client.force_authenticate(user=regular_user)
    resp = api_client.post("/api/social/follows/", {"target": staff_user.id}, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    assert Follow.objects.filter(follower=regular_user, target=staff_user).exists()

    list_resp = api_client.get("/api/social/follows/")
    assert list_resp.status_code == status.HTTP_200_OK
    assert len(list_resp.data["results"]) == 1


@pytest.mark.django_db
def test_activity_feed_from_following(api_client, regular_user, staff_user, place):
    api_client.force_authenticate(user=regular_user)
    Follow.objects.create(follower=regular_user, target=staff_user)

    trip = Trip.objects.create(owner=staff_user, title="Trip A")
    Activity.objects.create(
        actor=staff_user,
        verb=Activity.Verb.TRIP_CREATED,
        content_type=Activity._meta.get_field("content_type").remote_field.model.objects.get_for_model(trip),
        object_id=trip.id,
    )

    resp = api_client.get("/api/social/feed/")
    assert resp.status_code == status.HTTP_200_OK
    assert any(item["verb"] == Activity.Verb.TRIP_CREATED for item in resp.data["results"])


@pytest.mark.django_db
def test_activity_feed_recommended_for_anon(api_client, place):
    review_author = place.created_by
    review = Review.objects.create(author=review_author, place=place, rating=5, text="Nice")
    Activity.objects.create(
        actor=review_author,
        verb=Activity.Verb.REVIEW_CREATED,
        is_recommended=True,
        content_type=Activity._meta.get_field("content_type").remote_field.model.objects.get_for_model(review),
        object_id=review.id,
    )

    resp = api_client.get("/api/social/feed/")
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data["results"]) >= 1
