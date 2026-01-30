from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone, password, **extra_fields):
        if not phone:
            raise ValueError("Phone must be set")

        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "ADMIN")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(phone, password, **extra_fields)


class User(AbstractUser):
    ROLE_CHOICES = (
        ('CLIENT', 'Client'),
        ('MANAGER', 'Manager'),
        ('ADMIN', 'Admin'),
    )

    username = None
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.phone} ({self.role})"



class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class Manager(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.phone


class Deal(models.Model):
    STATUS_CHOICES = (
        ('AGREEMENT', 'Согласование'),
        ('CONTRACT', 'Договор'),
        ('PURCHASE_CHINA', 'Покупка в Китае'),
        ('DELIVERY_KZ', 'Доставка в КЗ'),
        ('SVH', 'СВХ'),
        ('CUSTOMS', 'Таможня'),
        ('DELIVERY_CLIENT', 'Доставка клиенту'),
        ('COMPLETED', 'Завершена'),
    )

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    manager = models.ForeignKey(Manager, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Document(models.Model):
    DOCUMENT_TYPES = (
        ('CONTRACT', 'Договор'),
        ('GTD', 'ГТД'),
        ('CMR', 'CMR'),
        ('ACCEPTANCE', 'Акт приёма'),
        ('PHOTO', 'Фото'),
    )

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='documents/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Comment(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Payment(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_confirmed = models.BooleanField(default=False)
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Lead(models.Model):
    STATUS_CHOICES = (
        ('NEW', 'Новая'),
        ('CONTACTED', 'Связались'),
        ('ARCHIVED', 'Архив'),
    )

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    source = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    created_at = models.DateTimeField(auto_now_add=True)
