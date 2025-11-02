import asyncio
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database import Database
from ui import MAIN_MENU_INLINE, days_keyboard, dynamic_main_menu

db = Database()

SELECTING_DAY = 0
ADDING_EXERCISES = 1

# utility to format program summary
def format_program_summary(program_id: int) -> str:
    exercises = db.get_exercises(program_id)
    if not exercises:
        return "این برنامه هنوز حرکتی ندارد."
    lines = []
    for i, ex in enumerate(exercises, 1):
        weight = f"{ex.get('weight',0)} کیلوگرم" if ex.get('weight',0) and ex.get('weight',0) > 0 else "بدون وزنه"
        lines.append(f"{i}. {ex['name']} — {ex.get('reps','?')} تکرار × {ex.get('sets','?')} ست — {weight}")
    return "\n".join(lines)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.add_user(user.id, user.username)
    welcome_message = (
        "سلام! 👋\n\n"
        "این ربات برنامه‌های تمرینی تو رو مدیریت میکنه — ساخت، ویرایش و اجرای تمرینات با رابط کاربری ساده.\n"
        "برای شروع از دکمه‌ها استفاده کن یا /help را بزن."
    )
    if getattr(update, "message", None):
        await update.message.reply_text(welcome_message, reply_markup=dynamic_main_menu(context))
    else:
        cb = getattr(update, "callback_query", None)
        if cb:
            await cb.edit_message_text(welcome_message, reply_markup=dynamic_main_menu(context))

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_my":
        await my_programs(update, context)
    elif data == "menu_start":
        await start_workout(update, context)
    elif data == "menu_help":
        await help_command(update, context)
    elif data == "menu_settings":
        user_id = query.from_user.id
        cur_rest = db.get_rest_seconds(user_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏱ 30s", callback_data="set_rest_30"),
             InlineKeyboardButton("⏱ 60s", callback_data="set_rest_60"),
             InlineKeyboardButton("⏱ 90s", callback_data="set_rest_90")],
            [InlineKeyboardButton("بازگشت", callback_data="menu_back")]
        ])
        await query.edit_message_text(f"تنظیمات — زمان استراحت فعلی: {cur_rest} ثانیه\nیکی را انتخاب کنید:", reply_markup=keyboard)
    elif data == "menu_back":
        # پاک کردن حالت‌های موقتی تا منوی داینامیک به حالت عادی برگردد
        for k in ('current_program_id', 'exercise_count', 'editing_exercise_id', 'current_day'):
            context.user_data.pop(k, None)
        await query.edit_message_text("بازگشت به منوی اصلی.", reply_markup=dynamic_main_menu(context))
    else:
        # دیگر منوهای menu_ که از قبل توسط handlers جدا هندل می‌شوند یا ورودی Conversation خواهند بود.
        await query.answer()

async def set_rest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        seconds = int(query.data.split('_')[-1])
    except Exception:
        seconds = 60
    user_id = query.from_user.id
    db.set_rest_seconds(user_id, seconds)
    await query.edit_message_text(f"✅ زمان استراحت به {seconds} ثانیه تغییر کرد.", reply_markup=dynamic_main_menu(context))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "راهنما و نکات استفاده — خلاصه و سریع:\n\n"
        "• ساخت برنامه: ➕ برنامه جدید → روز را انتخاب کن → حرکات را یکی‌یکی وارد کن.\n"
        "  فرمت ورود حرکت: نام حرکت تکرار تعداد_ست وزن(اختیاری) [مثال: پرس سینه 12 3 60]\n"
        "  یا گیف را ارسال کن با کپشنِ فرمت بالا.\n\n"
        "• ویرایش برنامه: وقتی برای روز برنامه‌ای داری، گزینه «ویرایش» ظاهر می‌شود — می‌توانی حرکت را ویرایش، حذف یا حرکت جدید اضافه کنی.\n\n"
        "• حین تمرین: هر حرکت نمایش داده می‌شود (گیف اگر وجود داشته باشد)؛ دکمه «✅ انجام شد» برای رفتن به حرکت بعدی و زمان استراحت خودت اعمال می‌شود.\n\n"
        "دنبال قابلیت جدیدی هستی؟ بگو تا اضافه کنم — اشتراک‌گذاری ساده‌ترین راه برای حمایت از پروژه است 🙏"
    )
    cb = getattr(update, "callback_query", None)
    if cb:
        await cb.edit_message_text(help_text, reply_markup=dynamic_main_menu(context))
    else:
        await update.message.reply_text(help_text, reply_markup=dynamic_main_menu(context))

async def new_program(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    callback = getattr(update, "callback_query", None)
    user_id = callback.from_user.id if callback else update.effective_user.id
    text = "روز هفته را برای برنامه ورزشی انتخاب کنید:"
    markup = days_keyboard()
    if callback:
        await callback.edit_message_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)
    return SELECTING_DAY

async def day_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    day_name = query.data
    user_id = query.from_user.id

    existing = db.get_program_by_user_day(user_id, day_name)
    if existing:
        # show choices: view / edit / delete / overwrite
        pid = existing['id']
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 نمایش برنامه", callback_data=f"program_view_{pid}")],
            [InlineKeyboardButton("✏️ ویرایش برنامه", callback_data=f"program_edit_{pid}")],
            [InlineKeyboardButton("🗑 حذف برنامه", callback_data=f"program_delete_{pid}")],
            [InlineKeyboardButton("🔁 بازنویسی (ایجاد جدید)", callback_data=f"program_overwrite_{pid}")],
            [InlineKeyboardButton("بازگشت", callback_data="menu_back")]
        ])
        await query.edit_message_text(f"برای روز {day_name} قبلاً برنامه‌ای ثبت شده — چه کاری می‌خواهی انجام بدی؟", reply_markup=keyboard)
        return ConversationHandler.END
    else:
        program_id = db.create_workout_program(user_id, day_name)
        db.delete_exercises(program_id)
        context.user_data['current_program_id'] = program_id
        context.user_data['current_day'] = day_name
        context.user_data['exercise_count'] = 0
        await query.edit_message_text(
            f"برنامه جدید برای روز {day_name} ایجاد شد ✅\n\n"
            "حالا شروع کن به افزودن حرکت‌ها.\n"
            "فرمت: نام حرکت تکرار تعداد_ست وزن(اختیاری)\nمثال: پرس سینه 12 3 60"
        )
        return ADDING_EXERCISES

# program_action router
async def program_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data  # e.g., program_view_5
    parts = data.split('_', 2)
    if len(parts) < 3:
        await query.edit_message_text("خطا: عملیات نامعتبر.", reply_markup=dynamic_main_menu(context))
        return

    action = parts[1]
    pid = int(parts[2])

    if action == "view":
        summary = format_program_summary(pid)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ ویرایش", callback_data=f"program_edit_{pid}")],
            [InlineKeyboardButton("🔁 بازنویسی", callback_data=f"program_overwrite_{pid}")],
            [InlineKeyboardButton("بازگشت", callback_data="menu_back")]
        ])
        await query.edit_message_text(f"📋 خلاصه برنامه:\n\n{summary}", reply_markup=keyboard)
    elif action == "edit":
        # show exercises with edit/delete buttons and add-new
        exercises = db.get_exercises(pid)
        keyboard = []
        for ex in exercises:
            keyboard.append([InlineKeyboardButton(f"✏️ ویرایش: {ex['name']}", callback_data=f"ex_edit_{ex['id']}")])
            keyboard.append([InlineKeyboardButton(f"🗑 حذف: {ex['name']}", callback_data=f"ex_delete_{ex['id']}")])
        keyboard.append([InlineKeyboardButton("➕ اضافه کردن حرکت جدید", callback_data=f"ex_add_{pid}")])
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="menu_back")])
        await query.edit_message_text(f"ویرایش برنامه — انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif action == "delete":
        # delete program and its exercises
        db.delete_exercises(pid)
        cur = db.conn.cursor()
        cur.execute("DELETE FROM programs WHERE id = ?", (pid,))
        db.conn.commit()
        await query.edit_message_text("✅ برنامه حذف شد.", reply_markup=dynamic_main_menu(context))
    elif action == "overwrite":
        # overwrite: delete exercises then create new program entry
        db.delete_exercises(pid)
        # create new program row reusing day name
        cur = db.conn.cursor()
        cur.execute("SELECT day_name, user_id FROM programs WHERE id = ?", (pid,))
        row = cur.fetchone()
        if row:
            day_name = row['day_name']
            user_id = row['user_id']
            # create new program record
            new_pid = db.create_workout_program(user_id, day_name)
            db.delete_exercises(new_pid)
            context.user_data['current_program_id'] = new_pid
            context.user_data['current_day'] = day_name
            context.user_data['exercise_count'] = 0
            await query.edit_message_text(f"برنامه جدید برای {day_name} آماده شد — اکنون حرکات را اضافه کنید.", reply_markup=None)
            return ADDING_EXERCISES
        else:
            await query.edit_message_text("خطا — برنامه پیدا نشد.", reply_markup=dynamic_main_menu(context))
    else:
        await query.edit_message_text("عملیات نامشخص.", reply_markup=dynamic_main_menu(context))

# exercise callbacks router
async def exercise_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data  # ex_edit_{id} / ex_delete_{id} / ex_add_{program_id}
    if data.startswith("ex_edit_"):
        ex_id = int(data.split('_')[-1])
        # prompt user to send updated exercise line
        context.user_data['editing_exercise_id'] = ex_id
        await query.edit_message_text(
            "✏️ ویرایش حرکت: لطفا مشخصات جدید حرکت را به همین فرمت ارسال کن:\n"
            "نام حرکت تکرار تعداد_ست وزن(اختیاری)\nمثال: پرس سینه 10 3 60\nیا گیف با کپشن بفرست."
        )
        return ADDING_EXERCISES
    elif data.startswith("ex_delete_"):
        ex_id = int(data.split('_')[-1])
        deleted = db.delete_exercise_by_id(ex_id)
        if deleted:
            await query.edit_message_text("✅ حرکت حذف شد.", reply_markup=dynamic_main_menu(context))
        else:
            await query.edit_message_text("خطا: حرکت پیدا نشد.", reply_markup=dynamic_main_menu(context))
    elif data.startswith("ex_add_"):
        pid = int(data.split('_')[-1])
        context.user_data['current_program_id'] = pid
        context.user_data['current_day'] = None
        context.user_data['exercise_count'] = len(db.get_exercises(pid))
        await query.edit_message_text("➕ لطفا حرکت جدید را ارسال کنید (فرمت: نام حرکت تکرار تعداد_ست وزن(اختیاری)).")
        return ADDING_EXERCISES
    else:
        await query.edit_message_text("عملیات نامعتبر.", reply_markup=dynamic_main_menu(context))

# modify add_exercise to support edit flow
async def add_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    gif_file = None
    if getattr(update.message, "animation", None):
        gif_file = update.message.animation.file_id
        text = (update.message.caption or "").strip()
        if not text:
            await update.message.reply_text("شما گیف فرستادی — لطفا در کپشن مشخصات حرکت را بنویسید.\nمثال: پرس سینه 12 3 60")
            return ADDING_EXERCISES
    else:
        text = (update.message.text or "").strip()

    # finish adding
    if text in ('تمام', 'تمام.'):
        exercise_count = context.user_data.get('exercise_count', 0)
        day_name = context.user_data.get('current_day', '')
        if getattr(update, "message", None):
            await update.message.reply_text(f"برنامه {day_name or ''} با {exercise_count} حرکت ذخیره شد! ✅", reply_markup=dynamic_main_menu(context))
        else:
            cb = getattr(update, "callback_query", None)
            if cb:
                await cb.edit_message_text(f"برنامه {day_name or ''} با {exercise_count} حرکت ذخیره شد! ✅", reply_markup=dynamic_main_menu(context))
        context.user_data.pop('editing_exercise_id', None)
        context.user_data.pop('current_program_id', None)
        return ConversationHandler.END

    # undo
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

    tokens = text.split()
    if len(tokens) < 3:
        await update.message.reply_text("❌ فرمت صحیح نیست! مثال: پرس سینه 12 3 60")
        return ADDING_EXERCISES

    gif_url = None
    if tokens[-1].startswith('http') or tokens[-1].endswith('.gif'):
        gif_url = tokens[-1]; tokens = tokens[:-1]

    try:
        weight = float(tokens[-1])
        sets = int(tokens[-2])
        reps = int(tokens[-3])
        name_tokens = tokens[:-3]
        if not name_tokens:
            raise ValueError()
        exercise_name = ' '.join(name_tokens)
    except Exception:
        await update.message.reply_text("❌ خطا در خواندن مقادیر! مثال: پرس سینه 12 3 60")
        return ADDING_EXERCISES

    gif_to_store = gif_file if gif_file else gif_url
    editing_ex_id = context.user_data.get('editing_exercise_id')
    program_id = context.user_data.get('current_program_id')

    if editing_ex_id:
        ok = db.update_exercise(editing_ex_id, exercise_name, reps, sets, weight, gif_to_store)
        context.user_data.pop('editing_exercise_id', None)
        if ok:
            await update.message.reply_text(f"✅ حرکت به‌روز شد: {exercise_name}", reply_markup=dynamic_main_menu(context))
        else:
            await update.message.reply_text("خطا: نتوانستم حرکت را بروزرسانی کنم.", reply_markup=dynamic_main_menu(context))
        return ADDING_EXERCISES

    if not program_id:
        await update.message.reply_text("خطا: شناسه برنامه مشخص نیست. اول یک برنامه بساز.", reply_markup=dynamic_main_menu(context))
        return ADDING_EXERCISES

    position = context.user_data.get('exercise_count', 0)
    db.add_exercise(program_id, exercise_name, reps, sets, weight, gif_to_store, position)
    context.user_data['exercise_count'] = position + 1

    await update.message.reply_text(f"✅ حرکت اضافه شد: {exercise_name}\nتکرار: {reps} - ست: {sets} - وزن: {weight if weight>0 else 'بدون وزنه'}", reply_markup=dynamic_main_menu(context))
    return ADDING_EXERCISES

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    if getattr(update, "message", None):
        await update.message.reply_text("عملیات لغو شد. ❌", reply_markup=dynamic_main_menu(context))
    else:
        cb = getattr(update, "callback_query", None)
        if cb:
            await cb.edit_message_text("عملیات لغو شد. ❌", reply_markup=dynamic_main_menu(context))
    return ConversationHandler.END

async def my_programs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    callback = getattr(update, "callback_query", None)
    user_id = callback.from_user.id if callback else update.effective_user.id
    programs = db.get_user_programs(user_id)
    if not programs:
        text = "شما هنوز هیچ برنامه ورزشی ندارید! برای ساخت برنامه جدید از ➕ برنامه جدید استفاده کنید."
        if callback:
            await callback.edit_message_text(text, reply_markup=dynamic_main_menu(context))
        else:
            await update.message.reply_text(text, reply_markup=dynamic_main_menu(context))
        return

    message = "📋 برنامه‌های شما:\n\n"
    keyboard = []
    for program in programs:
        message += f"🗓️ {program['day_name']}\n"
        keyboard.append([InlineKeyboardButton(f"مشاهده / ویرایش {program['day_name']}", callback_data=f"program_view_{program['id']}")])

    keyboard.append([InlineKeyboardButton("بازگشت", callback_data="menu_back")])
    if callback:
        await callback.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

# -- BEGIN: missing workout handlers (append) --
async def start_workout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    callback = getattr(update, "callback_query", None)
    user_id = callback.from_user.id if callback else update.effective_user.id
    programs = db.get_user_programs(user_id)

    if not programs:
        text = "شما هنوز برنامه‌ای ندارید. برای ساخت برنامه از ➕ برنامه جدید استفاده کنید."
        if callback:
            await callback.edit_message_text(text, reply_markup=MAIN_MENU_INLINE)
        else:
            await update.message.reply_text(text, reply_markup=MAIN_MENU_INLINE)
        return

    keyboard = []
    for p in programs:
        keyboard.append([InlineKeyboardButton(p['day_name'], callback_data=f"start_{p['id']}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    prompt = "کدام برنامه را می‌خواهید شروع کنید؟"
    if callback:
        await callback.edit_message_text(prompt, reply_markup=reply_markup)
    else:
        await update.message.reply_text(prompt, reply_markup=reply_markup)


async def workout_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        program_id = int(query.data.replace('start_', ''))
    except Exception:
        await query.edit_message_text("خطا: شناسه برنامه نامعتبر است.")
        return

    user_id = query.from_user.id
    exercises = db.get_exercises(program_id)
    if not exercises:
        await query.edit_message_text("این برنامه هیچ حرکتی ندارد. ابتدا حرکات را اضافه کنید.", reply_markup=MAIN_MENU_INLINE)
        return

    session_id = db.create_workout_session(user_id, program_id)
    context.user_data['session_id'] = session_id
    context.user_data['program_id'] = program_id
    context.user_data['exercises'] = exercises
    context.user_data['current_index'] = 0

    await show_current_exercise(query, context)


async def show_current_exercise(query_or_message, context: ContextTypes.DEFAULT_TYPE) -> None:
    exercises = context.user_data.get('exercises', [])
    idx = context.user_data.get('current_index', 0)

    if idx >= len(exercises):
        session_id = context.user_data.get('session_id')
        if session_id:
            db.close_session(session_id)
        done_msg = "🎉 تبریک — تمرین تمام شد! استراحت کن و روز خوبی داشته باشی 💪"
        if hasattr(query_or_message, 'edit_message_text'):
            await query_or_message.edit_message_text(done_msg, reply_markup=MAIN_MENU_INLINE)
        else:
            await query_or_message.reply_text(done_msg, reply_markup=MAIN_MENU_INLINE)
        context.user_data.clear()
        return

    ex = exercises[idx]
    weight_text = f"{ex.get('weight', 0)} کیلوگرم" if ex.get('weight') and ex.get('weight') > 0 else "بدون وزنه"
    reps_text = f"{ex.get('reps','?')} تکرار"
    message = (
        f"💪 حرکت {idx+1} از {len(exercises)}\n\n"
        f"📌 {ex['name']}\n"
        f"🔁 {reps_text}\n"
        f"🔢 ست: {ex.get('sets','?')}\n"
        f"⚖️ {weight_text}\n\n"
        "بعد از انجام حرکت، «✅ انجام شد» را بزن."
    )

    keyboard = [
        [InlineKeyboardButton("✅ انجام شد", callback_data="exercise_done")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="session_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    gif = ex.get('gif')
    if gif:
        # send animation (file_id or url) with inline buttons
        if hasattr(query_or_message, 'message'):
            chat_id = query_or_message.message.chat_id
        else:
            chat_id = query_or_message.chat_id
        try:
            await context.bot.send_animation(chat_id=chat_id, animation=gif, caption=message, reply_markup=reply_markup)
            # optionally acknowledge previous inline message
            if hasattr(query_or_message, 'edit_message_text'):
                try:
                    await query_or_message.edit_message_text("حرکت ارسال شد ✅")
                except Exception:
                    pass
        except Exception:
            # fallback to plain text if animation fails
            if hasattr(query_or_message, 'edit_message_text'):
                await query_or_message.edit_message_text(message, reply_markup=reply_markup)
            else:
                await query_or_message.reply_text(message, reply_markup=reply_markup)
    else:
        if hasattr(query_or_message, 'edit_message_text'):
            await query_or_message.edit_message_text(message, reply_markup=reply_markup)
        else:
            await query_or_message.reply_text(message, reply_markup=reply_markup)


async def exercise_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    exercises = context.user_data.get('exercises', [])
    current_index = context.user_data.get('current_index', 0)

    # advance index
    context.user_data['current_index'] = current_index + 1
    session_id = context.user_data.get('session_id')
    if session_id is not None:
        db.update_session_exercise_index(session_id, current_index + 1)

    # if finished, show completion
    if current_index + 1 >= len(exercises):
        await show_current_exercise(query, context)
        return

    user_id = query.from_user.id
    rest_seconds = db.get_rest_seconds(user_id) or 60
    await query.edit_message_text(f"⏱️ زمان استراحت: {rest_seconds} ثانیه — استراحت کن.")
    await asyncio.sleep(rest_seconds)
    try:
        await query.message.reply_text(f"🔔 زمان استراحت ({rest_seconds}s) تمام شد! آماده حرکت بعدی؟")
    except Exception:
        pass
    await show_current_exercise(query.message, context)


async def session_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    current_index = context.user_data.get('current_index', 0)
    if current_index <= 0:
        await query.edit_message_text("شما در ابتدای جلسه هستید.", reply_markup=MAIN_MENU_INLINE)
        return
    context.user_data['current_index'] = current_index - 1
    session_id = context.user_data.get('session_id')
    if session_id is not None:
        db.update_session_exercise_index(session_id, current_index - 1)
    await show_current_exercise(query, context)
# -- END: missing workout handlers --

async def start_add_from_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry from dynamic main menu: add a new exercise to the current program."""
    query = update.callback_query
    await query.answer()
    program_id = context.user_data.get('current_program_id')
    if not program_id:
        # no active program -> show normal main menu
        await query.edit_message_text("هیچ برنامه فعالی پیدا نشد. ابتدا برنامه را باز یا ایجاد کنید.", reply_markup=dynamic_main_menu(context))
        return ConversationHandler.END

    # prepare for adding exercises
    context.user_data['exercise_count'] = len(db.get_exercises(program_id))
    await query.edit_message_text(
        "➕ لطفا حرکت جدید را ارسال کنید.\n\n"
        "فرمت: نام حرکت تکرار تعداد_ست وزن(اختیاری)\n"
        "مثال: پرس سینه 12 3 60\n\n"
        "یا گیف را همراه با کپشنِ فرمت بالا ارسال کنید."
    )
    return ADDING_EXERCISES