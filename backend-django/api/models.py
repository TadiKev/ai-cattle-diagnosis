from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("farmer", "Farmer"),
        ("vet", "Veterinarian"),
        ("admin", "Admin"),
    )
    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="farmer")
    farm_name = models.CharField(max_length=255, blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return f"{self.username} ({self.role})"


class Cattle(models.Model):
    tag_number = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255, blank=True)
    breed = models.CharField(max_length=100, blank=True)
    age_years = models.PositiveIntegerField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    last_checkup = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cattle")

    def __str__(self):
        return f"{self.tag_number} - {self.name or 'Unnamed'}"


class Media(models.Model):
    file = models.ImageField(upload_to="images/")
    thumbnail = models.ImageField(upload_to="thumbnails/", null=True, blank=True)
    gradcam_url = models.URLField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Media {self.id} - {self.file.name}"


class Diagnosis(models.Model):
    SEVERITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    )
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("under_treatment", "Under Treatment"),
        ("resolved", "Resolved"),
        ("failed", "Failed"),
        ("rejected", "Rejected"),
        ("edited", "Edited"),
    )

    cattle = models.ForeignKey(Cattle, on_delete=models.CASCADE, related_name="diagnoses")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="submitted_diagnoses",
    )
    symptom_text = models.TextField(blank=True)
    images = models.ManyToManyField(Media, blank=True, related_name="diagnoses")
    predictions = models.JSONField(null=True, blank=True)  # list/dict per your app conventions
    top_prediction = models.JSONField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, null=True, blank=True)
    recommendation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # --- Review metadata (new) ---
    REVIEW_STATUS_CHOICES = [
        ("pending", "Pending review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("edited", "Edited by vet"),
    ]
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="diagnoses_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS_CHOICES, default="pending")
    review_notes = models.TextField(null=True, blank=True)

    def mark_reviewed(self, user, status: str = "approved", notes: str = ""):
        """Helper to mark a diagnosis as reviewed (call from views)."""
        self.review_status = status
        self.review_notes = notes or self.review_notes
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        # update status field to reflect review outcome (you can adjust mapping)
        if status == "approved":
            self.status = "under_treatment"
        elif status == "rejected":
            self.status = "rejected"
        elif status == "edited":
            self.status = "edited"
        self.save()

    def __str__(self):
        top = self.top_prediction or "unknown"
        # if top is dict try to show label
        if isinstance(top, dict):
            label = top.get("disease") or str(top)
        else:
            label = str(top)
        return f"Diagnosis {self.id} for {self.cattle} ({label})"


class DiagnosisAudit(models.Model):
    """
    Immutable audit trail for manual reviews/edits performed by vets/admins.
    Stores a before/after snapshot and optional notes.
    """
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.CASCADE, related_name="audits")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50)  # e.g. "approved", "rejected", "edited"
    timestamp = models.DateTimeField(auto_now_add=True)
    before = models.JSONField(null=True, blank=True)   # snapshot before change
    after = models.JSONField(null=True, blank=True)    # snapshot after change
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ("-timestamp",)

    def __str__(self):
        return f"Audit {self.id} on Diagnosis {self.diagnosis_id} by {self.actor or 'system'}"
