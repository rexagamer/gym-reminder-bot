# ...existing code...
import os
import logging
import asyncio
from typing import Dict
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

from database import Database

# ...existing code...
# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
SELECTING_DAY, ADDING_EXERCISES, ADDING_EXERCISE_DETAILS = range(3)

# Days of the week in Persian
DAYS_PERSIAN = {
    'شنبه': 'شنبه',
    'یکشنبه': 'یکشنبه',
    'دوشنبه': 'دوشنبه',
    'سه‌شنبه': 'سه‌شنبه',
    'چهارشنبه': 'چهارشنبه',
    'پنجشنبه': 'پنجشنبه',
    'جمعه': 'جمعه',
}

# Initialize database
db = Database()

MAIN_MENU = [
    [KeyboardButton("/newprogram"), KeyboardButton("/myprograms")],
    [KeyboardButton("/start_workout"), KeyboardButton("/help")],
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    db.add_user(user.id, user.username)

    welcome_message = (
        f"سلام {user.first_name}! 👋\n\n"
        "به ربات یادآور ورزشی خوش آمدید! 💪\n\n"
        "دکمه‌ها را برای استفاده سریع لمس کنید یا از دستورات استفاده کنید."
    )

    reply_markup = ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "📋 راهنمای استفاده:\n\n"
        "1️⃣ برای ساخت برنامه ورزشی از /newprogram استفاده کنید\n"
        "2️⃣ روز هفته را انتخاب کنید\n"
        "3️⃣ حرکات را به صورت زیر اضافه کنید (بدون ویرگول):\n"
        "   نام حرکت [ممکن است شامل فاصله] تکرار_per_set تعداد_ست وزن(اختیاری) gif_url(اختیاری)\n"
        "   مثال: پرس سینه 12 3 60 https://example.com/demo.gif\n"
        "4️⃣ برای حذف آخرین حرکت 'بازگشت' یا /back بزنید\n"
        "5️⃣ برای پایان دادن به افزودن حرکات 'تمام' بنویسید\n"
        "6️⃣ برای شروع تمرین از /start_workout استفاده کنید\n\n"
        "در حین تمرین، ربات هر حرکت را نشان می‌دهد (گیف در صورت وجود) و پس از هر حرکت دکمه 'انجام شد' برای رفتن به حرکت بعدی وجود دارد."
    )

    await update.message.reply_text(help_text)


async def new_program(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation for creating a new workout program."""
    keyboard = []
    days_list = list(DAYS_PERSIAN.keys())

    # Create keyboard with 2 buttons per row
    for i in range(0, len(days_list), 2):
        row = []
        for j in range(i, min(i + 2, len(days_list))):
            row.append(InlineKeyboardButton(days_list[j], callback_data=days_list[j]))
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "روز هفته را برای برنامه ورزشی انتخاب کنید:",
        reply_markup=reply_markup
    )

    return SELECTING_DAY


async def day_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle day selection."""
    query = update.callback_query
    await query.answer()

    day_name = query.data
    user_id = update.effective_user.id

    # Create or get workout program
    program_id = db.create_workout_program(user_id, day_name)

    # Clear existing exercises for this program
    db.delete_exercises(program_id)

    # Store in context
    context.user_data['current_program_id'] = program_id
    context.user_data['current_day'] = day_name
    context.user_data['exercise_count'] = 0

    await query.edit_message_text(
        f"برنامه برای روز {day_name} ایجاد شد! ✅\n\n"
        "حالا حرکات ورزشی را اضافه کنید.\n"
        "فرمت: نام حرکت تکرار_per_set تعداد_ست وزن(اختیاری) gif_url(اختیاری)\n\n"
        "مثال: پرس سینه 12 3 60 https://example.com/demo.gif\n\n"
        "برای حذف آخرین حرکت 'بازگشت' را بزنید.\n"
        "برای پایان، 'تمام' بنویسید."
    )

    return ADDING_EXERCISES


async def add_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Add an exercise to the current workout program."""
    text = update.message.text.strip()

    # Handle cancellation/back
    if text in ('تمام', 'تمام.'):
        exercise_count = context.user_data.get('exercise_count', 0)
        day_name = context.user_data.get('current_day', '')

        await update.message.reply_text(
            f"برنامه {day_name} با {exercise_count} حرکت ذخیره شد! ✅\n\n"
            "برای مشاهده برنامه‌ها از /myprograms استفاده کنید.\n"
            "برای شروع تمرین از /start_workout استفاده کنید."
        )

        # Clear context
        context.user_data.clear()
        return ConversationHandler.END

    if text in ('بازگشت', '/back', 'undo'):
        program_id = context.user_data.get('current_program_id')
        if not program_id:
            await update.message.reply_text("هیچ برنامه‌ای در حال ساخت وجود ندارد.")
            return ADDING_EXERCISES

        removed = db.delete_last_exercise(program_id)
        if removed:
            context.user_data['exercise_count'] = max(0, context.user_data.get('exercise_count', 1) - 1)
            await update.message.reply_text("آخرین حرکت حذف شد. میتوانید حرکت جدید اضافه کنید یا 'تمام' بنویسید.")
        else:
            await update.message.reply_text("هیچ حرکتی وجود ندارد که حذف شود.")
        return ADDING_EXERCISES

    # Parse exercise details using whitespace-separated tokens; name can contain spaces.
    tokens = text.split()
    if len(tokens) < 3:
        await update.message.reply_text(
            "❌ فرمت صحیح نیست!\n"
            "لطفا به این صورت وارد کنید:\n"
            "نام حرکت تکرار_per_set تعداد_ست وزن(اختیاری) gif_url(اختیاری)\n\n"
            "مثال: پرس سینه 12 3 60 https://example.com/demo.gif"
        )
        return ADDING_EXERCISES

    # Determine if last token is gif url (simple heuristic)
    gif_url = None
    if tokens[-1].startswith('http') or tokens[-1].endswith('.gif'):
        gif_url = tokens[-1]
        tokens = tokens[:-1]

    try:
        weight = float(tokens[-1])  # last is weight (optional)
        sets = int(tokens[-2])
        reps = int(tokens[-3])
        name_tokens = tokens[:-3]
        if not name_tokens:
            raise ValueError("نام حرکت خالی است")
        exercise_name = ' '.join(name_tokens)
    except Exception:
        await update.message.reply_text(
            "❌ خطا در خواندن مقادیر!\n"
            "لطفا فرمت را رعایت کنید:\n"
            "نام حرکت تکرار_per_set تعداد_ست وزن(اختیاری) gif_url(اختیاری)\n"
            "مثال: پرس سینه 12 3 60 https://example.com/demo.gif"
        )
        return ADDING_EXERCISES

    # Add exercise to database
    program_id = context.user_data['current_program_id']
    exercise_count = context.user_data.get('exercise_count', 0)

    db.add_exercise(program_id, exercise_name, reps, sets, weight, gif_url, exercise_count)

    context.user_data['exercise_count'] = exercise_count + 1

    weight_text = f"{weight} کیلوگرم" if weight > 0 else "بدون وزنه"

    await update.message.reply_text(
        f"✅ حرکت اضافه شد:\n"
        f"📌 {exercise_name}\n"
        f"🔁 تکرار: {reps}\n"
        f"🔢 ست: {sets}\n"
        f"⚖️ {weight_text}\n\n"
        "حرکت بعدی را اضافه کنید یا 'تمام' بنویسید. برای حذف آخرین حرکت 'بازگشت' بزنید."
    )

    return ADDING_EXERCISES


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    context.user_data.clear()
    await update.message.reply_text(
        "عملیات لغو شد. ❌\n"
        "برای شروع دوباره از /newprogram استفاده کنید."
    )
    return ConversationHandler.END


async def my_programs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's workout programs."""
    user_id = update.effective_user.id
    programs = db.get_user_programs(user_id)

    if not programs:
        await update.message.reply_text(
            "شما هنوز هیچ برنامه ورزشی ندارید! 📋\n"
            "برای ساخت برنامه جدید از /newprogram استفاده کنید."
        )
        return

    message = "📋 برنامه‌های ورزشی شما:\n\n"

    for program in programs:
        program_id = program['id']
        day_name = program['day_name']
        exercises = db.get_exercises(program_id)

        message += f"🗓️ {day_name}:\n"

        if exercises:
            for i, exercise in enumerate(exercises, 1):
                weight_text = f"{exercise['weight']} کیلوگرم" if exercise['weight'] > 0 else "بدون وزنه"
                reps_text = f"{exercise.get('reps', '?')} تکرار"
                message += f"  {i}. {exercise['name']} - {reps_text} - {exercise['sets']} ست - {weight_text}\n"
        else:
            message += "  (هیچ حرکتی اضافه نشده)\n"

        message += "\n"

    await update.message.reply_text(message)


async def start_workout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a workout session."""
    user_id = update.effective_user.id
    programs = db.get_user_programs(user_id)

    if not programs:
        await update.message.reply_text(
            "شما هنوز هیچ برنامه ورزشی ندارید! 📋\n"
            "برای ساخت برنامه جدید از /newprogram استفاده کنید."
        )
        return

    # Create keyboard for program selection
    keyboard = []
    for program in programs:
        keyboard.append([InlineKeyboardButton(
            program['day_name'],
            callback_data=f"start_{program['id']}"
        )])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "کدام برنامه را می‌خواهید شروع کنید؟",
        reply_markup=reply_markup
    )


async def workout_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle workout program selection and start the session."""
    query = update.callback_query
    await query.answer()

    program_id = int(query.data.replace('start_', ''))
    user_id = update.effective_user.id

    # Get exercises
    exercises = db.get_exercises(program_id)

    if not exercises:
        await query.edit_message_text(
            "این برنامه هیچ حرکتی ندارد! ❌\n"
            "لطفا ابتدا حرکات را اضافه کنید."
        )
        return

    # Create workout session
    session_id = db.create_workout_session(user_id, program_id)

    # Store in context
    context.user_data['session_id'] = session_id
    context.user_data['program_id'] = program_id
    context.user_data['exercises'] = exercises
    context.user_data['current_index'] = 0

    # Start first exercise
    await show_current_exercise(query, context)


async def show_current_exercise(query_or_message, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the current exercise to the user. Supports sending GIF if available."""
    exercises = context.user_data.get('exercises', [])
    current_index = context.user_data.get('current_index', 0)

    if current_index >= len(exercises):
        # Workout completed
        session_id = context.user_data.get('session_id')
        if session_id:
            db.close_session(session_id)

        message = (
            "🎉 تبریک! تمرین امروز شما تمام شد! 🎉\n\n"
            "عالی بود! 💪\n"
            "برای تمرین بعدی از /start_workout استفاده کنید."
        )

        # if callback query object
        if hasattr(query_or_message, 'edit_message_text'):
            await query_or_message.edit_message_text(message)
        else:
            await query_or_message.reply_text(message)

        context.user_data.clear()
        return

    exercise = exercises[current_index]
    weight_text = f"{exercise['weight']} کیلوگرم" if exercise['weight'] > 0 else "بدون وزنه"
    reps_text = f"{exercise.get('reps', '?')} تکرار"

    message = (
        f"💪 حرکت {current_index + 1} از {len(exercises)}:\n\n"
        f"📌 {exercise['name']}\n"
        f"🔁 {reps_text}\n"
        f"🔢 تعداد ست: {exercise['sets']}\n"
        f"⚖️ وزنه: {weight_text}\n\n"
        "بعد از انجام حرکت، دکمه 'انجام شد' را بزنید."
    )

    keyboard = [
        [InlineKeyboardButton("✅ انجام شد", callback_data="exercise_done")],
        [InlineKeyboardButton("بازگشت", callback_data="session_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # If there's a gif, send it as animation with caption
    gif = exercise.get('gif')
    if gif:
        # Determine chat_id
        if hasattr(query_or_message, 'message'):
            chat_id = query_or_message.message.chat_id
        else:
            chat_id = query_or_message.chat_id

        # send animation message (and include inline keyboard)
        await context.bot.send_animation(chat_id=chat_id, animation=gif, caption=message, reply_markup=reply_markup)
        # Optionally edit the original inline message to remove previous text (if callback)
        if hasattr(query_or_message, 'edit_message_text'):
            try:
                await query_or_message.edit_message_text("حرکت ارسال شد ✅")
            except Exception:
                pass
    else:
        if hasattr(query_or_message, 'edit_message_text'):
            await query_or_message.edit_message_text(message, reply_markup=reply_markup)
        else:
            await query_or_message.reply_text(message, reply_markup=reply_markup)


async def exercise_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle exercise completion and start rest timer."""
    query = update.callback_query
    await query.answer()

    exercises = context.user_data.get('exercises', [])
    current_index = context.user_data.get('current_index', 0)

    # Move to next exercise
    context.user_data['current_index'] = current_index + 1

    # Update session in database
    session_id = context.user_data.get('session_id')
    if session_id:
        db.update_session_exercise_index(session_id, current_index + 1)

    # Check if there are more exercises
    if current_index + 1 >= len(exercises):
        # This was the last exercise
        await show_current_exercise(query, context)
        return

    # Start rest timer
    await query.edit_message_text("⏱️ زمان استراحت: 1 دقیقه\n\nاستراحت کنید...")

    # Wait for 60 seconds
    await asyncio.sleep(60)

    # Send alarm message
    await query.message.reply_text(
        "🔔 زمان استراحت تمام شد! ⏰\n\n"
        "آماده حرکت بعدی؟"
    )

    # Show next exercise
    await show_current_exercise(query.message, context)


async def session_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """User pressed back during workout: go back one exercise if possible."""
    query = update.callback_query
    await query.answer()

    current_index = context.user_data.get('current_index', 0)
    if current_index <= 0:
        await query.edit_message_text("در حال حاضر به ابتدای جلسه رسیدید.")
        return

    context.user_data['current_index'] = current_index - 1
    session_id = context.user_data.get('session_id')
    if session_id:
        db.update_session_exercise_index(session_id, current_index - 1)

    await show_current_exercise(query, context)


def main() -> None:
    """Start the bot."""
    # Get token from environment
    token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        return

    # Create the Application
    application = Application.builder().token(token).build()

    # Add conversation handler for creating workout programs
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('newprogram', new_program)],
        states={
            SELECTING_DAY: [CallbackQueryHandler(day_selected)],
            ADDING_EXERCISES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_exercise)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('back', cancel)],
        allow_reentry=True,
    )

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('myprograms', my_programs))
    application.add_handler(CommandHandler('start_workout', start_workout))
    application.add_handler(CallbackQueryHandler(workout_selected, pattern=r'^start_\d+$'))
    application.add_handler(CallbackQueryHandler(exercise_done, pattern=r'^exercise_done$'))
    application.add_handler(CallbackQueryHandler(session_back, pattern=r'^session_back$'))

    # Run the bot
    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
# ...existing code...