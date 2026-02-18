import json

from django.http import JsonResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from api.serializers import RegisterSerializer


def health(request):
    """
    Health check endpoint for load balancers and monitoring.

    Returns:
        JSON response with status and version information.
    """
    return JsonResponse({
        "status": "ok",
        "version": "0.1.0",
    })


class RegisterView(APIView):
    """Self-service registration endpoint for operator users."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            },
            status=status.HTTP_201_CREATED,
        )
