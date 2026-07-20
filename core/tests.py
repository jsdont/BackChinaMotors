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


class ManagerCabinetAPITest(TestCase):
    """Менеджер видит все сделки/заявки и меняет этап; клиент — нет."""

    def setUp(self):
        self.customer = User.objects.create_user(
            phone="+77000001001", password="pass12345", role="CUSTOMER_PERSON"
        )
        self.customer2 = User.objects.create_user(
            phone="+77000001002", password="pass12345", role="CUSTOMER_PERSON"
        )
        self.manager = User.objects.create_user(
            phone="+77000001003", password="pass12345", role="MANAGER"
        )
        self.deal1 = Deal.objects.create(customer=self.customer, title="Сделка 1", status="AGREEMENT")
        self.deal2 = Deal.objects.create(customer=self.customer2, title="Сделка 2", status="CUSTOMS")

    def _client_for(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_manager_sees_all_deals(self):
        res = self._client_for(self.manager).get("/api/manager/deals/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 2)

    def test_manager_deals_status_filter(self):
        res = self._client_for(self.manager).get("/api/manager/deals/?status=CUSTOMS")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Сделка 2")

    def test_customer_cannot_access_manager_deals(self):
        res = self._client_for(self.customer).get("/api/manager/deals/")
        self.assertEqual(res.status_code, 403)

    def test_manager_updates_deal_status(self):
        res = self._client_for(self.manager).patch(
            f"/api/manager/deals/{self.deal1.id}/status/", {"status": "CONTRACT"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.deal1.refresh_from_db()
        self.assertEqual(self.deal1.status, "CONTRACT")

    def test_customer_cannot_update_deal_status(self):
        res = self._client_for(self.customer).patch(
            f"/api/manager/deals/{self.deal1.id}/status/", {"status": "COMPLETED"}, format="json"
        )
        self.assertEqual(res.status_code, 403)
        self.deal1.refresh_from_db()
        self.assertEqual(self.deal1.status, "AGREEMENT")

    def test_manager_stats(self):
        res = self._client_for(self.manager).get("/api/manager/stats/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["deals_total"], 2)
        self.assertEqual(res.data["deals_active"], 2)
        self.assertEqual(res.data["deals_completed"], 0)
        self.assertEqual(res.data["deals_by_status"]["CUSTOMS"], 1)

    def test_manager_leads_requires_manager(self):
        self.assertEqual(self._client_for(self.customer).get("/api/manager/leads/").status_code, 403)
        self.assertEqual(self._client_for(self.manager).get("/api/manager/leads/").status_code, 200)
