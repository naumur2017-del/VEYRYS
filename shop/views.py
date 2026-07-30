from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_page

from .cart import Cart
from .forms import CartAddProductForm, OrderCreateForm
from .models import Category, OrderItem, Product
from .notifications import notify_admin_of_order, notify_customer_of_order

ORDER_FORM_SESSION_KEY = 'order_form_data'


def _get_order_form_initial_data(request):
    initial_data = {}
    saved_data = request.session.get(ORDER_FORM_SESSION_KEY, {})
    if isinstance(saved_data, dict):
        initial_data.update(saved_data)

    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        user_defaults = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        }
        for field_name, value in user_defaults.items():
            if value and not initial_data.get(field_name):
                initial_data[field_name] = value

    return initial_data


def _attach_list_add_forms(products):
    for product in products:
        product.cart_form = CartAddProductForm(
            product=product,
            initial={'quantity': 1, 'override': False},
        )


def product_list(request, category_slug=None):
    cache_key = f'products_{category_slug or "all"}'

    if request.GET.get('refresh'):
        cache.delete('products_all')
        for cat in Category.objects.all():
            cache.delete(f'products_{cat.slug}')

    context = cache.get(cache_key)

    if not context:
        from django.db.models import Count

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
            'products': products,
        }
        cache.set(cache_key, context, 3600)

    context = dict(context)
    _attach_list_add_forms(context['products'])

    return render(request, 'shop/product/list.html', context)


def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, is_active=True)
    cart_product_form = CartAddProductForm(
        product=product,
        initial={'quantity': 1, 'override': False},
    )
    return render(
        request,
        'shop/product/detail.html',
        {
            'product': product,
            'cart_product_form': cart_product_form,
        },
    )


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    is_update_mode = str(request.POST.get('override', '')).lower() in {'1', 'true', 'on'}
    was_new = False

    if is_update_mode:
        # Be permissive for cart quantity updates to avoid blocking users when
        # product options have changed after an item was already added.
        selected_color = request.POST.get('selected_color') or (
            product.get_color_options()[0] if product.get_color_options() else 'Noir'
        )
        selected_size = request.POST.get('selected_size') or (
            product.get_size_options()[0] if product.get_size_options() else 'M'
        )
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 1
        quantity = max(1, min(20, quantity))

        step = request.POST.get('step')
        if step in {'-1', '1'}:
            quantity = max(1, min(20, quantity + int(step)))

        was_new = cart.add(
            product=product,
            quantity=quantity,
            selected_color=selected_color,
            selected_size=selected_size,
            override_quantity=True,
        )

        item_key = cart._build_item_key(product.id, selected_color, selected_size)
        cart_item = cart.cart.get(item_key)
        item_quantity = cart_item['quantity'] if cart_item else quantity
        item_total_price = None
        for item in cart:
            if item.get('item_key') == item_key:
                item_total_price = item['total_price']
                break
        if item_total_price is None:
            item_total_price = product.price * item_quantity

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
            return JsonResponse(
                {
                    'status': 'success',
                    'product_name': product.name,
                    'cart_count': len(cart),
                    'was_new': was_new,
                    'item_key': item_key,
                    'item_quantity': item_quantity,
                    'item_total_price': f'{item_total_price:,.0f}',
                    'cart_total_price': f'{cart.get_total_price():,.0f}',
                }
            )
        return redirect('shop:cart_detail')

    # Process form submission robustly, avoiding strict ChoiceField validation failures
    selected_color = request.POST.get('selected_color')
    if not selected_color:
        color_opts = product.get_color_options()
        selected_color = color_opts[0] if color_opts else 'Noir'
        
    selected_size = request.POST.get('selected_size')
    if not selected_size:
        size_opts = product.get_size_options()
        selected_size = size_opts[0] if size_opts else 'M'
        
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1
    quantity = max(1, min(20, quantity))

    was_new = cart.add(
        product=product,
        quantity=quantity,
        selected_color=selected_color,
        selected_size=selected_size,
        override_quantity=False,
    )

    item_key = cart._build_item_key(product.id, selected_color, selected_size)
    cart_item = cart.cart.get(item_key)
    item_quantity = cart_item['quantity'] if cart_item else quantity
    item_total_price = None
    for item in cart:
        if item.get('item_key') == item_key:
            item_total_price = item['total_price']
            break
    if item_total_price is None:
        item_total_price = product.price * item_quantity

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
        return JsonResponse(
            {
                'status': 'success',
                'product_name': product.name,
                'cart_count': len(cart),
                'was_new': was_new,
                'item_key': item_key,
                'item_quantity': item_quantity,
                'item_total_price': f'{item_total_price:,.0f}',
                'cart_total_price': f'{cart.get_total_price():,.0f}',
            }
        )
        
    return redirect('shop:cart_detail')


@require_POST
def cart_remove(request, item_key):
    cart = Cart(request)
    cart.remove(item_key)
    return redirect('shop:cart_detail')


@require_POST
def cart_item_increment(request, item_key):
    cart = Cart(request)
    cart_item = cart.cart.get(item_key)
    if not cart_item:
        return redirect('shop:cart_detail')

    product = get_object_or_404(Product, id=cart_item['product_id'])
    current_qty = int(cart_item.get('quantity', 1))
    new_qty = min(20, current_qty + 1)
    cart.add(
        product=product,
        quantity=new_qty,
        selected_color=cart_item.get('selected_color', 'Noir'),
        selected_size=cart_item.get('selected_size', 'M'),
        override_quantity=True,
    )
    return redirect('shop:cart_detail')


@require_POST
def cart_item_decrement(request, item_key):
    cart = Cart(request)
    cart_item = cart.cart.get(item_key)
    if not cart_item:
        return redirect('shop:cart_detail')

    product = get_object_or_404(Product, id=cart_item['product_id'])
    current_qty = int(cart_item.get('quantity', 1))
    new_qty = max(1, current_qty - 1)
    cart.add(
        product=product,
        quantity=new_qty,
        selected_color=cart_item.get('selected_color', 'Noir'),
        selected_size=cart_item.get('selected_size', 'M'),
        override_quantity=True,
    )
    return redirect('shop:cart_detail')


def cart_detail(request):
    cart = Cart(request)
    for item in cart:
        item['update_quantity_form'] = CartAddProductForm(
            product=item['product'],
            variant_hidden=True,
            initial={
                'quantity': item['quantity'],
                'override': True,
                'selected_color': item['selected_color'],
                'selected_size': item['selected_size'],
            },
        )
    return render(request, 'shop/cart/detail.html', {'cart': cart})


def order_create(request):
    cart = Cart(request)

    if len(cart) < 1:
        return redirect('shop:cart_detail')

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = form.save()
                for item in cart:
                    OrderItem.objects.create(
                        order=order,
                        product=item['product'],
                        price=item['price'],
                        quantity=item['quantity'],
                        selected_color=item['selected_color'],
                        selected_size=item['selected_size'],
                    )

            admin_notification = notify_admin_of_order(order)
            customer_notification = notify_customer_of_order(order)
            request.session[ORDER_FORM_SESSION_KEY] = {
                'first_name': order.first_name,
                'last_name': order.last_name,
                'email': order.email,
                'phone': order.phone,
                'address': order.address,
                'city': order.city,
            }

            if customer_notification.status == 'sent':
                cart.clear()
                notification_title = 'Commande prise en compte'
                notification_message = (
                    'Votre commande a ete notifiee a notre equipe pour traitement '
                    'et une confirmation vous a ete envoyee par email.'
                )
            else:
                notification_title = 'Commande enregistree'
                notification_message = (
                    'Votre commande est enregistree. La confirmation email est en cours '
                    'de finalisation; votre panier est conserve en attendant.'
                )

            return render(
                request,
                'shop/order/created.html',
                {
                    'order': order,
                    'notification_title': notification_title,
                    'notification_message': notification_message,
                },
            )
    else:
        form = OrderCreateForm(initial=_get_order_form_initial_data(request))

    return render(request, 'shop/order/create.html', {'cart': cart, 'form': form})


@cache_page(60 * 60)
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /cart/",
        "Disallow: /order/",
        f"Sitemap: {settings.SITE_URL}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


@cache_page(60 * 60)
def sitemap_xml(request):
    base_url = settings.SITE_URL
    urls = [
        {
            "loc": f"{base_url}/",
            "priority": "1.0",
            "changefreq": "daily",
        }
    ]

    for category in Category.objects.all():
        urls.append(
            {
                "loc": f"{base_url}/{category.slug}/",
                "priority": "0.8",
                "changefreq": "weekly",
            }
        )

    products = Product.objects.filter(is_active=True).only("id", "slug", "updated")
    for product in products:
        urls.append(
            {
                "loc": f"{base_url}/{product.id}/{product.slug}/",
                "lastmod": product.updated.date().isoformat(),
                "priority": "0.9",
                "changefreq": "weekly",
            }
        )

    return render(
        request,
        "shop/sitemap.xml",
        {"urls": urls},
        content_type="application/xml",
    )


def ajax_search(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})
    
    # Filter products that are active and match query
    products = Product.objects.filter(name__icontains=query, is_active=True).prefetch_related('images')[:5]
    
    results = []
    from django.urls import reverse
    for p in products:
        image_url = ''
        first_img = p.images.first()
        if first_img and first_img.image:
            image_url = first_img.image.url
            
        results.append({
            'name': p.name,
            'url': reverse('shop:product_detail', args=[p.id, p.slug]),
            'price': str(p.price),
            'image_url': image_url,
            'category': p.category.name if p.category else ''
        })
        
    return JsonResponse({'results': results})
