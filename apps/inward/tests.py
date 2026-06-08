from django.test import TestCase, Client
from django.urls import reverse
from apps.inward.models import Inward, InwardItem
from datetime import date

class InwardModelTest(TestCase):
    def test_inward_creation(self):
        inward = Inward.objects.create(
            sr_no=1,
            challan_no="CH-001",
            date=date.today(),
            delivery_party="Party A",
            buyer_party="Buyer A",
            article_no="ART-101"
        )
        InwardItem.objects.create(inward=inward, roll_no="R-001", color="Blue", meters=100.00)
        
        self.assertEqual(inward.sr_no, 1)
        self.assertEqual(inward.items.count(), 1)
        self.assertEqual(str(inward), "Inward 1 - CH-001")

class InwardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')
        
        self.inward = Inward.objects.create(
            sr_no=1,
            challan_no="CH-001",
            date=date.today(),
            delivery_party="Party A",
            buyer_party="Buyer A",
            article_no="ART-101"
        )
        InwardItem.objects.create(inward=self.inward, roll_no="R-001", color="Blue", meters=100.00)

    def test_inward_list_view(self):
        response = self.client.get(reverse('inward:inward_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CH-001")

    def test_inward_create_view(self):
        data = {
            'sr_no': 2,
            'challan_no': 'CH-002',
            'date': date.today(),
            'delivery_party': 'Party B',
            'buyer_party': 'Buyer B',
            'article_no': 'ART-102',
            'roll_no[]': ['R-002'],
            'color[]': ['Red'],
            'meters[]': ['150.00']
        }
        response = self.client.post(reverse('inward:inward_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Inward.objects.filter(sr_no=2).exists())
        self.assertTrue(InwardItem.objects.filter(inward__sr_no=2).exists())

    def test_inward_update_view(self):
        data = {
            'sr_no': 1,
            'challan_no': 'CH-001-UPDATED',
            'date': date.today(),
            'delivery_party': 'Party A',
            'buyer_party': 'Buyer A',
            'article_no': 'ART-101',
            'roll_no[]': ['R-001-UP'],
            'color[]': ['Green'],
            'meters[]': ['110.00']
        }
        response = self.client.post(reverse('inward:inward_update', kwargs={'pk': self.inward.pk}), data)
        self.assertEqual(response.status_code, 302)
        self.inward.refresh_from_db()
        self.assertEqual(self.inward.challan_no, 'CH-001-UPDATED')
        self.assertEqual(self.inward.items.first().roll_no, 'R-001-UP')

    def test_inward_delete_view(self):
        response = self.client.post(reverse('inward:inward_delete', kwargs={'pk': self.inward.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Inward.objects.filter(pk=self.inward.pk).exists())
