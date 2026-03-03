from decimal import Decimal

from django.conf import settings

from .models import Product


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def _normalize_option(self, value):
        return ''.join(ch for ch in str(value).strip().lower() if ch.isalnum())

    def _build_item_key(self, product_id, selected_color, selected_size):
        color_key = self._normalize_option(selected_color)
        size_key = self._normalize_option(selected_size)
        return f'{product_id}:{color_key}:{size_key}'

    def add(self, product, quantity=1, selected_color='Noir', selected_size='M', override_quantity=False):
        item_key = self._build_item_key(product.id, selected_color, selected_size)
        was_in_cart = item_key in self.cart
        if not was_in_cart:
            self.cart[item_key] = {
                'product_id': product.id,
                'quantity': 0,
                'price': str(product.price),
                'selected_color': selected_color,
                'selected_size': selected_size,
            }

        if override_quantity:
            self.cart[item_key]['quantity'] = quantity
        else:
            self.cart[item_key]['quantity'] += quantity

        self.save()
        return not was_in_cart

    def save(self):
        self.session.modified = True

    def remove(self, item_key):
        if item_key in self.cart:
            del self.cart[item_key]
            self.save()

    def __iter__(self):
        product_ids = []
        cart_changed = False
        for item_key, item in self.cart.items():
            product_id = item.get('product_id')
            if not product_id:
                product_id = item_key.split(':')[0]
                item['product_id'] = int(product_id)
                item.setdefault('selected_color', 'Noir')
                item.setdefault('selected_size', 'M')
                cart_changed = True
            product_ids.append(str(product_id))

        if cart_changed:
            self.save()

        products = Product.objects.filter(id__in=product_ids)
        products_map = {str(product.id): product for product in products}

        for item_key, item in self.cart.items():
            product = products_map.get(str(item.get('product_id')))
            if not product:
                continue

            item_data = item.copy()
            item_data['product'] = product
            item_data['price'] = Decimal(item_data['price'])
            item_data['total_price'] = item_data['price'] * item_data['quantity']
            item_data['item_key'] = item_key
            yield item_data

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        if settings.CART_SESSION_ID in self.session:
            del self.session[settings.CART_SESSION_ID]
            self.save()
