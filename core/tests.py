import tempfile
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
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


_TMP_MEDIA = tempfile.mkdtemp()


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}, MEDIA_ROOT=_TMP_MEDIA)
class ManagerAddPaymentsDocumentsTest(TestCase):
    """Менеджер добавляет платежи и документы по сделке из веб-кабинета."""

    def setUp(self):
        self.manager = User.objects.create_user(
            phone="+77000003001", password="pass12345", role="MANAGER"
        )
        self.customer = User.objects.create_user(
            phone="+77000003002", password="pass12345", role="CUSTOMER_PERSON"
        )
        self.deal = Deal.objects.create(customer=self.customer, title="Сделка", status="AGREEMENT")

    def _mgr(self):
        c = APIClient()
        c.force_authenticate(user=self.manager)
        return c

    def test_manager_adds_confirmed_payment(self):
        res = self._mgr().post(
            f"/api/manager/deals/{self.deal.id}/payments/",
            {"amount": "1200000.00", "is_confirmed": True}, format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        p = Payment.objects.get(deal=self.deal)
        self.assertEqual(p.amount, Decimal("1200000.00"))
        self.assertTrue(p.is_confirmed)
        self.assertEqual(p.confirmed_by_id, self.manager.id)

    def test_unconfirmed_payment_has_no_confirmer(self):
        res = self._mgr().post(
            f"/api/manager/deals/{self.deal.id}/payments/",
            {"amount": "500000.00"}, format="json",
        )
        self.assertEqual(res.status_code, 201)
        p = Payment.objects.get(deal=self.deal)
        self.assertFalse(p.is_confirmed)
        self.assertIsNone(p.confirmed_by_id)

    def test_customer_cannot_add_payment(self):
        c = APIClient()
        c.force_authenticate(user=self.customer)
        res = c.post(f"/api/manager/deals/{self.deal.id}/payments/", {"amount": "1"}, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(Payment.objects.count(), 0)

    def test_manager_uploads_document(self):
        f = SimpleUploadedFile("contract.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        res = self._mgr().post(
            f"/api/manager/deals/{self.deal.id}/documents/",
            {"type": "CONTRACT", "file": f}, format="multipart",
        )
        self.assertEqual(res.status_code, 201, res.data)
        d = Document.objects.get(deal=self.deal)
        self.assertEqual(d.type, "CONTRACT")
        self.assertEqual(d.uploaded_by_id, self.manager.id)
        self.assertTrue(d.file)

    def test_customer_cannot_upload_document(self):
        c = APIClient()
        c.force_authenticate(user=self.customer)
        f = SimpleUploadedFile("x.pdf", b"data", content_type="application/pdf")
        res = c.post(f"/api/manager/deals/{self.deal.id}/documents/", {"type": "GTD", "file": f}, format="multipart")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(Document.objects.count(), 0)
