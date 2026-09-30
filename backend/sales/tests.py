from django.test import TestCase, Client
from .models import Product, Order


class BuyProductTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(
            name="Test Item",
            price=100,
            stock=1
        )

    def test_successful_purchase_decrements_stock(self):
        """Buying an available product should succeed and reduce stock by 1."""
        response = self.client.post(f'/api/buy/{self.product.id}/')
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['remaining_stock'], 0)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)

    def test_purchase_fails_when_out_of_stock(self):
        """Buying a product with 0 stock should fail with 'Sold out'."""
        self.product.stock = 0
        self.product.save()

        response = self.client.post(f'/api/buy/{self.product.id}/')
        data = response.json()

        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'Sold out')

    def test_stock_never_goes_negative(self):
        """Multiple purchase attempts on 1 unit of stock should never result in negative stock."""
        for _ in range(5):
            self.client.post(f'/api/buy/{self.product.id}/')

        self.product.refresh_from_db()
        self.assertGreaterEqual(self.product.stock, 0)

    def test_only_one_order_succeeds_when_stock_is_one(self):
        """With only 1 unit in stock, exactly 1 order should succeed even across multiple attempts."""
        for _ in range(5):
            self.client.post(f'/api/buy/{self.product.id}/')

        successful_orders = Order.objects.filter(
            product=self.product, status='success'
        ).count()
        self.assertEqual(successful_orders, 1)