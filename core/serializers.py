from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from .models import User, Client, Company


class RegisterPersonSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(required=False, allow_blank=True, default="")
    iin = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Такой телефон уже зарегистрирован.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            phone=validated_data["phone"],
            password=validated_data["password"],
            role="CUSTOMER_PERSON",
        )
        Client.objects.create(
            user=user,
            full_name=validated_data.get("full_name") or "",
            iin=validated_data.get("iin") or "",
        )
        return user


class RegisterCompanySerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    company_name = serializers.CharField()
    bin = serializers.CharField(required=False, allow_blank=True, default="")
    address = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Такой телефон уже зарегистрирован.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            phone=validated_data["phone"],
            password=validated_data["password"],
            role="CUSTOMER_COMPANY",
        )
        Company.objects.create(
            user=user,
            company_name=validated_data["company_name"],
            bin=validated_data.get("bin") or "",
            address=validated_data.get("address") or "",
        )
        return user


class PhoneTokenObtainPairSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone = attrs.get("phone")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            username=phone,   # ВАЖНО
            password=password,
        )

        if not user:
            raise serializers.ValidationError("Неверный телефон или пароль")

        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "role": user.role,
            "is_verified": user.is_verified,
        }
