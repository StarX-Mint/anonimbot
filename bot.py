import psycopg2
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Токен бота и настройки
BOT_TOKEN = "8191881269:AAHHU-0UJ0dyU1stmhQpvNnuru3kFjiOM5I"
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID") or 7945088917)  # ЗАМЕНИ НА СВОЙ ID В TELEGRAM

# Параметры подключения к PostgreSQL
DB_CONFIG = {
    'host': 'dpg-d579gclactks73c1efkg-a.oregon-postgres.render.com',
    'port': 5432,
    'database': 'telegram_bot_db_anonimbot',
    'user': 'telegram_bot_db_anonimbot_user',
    'password': '6xdN9So5REGUHCTEX8Qv0KvlckKqVfkR'
}

# Инициализация базы данных
def init_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Таблица для связей сообщений
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            admin_message_id BIGINT PRIMARY KEY,
            user_id BIGINT NOT NULL
        )
    ''')
    
    # Таблица для забаненных пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id BIGINT PRIMARY KEY,
            banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

# Проверка, забанен ли пользователь
def is_user_banned(user_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute('SELECT 1 FROM banned_users WHERE user_id = %s', (user_id,))
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return result is not None

# Забанить пользователя
def ban_user(user_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO banned_users (user_id)
        VALUES (%s)
        ON CONFLICT (user_id) DO NOTHING
    ''', (user_id,))
    
    conn.commit()
    cursor.close()
    conn.close()

# Разбанить пользователя
def unban_user(user_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM banned_users WHERE user_id = %s', (user_id,))
    
    conn.commit()
    cursor.close()
    conn.close()

# Сохранить связь сообщения и пользователя
def save_message_link(admin_message_id, user_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO messages (admin_message_id, user_id)
        VALUES (%s, %s)
        ON CONFLICT (admin_message_id) DO NOTHING
    ''', (admin_message_id, user_id))
    
    conn.commit()
    cursor.close()
    conn.close()

# Получить user_id по admin_message_id
def get_user_id(admin_message_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM messages WHERE admin_message_id = %s', (admin_message_id,))
    row = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return row[0] if row else None

# Стартовое сообщение
START_MESSAGE = """
🌌 *Добро пожаловать в Анонимный Космический Бот!* 🌠

🚀 Отправь мне сообщение, фото, стикер или медиа — и я передам его анонимно в космос…  
🌠 Твое послание будет доставлено без указания имени.

💫 Просто отправь что угодно!
"""

# Команда бана для админа
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    
    try:
        user_id = int(context.args[0])
        ban_user(user_id)
        await update.message.reply_text(f"✅ Пользователь {user_id} забанен!")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Использование: /ban <user_id>")

# Команда разбана для админа
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    
    try:
        user_id = int(context.args[0])
        unban_user(user_id)
        await update.message.reply_text(f"✅ Пользователь {user_id} разбанен!")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Использование: /unban <user_id>")

# Команда для получения своего ID
async def get_my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"🆔 Твой ID: {user_id}")

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        START_MESSAGE,
        parse_mode="Markdown"
    )

# Форматирование сообщения с ID пользователя
def format_admin_message(user_id, content, content_type="text"):
    emoji_map = {
        "text": "💬",
        "photo": "📸",
        "document": "📄",
        "sticker": "ickerView",
        "voice": "🎤",
        "video": "🎬",
        "audio": "🎵"
    }
    
    emoji = emoji_map.get(content_type, "📎")
    
    return f"""
🚀 *Новое анонимное сообщение* {emoji}

🆔 ID отправителя: `{user_id}`

{content if content_type == "text" else f"📎 Тип вложения: {content_type}"}
"""

# Обработчик всех типов сообщений от пользователя
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Проверка бана
    if is_user_banned(user_id):
        await update.message.reply_text("🚫 Вы забанены и не можете отправлять сообщения.")
        return

    # Определяем тип контента
    if update.message.text:
        content = update.message.text
        content_type = "text"
    elif update.message.photo:
        content = "Фото"
        content_type = "photo"
    elif update.message.document:
        content = f"Документ: {update.message.document.file_name}"
        content_type = "document"
    elif update.message.sticker:
        content = "Стикер"
        content_type = "sticker"
    elif update.message.voice:
        content = "Голосовое сообщение"
        content_type = "voice"
    elif update.message.video:
        content = "Видео"
        content_type = "video"
    elif update.message.audio:
        content = f"Аудио: {update.message.audio.title or 'Без названия'}"
        content_type = "audio"
    else:
        content = "Вложение"
        content_type = "other"

    # Отправляем сообщение админу
    if content_type == "text":
        sent_message = await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=format_admin_message(user_id, content, content_type),
            parse_mode="Markdown"
        )
    elif update.message.photo:
        # Отправляем фото с подписью
        photo = update.message.photo[-1]  # Берем фото максимального размера
        caption = format_admin_message(user_id, content, content_type)
        sent_message = await context.bot.send_photo(
            chat_id=ADMIN_USER_ID,
            photo=photo.file_id,
            caption=caption,
            parse_mode="Markdown"
        )
    elif update.message.document:
        caption = format_admin_message(user_id, content, content_type)
        sent_message = await context.bot.send_document(
            chat_id=ADMIN_USER_ID,
            document=update.message.document.file_id,
            caption=caption,
            parse_mode="Markdown"
        )
    elif update.message.sticker:
        # Отправляем стикер отдельно
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=format_admin_message(user_id, content, content_type),
            parse_mode="Markdown"
        )
        sent_message = await context.bot.send_sticker(
            chat_id=ADMIN_USER_ID,
            sticker=update.message.sticker.file_id
        )
    elif update.message.voice:
        caption = format_admin_message(user_id, content, content_type)
        sent_message = await context.bot.send_voice(
            chat_id=ADMIN_USER_ID,
            voice=update.message.voice.file_id,
            caption=caption,
            parse_mode="Markdown"
        )
    elif update.message.video:
        caption = format_admin_message(user_id, content, content_type)
        sent_message = await context.bot.send_video(
            chat_id=ADMIN_USER_ID,
            video=update.message.video.file_id,
            caption=caption,
            parse_mode="Markdown"
        )
    elif update.message.audio:
        caption = format_admin_message(user_id, content, content_type)
        sent_message = await context.bot.send_audio(
            chat_id=ADMIN_USER_ID,
            audio=update.message.audio.file_id,
            caption=caption,
            parse_mode="Markdown"
        )
    else:
        # Для других типов
        sent_message = await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=format_admin_message(user_id, content, content_type),
            parse_mode="Markdown"
        )

    # Сохраняем связь в базе данных
    save_message_link(sent_message.message_id, user_id)

    # Подтверждение пользователю
    await update.message.reply_text("🌠 Твое сообщение отправлено в космос анонимно!")

# Обработчик ответов от админа
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
        
    if update.message.reply_to_message is None:
        return  # Это не ответ

    original_message_id = update.message.reply_to_message.message_id
    user_id = get_user_id(original_message_id)

    if not user_id:
        return  # Не наше сообщение

    # Отправляем ответ пользователю
    try:
        # Отправляем тот же тип контента, что и админ
        if update.message.text:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📬 *Ответ из космоса:*\n\n{update.message.text}",
                parse_mode="Markdown"
            )
        elif update.message.photo:
            photo = update.message.photo[-1]
            await context.bot.send_photo(
                chat_id=user_id,
                photo=photo.file_id,
                caption=f"📬 *Ответ из космоса:*" if update.message.caption is None else f"📬 *Ответ из космоса:*\n\n{update.message.caption}",
                parse_mode="Markdown"
            )
        elif update.message.document:
            await context.bot.send_document(
                chat_id=user_id,
                document=update.message.document.file_id,
                caption=f"📬 *Ответ из космоса:*" if update.message.caption is None else f"📬 *Ответ из космоса:*\n\n{update.message.caption}",
                parse_mode="Markdown"
            )
        elif update.message.sticker:
            await context.bot.send_sticker(
                chat_id=user_id,
                sticker=update.message.sticker.file_id
            )
        elif update.message.voice:
            await context.bot.send_voice(
                chat_id=user_id,
                voice=update.message.voice.file_id,
                caption=f"📬 *Ответ из космоса:*" if update.message.caption is None else f"📬 *Ответ из космоса:*\n\n{update.message.caption}",
                parse_mode="Markdown"
            )
        elif update.message.video:
            await context.bot.send_video(
                chat_id=user_id,
                video=update.message.video.file_id,
                caption=f"📬 *Ответ из космоса:*" if update.message.caption is None else f"📬 *Ответ из космоса:*\n\n{update.message.caption}",
                parse_mode="Markdown"
            )
        elif update.message.audio:
            await context.bot.send_audio(
                chat_id=user_id,
                audio=update.message.audio.file_id,
                caption=f"📬 *Ответ из космоса:*" if update.message.caption is None else f"📬 *Ответ из космоса:*\n\n{update.message.caption}",
                parse_mode="Markdown"
            )

        await update.message.reply_text("✅ Ответ отправлен пользователю.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка отправки: {e}")

# Основная функция
def main():
    init_db()  # Инициализируем базу данных при запуске

    app = Application.builder().token(BOT_TOKEN).build()

    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("myid", get_my_id))
    
    # Обработчики сообщений - ИСПРАВЛЕННЫЕ ФИЛЬТРЫ
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.ATTACHMENT | filters.Sticker.ALL | 
         filters.VOICE | filters.VIDEO | filters.AUDIO) & 
        ~filters.COMMAND & filters.ChatType.PRIVATE, 
        handle_user_message
    ))
    
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.ATTACHMENT | filters.Sticker.ALL | 
         filters.VOICE | filters.VIDEO | filters.AUDIO) & 
        filters.REPLY, 
        handle_admin_reply
    ))

    print("🚀 Анонимный космический бот запущен! Поддерживает фото, медиа, стикеры и бан.")
    app.run_polling()

if __name__ == "__main__":
    main()
