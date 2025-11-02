import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters

load_dotenv()
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        return

    application = Application.builder().token(token).build()

    # import handlers late to avoid circular imports
    from handlers import (
        start, help_command, menu_callback, set_rest_callback,
        new_program, day_selected, add_exercise, cancel,
        my_programs, start_workout, workout_selected,
        exercise_done, session_back,
        program_action, exercise_action,
        start_add_from_menu
    )

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('newprogram', new_program),
            CallbackQueryHandler(new_program, pattern=r'^menu_new$'),
            CallbackQueryHandler(start_add_from_menu, pattern=r'^menu_new_add$'),
        ],
        states={
            0: [CallbackQueryHandler(day_selected)],
            1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_exercise),
                MessageHandler(filters.ANIMATION, add_exercise),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('back', cancel)],
        allow_reentry=True,
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('myprograms', my_programs))
    application.add_handler(CommandHandler('start_workout', start_workout))
    application.add_handler(CallbackQueryHandler(workout_selected, pattern=r'^start_\d+$'))
    application.add_handler(CallbackQueryHandler(exercise_done, pattern=r'^exercise_done$'))
    application.add_handler(CallbackQueryHandler(session_back, pattern=r'^session_back$'))
    # register program/exercise routers so program_* and ex_* buttons work
    application.add_handler(CallbackQueryHandler(program_action, pattern=r'^program_'))
    application.add_handler(CallbackQueryHandler(exercise_action, pattern=r'^ex_'))
    application.add_handler(CallbackQueryHandler(menu_callback, pattern=r'^menu_'))
    application.add_handler(CallbackQueryHandler(set_rest_callback, pattern=r'^set_rest_\d+$'))

    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()