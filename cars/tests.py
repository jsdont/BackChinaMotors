from django.test import TestCase
from rest_framework.test import APIClient

from core.models import User
from .models import Vehicle


class PartnerListingsTest(TestCase):
    """Партнёр-продавец может размещать товары (объявления), они уходят на
    модерацию; сервисные аккаунты — не могут; каждый видит только свои."""

    def setUp(self):
        self.partner = User.objects.create_user(phone="+77000010001", password="p", role="PARTNER")
        self.partner2 = User.objects.create_user(phone="+77000010002", password="p", role="PARTNER")
        self.broker = User.objects.create_user(phone="+77000010003", password="p", role="SERVICE_BROKER")

    def _c(self, u):
        c = APIClient(); c.force_authenticate(user=u); return c

    def _payload(self, name):
        return {"brand": "HOWO", "model": name, "body_type": name}

    def test_partner_can_create_listing_pending_moderation(self):
        res = self._c(self.partner).post("/api/vehicles/my-listings/", self._payload("Самосвал"), format="json")
        self.assertEqual(res.status_code, 201, res.data)
        v = Vehicle.objects.get(id=res.data["id"])
        self.assertEqual(v.owner_id, self.partner.id)
        self.assertFalse(v.is_approved)

    def test_service_role_cannot_create_listing(self):
        res = self._c(self.broker).post("/api/vehicles/my-listings/", self._payload("X"), format="json")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(Vehicle.objects.count(), 0)

    def test_partner_sees_only_own_listings(self):
        Vehicle.objects.create(owner=self.partner, body_type="A")
        Vehicle.objects.create(owner=self.partner2, body_type="B")
        res = self._c(self.partner).get("/api/vehicles/my-listings/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["body_type"], "A")

    def test_partner_can_delete_own_listing(self):
        v = Vehicle.objects.create(owner=self.partner, body_type="A")
        res = self._c(self.partner).delete(f"/api/vehicles/my-listings/{v.id}/")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(Vehicle.objects.count(), 0)
