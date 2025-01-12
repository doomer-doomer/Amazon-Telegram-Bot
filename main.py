import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from data_manager import DataManager
from config import TELEGRAM_TOKEN

# Initialize data manager
data_manager = DataManager()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message and show main categories"""
    # Create 2-column layout
    keyboard = []
    items = list(data_manager.csv_files.keys())
    for i in range(0, len(items), 2):
        row = []
        row.append(InlineKeyboardButton(items[i].title(), callback_data=f"file_{items[i]}"))
        if i + 1 < len(items):  # Check if there's a second item for the row
            row.append(InlineKeyboardButton(items[i+1].title(), callback_data=f"file_{items[i+1]}"))
        keyboard.append(row)
    
    # Add back button row
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌟 Welcome to Your Deal Hunter! 🛍️\n\n"
        "Looking for amazing discounts and unbeatable offers? You've come to the right place! 🎉\n\n"
        "✨ Explore Categories:\n"

        "Discover the best deals tailored just for you. From gadgets to fashion, and everything in between, we've got it all!\n\n"
        "👉 Tap a category below to start saving big today:\n\n"
         "*if you want to go back to the main menu, type /mainmenu. "
        "if you want to go back to the previous menu, type /back\n\n"
        ,
        reply_markup=reply_markup
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()

    data = query.data.split('_')
    action = data[0]

    if action == 'file':
        # Show main categories for selected file in 2-column layout
        file_key = data[1]
        categories = data_manager.get_main_categories(file_key)
        keyboard = []
        
        # Create 2-column layout for categories
        for i in range(0, len(categories), 2):
            row = []
            row.append(InlineKeyboardButton(
                categories[i], 
                callback_data=f"cat_{file_key}_{categories[i]}"
            ))
            if i + 1 < len(categories):
                row.append(InlineKeyboardButton(
                    categories[i+1], 
                    callback_data=f"cat_{file_key}_{categories[i+1]}"
                ))
            keyboard.append(row)
            
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="start")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"Select a category from {file_key.title()}:",
            reply_markup=reply_markup
        )

    elif action == 'cat':
        file_key = data[1]
        category = '_'.join(data[2:])
        # Get just 5 products without pagination
        result = data_manager.get_products(file_key, category, 5)
        
        if result:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data=f"file_{file_key}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send product messages
            for product in result:
                formatted = data_manager.format_product(product)
                product_keyboard = [[InlineKeyboardButton("🛍️ Buy Now", url=formatted['link'])]]
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=formatted['text'],
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(product_keyboard)
                )
            
            # Send back button
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Use /back or click below to return:",
                reply_markup=reply_markup
            )
            
            await query.message.delete()

    elif action == 'start':
        # Go back to start with 2-column layout
        keyboard = []
        items = list(data_manager.csv_files.keys())
        for i in range(0, len(items), 2):
            row = []
            row.append(InlineKeyboardButton(items[i].title(), callback_data=f"file_{items[i]}"))
            if i + 1 < len(items):
                row.append(InlineKeyboardButton(items[i+1].title(), callback_data=f"file_{items[i+1]}"))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Please select a category:",
            reply_markup=reply_markup
        )

async def command_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mainmenu command"""
    await start(update, context)

async def command_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /back command"""
    if 'last_category' not in context.user_data:
        await start(update, context)
        return
    
    last_category = context.user_data['last_category']
    if '_' in last_category:
        file_key = last_category.split('_')[0]
        await show_category(update, context, file_key)
    else:
        await start(update, context)

async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    """Show category products from command"""
    context.user_data['last_category'] = category
    categories = data_manager.get_main_categories(category)
    
    keyboard = []
    for cat in categories:
        clean_cat = cat.replace(' ', '_').lower()
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"cat_{category}_{clean_cat}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="start")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(
            f"Browse {category.title()} Categories:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"Browse {category.title()} Categories:",
            reply_markup=reply_markup
        )

def main():
    """Start the bot"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mainmenu", command_main_menu))
    application.add_handler(CommandHandler("back", command_back))
    
    # Add category command handlers
    for category in data_manager.csv_files.keys():
        application.add_handler(
            CommandHandler(category, lambda update, context, cat=category: 
                         show_category(update, context, cat))
        )
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_handler))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
