from decimal import Decimal

from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

from .models import Category, Product
from .cart import Cart


def make_request_with_session():
    rf = RequestFactory()
    request = rf.get('/')
    middleware = SessionMiddleware(get_response=lambda req: None)
    middleware.process_request(request)
    request.session.save()
    return request


class CartTests(TestCase):
	def setUp(self):
		self.request = make_request_with_session()
		self.category = Category.objects.create(name='TestCat')
		self.product = Product.objects.create(
			category=self.category, name='Test product', price=Decimal('10.00')
		)
		self.cart = Cart(self.request)

	def test_add_new_item_returns_true_and_stores_quantity(self):
		added = self.cart.add(self.product, quantity=2)
		self.assertTrue(added)
		item_key = next(iter(self.cart.cart))
		self.assertEqual(self.cart.cart[item_key]['quantity'], 2)

	def test_add_existing_item_returns_false_and_increments(self):
		self.cart.add(self.product, quantity=1)
		added = self.cart.add(self.product, quantity=3)
		self.assertFalse(added)
		item_key = next(iter(self.cart.cart))
		self.assertEqual(self.cart.cart[item_key]['quantity'], 4)

	def test_override_quantity(self):
		self.cart.add(self.product, quantity=1)
		self.cart.add(self.product, quantity=5, override_quantity=True)
		item_key = next(iter(self.cart.cart))
		self.assertEqual(self.cart.cart[item_key]['quantity'], 5)

	def test_remove(self):
		self.cart.add(self.product, quantity=1)
		item_key = next(iter(self.cart.cart))
		self.cart.remove(item_key)
		self.assertEqual(len(self.cart.cart), 0)

	def test_len_and_total_price(self):
		self.cart.add(self.product, quantity=2)
		p2 = Product.objects.create(category=self.category, name='Other', price=Decimal('5.50'))
		self.cart.add(p2, quantity=3)
		self.assertEqual(len(self.cart), 5)
		expected = Decimal('10.00') * 2 + Decimal('5.50') * 3
		self.assertEqual(self.cart.get_total_price(), expected)

	def test_iter_yields_products_and_total_price(self):
		self.cart.add(self.product, quantity=2)
		items = list(self.cart)
		self.assertEqual(len(items), 1)
		item = items[0]
		self.assertIn('product', item)
		self.assertEqual(item['total_price'], Decimal('20.00'))
		self.assertIn('item_key', item)

	def test_iter_handles_legacy_item_without_product_id(self):
		item_key = f'{self.product.id}:noir:m'
		# simulate legacy item missing product_id
		self.cart.cart[item_key] = {
			'quantity': 1,
			'price': str(self.product.price),
			'selected_color': 'Noir',
			'selected_size': 'M',
		}
		# ensure product_id not present
		self.assertNotIn('product_id', self.cart.cart[item_key])
		items = list(self.cart)
		self.assertEqual(len(items), 1)
		# after iteration, product_id should be set to integer id
		self.assertEqual(self.cart.cart[item_key]['product_id'], self.product.id)

	def test_clear(self):
		self.cart.add(self.product, quantity=1)
		self.cart.clear()
		self.assertNotIn('cart', self.request.session)
