import pandas as pd
from collections import defaultdict

class DataManager:
    def __init__(self):
        self.categories = defaultdict(dict)
        self.products = defaultdict(dict)
        self.csv_files = {
            'books': 'BOOKS.csv',
            'electronics': 'ELECTRONICS.csv',
            'clothing': 'CLOTHES.csv',
            'beauty': 'BEAUTY.csv',
            'toys': 'TOYS.csv',
            'books': 'BOOKS.csv',
            'kitchen': 'KITCHEN.csv',
            'baby': 'BABY.csv',
            'computer': 'COMPUTER.csv',
            'health': 'HEALTH.csv',
            'jwellery': 'JWELLERY.csv',
            'movies': 'MOVIES.csv',
            # Add other CSV files here
        }
        self.ITEMS_PER_PAGE = 5
        self.load_data()

    def load_data(self):
        """Load and organize data from all CSV files"""
        for file_key, file_path in self.csv_files.items():
            df = pd.read_csv(file_path)
            
            # Filter out rows where price or discount is N/A
            df = df[
                (df['price'].notna()) & 
                (df['price'] != 'N/A') & 
                (df['discount'].notna()) & 
                (df['discount'] != 'N/A')
            ]
            
            # Convert discount to numeric, removing '%' and handling NaN
            df['discount_value'] = pd.to_numeric(df['discount'].str.rstrip('%'), errors='coerce')
            
            # Get unique categories at each level
            categories = df['category'].unique()
            category_level1 = df['category'].unique()
            category_level2 = df[df['category_level'] == 1]['category'].unique()
            category_level3 = df[df['category_level'] == 2]['parent_category'].unique()

            self.categories[file_key] = {
                'level1': list(category_level1),
                'level2': list(category_level2),
                'level3': list(category_level3)
            }

            # Organize products by category
            for category in categories:
                products = df[df['category'] == category].to_dict('records')
                if products:  # Only add categories that have products
                    self.products[file_key][category] = products

    def get_main_categories(self, file_key):
        """Get top-level categories for a file"""
        return self.categories[file_key]['level1']

    def get_subcategories(self, file_key, parent_category):
        """Get subcategories for a parent category that have valid products"""
        products = self.products[file_key]
        return [cat for cat in products.keys() 
                if cat.startswith(parent_category + ' > ') and products[cat]]

    def get_products(self, file_key, category, limit=5):
        """Get products for a category with optional limit"""
        if category in self.products[file_key]:
            products = self.products[file_key][category]
            
            # Sort by discount before limiting
            def get_discount_value(product):
                discount = product.get('discount', 'N/A')
                if discount != 'N/A':
                    try:
                        return float(str(discount).rstrip('%'))
                    except (ValueError, TypeError):
                        return -1
                return -1
            
            products = sorted(products, 
                           key=get_discount_value,
                           reverse=True)
            
            return products[:limit]
        return []

    def format_product(self, product):
        """Format a product for display"""
        name = product['name']
        price = product['price']
        mrp = product.get('mrp', 'N/A')
        discount = product.get('discount', 'N/A')
        link = product['affiliate_link']
        image_url = product.get('image', '')

        message = f"[⁣]({image_url})\n"
        message += f"📦 *{name}*\n\n"
        message += f"💰 *Price:* ₹{price}\n"
        if mrp and mrp != 'N/A':
            message += f"📌 *MRP:* ₹{mrp}\n"
        if discount and discount != 'N/A':
            message += f"🏷️ *Discount:* {discount}\n"
        return {
            'text': message,
            'link': link
        }
