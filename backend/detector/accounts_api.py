"""
Account and project-management API used by the React dashboard's login and
"create project" flows. Separate from:
  - api.py       (ProjectTokenAuthentication, used only by CI uploads)
  - read_api.py  (unauthenticated, scoped by Project.is_public)

Login uses JWT (djangorestframework-simplejwt). A project's CI upload token
is a completely different credential and is never derived from a JWT.
"""
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Project

User = get_user_model()


# ---- registration / identity ------------------------------------------------

class RegisterSerializer(serializers.Serializer):
    username = serializers.RegexField(r"^[\w.@+-]{3,150}$")
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("That username is taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with that email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)  # enforces Django's AUTH_PASSWORD_VALIDATORS
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class RegisterView(APIView):
    """POST /api/auth/register/ -> creates the user and logs them in (returns JWTs)."""

    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh), "username": user.username},
            status=201,
        )


class MeView(APIView):
    """GET /api/auth/me/ -> the logged-in user's identity."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"username": request.user.username, "email": request.user.email})


# ---- project management (owner-scoped, distinct from the public read API) --

SLUG_RE = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class OwnedProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "slug", "repo", "default_branch", "is_public", "created_at"]
        read_only_fields = fields


class ProjectCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    slug = serializers.RegexField(SLUG_RE, max_length=50)
    repo = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    default_branch = serializers.CharField(max_length=100, required=False, default="main")
    is_public = serializers.BooleanField(required=False, default=False)

    def validate_slug(self, value):
        if Project.objects.filter(slug=value).exists():
            raise serializers.ValidationError("That project slug is already taken.")
        return value


class ProjectUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        # Slug is intentionally excluded: it's baked into the CI config and
        # the public dashboard URL, so changing it would break both silently.
        fields = ["name", "repo", "default_branch", "is_public"]
        extra_kwargs = {f: {"required": False} for f in fields}


class MyProjectsView(APIView):
    """GET /api/auth/projects/  (list mine)   POST /api/auth/projects/  (create)"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        projects = Project.objects.filter(owner=request.user).order_by("-created_at")
        return Response(OwnedProjectSerializer(projects, many=True).data)

    def post(self, request):
        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project, token = Project.create_with_token(owner=request.user, **serializer.validated_data)
        # The raw token is shown exactly once. It is never retrievable again,
        # only replaceable via regenerate-token.
        return Response(
            {"project": OwnedProjectSerializer(project).data, "token": token}, status=201
        )


class ProjectDetailView(APIView):
    """GET/PATCH /api/auth/projects/<slug>/  (mine only; 404s for anyone else's)"""

    permission_classes = [IsAuthenticated]

    def _get(self, request, slug):
        return get_object_or_404(Project, slug=slug, owner=request.user)

    def get(self, request, slug):
        return Response(OwnedProjectSerializer(self._get(request, slug)).data)

    def patch(self, request, slug):
        project = self._get(request, slug)
        serializer = ProjectUpdateSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(OwnedProjectSerializer(project).data)


class RegenerateTokenView(APIView):
    """POST /api/auth/projects/<slug>/regenerate-token/ -> invalidates the old
    token immediately and returns the new one, shown exactly once."""

    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        project = get_object_or_404(Project, slug=slug, owner=request.user)
        raw = secrets.token_urlsafe(32)
        project.token_hash = Project.hash_token(raw)
        project.save(update_fields=["token_hash"])
        return Response({"token": raw})