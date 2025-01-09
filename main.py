import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler

(BROWSING,) = range(1)

class ProductAnalyzer:
    def __init__(self, csv_paths):
        self.dfs = {}
        for path in csv_paths:
            df = pd.read_csv(path)
            if 'grandparent' not in df.columns:
                df['grandparent'] = df['category'].apply(lambda x: x.split('>')[0].strip())
            if 'parent' not in df.columns:
                df['parent'] = df['category'].apply(lambda x: x.split('>')[1].strip() if len(x.split('>')) > 1 else '')
            if 'child' not in df.columns:
                df['child'] = df['category'].apply(lambda x: x.split('>')[2].strip() if len(x.split('>')) > 2 else '')
            self.dfs[path] = df
        
        self.df = pd.concat(self.dfs.values(), ignore_index=True)
        self.clean_data()

    def clean_data(self):
        self.df['price'] = pd.to_numeric(self.df['price'], errors='coerce')
        self.df['mrp'] = pd.to_numeric(self.df['mrp'], errors='coerce')
        self.df['discount'] = pd.to_numeric(self.df['discount'].str.replace('%', ''), errors='coerce')
        self.df['savings'] = self.df['mrp'] - self.df['price']
        self.df = self.df[self.df['price'] > 0].copy()

    def get_grandparents(self):
        return sorted(self.df['grandparent'].unique())

    def get_parents(self, grandparent):
        return sorted(self.df[self.df['grandparent'] == grandparent]['parent'].unique())

    def get_children(self, parent):
        return sorted(self.df[self.df['parent'] == parent]['child'].unique())

    def get_top_deals(self, level, value, limit=10):
        if level == 'grandparent':
            items = self.df[self.df['grandparent'] == value]
        elif level == 'parent':
            items = self.df[self.df['parent'] == value]
        else:  # child
            items = self.df[self.df['child'] == value]

        return items.nlargest(limit, 'discount')[
            ['name', 'price', 'mrp', 'discount', 'savings', 'img_link', 'affiliate_link']
        ].to_dict('records')

class DealBot:
    def __init__(self, token):
        self.analyzer = ProductAnalyzer([
            'ELECTRONICS.csv', 'CLOTHES.csv', 'KITCHEN.csv', 
            'BEAUTY.csv', 'TOYS.csv'
        ])
        self.token = token
        self.ITEMS_PER_ROW = 2
        self.BROWSING = BROWSING  # Add state to instance
        self.main_categories = ['Electronics', 'Toys', 'Beauty', 'Clothes', 'Kitchen']


    def create_product_message(self, item):
        return (
            f"<a href='{item['img_link']}'>​</a>\n"
            f"📌 {item['name']}\n"
            f"💰 ₹{item['price']:,.0f} (🏷️ {item['discount']}% OFF!)\n"
            f"❌ MRP: ₹{item['mrp']:,.0f}\n"
            f"💫 Save: ₹{item['savings']:,.0f}"
        )

    async def send_products_grid(self, update, items, back_data=None):
        for i in range(0, len(items), self.ITEMS_PER_ROW):
            row_items = items[i:i + self.ITEMS_PER_ROW]
            for item in row_items:
                keyboard = [[InlineKeyboardButton("🛒 Buy Now", url=item['affiliate_link'])]]
                
                # Add navigation buttons to last row's last item
                if i + self.ITEMS_PER_ROW >= len(items) and row_items.index(item) == len(row_items) - 1:
                    nav_row = []
                    if back_data:
                        nav_row.append(InlineKeyboardButton("⬅️ Back", callback_data=back_data))
                    nav_row.append(InlineKeyboardButton("🏠 Main Menu", callback_data="main"))
                    keyboard.append(nav_row)
                
                await update.callback_query.message.reply_text(
                    self.create_product_message(item),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("🔥 TOP DEALS", callback_data="all_deals")],
            [
                InlineKeyboardButton("📱 Electronics", callback_data="cat_Electronics"),
                InlineKeyboardButton("🎮 Toys", callback_data="cat_Toys")
            ],
            [
                InlineKeyboardButton("💄 Beauty", callback_data="cat_Beauty"),
                InlineKeyboardButton("👕 Clothes", callback_data="cat_Clothes")
            ],
            [InlineKeyboardButton("🍳 Kitchen", callback_data="cat_Kitchen")]
        ]
        
        message = "🎉 Browse deals by category:"
        markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.message.edit_text(text=message, reply_markup=markup)
        else:
            await update.message.reply_text(text=message, reply_markup=markup)
        return BROWSING

    async def handle_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        category = query.data.split('_')[1]
        subcategories = self.analyzer.get_category_list(category)
        
        keyboard = [
            [InlineKeyboardButton(f"🏆 Top Deals in {category}", callback_data=f"deals_{category}")]
        ]
        
        # Create 2x2 grid of subcategories
        for i in range(0, len(subcategories), 2):
            row = []
            for subcat in subcategories[i:i+2]:
                row.append(InlineKeyboardButton(f"📁 {subcat}", callback_data=f"subcat_{category}_{subcat}"))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main")])
        
        await query.message.edit_text(
            f"Browse {category}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    async def handle_grandparent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        grandparent = query.data.split('_')[1]
        parents = self.analyzer.get_parents(grandparent)
        
        keyboard = [[InlineKeyboardButton(
            f"🏆 Top Deals in {grandparent}", 
            callback_data=f"grand_deals_{grandparent}"
        )]]
        
        for parent in parents:
            keyboard.append([InlineKeyboardButton(
                f"📁 {parent}", 
                callback_data=f"parent_{parent}"
            )])
        
        keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main")])
        
        await query.message.edit_text(
            f"Browse {grandparent}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_parent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        parent = query.data.split('_')[1]
        children = self.analyzer.get_children(parent)
        
        keyboard = [[InlineKeyboardButton(
            f"🏆 Top Deals in {parent}", 
            callback_data=f"parent_deals_{parent}"
        )]]
        
        for child in children:
            keyboard.append([InlineKeyboardButton(
                f"📁 {child}", 
                callback_data=f"child_deals_{child}"
            )])
        
        keyboard.append([
            InlineKeyboardButton("⬅️ Back", callback_data="main"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main")
        ])
        
        await query.message.edit_text(
            f"Browse {parent}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_deals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data.split('_')
        level = data[0]
        value = data[2]
        
        await query.message.edit_text(f"🔥 Top Deals in {value}:")
        items = self.analyzer.get_top_deals(level, value)
        back_data = {
            'grand': f"grand_{value}",
            'parent': f"parent_{value}",
            'child': f"parent_{value}"  # Back to parent level
        }.get(level, 'main')
        
        await self.send_products_grid(update, items, back_data)

    def run(self):
        application = Application.builder().token(self.token).build()
        
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.show_main_menu)],
            states={
                BROWSING: [
                    CallbackQueryHandler(self.show_main_menu, pattern='^main$'),
                    CallbackQueryHandler(self.handle_grandparent, pattern='^grand_[^_]+$'),
                    CallbackQueryHandler(self.handle_parent, pattern='^parent_[^_]+$'),
                    CallbackQueryHandler(self.handle_deals, pattern='.*_deals_.*'),
                ]
            },
            fallbacks=[CommandHandler('start', self.show_main_menu)]
        )
        
        application.add_handler(conv_handler)
        application.run_polling()

if __name__ == '__main__':
    bot = DealBot("8001175573:AAGTgsdRLkcYLXHSwVXJJ4YdzgY3938CLYQ")
    bot.run()

