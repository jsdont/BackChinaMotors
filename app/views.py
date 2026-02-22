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


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_lead_status(request, pk):
    try:
        lead = CalculatorLead.objects.get(pk=pk, manager=request.user)
    except CalculatorLead.DoesNotExist:
        return Response({"error": "Lead not found"}, status=404)

    serializer = LeadStatusUpdateSerializer(lead, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=400)