import tempfile
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import User, Deal, Payment, Document, Expense, DealStage


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

    def test_manager_can_set_total_price(self):
        res = self._client_for(self.manager).patch(
            f"/api/manager/deals/{self.deal1.id}/status/", {"total_price": "5000000.00"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.deal1.refresh_from_db()
        self.assertEqual(self.deal1.total_price, Decimal("5000000.00"))


class ManagerFinanceReportTest(TestCase):
    """Финансовый отчёт: стоимость сделок против полученных/ожидаемых платежей."""

    def setUp(self):
        self.manager = User.objects.create_user(phone="+77000004001", password="p", role="MANAGER")
        self.customer = User.objects.create_user(phone="+77000004002", password="p", role="CUSTOMER_PERSON")
        # Сделка с ценой и частичной оплатой
        self.d1 = Deal.objects.create(customer=self.customer, title="Сделка 1", total_price=Decimal("10000000.00"))
        Payment.objects.create(deal=self.d1, amount=Decimal("6000000.00"), is_confirmed=True)
        Payment.objects.create(deal=self.d1, amount=Decimal("2000000.00"), is_confirmed=False)
        # Сделка без цены
        self.d2 = Deal.objects.create(customer=self.customer, title="Сделка 2")

    def _mgr(self):
        c = APIClient()
        c.force_authenticate(user=self.manager)
        return c

    def test_finance_report_totals(self):
        res = self._mgr().get("/api/manager/finance/")
        self.assertEqual(res.status_code, 200)
        s = res.data["summary"]
        self.assertEqual(s["deals_total"], 2)
        self.assertEqual(s["deals_with_price"], 1)
        self.assertEqual(Decimal(s["total_value"]), Decimal("10000000.00"))
        self.assertEqual(Decimal(s["total_received"]), Decimal("6000000.00"))
        self.assertEqual(Decimal(s["total_pending"]), Decimal("2000000.00"))
        self.assertEqual(Decimal(s["total_outstanding"]), Decimal("4000000.00"))

    def test_finance_report_per_deal(self):
        res = self._mgr().get("/api/manager/finance/")
        row = next(r for r in res.data["deals"] if r["id"] == self.d1.id)
        self.assertEqual(Decimal(row["received"]), Decimal("6000000.00"))
        self.assertEqual(Decimal(row["balance"]), Decimal("4000000.00"))

    def test_finance_requires_manager(self):
        c = APIClient()
        c.force_authenticate(user=self.customer)
        self.assertEqual(c.get("/api/manager/finance/").status_code, 403)


class ManagerExpensesTest(TestCase):
    """Расходы по сделке: менеджер добавляет/удаляет, клиент не имеет доступа;
    прибыль в отчёте = стоимость − расходы."""

    def setUp(self):
        self.manager = User.objects.create_user(phone="+77000005001", password="p", role="MANAGER")
        self.customer = User.objects.create_user(phone="+77000005002", password="p", role="CUSTOMER_PERSON")
        self.deal = Deal.objects.create(customer=self.customer, title="Сделка", total_price=Decimal("10000000.00"))

    def _mgr(self):
        c = APIClient()
        c.force_authenticate(user=self.manager)
        return c

    def _cust(self):
        c = APIClient()
        c.force_authenticate(user=self.customer)
        return c

    def test_manager_adds_and_lists_expense(self):
        res = self._mgr().post(
            f"/api/manager/deals/{self.deal.id}/expenses/",
            {"category": "PURCHASE", "amount": "4000000.00", "note": "Оплата поставщику"}, format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        e = Expense.objects.get(deal=self.deal)
        self.assertEqual(e.amount, Decimal("4000000.00"))
        self.assertEqual(e.created_by_id, self.manager.id)
        lst = self._mgr().get(f"/api/manager/deals/{self.deal.id}/expenses/")
        self.assertEqual(len(lst.data), 1)
        self.assertEqual(lst.data[0]["category_display"], "Закупка в Китае")

    def test_customer_cannot_access_expenses(self):
        self.assertEqual(self._cust().get(f"/api/manager/deals/{self.deal.id}/expenses/").status_code, 403)
        self.assertEqual(
            self._cust().post(f"/api/manager/deals/{self.deal.id}/expenses/", {"category": "OTHER", "amount": "1"}, format="json").status_code,
            403,
        )
        self.assertEqual(Expense.objects.count(), 0)

    def test_manager_deletes_expense(self):
        e = Expense.objects.create(deal=self.deal, category="LOGISTICS", amount=Decimal("500000.00"))
        res = self._mgr().delete(f"/api/manager/expenses/{e.id}/")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(Expense.objects.count(), 0)

    def test_finance_profit_is_value_minus_expenses(self):
        Payment.objects.create(deal=self.deal, amount=Decimal("6000000.00"), is_confirmed=True)
        Expense.objects.create(deal=self.deal, category="PURCHASE", amount=Decimal("4000000.00"))
        Expense.objects.create(deal=self.deal, category="CUSTOMS", amount=Decimal("1500000.00"))
        res = self._mgr().get("/api/manager/finance/")
        s = res.data["summary"]
        self.assertEqual(Decimal(s["total_expenses"]), Decimal("5500000.00"))
        # profit = 10,000,000 − 5,500,000 = 4,500,000
        self.assertEqual(Decimal(s["total_profit"]), Decimal("4500000.00"))
        row = next(r for r in res.data["deals"] if r["id"] == self.deal.id)
        self.assertEqual(Decimal(row["expenses"]), Decimal("5500000.00"))
        self.assertEqual(Decimal(row["profit"]), Decimal("4500000.00"))

    def test_finance_profit_null_without_price(self):
        d = Deal.objects.create(customer=self.customer, title="Без цены")
        Expense.objects.create(deal=d, category="OTHER", amount=Decimal("100000.00"))
        res = self._mgr().get("/api/manager/finance/")
        row = next(r for r in res.data["deals"] if r["id"] == d.id)
        self.assertIsNone(row["profit"])


class DealStageConstructorTest(TestCase):
    """Конструктор сценариев: менеджер создаёт/меняет/удаляет кастомные этапы;
    участник сделки (клиент) видит план, но менять не может."""

    def setUp(self):
        self.manager = User.objects.create_user(phone="+77000006001", password="p", role="MANAGER")
        self.customer = User.objects.create_user(phone="+77000006002", password="p", role="CUSTOMER_PERSON")
        self.other = User.objects.create_user(phone="+77000006003", password="p", role="CUSTOMER_PERSON")
        self.deal = Deal.objects.create(customer=self.customer, title="Сделка")

    def _c(self, u):
        c = APIClient()
        c.force_authenticate(user=u)
        return c

    def test_manager_adds_stages_in_order(self):
        r1 = self._c(self.manager).post(f"/api/manager/deals/{self.deal.id}/stages/", {"title": "Проверка техники"}, format="json")
        r2 = self._c(self.manager).post(f"/api/manager/deals/{self.deal.id}/stages/", {"title": "Оплата поставщику"}, format="json")
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(r1.data["order"], 0)
        self.assertEqual(r2.data["order"], 1)

    def test_customer_sees_stages_readonly(self):
        DealStage.objects.create(deal=self.deal, title="Этап 1", order=0)
        res = self._c(self.customer).get(f"/api/deals/{self.deal.id}/stages/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        # клиент не может создавать этапы (эндпоинт менеджерский → 403)
        self.assertEqual(
            self._c(self.customer).post(f"/api/manager/deals/{self.deal.id}/stages/", {"title": "x"}, format="json").status_code,
            403,
        )

    def test_non_participant_cannot_read(self):
        DealStage.objects.create(deal=self.deal, title="Этап", order=0)
        self.assertEqual(self._c(self.other).get(f"/api/deals/{self.deal.id}/stages/").status_code, 403)

    def test_manager_toggles_and_reorders(self):
        s1 = DealStage.objects.create(deal=self.deal, title="A", order=0)
        s2 = DealStage.objects.create(deal=self.deal, title="B", order=1)
        # отметить готовым
        r = self._c(self.manager).patch(f"/api/manager/stages/{s1.id}/", {"is_done": True}, format="json")
        self.assertEqual(r.status_code, 200)
        s1.refresh_from_db(); self.assertTrue(s1.is_done)
        # поменять порядок (swap)
        self._c(self.manager).patch(f"/api/manager/stages/{s1.id}/", {"order": 1}, format="json")
        self._c(self.manager).patch(f"/api/manager/stages/{s2.id}/", {"order": 0}, format="json")
        s1.refresh_from_db(); s2.refresh_from_db()
        self.assertEqual(s1.order, 1); self.assertEqual(s2.order, 0)

    def test_manager_deletes_stage(self):
        s = DealStage.objects.create(deal=self.deal, title="X", order=0)
        r = self._c(self.manager).delete(f"/api/manager/stages/{s.id}/")
        self.assertEqual(r.status_code, 204)
        self.assertEqual(DealStage.objects.count(), 0)

    def test_customer_cannot_modify_stage(self):
        s = DealStage.objects.create(deal=self.deal, title="X", order=0)
        self.assertEqual(self._c(self.customer).patch(f"/api/manager/stages/{s.id}/", {"is_done": True}, format="json").status_code, 403)
        self.assertEqual(self._c(self.customer).delete(f"/api/manager/stages/{s.id}/").status_code, 403)


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
