from decimal import Decimal

from django.db.models import Count
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenViewBase

from .models import Deal, DealAssignment, Comment, Payment, Document, Expense, DealStage, DealMedia, DealActivity
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
    PaymentSerializer,
    DocumentSerializer,
    DealStatusUpdateSerializer,
    PaymentCreateSerializer,
    DocumentCreateSerializer,
    ExpenseSerializer,
    DealStageSerializer,
    DealMediaSerializer,
    DealMediaCreateSerializer,
    DealActivitySerializer,
)
from .serializers import _user_label
from .permissions import IsManager
from .activity import log_activity
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser


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
        log_activity(deal, request.user, "Сделка создана клиентом")
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


def _get_participant_deal(user, deal_id):
    """Достаёт сделку и проверяет, что пользователь — её участник (клиент,
    исполнитель или админ). Иначе 404/403."""
    deal = generics.get_object_or_404(Deal, pk=deal_id)
    if not _is_deal_participant(user, deal):
        raise PermissionDenied("Нет доступа к этой сделке.")
    return deal


class DealPaymentsView(generics.ListAPIView):
    """Платежи по сделке — просмотр для участников сделки. Создаются менеджером
    через Django admin (MVP)."""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        deal = _get_participant_deal(self.request.user, self.kwargs["deal_id"])
        return Payment.objects.filter(deal=deal).order_by("created_at")


class DealDocumentsView(generics.ListAPIView):
    """Документы по сделке — просмотр/скачивание для участников сделки.
    Загружаются менеджером через Django admin (MVP)."""
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        deal = _get_participant_deal(self.request.user, self.kwargs["deal_id"])
        return Document.objects.filter(deal=deal).order_by("-created_at")


class DealStagesView(generics.ListAPIView):
    """Кастомный план сделки — участники сделки (в т.ч. клиент) видят его как
    чек-лист. Составляет и меняет только менеджер (см. Manager*StageView)."""
    serializer_class = DealStageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        deal = _get_participant_deal(self.request.user, self.kwargs["deal_id"])
        return deal.stages.all()


class DealMediaView(generics.ListAPIView):
    """Галерея сделки (фото/видео) — участники сделки, включая клиента.
    Добавляет/удаляет только менеджер (см. ManagerDealMedia*View)."""
    serializer_class = DealMediaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        deal = _get_participant_deal(self.request.user, self.kwargs["deal_id"])
        return deal.media.all()


class DealActivityView(generics.ListAPIView):
    """Лог изменений — участники сделки (в т.ч. клиент). Внутренние события
    (расходы) клиенту не показываются."""
    serializer_class = DealActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        deal = _get_participant_deal(self.request.user, self.kwargs["deal_id"])
        return deal.activities.filter(internal=False)


# =========================================================
# КАБИНЕТ МЕНЕДЖЕРА — оперативный обзор: все сделки, смена этапа, инбокс
# заявок и сводка по счётчикам. Доступ только менеджеру/админу.
# =========================================================


class ManagerDealsView(generics.ListAPIView):
    """Все сделки (не только свои) с необязательным фильтром по этапу:
    ?status=CUSTOMS."""
    serializer_class = DealSerializer
    permission_classes = [IsManager]

    def get_queryset(self):
        qs = Deal.objects.all().order_by("-created_at")
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs


class ManagerDealStatusView(generics.UpdateAPIView):
    """Менеджер меняет этап сделки (status) и отметку об оплате (is_paid)."""
    serializer_class = DealStatusUpdateSerializer
    permission_classes = [IsManager]
    queryset = Deal.objects.all()
    http_method_names = ["patch"]

    def perform_update(self, serializer):
        deal = serializer.instance
        old_status, old_paid, old_price = deal.status, deal.is_paid, deal.total_price
        labels = dict(Deal.STATUS_CHOICES)
        obj = serializer.save()
        data = serializer.validated_data
        if "status" in data and obj.status != old_status:
            log_activity(obj, self.request.user,
                         f"Этап сделки изменён: {labels.get(old_status, old_status)} → {obj.get_status_display()}")
        if "is_paid" in data and obj.is_paid != old_paid:
            log_activity(obj, self.request.user,
                         "Отметка об оплате: " + ("оплачено" if obj.is_paid else "снята"))
        if "total_price" in data and obj.total_price != old_price:
            log_activity(obj, self.request.user, f"Указана стоимость сделки: {obj.total_price} ₸")


class ManagerStatsView(APIView):
    """Счётчики для дашборда менеджера: сделки по этапам и открытые заявки."""
    permission_classes = [IsManager]

    def get(self, request):
        from app.models import CalculatorLead

        by_status = {code: 0 for code, _ in Deal.STATUS_CHOICES}
        for row in Deal.objects.values("status").annotate(n=Count("id")):
            by_status[row["status"]] = row["n"]

        total_deals = sum(by_status.values())
        completed = by_status.get("COMPLETED", 0)

        leads_qs = CalculatorLead.objects.all()
        open_leads = leads_qs.exclude(status__in=["won", "lost"]).count()

        return Response({
            "deals_total": total_deals,
            "deals_active": total_deals - completed,
            "deals_completed": completed,
            "deals_by_status": by_status,
            "leads_total": leads_qs.count(),
            "leads_open": open_leads,
        })


class ManagerFinanceView(APIView):
    """Финансовый отчёт по сделкам (P&L): стоимость сделки, фактически
    полученные деньги (подтверждённые платежи), внутренние расходы и прибыль
    = стоимость − расходы. Все цифры реальные — из платежей и расходов,
    занесённых менеджером."""
    permission_classes = [IsManager]

    def get(self, request):
        from django.db.models import Sum, Q

        deals = (
            Deal.objects.all()
            .select_related("customer")
            .annotate(
                received=Sum("payment__amount", filter=Q(payment__is_confirmed=True)),
                pending=Sum("payment__amount", filter=Q(payment__is_confirmed=False)),
                expenses_sum=Sum("expenses__amount"),
            )
            .order_by("-created_at")
        )

        status_labels = dict(Deal.STATUS_CHOICES)
        rows = []
        total_value = Decimal("0")
        total_received = Decimal("0")
        total_pending = Decimal("0")
        total_expenses = Decimal("0")
        total_profit = Decimal("0")
        deals_with_price = 0

        for d in deals:
            value = d.total_price or Decimal("0")
            received = d.received or Decimal("0")
            pending = d.pending or Decimal("0")
            expenses = d.expenses_sum or Decimal("0")
            balance = value - received
            profit = value - expenses
            if d.total_price is not None:
                deals_with_price += 1
                total_value += value
                total_profit += profit
            total_received += received
            total_pending += pending
            total_expenses += expenses
            rows.append({
                "id": d.id,
                "title": d.title or f"Сделка #{d.id}",
                "customer": _user_label(d.customer),
                "status": d.status,
                "status_display": status_labels.get(d.status, d.status),
                "total_price": value,
                "received": received,
                "pending": pending,
                "balance": balance,
                "expenses": expenses,
                # Прибыль показываем только когда указана стоимость сделки —
                # иначе "прибыль" была бы просто минус расходы, что вводит в
                # заблуждение.
                "profit": (profit if d.total_price is not None else None),
            })

        return Response({
            "summary": {
                "deals_total": len(rows),
                "deals_with_price": deals_with_price,
                "total_value": total_value,
                "total_received": total_received,
                "total_pending": total_pending,
                "total_outstanding": total_value - total_received,
                "total_expenses": total_expenses,
                "total_profit": total_profit,
            },
            "deals": rows,
        })


class ManagerDealPaymentsCreateView(generics.CreateAPIView):
    """Менеджер добавляет платёж по сделке."""
    serializer_class = PaymentCreateSerializer
    permission_classes = [IsManager]

    def perform_create(self, serializer):
        deal = generics.get_object_or_404(Deal, pk=self.kwargs["deal_id"])
        confirmed = serializer.validated_data.get("is_confirmed", False)
        obj = serializer.save(deal=deal, confirmed_by=self.request.user if confirmed else None)
        log_activity(deal, self.request.user,
                     f"Добавлен платёж {obj.amount} ₸ ({'подтверждён' if obj.is_confirmed else 'ожидает'})")


class ManagerDealDocumentsCreateView(generics.CreateAPIView):
    """Менеджер загружает документ по сделке (файл уходит в Cloudinary)."""
    serializer_class = DocumentCreateSerializer
    permission_classes = [IsManager]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        deal = generics.get_object_or_404(Deal, pk=self.kwargs["deal_id"])
        obj = serializer.save(deal=deal, uploaded_by=self.request.user)
        log_activity(deal, self.request.user, f"Загружен документ: {obj.get_type_display()}")


class ManagerDealExpensesView(generics.ListCreateAPIView):
    """Расходы по сделке — список и добавление. ТОЛЬКО менеджер: клиенту эти
    внутренние затраты не показываются (нужны для расчёта прибыли)."""
    serializer_class = ExpenseSerializer
    permission_classes = [IsManager]

    def get_queryset(self):
        return Expense.objects.filter(deal_id=self.kwargs["deal_id"]).order_by("created_at")

    def perform_create(self, serializer):
        deal = generics.get_object_or_404(Deal, pk=self.kwargs["deal_id"])
        obj = serializer.save(deal=deal, created_by=self.request.user)
        log_activity(deal, self.request.user,
                     f"Добавлен расход: {obj.get_category_display()} {obj.amount} ₸", internal=True)


class ManagerExpenseDeleteView(generics.DestroyAPIView):
    """Менеджер удаляет ошибочно добавленный расход."""
    permission_classes = [IsManager]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

    def perform_destroy(self, instance):
        deal = instance.deal
        log_activity(deal, self.request.user,
                     f"Удалён расход: {instance.get_category_display()} {instance.amount} ₸", internal=True)
        instance.delete()


class ManagerDealStagesCreateView(generics.ListCreateAPIView):
    """Менеджер: список и добавление кастомных этапов сделки (конструктор
    сценариев). Новый этап встаёт в конец плана."""
    serializer_class = DealStageSerializer
    permission_classes = [IsManager]

    def get_queryset(self):
        return DealStage.objects.filter(deal_id=self.kwargs["deal_id"])

    def perform_create(self, serializer):
        deal = generics.get_object_or_404(Deal, pk=self.kwargs["deal_id"])
        last = deal.stages.order_by("-order").first()
        next_order = (last.order + 1) if last else 0
        obj = serializer.save(deal=deal, order=next_order)
        log_activity(deal, self.request.user, f"Добавлен этап плана: {obj.title}")


class ManagerDealStageDetailView(generics.UpdateAPIView, generics.DestroyAPIView):
    """Менеджер меняет этап (готовность/название/порядок) или удаляет его."""
    serializer_class = DealStageSerializer
    permission_classes = [IsManager]
    queryset = DealStage.objects.all()
    http_method_names = ["patch", "delete"]

    def perform_update(self, serializer):
        old_done = serializer.instance.is_done
        obj = serializer.save()
        if "is_done" in serializer.validated_data and obj.is_done != old_done:
            log_activity(obj.deal, self.request.user,
                         f"Этап плана {'выполнен' if obj.is_done else 'снят'}: {obj.title}")

    def perform_destroy(self, instance):
        log_activity(instance.deal, self.request.user, f"Удалён этап плана: {instance.title}")
        instance.delete()


class ManagerDealMediaCreateView(generics.ListCreateAPIView):
    """Менеджер: список галереи и добавление фото (файл, multipart) или видео
    (ссылка, JSON)."""
    permission_classes = [IsManager]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        return DealMediaCreateSerializer if self.request.method == "POST" else DealMediaSerializer

    def get_queryset(self):
        return DealMedia.objects.filter(deal_id=self.kwargs["deal_id"])

    def perform_create(self, serializer):
        deal = generics.get_object_or_404(Deal, pk=self.kwargs["deal_id"])
        obj = serializer.save(deal=deal, uploaded_by=self.request.user)
        log_activity(deal, self.request.user,
                     f"Добавлено {'видео' if obj.video_url else 'фото'} в галерею")


class ManagerDealMediaDeleteView(generics.DestroyAPIView):
    """Менеджер удаляет элемент галереи сделки."""
    permission_classes = [IsManager]
    queryset = DealMedia.objects.all()
    serializer_class = DealMediaSerializer

    def perform_destroy(self, instance):
        deal = instance.deal
        log_activity(deal, self.request.user, "Удалён файл из галереи")
        instance.delete()


class ManagerDealActivityView(generics.ListAPIView):
    """Полный лог изменений сделки — только менеджер (видит и внутренние
    события, например расходы)."""
    serializer_class = DealActivitySerializer
    permission_classes = [IsManager]

    def get_queryset(self):
        return DealActivity.objects.filter(deal_id=self.kwargs["deal_id"])
