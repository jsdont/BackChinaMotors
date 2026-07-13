from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from .models import User, Client, Company, ServiceProvider, Bank, Partner, Deal, DealAssignment, Comment


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


class RegisterServiceSerializer(serializers.Serializer):
    # Брокер / СВХ / Лаборатория / Логист / Декларант — одна форма с
    # выбором роли, как register_service.ejs в v32fix_work.
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    company_name = serializers.CharField()
    bin = serializers.CharField(required=False, allow_blank=True, default="")
    role_key = serializers.ChoiceField(choices=ServiceProvider.SERVICE_TYPE_CHOICES)

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Такой телефон уже зарегистрирован.")
        return value

    def create(self, validated_data):
        role_key = validated_data["role_key"]
        user = User.objects.create_user(
            phone=validated_data["phone"],
            password=validated_data["password"],
            role=f"SERVICE_{role_key}",
        )
        ServiceProvider.objects.create(
            user=user,
            service_type=role_key,
            company_name=validated_data["company_name"],
            bin=validated_data.get("bin") or "",
        )
        return user


class RegisterBankSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    bank_name = serializers.CharField()
    bik = serializers.CharField(required=False, allow_blank=True, default="")
    address = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Такой телефон уже зарегистрирован.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            phone=validated_data["phone"],
            password=validated_data["password"],
            role="BANK",
        )
        Bank.objects.create(
            user=user,
            bank_name=validated_data["bank_name"],
            bik=validated_data.get("bik") or "",
            address=validated_data.get("address") or "",
        )
        return user


class RegisterPartnerSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    company_name = serializers.CharField()
    country = serializers.CharField(required=False, allow_blank=True, default="China")
    reg_no = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Такой телефон уже зарегистрирован.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            phone=validated_data["phone"],
            password=validated_data["password"],
            role="PARTNER",
        )
        Partner.objects.create(
            user=user,
            company_name=validated_data["company_name"],
            country=validated_data.get("country") or "China",
            reg_no=validated_data.get("reg_no") or "",
        )
        return user


def _user_label(user):
    if not user:
        return None
    profile = (
        getattr(user, "client_profile", None)
        or getattr(user, "company_profile", None)
        or getattr(user, "service_profile", None)
        or getattr(user, "bank_profile", None)
        or getattr(user, "partner_profile", None)
    )
    name = None
    if profile is not None:
        name = getattr(profile, "full_name", None) or getattr(profile, "company_name", None) or getattr(profile, "bank_name", None)
    return {"id": user.id, "phone": user.phone, "role": user.role, "name": name}


class DealAssignmentSerializer(serializers.ModelSerializer):
    assigned_user_info = serializers.SerializerMethodField()

    class Meta:
        model = DealAssignment
        fields = ["id", "deal", "role", "assigned_user", "assigned_user_info", "status", "note", "updated_at"]
        read_only_fields = ["id", "deal", "role", "assigned_user", "updated_at"]

    def get_assigned_user_info(self, obj):
        return _user_label(obj.assigned_user)


class DealSerializer(serializers.ModelSerializer):
    assignments = DealAssignmentSerializer(many=True, read_only=True)
    customer_info = serializers.SerializerMethodField()
    vehicle_title = serializers.SerializerMethodField()

    class Meta:
        model = Deal
        fields = [
            "id", "customer", "customer_info", "vehicle", "vehicle_title",
            "title", "status", "total_price", "is_paid",
            "created_at", "updated_at", "assignments",
        ]
        read_only_fields = ["id", "customer", "created_at", "updated_at", "assignments"]

    def get_customer_info(self, obj):
        return _user_label(obj.customer)

    def get_vehicle_title(self, obj):
        v = obj.vehicle
        if not v:
            return None
        return v.name or f"{v.brand} {v.model}".strip()


class DealCreateSerializer(serializers.Serializer):
    vehicle_id = serializers.IntegerField(required=False, allow_null=True)
    title = serializers.CharField(required=False, allow_blank=True, default="")

    def create(self, validated_data):
        from cars.models import Vehicle

        user = self.context["request"].user
        vehicle = None
        vehicle_id = validated_data.get("vehicle_id")
        if vehicle_id:
            try:
                vehicle = Vehicle.objects.get(id=vehicle_id)
            except Vehicle.DoesNotExist:
                raise serializers.ValidationError({"vehicle_id": "Техника не найдена."})

        title = validated_data.get("title") or (str(vehicle) if vehicle else "")
        deal = Deal.objects.create(customer=user, vehicle=vehicle, title=title)
        return deal


class CommentSerializer(serializers.ModelSerializer):
    author_info = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "deal", "author", "author_info", "text", "created_at"]
        read_only_fields = ["id", "deal", "author", "author_info", "created_at"]

    def get_author_info(self, obj):
        return _user_label(obj.author)


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
