from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from .models import Category, Product, OrderItem
from .cart import Cart
from .forms import CartAddProductForm, OrderCreateForm
from django.core.cache import cache
import urllib.parse

def product_list(request, category_slug=None):
    # Determine the cache key
    cache_key = f'products_{category_slug or "all"}'
    
    # If a 'refresh' flag is passed, clear the cache for this view
    # If a 'refresh' flag is passed, clear relevant cache keys
    if request.GET.get('refresh'):
        cache.delete('products_all')
        for cat in Category.objects.all():
            cache.delete(f'products_{cat.slug}')

    context = cache.get(cache_key)
    
    if not context:
        from django.db.models import Count
        # Only show categories that have active products
        categories = list(Category.objects.annotate(p_count=Count('products')).filter(p_count__gt=0))
        
        products_qs = Product.objects.filter(is_active=True)
        category = None
        
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            products_qs = products_qs.filter(category=category)
            
        products = list(products_qs.prefetch_related('images'))
        
        context = {
            'category': category,
            'categories': categories,
            'products': products
        }
        cache.set(cache_key, context, 3600)

    return render(request, 'shop/product/list.html', context)

def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, is_active=True)
    cart_product_form = CartAddProductForm()
    return render(request, 'shop/product/detail.html', {
        'product': product,
        'cart_product_form': cart_product_form
    })

from django.http import JsonResponse

@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        was_new = cart.add(product=product, quantity=cd['quantity'], override_quantity=cd['override'])
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
        return JsonResponse({
            'status': 'success',
            'product_name': product.name,
            'cart_count': len(cart),
            'was_new': was_new
        })
        
    return redirect('shop:cart_detail')

@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('shop:cart_detail')

def cart_detail(request):
    cart = Cart(request)
    for item in cart:
        item['update_quantity_form'] = CartAddProductForm(initial={
            'quantity': item['quantity'],
            'override': True
        })
    return render(request, 'shop/cart/detail.html', {'cart': cart})

def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save()
            for item in cart:
                OrderItem.objects.create(order=order,
                                        product=item['product'],
                                        price=item['price'],
                                        quantity=item['quantity'])
            # Prepare WhatsApp message
            message = f"👔 *NOUVELLE COMMANDE VEYRYS*\n\n"
            message += f"👤 *Client :* {order.first_name} {order.last_name}\n"
            message += f"📍 *Lieu :* {order.city}, {order.address}\n"
            message += f"📱 *Contact :* {order.phone}\n\n"
            
            message += "📦 *DÉTAILS DE LA COMMANDE :*\n"
            for item in order.items.all():
                message += f"▪️ {item.quantity}x {item.product.name} — {item.get_cost():,.0f} FCFA\n"
            
            message += f"\n💰 *TOTAL À PAYER : {order.get_total_cost():,.0f} FCFA*\n\n"
            message += "✨ _Merci pour votre confiance chez VEYRYS — Le Sublime Raisonnable._"
            
            whatsapp_url = f"https://wa.me/237656916923?text={urllib.parse.quote(message)}"
            
            # clear the cart
            cart.clear()
            return render(request, 'shop/order/created.html', {
                'order': order,
                'whatsapp_url': whatsapp_url
            })
    else:
        form = OrderCreateForm()
    return render(request, 'shop/order/create.html', {'cart': cart, 'form': form})
