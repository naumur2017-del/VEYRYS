from django.db import models
from django.utils.text import slugify


DEFAULT_COLORS = "Noir, Vert"
DEFAULT_CLOTHING_SIZES = "XS, S, M, L, XL, 2XL, 3XL, 4XL"
DEFAULT_BELT_SIZES = "10, 20, 30, 40, 50"
DEFAULT_UNIQUE_SIZE = "Unique"


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    colors = models.CharField(max_length=255, default=DEFAULT_COLORS, help_text="List of colors separated by comma")
    sizes = models.CharField(max_length=255, default=DEFAULT_CLOTHING_SIZES, help_text="List of sizes separated by comma")
    stock = models.PositiveIntegerField(default=10)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.colors:
            self.colors = DEFAULT_COLORS
        if not self.sizes:
            self.sizes = self.get_default_sizes()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_default_sizes(self):
        category_slug = (self.category.slug or "").lower()
        product_name = (self.name or "").lower()
        if "ceinture" in product_name or "belt" in product_name:
            return DEFAULT_BELT_SIZES
        if category_slug in {"chemises", "pantalons", "costumes", "nuit"}:
            return DEFAULT_CLOTHING_SIZES
        if category_slug in {"montres", "accessoires", "maroquinerie"}:
            return DEFAULT_UNIQUE_SIZE
        return DEFAULT_CLOTHING_SIZES

    def get_color_options(self):
        return [value.strip() for value in (self.colors or "").split(",") if value.strip()]

    def get_size_options(self):
        return [value.strip() for value in (self.sizes or "").split(",") if value.strip()]

    @property
    def is_belt_product(self):
        product_name = (self.name or "").lower()
        return "ceinture" in product_name or "belt" in product_name

    @property
    def has_single_size(self):
        return len(self.get_size_options()) == 1

    @property
    def size_label(self):
        if self.is_belt_product:
            return "Tour de ceinture (cm)"
        return "Taille"

    @property
    def first_size_option(self):
        options = self.get_size_options()
        return options[0] if options else ""

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/%Y/%m/%d/')
    alt_text = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Image for {self.product.name}"

class Order(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=250)
    city = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return f'Order {self.id}'

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    selected_color = models.CharField(max_length=50, default='Noir')
    selected_size = models.CharField(max_length=50, default='M')

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity


class OrderNotification(models.Model):
    order = models.ForeignKey(Order, related_name='notifications', on_delete=models.CASCADE)
    recipient = models.CharField(max_length=254)
    provider = models.CharField(max_length=50, default='email_smtp')
    status = models.CharField(max_length=20)
    message_preview = models.TextField()
    response_body = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return f'Notification {self.id} ({self.status}) for order {self.order_id}'
