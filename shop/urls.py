from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<str:item_key>/', views.cart_remove, name='cart_remove'),
    path('cart/increment/<str:item_key>/', views.cart_item_increment, name='cart_item_increment'),
    path('cart/decrement/<str:item_key>/', views.cart_item_decrement, name='cart_item_decrement'),
    path('order/create/', views.order_create, name='order_create'),
    path('order/<int:order_id>/payer/', views.payment_checkout, name='payment_checkout'),
    path('order/<int:order_id>/retour/', views.payment_return, name='payment_return'),
    path('paiement/webhook/camerpay/', views.camerpay_webhook, name='camerpay_webhook'),
    path('search/ajax/', views.ajax_search, name='ajax_search'),
    path('<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),
]
