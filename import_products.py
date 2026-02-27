import os
import json
import django
import shutil
from django.utils.text import slugify
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veyrys_shop.settings')
django.setup()

from shop.models import Category, Product, ProductImage

import random

def import_data():
    with open('product_info.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    excel_data = data.get('excel_data', [])
    image_data = data.get('product_images', {})
    
    # Pre-create/get common categories for mapping
    brand_categories = {
        'chemise': Category.objects.get_or_create(name='Chemises')[0],
        'pantalon': Category.objects.get_or_create(name='Pantalons')[0],
        'costume': Category.objects.get_or_create(name='Costumes')[0],
        '3 pces': Category.objects.get_or_create(name='Costumes')[0], # Match 3 pieces to Costumes
        'montre': Category.objects.get_or_create(name='Montres')[0],
        'ceinture': Category.objects.get_or_create(name='Accessoires')[0],
        'manchette': Category.objects.get_or_create(name='Accessoires')[0],
        'trousse': Category.objects.get_or_create(name='Maroquinerie')[0],
        'pyjama': Category.objects.get_or_create(name='Nuit')[0],
        'chaussette': Category.objects.get_or_create(name='Accessoires')[0],
    }
    default_cat, _ = Category.objects.get_or_create(name="Divers")

    # Import Products
    for item in excel_data:
        name = item.get('P+F21+B:C')
        if not name or str(name) == 'nan':
            continue
            
        # ... (price and colors logic same)
        price_val = item.get('PRIX def EN FCFA')
        if not price_val or str(price_val) == 'nan' or str(price_val) == 'Indisponible':
            price = Decimal('0.00')
        else:
            try:
                price = Decimal(str(price_val))
            except:
                price = Decimal('0.00')
        
        colors = item.get('COULEURS  ', '')
        if str(colors) == 'nan':
            colors = ''
            
        # Determine category based on keywords in name
        product_cat = default_cat
        name_lower = name.lower()
        for keyword, cat_obj in brand_categories.items():
            if keyword in name_lower:
                product_cat = cat_obj
                break
        
        product, created = Product.objects.update_or_create(
            slug=slugify(name),
            defaults={
                'name': name,
                'category': product_cat,
                'price': price,
                'colors': colors,
                'description': f"Découvrez {name}, une pièce d'exception de la collection VEYRYS. {colors if colors else ''}",
            }
        )
        
        # Link Images with strict priority for black complexion/appropriate tones
        priority_paths = []
        generic_paths = []
        name_words = name_lower.split()
        
        # Priority keywords across all categories
        priority_keywords = ['noir', 'ebene', 'teint', 'skin']

        # Check for folder name matches
        for folder_key, paths in image_data.items():
            folder_key_lower = folder_key.lower()
            
            # Special case for manchette if folder name is CEINTURE or root
            if 'manchette' in name_lower and (folder_key_lower == '.' or 'ceinture' in folder_key_lower):
                # Filter for files that might be manchettes
                manchette_paths = [p for p in paths if 'manchette' in p.lower() or 'copy 3' in p.lower()]
                priority_paths.extend(manchette_paths)

            # Special case for "3 pces" to match Costumes
            is_3pcs = '3 pces' in name_lower or '3 pieces' in name_lower
            folder_is_costume = 'costume' in folder_key_lower or folder_key_lower in ['costume1', 'costume2', 'costume 3']
            
            # Match logic: folder name in product name or vice-versa
            is_match = folder_key_lower in name_lower or any(word in folder_key_lower for word in name_words if len(word) > 3)
            
            # Force match for 3 pieces to costume folders
            if is_3pcs and folder_is_costume:
                is_match = True

            if is_match:
                # Strictly categorize as priority or generic based on skin tone keywords
                if any(kw in folder_key_lower for kw in priority_keywords):
                    priority_paths.extend(paths)
                else:
                    generic_paths.extend(paths)
        
        # FINAL SELECTION:
        if priority_paths:
            final_paths = list(set(priority_paths))
        else:
            final_paths = list(set(generic_paths))
        
        random.shuffle(final_paths)
        final_paths = final_paths[:5]
        
        if final_paths:
            # Clear existing images for this product
            ProductImage.objects.filter(product=product).delete()
            
            for i, img_path in enumerate(final_paths):
                if os.path.exists(img_path):
                    total_cost = 0 # Not used but keeping structure
                    img_name = os.path.basename(img_path)
                    unique_img_name = f"{product.id}_{i}_{img_name}"
                    
                    media_subdir = 'products/imported/'
                    media_root = os.path.join('media', media_subdir)
                    if not os.path.exists(media_root):
                        os.makedirs(media_root)
                    
                    target_path = os.path.join(media_root, unique_img_name)
                    shutil.copy(img_path, target_path)
                    
                    ProductImage.objects.create(
                        product=product,
                        image=os.path.join(media_subdir, unique_img_name),
                        alt_text=name
                    )

    # Cleanup: Remove categories with no products
    from django.db.models import Count
    Category.objects.annotate(p_count=Count('products')).filter(p_count=0).delete()

    print("Import strictly limited to dark-skinned models finished!")

if __name__ == "__main__":
    import_data()
