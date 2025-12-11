from typing import Any, Dict, List
from rest_framework import serializers
from .models import CustomUser, Cattle, Diagnosis, Media, DiagnosisAudit


class MediaSerializer(serializers.ModelSerializer):
    """Serializer for uploaded media files associated with Diagnoses."""
    class Meta:
        model = Media
        fields = ("id", "file", "thumbnail", "gradcam_url", "uploaded_at")
        read_only_fields = ("id", "thumbnail", "gradcam_url", "uploaded_at")


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for CustomUser.
    - write-only password field (so it never gets serialized back).
    - create() handles password hashing.
    """
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "username",
            "email",
            "password",
            "full_name",
            "role",
            "farm_name",
        )
        read_only_fields = ("id",)

    def create(self, validated_data: Dict[str, Any]) -> CustomUser:
        password = validated_data.pop("password")
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance: CustomUser, validated_data: Dict[str, Any]) -> CustomUser:
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class CattleSerializer(serializers.ModelSerializer):
    """Serializer for Cattle model. 'owner' is read-only (set from request.user in views)."""
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Cattle
        fields = (
            "id",
            "tag_number",
            "name",
            "breed",
            "age_years",
            "weight_kg",
            "last_checkup",
            "owner",
        )
        read_only_fields = ("id", "owner")


class DiagnosisSerializer(serializers.ModelSerializer):
    """
    Serializer for Diagnosis.
    Handles uploaded images and read-only fields for vet review.
    """
    images = MediaSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(
            max_length=None, allow_empty_file=False, use_url=False
        ),
        write_only=True,
        required=False,
        help_text="List of image files to attach to this diagnosis (write-only).",
    )
    cattle_id = serializers.PrimaryKeyRelatedField(
        source="cattle",
        queryset=Cattle.objects.all(),
        write_only=True,
        help_text="Primary key of the cattle related to this diagnosis.",
    )
    cattle = CattleSerializer(read_only=True)
    submitted_by = serializers.PrimaryKeyRelatedField(read_only=True)

    # Review fields
    reviewed_by = serializers.PrimaryKeyRelatedField(read_only=True)
    reviewed_at = serializers.DateTimeField(read_only=True)
    review_status = serializers.CharField(read_only=True)
    review_notes = serializers.CharField(read_only=True, allow_blank=True)

    class Meta:
        model = Diagnosis
        fields = (
            "id",
            "cattle",
            "cattle_id",
            "submitted_by",
            "symptom_text",
            "images",
            "uploaded_images",
            "predictions",
            "top_prediction",
            "confidence",
            "severity",
            "recommendation",
            "created_at",
            "status",
            # Review fields
            "review_status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
        )
        read_only_fields = (
            "id",
            "cattle",
            "images",
            "submitted_by",
            "created_at",
            "predictions",
            "top_prediction",
            "confidence",
            "review_status",
            "reviewed_by",
            "reviewed_at",
        )

    def create(self, validated_data: Dict[str, Any]) -> Diagnosis:
        uploaded_images: List[Any] = validated_data.pop("uploaded_images", [])
        cattle = validated_data.pop("cattle", None)
        user = self.context["request"].user if "request" in self.context else None

        diagnosis = Diagnosis.objects.create(
            cattle=cattle, submitted_by=user, **validated_data
        )

        for uploaded_file in uploaded_images:
            media = Media.objects.create(file=uploaded_file)
            diagnosis.images.add(media)

        diagnosis.save()
        return diagnosis


class DiagnosisReviewSerializer(serializers.Serializer):
    """
    Serializer for veterinary review of a diagnosis.
    Fields:
      - review_status: 'approved', 'rejected', 'edited'
      - review_notes: optional notes
      - top_prediction: optional override
      - predictions: optional override
      - recommendation: optional override
    """
    review_status = serializers.ChoiceField(
        choices=["approved", "rejected", "edited"], required=True
    )
    review_notes = serializers.CharField(required=False, allow_blank=True)
    top_prediction = serializers.DictField(child=serializers.CharField(), required=False)
    predictions = serializers.ListField(child=serializers.DictField(), required=False)
    recommendation = serializers.CharField(required=False, allow_blank=True)
