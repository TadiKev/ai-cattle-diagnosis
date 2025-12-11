from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Cattle, Diagnosis, Media

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("username", "email", "full_name", "role", "farm_name", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Extra", {"fields": ("full_name", "role", "farm_name")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Extra", {"fields": ("full_name", "role", "farm_name")}),
    )

@admin.register(Cattle)
class CattleAdmin(admin.ModelAdmin):
    list_display = ("tag_number", "name", "breed", "age_years", "weight_kg", "last_checkup", "owner")
    search_fields = ("tag_number", "name", "breed")
    list_filter = ("breed",)

@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ("id", "file", "uploaded_at", "gradcam_url")
    readonly_fields = ("uploaded_at",)

@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ("id", "cattle", "top_prediction", "confidence", "severity", "status", "created_at")
    list_filter = ("severity", "status", "created_at")
    search_fields = ("cattle__tag_number", "top_prediction")
    readonly_fields = ("created_at",)
