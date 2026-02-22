from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import CalculatorLead
from .serializers import LeadSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_leads(request):
    leads = CalculatorLead.objects.filter(manager=request.user)
    serializer = LeadSerializer(leads, many=True)
    return Response(serializer.data)