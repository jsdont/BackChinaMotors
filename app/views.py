from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import CalculatorLead
from .serializers import LeadSerializer

from rest_framework import status
from .serializers import LeadStatusUpdateSerializer

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_leads(request):
    leads = CalculatorLead.objects.filter(manager=request.user)
    serializer = LeadSerializer(leads, many=True)
    return Response(serializer.data)


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