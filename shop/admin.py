from django.contrib import admin
from .models import Category, Product, ProductImage, Order, OrderItem, OrderNotification

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price', 'colors', 'sizes', 'stock', 'is_active', 'created', 'updated']
    list_filter = ['is_active', 'created', 'updated', 'category']
    list_editable = ['price', 'stock', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    readonly_fields = ['selected_color', 'selected_size']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email',
                    'address', 'city', 'paid', 'created', 'updated']
    list_filter = ['paid', 'created', 'updated']
    inlines = [OrderItemInline]


@admin.register(OrderNotification)
class OrderNotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'recipient', 'provider', 'status', 'short_error', 'created']
    list_filter = ['status', 'provider', 'created']
    search_fields = ['recipient', 'order__id']

    def short_error(self, obj):
        if not obj.error_message:
            return "-"
        message = obj.error_message.strip().replace("\n", " ")
        return (message[:90] + "...") if len(message) > 90 else message

    short_error.short_description = "Erreur SMTP"
