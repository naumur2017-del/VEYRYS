from django.conf import settings

from .cart import Cart


def cart(request):
    return {'cart': Cart(request)}


def seo(request):
    return {
        'site_url': settings.SITE_URL,
        'current_absolute_url': request.build_absolute_uri(),
    }
