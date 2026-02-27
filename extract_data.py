import pandas as pd
import os
import json

def extract_data():
    excel_path = r"c:\Users\hp\Documents\VERYS\Business Central 1.xlsx"
    image_dir = r"c:\Users\hp\Documents\VERYS\IMAGE PRODUITS"
    
    # Read Excel
    df = pd.read_excel(excel_path)
    
    # List images
    products_images = {}
    for root, dirs, files in os.walk(image_dir):
        images = [os.path.join(root, f) for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.avif'))]
        if images:
            # We want to store images indexed by folder names (including parents)
            rel_path = os.path.relpath(root, image_dir)
            parts = rel_path.split(os.sep)
            for part in parts:
                if part not in products_images:
                    products_images[part] = []
                products_images[part].extend(images)
    
    # Combine data
    # ... (Rest of the function)
    # Let's see what's in the Excel first
    print("Excel Columns:", df.columns.tolist())
    print("First 5 rows:\n", df.head())
    
    # Save to json for later import
    data = {
        "excel_data": df.to_dict(orient='records'),
        "product_images": products_images
    }
    
    with open('product_info.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    extract_data()
