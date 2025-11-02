from telegram import InlineKeyboardButton, InlineKeyboardMarkup

DAYS_PERSIAN = [
    'شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه'
]

def main_menu_base():
    return [
        [InlineKeyboardButton("➕ برنامه جدید", callback_data="menu_new")],
        [InlineKeyboardButton("📋 برنامه‌ها", callback_data="menu_my")],
        [InlineKeyboardButton("▶️ شروع تمرین", callback_data="menu_start")],
        [
            InlineKeyboardButton("⚙️ تنظیمات", callback_data="menu_settings"),
            InlineKeyboardButton("❓ راهنما", callback_data="menu_help")
        ],
    ]

def dynamic_main_menu(context=None) -> InlineKeyboardMarkup:
    # اگر در حال ادیت برنامه‌ای هستیم، منو را تغییر بده
    user_data = context.user_data if context else {}
    if user_data.get('current_program_id'):
        # در حالت ساخت/ادیت برنامه، دکمه‌های کم‌تر و مربوط نمایش بده
        menu = [
            [InlineKeyboardButton("➕ افزودن حرکت", callback_data="menu_new_add")],
            [InlineKeyboardButton("✅ ذخیره و بازگشت", callback_data="menu_back")],
        ]
        return InlineKeyboardMarkup(menu)
    # حالت عادی
    return InlineKeyboardMarkup(main_menu_base())

def days_keyboard() -> InlineKeyboardMarkup:
    keyboard = []
    days = DAYS_PERSIAN
    for i in range(0, len(days), 2):
        row = []
        for j in range(i, min(i+2, len(days))):
            row.append(InlineKeyboardButton(days[j], callback_data=days[j]))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

# also export a constant for legacy code
MAIN_MENU_INLINE = dynamic_main_menu()