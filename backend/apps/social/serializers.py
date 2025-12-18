from rest_framework import serializers

from .models import Activity, Follow


class FollowSerializer(serializers.ModelSerializer):
    follower = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Follow
        fields = ["id", "follower", "target", "created_at"]
        read_only_fields = ["id", "follower", "created_at"]


class ActivitySerializer(serializers.ModelSerializer):
    actor = serializers.PrimaryKeyRelatedField(read_only=True)
    target_type = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            "id",
            "actor",
            "verb",
            "object_id",
            "target_type",
            "payload",
            "is_recommended",
            "created_at",
        ]
        read_only_fields = fields

    def get_target_type(self, obj: Activity) -> str:
        return f"{obj.content_type.app_label}.{obj.content_type.model}"
