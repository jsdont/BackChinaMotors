from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import CalculatorLead
from .serializers import LeadSerializer, ManagerLeadSerializer

from rest_framework import status
from .serializers import LeadStatusUpdateSerializer
from core.permissions import IsManager
from core.models import Deal, Manager, Client
from core.activity import log_activity

User = get_user_model()

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_leads(request):
    leads = CalculatorLead.objects.filter(manager=request.user)
    serializer = LeadSerializer(leads, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsManager])
def manager_leads(request):
    """Инбокс менеджера — все входящие заявки (с сайта/калькулятора),
    не только назначенные ему. Фильтр по статусу: ?status=new."""
    leads = CalculatorLead.objects.all().order_by("-created_at")
    status_filter = request.query_params.get("status")
    if status_filter:
        leads = leads.filter(status=status_filter)
    serializer = ManagerLeadSerializer(leads, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsManager])
def convert_lead_to_deal(request, pk):
    """Менеджер превращает заявку в сделку: находит клиента по телефону
    (или создаёт нового CUSTOMER_PERSON, если такого ещё нет), создаёт Deal
    с товаром из заявки и связывает заявку со сделкой, чтобы её нельзя было
    сконвертировать повторно."""
    try:
        lead = CalculatorLead.objects.get(pk=pk)
    except CalculatorLead.DoesNotExist:
        return Response({"error": "Заявка не найдена"}, status=404)

    if lead.converted_deal_id:
        return Response(
            {"error": "Заявка уже сконвертирована в сделку", "deal_id": lead.converted_deal_id},
            status=400,
        )

    phone = (lead.phone or "").strip()
    if not phone:
        return Response({"error": "У заявки нет телефона — сделку создать нельзя"}, status=400)

    with transaction.atomic():
        customer = User.objects.filter(phone=phone).first()
        created_customer = False
        if customer is None:
            customer = User.objects.create_user(
                phone=phone, password=None, role="CUSTOMER_PERSON", is_verified=False
            )
            Client.objects.create(user=customer, full_name=(lead.name or phone))
            created_customer = True

        manager = Manager.objects.filter(user=request.user).first()

        title = str(lead.product) if lead.product else (lead.name or f"Заявка {lead.calc_id}")

        deal = Deal.objects.create(
            customer=customer,
            vehicle=lead.product,
            manager=manager,
            title=title,
            calc_breakdown=lead.calc_breakdown,
        )
        # Материализуем расчёт в построчные строки, чтобы менеджер правил их
        # в админке, а не JSON.
        if lead.calc_breakdown:
            deal.sync_calc_rows(lead.calc_breakdown)

        lead.converted_deal = deal
        if lead.status == "new":
            lead.status = "in_progress"
        lead.save()

        log_activity(deal, request.user, f"Сделка создана из заявки {lead.calc_id}")

    return Response({
        "deal_id": deal.id,
        "deal_title": deal.title,
        "customer_phone": customer.phone,
        "created_customer": created_customer,
        "lead_id": lead.id,
        "lead_status": lead.status,
    }, status=201)


from django.utils import timezone

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_lead_status(request, pk):
    try:
        lead = CalculatorLead.objects.get(pk=pk, manager=request.user)
    except CalculatorLead.DoesNotExist:
        return Response({"error": "Lead not found"}, status=404)

    new_status = request.data.get("status")

    if not new_status:
        return Response({"error": "Status is required"}, status=400)

    # ❌ Нельзя менять закрытые лиды
    if lead.status in ["won", "lost"]:
        return Response(
            {"error": "Cannot change status of closed lead"},
            status=400
        )

    # ❌ Нельзя ставить won без продукта
    if new_status == "won" and not lead.product:
        return Response(
            {"error": "Cannot mark as won without product"},
            status=400
        )

    # Обновляем статус
    lead.status = new_status

    # Если выиграли — фиксируем дату и прибыль
    if new_status == "won":
        lead.closed_at = timezone.now()
        if lead.product:
            lead.profit_snapshot = lead.product.profit

    lead.save()

    return Response({
        "id": lead.id,
        "status": lead.status,
        "closed_at": lead.closed_at,
        "profit_snapshot": lead.profit_snapshot
    })