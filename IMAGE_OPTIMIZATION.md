# Optimisation des images produit

Les nouvelles images produit sont automatiquement converties en WebP lors de
leur enregistrement : longueur maximale de 1 600 px et qualité WebP de 82.
L'original est supprimé uniquement après la création du fichier optimisé.

Les réglages peuvent être ajustés dans `veyrys_shop/settings.py` :

```python
PRODUCT_IMAGE_MAX_DIMENSION = 1600
PRODUCT_IMAGE_WEBP_QUALITY = 82
```

Pour convertir les images déjà associées aux produits :

```powershell
python manage.py optimize_product_images --dry-run
python manage.py optimize_product_images
python manage.py optimize_product_images --delete-orphans
```

La première commande ne modifie rien. La seconde remplace les PNG et JPEG
référencés en base par leur version WebP. Les AVIF et WebP déjà présents sont
conservés, car ils sont déjà des formats compacts. L'option `--delete-orphans`
supprime les fichiers dans `media/products` qui ne sont plus référencés en base.
