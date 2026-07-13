from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenViewBase

from .serializers import (
    PhoneTokenObtainPairSerializer,
    RegisterPersonSerializer,
    RegisterCompanySerializer,
    RegisterServiceSerializer,
    RegisterBankSerializer,
    RegisterPartnerSerializer,
)


class PhoneTokenObtainPairView(TokenViewBase):
    serializer_class = PhoneTokenObtainPairSerializer


def _register_response(user):
    refresh = RefreshToken.for_user(user)
    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "role": user.role,
        "is_verified": user.is_verified,
    }, status=201)


class RegisterPersonView(generics.CreateAPIView):
    serializer_class = RegisterPersonSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _register_response(user)


class RegisterCompanyView(generics.CreateAPIView):
    serializer_class = RegisterCompanySerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _register_response(user)


class RegisterServiceView(generics.CreateAPIView):
    serializer_class = RegisterServiceSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _register_response(user)


class RegisterBankView(generics.CreateAPIView):
    serializer_class = RegisterBankSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _register_response(user)


class RegisterPartnerView(generics.CreateAPIView):
    serializer_class = RegisterPartnerSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _register_response(user)
