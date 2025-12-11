from rest_framework import permissions


class IsVetOrAdmin(permissions.BasePermission):
    """
    Allows access only to users with role 'vet' or 'admin'.
    Use this for endpoints/actions that only vets or admins should call (e.g. review).
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        # superuser always allowed
        if getattr(user, "is_superuser", False):
            return True
        role = getattr(user, "role", None)
        return role in ("vet", "admin")


class IsOwnerOrVetAdmin(permissions.BasePermission):
    """
    Object-level permission:
      - vets and admins have full access
      - owners (cattle owner or submitted_by) can access their objects
      - authenticated users can list/create (adjustable)
    """

    def has_permission(self, request, view):
        # require authentication for all actions (adjust if you allow public read)
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user

        # superuser always allowed
        if getattr(user, "is_superuser", False):
            return True

        # vets/admins allowed
        role = getattr(user, "role", None)
        if role in ("vet", "admin"):
            return True

        # Safe methods: allow authenticated users to read if they own the object or are related
        if request.method in permissions.SAFE_METHODS:
            # For Cattle model: check owner
            if hasattr(obj, "owner"):
                return obj.owner == user
            # For Diagnosis model: allow if submitted_by or cattle.owner matches user
            if hasattr(obj, "submitted_by"):
                if obj.submitted_by == user:
                    return True
                if hasattr(obj, "cattle") and getattr(obj.cattle, "owner", None) == user:
                    return True
            # default deny for safe methods if no relation
            return False

        # Non-safe methods (write/update/delete):
        # - allow if the user created/submitted it
        if hasattr(obj, "submitted_by") and obj.submitted_by == user:
            return True
        # - allow if the user is cattle owner
        if hasattr(obj, "cattle") and getattr(obj.cattle, "owner", None) == user:
            return True

        # otherwise deny
        return False
