from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from .models import User, Deal, Payment, Document


class DealPaymentsDocumentsAPITest(TestCase):
    """Клиент видит платежи и документы своей сделки; чужой пользователь — нет."""

    def setUp(self):
        self.owner = User.objects.create_user(
            phone="+77000000001", password="pass12345", role="CUSTOMER_PERSON"
        )
        self.other = User.objects.create_user(
            phone="+77000000002", password="pass12345", role="CUSTOMER_PERSON"
        )
        self.manager = User.objects.create_user(
            phone="+77000000003", password="pass12345", role="MANAGER", is_staff=True
        )
        self.deal = Deal.objects.create(customer=self.owner, title="Тестовая сделка")
        Payment.objects.create(deal=self.deal, amount=Decimal("1500000.00"), is_confirmed=True,
                               confirmed_by=self.manager)
        Payment.objects.create(deal=self.deal, amount=Decimal("500000.00"), is_confirmed=False)
        Document.objects.create(deal=self.deal, type="CONTRACT", uploaded_by=self.manager)

    def _client_for(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_owner_sees_payments(self):
        res = self._client_for(self.owner).get(f"/api/deals/{self.deal.id}/payments/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 2)
        amounts = {str(p["amount"]) for p in res.data}
        self.assertEqual(amounts, {"1500000.00", "500000.00"})
        confirmed = {p["is_confirmed"] for p in res.data}
        self.assertEqual(confirmed, {True, False})

    def test_owner_sees_documents_with_type_label(self):
        res = self._client_for(self.owner).get(f"/api/deals/{self.deal.id}/documents/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["type"], "CONTRACT")
        self.assertEqual(res.data[0]["type_display"], "Договор")

    def test_non_participant_denied(self):
        for path in ("payments", "documents"):
            res = self._client_for(self.other).get(f"/api/deals/{self.deal.id}/{path}/")
            self.assertEqual(res.status_code, 403, f"{path} should be forbidden for non-participant")

    def test_manager_sees_everything(self):
        res = self._client_for(self.manager).get(f"/api/deals/{self.deal.id}/payments/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 2)

    def test_anonymous_denied(self):
        res = APIClient().get(f"/api/deals/{self.deal.id}/payments/")
        self.assertEqual(res.status_code, 401)
