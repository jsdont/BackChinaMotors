from django.test import TestCase
from rest_framework.test import APIClient

from core.models import User, Deal
from .models import CalculatorLead


class ConvertLeadToDealTest(TestCase):
    """Менеджер конвертирует заявку в сделку; клиент создаётся по телефону;
    повторная конвертация запрещена; доступ только менеджеру."""

    def setUp(self):
        self.manager = User.objects.create_user(
            phone="+77000002001", password="pass12345", role="MANAGER"
        )
        self.customer = User.objects.create_user(
            phone="+77000002002", password="pass12345", role="CUSTOMER_PERSON"
        )
        self.lead_new_phone = CalculatorLead.objects.create(
            calc_id="CM-NEW-1", source="contacts", name="Асхат",
            phone="+77000009999", message="Нужен самосвал", status="new",
        )
        self.lead_existing_phone = CalculatorLead.objects.create(
            calc_id="CM-EXIST-1", source="calculator", name="Существующий",
            phone="+77000002002", message="Расчёт", status="new",
        )
        self.lead_no_phone = CalculatorLead.objects.create(
            calc_id="CM-NOPHONE-1", source="calculator", name="Без телефона",
            phone="", message="Расчёт", status="new",
        )

    def _mgr(self):
        c = APIClient()
        c.force_authenticate(user=self.manager)
        return c

    def test_convert_creates_deal_and_customer(self):
        res = self._mgr().post(f"/api/manager/leads/{self.lead_new_phone.id}/convert/")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(res.data["created_customer"])
        deal = Deal.objects.get(id=res.data["deal_id"])
        self.assertEqual(deal.customer.phone, "+77000009999")
        self.assertEqual(deal.customer.role, "CUSTOMER_PERSON")
        self.assertEqual(deal.customer.client_profile.full_name, "Асхат")
        self.lead_new_phone.refresh_from_db()
        self.assertEqual(self.lead_new_phone.converted_deal_id, deal.id)
        self.assertEqual(self.lead_new_phone.status, "in_progress")

    def test_convert_reuses_existing_customer(self):
        res = self._mgr().post(f"/api/manager/leads/{self.lead_existing_phone.id}/convert/")
        self.assertEqual(res.status_code, 201)
        self.assertFalse(res.data["created_customer"])
        deal = Deal.objects.get(id=res.data["deal_id"])
        self.assertEqual(deal.customer_id, self.customer.id)

    def test_double_convert_rejected(self):
        first = self._mgr().post(f"/api/manager/leads/{self.lead_new_phone.id}/convert/")
        self.assertEqual(first.status_code, 201)
        second = self._mgr().post(f"/api/manager/leads/{self.lead_new_phone.id}/convert/")
        self.assertEqual(second.status_code, 400)
        self.assertEqual(second.data["deal_id"], first.data["deal_id"])
        self.assertEqual(Deal.objects.count(), 1)

    def test_convert_without_phone_rejected(self):
        res = self._mgr().post(f"/api/manager/leads/{self.lead_no_phone.id}/convert/")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Deal.objects.count(), 0)

    def test_non_manager_cannot_convert(self):
        c = APIClient()
        c.force_authenticate(user=self.customer)
        res = c.post(f"/api/manager/leads/{self.lead_new_phone.id}/convert/")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(Deal.objects.count(), 0)


class LeadBreakdownFlowTest(TestCase):
    """Расчёт калькулятора: приходит с заявкой (contacts) -> переносится в
    сделку при конвертации."""

    def setUp(self):
        self.manager = User.objects.create_user(
            phone="+77000003001", password="pass12345", role="MANAGER"
        )
        self.breakdown = {
            "currency": {"usd_kzt": 493.11},
            "groups": [
                {"title": "Таможенная стоимость и платежи",
                 "rows": [["ТС в тенге", 29156149], ["НДС", 5135634]]},
            ],
            "total": 42977255,
        }

    def _mgr(self):
        c = APIClient()
        c.force_authenticate(user=self.manager)
        return c

    def test_contacts_form_stores_breakdown(self):
        c = APIClient()
        res = c.post(
            "/api/contacts/",
            {"name": "Клиент", "phone": "+77000008888",
             "message": "Расчёт CM-BD-1", "calc_breakdown": self.breakdown},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        lead = CalculatorLead.objects.get(phone="+77000008888")
        self.assertEqual(lead.calc_breakdown["total"], 42977255)

    def test_convert_copies_breakdown_to_deal(self):
        lead = CalculatorLead.objects.create(
            calc_id="CM-BD-2", source="calculator", name="Клиент",
            phone="+77000007777", message="Расчёт", status="new",
            calc_breakdown=self.breakdown,
        )
        res = self._mgr().post(f"/api/manager/leads/{lead.id}/convert/")
        self.assertIn(res.status_code, (200, 201))
        deal = Deal.objects.get(pk=res.data["deal_id"])
        self.assertIsNotNone(deal.calc_breakdown)
        self.assertEqual(deal.calc_breakdown["total"], 42977255)

    def test_kp_renders_with_breakdown(self):
        from core.kp import build_kp_pdf
        customer = User.objects.create_user(
            phone="+77000006666", password="pass12345",
            role="CUSTOMER_PERSON", email="c@e.com",
        )
        deal = Deal.objects.create(customer=customer, calc_breakdown=self.breakdown)
        pdf = build_kp_pdf(deal)
        self.assertTrue(pdf.startswith(b"%PDF"))
