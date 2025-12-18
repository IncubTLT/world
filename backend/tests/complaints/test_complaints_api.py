import pytest
from rest_framework import status

from apps.complaints.models import Complaint, ComplaintStatus
from apps.geohub.models import PlaceType
from apps.places.models import Place


@pytest.fixture
def place(db, regular_user):
    pt = PlaceType.objects.create(code="city", name="Город", radius_meters_default=250)
    return Place.objects.create(name="Test place", place_type=pt, created_by=regular_user)


@pytest.mark.django_db
def test_create_complaint(api_client, regular_user, place):
    api_client.force_authenticate(user=regular_user)
    payload = {
        "target_app_label": "places",
        "target_model": "place",
        "target_object_id": place.id,
        "reason": "Спам",
    }
    resp = api_client.post("/api/complaints/complaints/", payload, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    complaint = Complaint.objects.get(id=resp.data["id"])
    assert complaint.author_id == regular_user.id
    assert complaint.content_object == place
    assert complaint.status == ComplaintStatus.OPEN
    assert complaint.snapshot.get("label")


@pytest.mark.django_db
def test_owner_cannot_update(api_client, regular_user, place):
    complaint = Complaint.objects.create(
        author=regular_user,
        content_object=place,
        content_type=Complaint._meta.get_field("content_type").remote_field.model.objects.get_for_model(place),
        object_id=place.id,
        reason="Спам",
    )
    api_client.force_authenticate(user=regular_user)
    resp = api_client.patch(
        f"/api/complaints/complaints/{complaint.id}/",
        {"status": ComplaintStatus.RESOLVED},
        format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_moderator_can_update(api_client, staff_user, place):
    staff_user.role = "moderator"
    staff_user.save(update_fields=["role"])
    complaint = Complaint.objects.create(
        author=staff_user,
        content_object=place,
        content_type=Complaint._meta.get_field("content_type").remote_field.model.objects.get_for_model(place),
        object_id=place.id,
        reason="Проверить",
    )
    api_client.force_authenticate(user=staff_user)
    resp = api_client.patch(
        f"/api/complaints/complaints/{complaint.id}/",
        {"status": ComplaintStatus.RESOLVED, "moderator_comment": "Ок"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    complaint.refresh_from_db()
    assert complaint.status == ComplaintStatus.RESOLVED
    assert complaint.moderator_comment == "Ок"


@pytest.mark.django_db
def test_owner_can_delete(api_client, regular_user, place):
    complaint = Complaint.objects.create(
        author=regular_user,
        content_object=place,
        content_type=Complaint._meta.get_field("content_type").remote_field.model.objects.get_for_model(place),
        object_id=place.id,
        reason="Удалить",
    )
    api_client.force_authenticate(user=regular_user)
    resp = api_client.delete(f"/api/complaints/complaints/{complaint.id}/")
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert not Complaint.objects.filter(id=complaint.id).exists()
