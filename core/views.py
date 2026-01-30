from rest_framework_simplejwt.views import TokenViewBase
from .serializers import PhoneTokenObtainPairSerializer


class PhoneTokenObtainPairView(TokenViewBase):
    serializer_class = PhoneTokenObtainPairSerializer
