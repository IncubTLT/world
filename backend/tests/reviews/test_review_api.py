import pytest
from rest_framework import status

from apps.reviews.models import Review
from apps.places.models import Place
from apps.geohub.models import PlaceType


@pytest.fixture
def place(db, regular_user):
    pt = PlaceType.objects.create(code="city", name="Город", radius_meters_default=250)
    return Place.objects.create(name="Place for review", place_type=pt, created_by=regular_user)


@pytest.mark.django_db
def test_create_review(api_client, regular_user, place):
    api_client.force_authenticate(user=regular_user)
    payload = {
        "place": place.id,
        "rating": 5,
        "text": "Отличное место",
    }
    resp = api_client.post("/api/reviews/reviews/", payload, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    review = Review.objects.get(id=resp.data["id"])
    assert review.author_id == regular_user.id
    assert review.place_id == place.id
    assert review.rating == 5


@pytest.mark.django_db
def test_review_owner_permission(api_client, regular_user, staff_user, place):
    review = Review.objects.create(author=staff_user, place=place, rating=3, text="Сойдёт")
    api_client.force_authenticate(user=regular_user)

    resp = api_client.patch(
        f"/api/reviews/reviews/{review.id}/",
        {"text": "Пытаюсь изменить"},
        format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_moderator_can_update_review(api_client, staff_user, place):
    staff_user.role = "moderator"
    staff_user.save(update_fields=["role"])
    review = Review.objects.create(author=staff_user, place=place, rating=4, text="ok")

    api_client.force_authenticate(user=staff_user)
    resp = api_client.patch(
        f"/api/reviews/reviews/{review.id}/",
        {"text": "approved", "is_hidden": True},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    review.refresh_from_db()
    assert review.text == "approved"
    assert review.is_hidden is True


@pytest.mark.django_db
def test_hidden_reviews_not_visible_for_regular(api_client, regular_user, staff_user, place):
    review = Review.objects.create(author=regular_user, place=place, rating=5, text="виден", is_hidden=False)
    Review.objects.create(author=staff_user, place=place, rating=4, text="скрыт", is_hidden=True)

    resp = api_client.get("/api/reviews/reviews/?place=%s" % place.id)
    assert resp.status_code == status.HTTP_200_OK
    results = resp.data["results"] if isinstance(resp.data, dict) and "results" in resp.data else resp.data
    assert len(results) == 1
    assert results[0]["id"] == review.id


@pytest.mark.django_db
def test_place_average_rating(api_client, regular_user, staff_user, place):
    Review.objects.create(author=regular_user, place=place, rating=4, text="good")
    Review.objects.create(author=staff_user, place=place, rating=2, text="bad", is_hidden=True)
    api_client.force_authenticate(user=regular_user)
    resp = api_client.get(f"/api/places/places/{place.id}/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["rating_avg"] == "4.00"
    assert resp.data["rating_count"] == 1
