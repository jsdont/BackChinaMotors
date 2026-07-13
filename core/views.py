from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenViewBase

from .models import Deal, DealAssignment, Comment
from .serializers import (
    PhoneTokenObtainPairSerializer,
    RegisterPersonSerializer,
    RegisterCompanySerializer,
    RegisterServiceSerializer,
    RegisterBankSerializer,
    RegisterPartnerSerializer,
    DealSerializer,
    DealCreateSerializer,
    DealAssignmentSerializer,
    CommentSerializer,
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
        "user_id": user.id,
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


# =========================================================
# СДЕЛКИ — MVP-взаимодействие ролей: клиент создаёт сделку по технике,
# админ назначает исполнителей (брокер/СВХ/лаборатория/логист/декларант/
# банк) через Django admin, каждый видит и обновляет свою часть.
# =========================================================

CUSTOMER_ROLES = ("CUSTOMER_PERSON", "CUSTOMER_COMPANY")


def _is_deal_participant(user, deal):
    if user.is_staff or user.role == "ADMIN":
        return True
    if deal.customer_id == user.id:
        return True
    return DealAssignment.objects.filter(deal=deal, assigned_user=user).exists()


class MyDealsView(generics.ListCreateAPIView):
    """Клиент: список своих сделок / создание новой сделки по технике."""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Deal.objects.filter(customer=self.request.user).order_by("-created_at")

    def get_serializer_class(self):
        return DealCreateSerializer if self.request.method == "POST" else DealSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role not in CUSTOMER_ROLES:
            raise PermissionDenied("Сделку может создать только клиент.")
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        deal = serializer.save()
        return Response(DealSerializer(deal).data, status=201)


class AssignedDealsView(generics.ListAPIView):
    """Сервисный/банковский аккаунт: сделки, где он назначен исполнителем."""
    serializer_class = DealSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Deal.objects.filter(
            assignments__assigned_user=self.request.user
        ).distinct().order_by("-created_at")


class DealDetailView(generics.RetrieveAPIView):
    serializer_class = DealSerializer
    permission_classes = [IsAuthenticated]
    queryset = Deal.objects.all()

    def get_object(self):
        deal = super().get_object()
        if not _is_deal_participant(self.request.user, deal):
            raise PermissionDenied("Нет доступа к этой сделке.")
        return deal


class UpdateMyAssignmentView(generics.UpdateAPIView):
    """Исполнитель обновляет статус/заметку своего этапа сделки."""
    serializer_class = DealAssignmentSerializer
    permission_classes = [IsAuthenticated]
    queryset = DealAssignment.objects.all()
    http_method_names = ["patch"]

    def get_object(self):
        assignment = super().get_object()
        if assignment.assigned_user_id != self.request.user.id and not self.request.user.is_staff:
            raise PermissionDenied("Это назначение принадлежит другому исполнителю.")
        return assignment


class DealCommentsView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def _get_deal(self):
        deal = generics.get_object_or_404(Deal, pk=self.kwargs["deal_id"])
        if not _is_deal_participant(self.request.user, deal):
            raise PermissionDenied("Нет доступа к этой сделке.")
        return deal

    def get_queryset(self):
        deal = self._get_deal()
        return Comment.objects.filter(deal=deal).order_by("created_at")

    def perform_create(self, serializer):
        deal = self._get_deal()
        serializer.save(deal=deal, author=self.request.user)
