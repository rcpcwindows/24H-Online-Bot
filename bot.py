from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, PicklePersistence
)
import requests
import datetime
import os

# আপনার বট টোকেন এখানে দিন
BOT_TOKEN = "8422788590:AAHRryFoq16PoLEPk2bVQEDSD4UK0yBJwAM"

# --- API কল করার ফাংশন (কোনো পরিবর্তন নেই) ---
def sowrov_stats(api_key, day="today", date_from=None, date_to=None):
    if day == "today":
        date_from = date_to = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    elif day == "yesterday":
        date_from = date_to = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    elif date_from and date_to:
        date_from = date_from.strftime("%Y-%m-%d")
        date_to = date_to.strftime("%Y-%m-%d")
    else:
        date_from = date_to = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    url = "https://api.monetag.com/v5/pub/statistics"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"group_by": ["site_id"], "date_from": date_from, "date_to": date_to, "page": 1, "page_size": 100}

    try:
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        impressions = revenue = cpm = 0
        for row in data.get("result", []):
            impressions += int(row.get("impressions", 0))
            revenue += float(row.get("money", 0))
        if impressions > 0:
            cpm = revenue / impressions * 1000
        return impressions, revenue, cpm
    except Exception as e:
        print("Stats Error:", e)
        return 0, 0, 0


# --- নতুন Reply Keyboard তৈরির ফাংশন ---
def get_main_reply_keyboard():
    keyboard = [
        ["📊 Today Stats", "📅 Yesterday Stats"],
        ["📈 Weekly Stats", "🗓 This Year Stats"],
        ["✨ Custom Date Range","🚪 Logout"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# --- বট হ্যান্ডলার ---
async def sowrov_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_tokens = context.bot_data.get('user_tokens', {})
    if user_id not in user_tokens:
        await update.message.reply_text("🔑 Please send your Monetag API Token:", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("✅ Welcome back!\nChoose an option:", reply_markup=get_main_reply_keyboard())

# --- সকল মেসেজ এবং বাটন এখন এই একটি ফাংশন দিয়ে পরিচালিত হবে ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    state = context.user_data.get('state')
    
    user_tokens = context.bot_data.setdefault('user_tokens', {})

    # ধাপ ১: লগইন বা API Key সেভ করা
    if user_id not in user_tokens:
        user_tokens[user_id] = text
        await update.message.reply_text("✅ API Token Saved!\nNow choose an option:", reply_markup=get_main_reply_keyboard())
        return

    api_key = user_tokens[user_id]

    # ধাপ ২: কাস্টম তারিখ ইনপুট নেওয়া
    if state == 'awaiting_start_date':
        try:
            start_date = datetime.datetime.strptime(text, "%Y-%m-%d")
            context.user_data['start_date'] = start_date
            context.user_data['state'] = 'awaiting_end_date'
            await update.message.reply_text("Great! Now send the end date in YYYY-MM-DD format.")
        except ValueError:
            await update.message.reply_text("Invalid date format. Please use YYYY-MM-DD.")
        return

    elif state == 'awaiting_end_date':
        try:
            end_date = datetime.datetime.strptime(text, "%Y-%m-%d")
            start_date = context.user_data.get('start_date')
            if not start_date or end_date < start_date:
                await update.message.reply_text("End date cannot be before the start date. Please try again.", reply_markup=get_main_reply_keyboard())
            else:
                impressions, revenue, cpm = sowrov_stats(api_key, day=None, date_from=start_date, date_to=end_date)
                msg = (f"📊 Report from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n\n"
                       f"👁 Impressions: {impressions}\n💵 Profit: ${round(revenue, 3)}\n📈 CPM: ${round(cpm, 2)}")
                await update.message.reply_text(text=msg, reply_markup=get_main_reply_keyboard())
            
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("Invalid date format. Please use YYYY-MM-DD.")
        return

    # ধাপ ৩: Reply Keyboard বাটনের কমান্ডগুলো পরিচালনা করা
    if text == "📊 Today Stats":
        impressions, revenue, cpm = sowrov_stats(api_key, "today")
        msg = f"📊 Today's Report\n\n👁 Impressions: {impressions}\n💵 Profit: ${round(revenue, 3)}\n📈 CPM: ${round(cpm, 2)}"
        await update.message.reply_text(text=msg, reply_markup=get_main_reply_keyboard())

    elif text == "📅 Yesterday Stats":
        impressions, revenue, cpm = sowrov_stats(api_key, "yesterday")
        msg = f"📅 Yesterday's Report\n\n👁 Impressions: {impressions}\n💵 Revenue: ${round(revenue, 3)}\n📈 CPM: ${round(cpm, 2)}"
        await update.message.reply_text(text=msg, reply_markup=get_main_reply_keyboard())

    elif text == "📈 Weekly Stats":
        now = datetime.datetime.now(datetime.timezone.utc)
        week_ago = now - datetime.timedelta(days=7)
        impressions, revenue, cpm = sowrov_stats(api_key, day=None, date_from=week_ago, date_to=now)
        msg = f"📈 Weekly Report\n\n👁 Impressions: {impressions}\n💵 Revenue: ${round(revenue, 3)}\n📈 CPM: ${round(cpm, 2)}"
        await update.message.reply_text(text=msg, reply_markup=get_main_reply_keyboard())
        
    elif text == "🗓 This Year Stats":
        now = datetime.datetime.now(datetime.timezone.utc)
        start_of_year = datetime.datetime(now.year, 1, 1, tzinfo=datetime.timezone.utc)
        impressions, revenue, cpm = sowrov_stats(api_key, day=None, date_from=start_of_year, date_to=now)
        msg = f"🗓 This Year's Report\n\n👁 Impressions: {impressions}\n💵 Revenue: ${round(revenue, 3)}\n📈 CPM: ${round(cpm, 2)}"
        await update.message.reply_text(text=msg, reply_markup=get_main_reply_keyboard())

    elif text == "✨ Custom Date Range":
        context.user_data['state'] = 'awaiting_start_date'
        await update.message.reply_text("Please send the start date in YYYY-MM-DD format.", reply_markup=ReplyKeyboardRemove())

    elif text == "🌍 Country Stats":
        await update.message.reply_text("Select a period for the country report:", reply_markup=get_country_reply_keyboard())

    elif text == "📊 Today's Country Stats":
        now = datetime.datetime.now(datetime.timezone.utc)
        stats = sowrov_country_stats(api_key, now, now)
        msg = "🌍 Country-wise Stats (Today)\n\n"
        if not stats:
            msg += "ℹ No country data available yet for today."
        else:
            for country_name, impressions, revenue, cpm in stats:
                msg += f"{country_name}\n👁 Imp: {impressions} | 💵 Rev: ${round(revenue, 2)} | 📈 CPM: ${round(cpm, 2)}\n\n"
        await update.message.reply_text(text=msg, reply_markup=get_main_reply_keyboard())
        
    elif text == "📅 Yesterday's Country Stats":
        yesterday = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
        stats = sowrov_country_stats(api_key, yesterday, yesterday)
        msg = "🌍 Country-wise Stats (Yesterday)\n\n"
        if not stats:
            msg += "ℹ No country data available for yesterday."
        else:
            for country_name, impressions, revenue, cpm in stats:
                msg += f"{country_name}\n👁 Imp: {impressions} | 💵 Rev: ${round(revenue, 2)} | 📈 CPM: ${round(cpm, 2)}\n\n"
        await update.message.reply_text(text=msg, reply_markup=get_main_reply_keyboard())

    elif text == "🔙 Back to Menu":
        await update.message.reply_text("🔙 Back to main menu:", reply_markup=get_main_reply_keyboard())
        
    elif text == "🧩 Zone Info":
        zones = sowrov_zone_info(api_key)
        msg = "🧩 Zone Information\n\n" + "\n".join(zones[:20])
        await update.message.reply_text(text=msg, reply_markup=get_main_reply_keyboard())

    elif text == "🚪 Logout":
        if 'user_tokens' in context.bot_data:
            context.bot_data['user_tokens'].pop(user_id, None)
        await update.message.reply_text("🚪 You have been logged out!\n\n/start again to login.", reply_markup=ReplyKeyboardRemove())

    # যদি কোনো বাটন না মেলে তবে ডিফল্ট বার্তা
    else:
        await update.message.reply_text("Please choose a valid option from the keyboard.", reply_markup=get_main_reply_keyboard())

if __name__ == "__main__":
    if not BOT_TOKEN:
        raise ValueError("Error: BOT_TOKEN is not set.")

    persistence = PicklePersistence(filepath="bot_data.pickle")
    app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", sowrov_start))
    # CallbackQueryHandler বাদ দেওয়া হয়েছে
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running with Reply Keyboard... 🚀")
    app.run_polling()