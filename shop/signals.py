from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Product, Category

@receiver([post_save, post_delete], sender=Product)
@receiver([post_save, post_delete], sender=Category)
def invalidate_product_cache(sender, instance, **kwargs):
    """
    Vider le cache des produits lorsque la base de données change.
    On supprime le cache global et le cache par catégorie.
    """
    cache.delete('products_all')
    
    if sender == Product:
        cache.delete(f'product_{instance.id}_{instance.slug}')
    
    # Pour s'assurer de bien invalider, on parcourt toutes les catégories
    for cat in Category.objects.all():
        cache.delete(f'products_{cat.slug}')
