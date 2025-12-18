from typing import Any

from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Trip, TripPoint


class TripPointSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=TripPoint.objects.all(),
        required=False,
        allow_null=True,
        help_text=_("Родительская точка (для древовидной структуры)."),
    )

    class Meta:
        model = TripPoint
        fields = [
            "id",
            "trip",
            "parent",
            "place",
            "note",
            "path",
            "depth",
        ]
        read_only_fields = ("id", "path", "depth")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        trip = attrs.get("trip") or getattr(self.instance, "trip", None)
        if self.instance and "trip" in attrs and attrs["trip"] != self.instance.trip:
            raise serializers.ValidationError(_("Нельзя менять маршрут у точки."))
        parent = attrs.get("parent")
        if parent and parent.trip_id != (trip.id if trip else None):
            raise serializers.ValidationError(_("Родительская точка принадлежит другому маршруту."))
        if parent and self.instance and parent.id == self.instance.id:
            raise serializers.ValidationError(_("Точка не может быть родителем самой себя."))
        return attrs

    def create(self, validated_data):
        parent = validated_data.pop("parent", None)
        if parent:
            return parent.add_child(**validated_data)
        return TripPoint.add_root(**validated_data)

    def update(self, instance, validated_data):
        parent = validated_data.pop("parent", None)
        if parent is not None and parent != instance.get_parent():
            instance.move(parent, pos="last-child")
        elif parent is None and instance.get_parent():
            raise serializers.ValidationError(_("Нельзя переносить в корень через этот метод."))
        return super().update(instance, validated_data)


class TripPointTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = TripPoint
        fields = [
            "id",
            "trip",
            "place",
            "note",
            "path",
            "depth",
            "children",
        ]

    def get_children(self, obj):
        children = obj.get_children()
        serializer = TripPointTreeSerializer(children, many=True, context=self.context)
        return serializer.data


class TripSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    source_trip = serializers.PrimaryKeyRelatedField(read_only=True)
    points = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Trip
        fields = [
            "id",
            "owner",
            "title",
            "short_description",
            "description",
            "is_public",
            "is_hidden",
            "source_trip",
            "points",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "owner", "source_trip", "created_at", "updated_at", "points")

    @extend_schema_field({"type": "array", "items": {"type": "object"}})
    def get_points(self, obj) -> list[dict[str, Any]]:
        nodes = obj.points.all().order_by("path")
        path_map = {}
        roots = []
        steplen = nodes[0].steplen if nodes else 4

        for node in nodes:
            data = {
                "id": node.id,
                "trip": node.trip_id,
                "place": node.place_id,
                "note": node.note,
                "path": node.path,
                "depth": node.depth,
                "children": [],
            }
            path_map[node.path] = data
            parent_path = node.path[:-steplen] if node.depth > 1 else None
            if parent_path and parent_path in path_map:
                path_map[parent_path]["children"].append(data)
            else:
                roots.append(data)
        return roots
