# === Установка необходимых библиотек ===
# pip install python-telegram-bot==20.3

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# === Настройки ===
BOT_TOKEN = "7659801527:AAEVQxwPFm6HBLFFi0SoEpjdpkunolyuAro"
ADMIN_IDS = [5445206649]
GROUPS_FILE = "groups.txt"
awaiting_admin_action = {}
ping_history = {}  # глобальное хранилище времени ответов по группам

# === Работа с группами ===
def load_groups():
    if not os.path.exists(GROUPS_FILE):
        open(GROUPS_FILE, "w", encoding="utf-8").close()
        return []
    with open(GROUPS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def save_groups(groups):
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(groups))

def add_group(chat_id, title):
    if not os.path.exists(GROUPS_FILE):
        open(GROUPS_FILE, "w", encoding="utf-8").close()
    groups = load_groups()
    entry = f"{chat_id} ({title})"
    if all(str(chat_id) not in g for g in groups):
        groups.append(entry)
        save_groups(groups)
        print(f"✅ Добавлена группа: {entry}")

# === Главное меню ===
async def show_main_menu(chat_id, context):
    keyboard = [
        [InlineKeyboardButton("📋 Projects", callback_data="list_projects")],
        [InlineKeyboardButton("ℹ️ Info", callback_data="info")],
        [InlineKeyboardButton("👥 Admins", callback_data="admin_panel")],
        [InlineKeyboardButton("❌ Exit", callback_data="exit")]
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text="Привет, я твой персональный помощник в работе с B2B iOS-разработчиками, выбери опцию для продолжения работы, но помни, пока ты думаешь - конкуренты делают 🙂",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update.effective_chat.id, context)

# === Обработка callback-кнопок ===
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "main_menu":
        await show_main_menu(query.message.chat_id, context)

    elif data == "list_projects":
        groups = load_groups()
        text = "Список групп:\n" + ("\n".join(groups) if groups else "Нет групп.")
        keyboard = [
            [InlineKeyboardButton("📢 Пинг по проекту", callback_data="ping_all")],
            [InlineKeyboardButton("📊 Отчёт по пингу", callback_data="ping_report")],
            [InlineKeyboardButton("🔁 Обновить список", callback_data="refresh_groups")],
            [InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "refresh_groups":
        groups = load_groups()
        text = "🔄 Список актуализирован:\n" + ("\n".join(groups) if groups else "Нет групп.")
        keyboard = [
            [InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "info":
        text = (
            "📘 *Инструкция по использованию бота*\n\n"
            "👨‍💻 *О боте:*\n"
            "Этот бот помогает управлять проектами в сфере *B2B iOS-разработки*:\n"
            "• отслеживает статус проектов\n"
            "• рассылает напоминания в группы\n"
            "• управляет правами доступа\n\n"
            
            "📥 *Добавление проекта:*\n"
            "1. Добавьте бота в Telegram-группу, где ведётся обсуждение проекта\n"
            "2. В появившемся окне Telegram включите только переключатель *Администратор* и отключите все остальные разрешения\n"
            "3. Отправьте любое сообщение в группу, чтобы бот зарегистрировал её как проект\n\n"

            "🛠 *Возможности:*\n"
            "• Просмотр списка всех проектов\n"
            "• Массовая и выборочная рассылка статуса\n"
            "• Автоматическое удаление проекта при удалении бота из группы\n\n"
            
            "👥 *Администраторы:*\n"
            "Только админы могут управлять проектами, запускать пинг и управлять другими администраторами.\n"
            "*Список администраторов:*\n" +
            "\n".join([f"• `{i}`" for i in ADMIN_IDS])
        )
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]),
            parse_mode="Markdown"
        )

    elif data == "admin_panel":
        keyboard = [
            [InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin")],
            [InlineKeyboardButton("➖ Удалить админа", callback_data="remove_admin")],
            [InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]
        ]
        await query.message.edit_text("Настройки администратора:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "add_admin":
        awaiting_admin_action[user_id] = "add"
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]]
        await query.message.edit_text("Введите ID пользователя для добавления в админы:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "remove_admin":
        awaiting_admin_action[user_id] = "remove"
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]]
        await query.message.edit_text("Введите ID пользователя для удаления из админов:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "ping_all":
        groups = load_groups()
        if not groups:
            await query.message.edit_text("❗ Нет групп для рассылки.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]))
            return

        project_list = "\n".join([f"{idx+1}. {entry.split(' ', 1)[-1]}" for idx, entry in enumerate(groups)])

        control_buttons = [
            [InlineKeyboardButton("📤 Пинг всех", callback_data="ping_all_now")],
            [InlineKeyboardButton("🎯 Выборочный пинг", callback_data="ping_select_mode")],
            [InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]
        ]

        keyboard = control_buttons
        await query.message.edit_text(f"📋 Список проектов:\n\n{project_list}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "ping_all_now":
        groups = load_groups()
        success, failed = 0, 0
        for entry in groups:
            group_id = int(entry.split()[0])
            try:
                await context.bot.send_message(
                    group_id,
                    "👋 Привет! Как продвигается работа над проектом?\n\n⏳ Напиши коротко о текущем прогрессе.\n\n📩 Пожалуйста, ответьте на это сообщение через функцию «Ответить», чтобы зафиксировать текущий статус проекта."
                )
                ping_history[group_id] = []
                success += 1
            except Exception as e:
                print(f"Ошибка рассылки в {group_id}: {e}")
                failed += 1

        await query.message.edit_text(
            f"📢 Рассылка завершена!\n✅ Успешно: {success}\n❌ Ошибки: {failed}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]])
        )

    elif data == "ping_select_mode":
        groups = load_groups()
        if not groups:
            await query.message.edit_text("❗ Нет доступных групп.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="ping_all")]]))
            return

        text = "📋 Список доступных групп:\n\n"
        text += "\n".join([f"{idx+1}. {entry.split(' ', 1)[-1]}" for idx, entry in enumerate(groups)])
        text += "\n\n✏️ Введите номера групп через запятую (например: 1,3,5)"

        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="ping_all")]]))
        context.user_data["awaiting_group_selection"] = True

    elif data.startswith("ping_one_"):
        idx = int(data.split("_")[-1])
        groups = load_groups()
        if idx >= len(groups):
            await query.message.edit_text("⚠️ Группа не найдена.")
            return
        group_id = int(groups[idx].split()[0])
        try:
            await context.bot.send_message(
                group_id,
                "👋 Привет! Как продвигается работа над проектом?\n\n⏳ Напиши коротко о текущем прогрессе.\n\n📩 Пожалуйста, ответьте на это сообщение через функцию «Ответить», чтобы зафиксировать текущий статус проекта."
            )
            await query.message.edit_text(f"✅ Пинг отправлен в {groups[idx]}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="ping_select_mode")]]))
        except Exception as e:
            await query.message.edit_text(f"❌ Ошибка при отправке: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="ping_select_mode")]]))

    elif data == "exit":
        await query.message.delete()

    elif data == "ping_report":
        keyboard = [
            [InlineKeyboardButton("🕐 За 1 час", callback_data="report_1")],
            [InlineKeyboardButton("🕓 За 4 часа", callback_data="report_4")],
            [InlineKeyboardButton("🕛 За 24 часа", callback_data="report_24")],
            [InlineKeyboardButton("◀️ Назад", callback_data="list_projects")]
        ]
        await query.message.edit_text("Выберите период для анализа активности:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("report_"):
        period = int(data.split("_")[1])
        groups = load_groups()
        now = update.effective_message.date.timestamp()
        results = []

        for entry in groups:
            gid = int(entry.split()[0])
            history = ping_history.get(gid, [])
            recent = [msg_time for msg_time in history if now - msg_time <= period * 3600]
            status = "✅" if recent else "❌"
            results.append(f"{status} {entry}")

        text = "📊 Отчёт по активности:\n\n" + "\n".join(results)
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="ping_report")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# === Обработка обычных сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if chat.type in ["group", "supergroup"]:
        add_group(chat.id, chat.title or "Без названия")
        if update.message.reply_to_message and update.message.reply_to_message.from_user.id == (await context.bot.get_me()).id:
            ts = update.message.date.timestamp()
            ping_history.setdefault(chat.id, []).append(ts)

    if context.user_data.get("awaiting_group_selection"):
        context.user_data["awaiting_group_selection"] = False
        groups = load_groups()
        try:
            selected_indices = [int(i.strip()) - 1 for i in text.split(",")]
            success, failed = 0, 0
            for idx in selected_indices:
                if 0 <= idx < len(groups):
                    group_id = int(groups[idx].split()[0])
                    try:
                        await context.bot.send_message(
                            group_id,
                            "👋 Привет! Как продвигается работа над проектом?\n\n⏳ Напиши коротко о текущем прогрессе.\n\n📩 Пожалуйста, ответьте на это сообщение через функцию «Ответить», чтобы зафиксировать текущий статус проекта."
                        )
                        context.chat_data[f"ping_history_{group_id}"] = []
                        success += 1
                    except Exception as e:
                        print(f"Ошибка при рассылке в {group_id}: {e}")
                        failed += 1
            await update.message.reply_text(
                f"📢 Рассылка завершена!\n✅ Успешно: {success}\n❌ Ошибки: {failed}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="list_projects")]
                ])
            )
        except:
            await update.message.reply_text("⚠️ Ошибка обработки ввода. Введите номера через запятую, например: 1,2")
        return

    if user_id in awaiting_admin_action:
        action = awaiting_admin_action.pop(user_id)
        try:
            new_id = int(text)
            if action == "add":
                if new_id not in ADMIN_IDS:
                    ADMIN_IDS.append(new_id)
                    await update.message.reply_text("✅ Админ добавлен!")
                else:
                    await update.message.reply_text("ℹ️ Уже в списке админов.")
            elif action == "remove":
                if new_id in ADMIN_IDS:
                    ADMIN_IDS.remove(new_id)
                    await update.message.reply_text("❌ Админ удалён!")
                else:
                    await update.message.reply_text("⚠️ Такого админа нет.")
        except:
            await update.message.reply_text("❗ Введите корректный числовой ID.")

# === Запуск бота ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

from telegram.ext import ChatMemberHandler

def remove_group(chat_id):
    groups = load_groups()
    updated = [g for g in groups if not g.startswith(str(chat_id))]
    save_groups(updated)

async def handle_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = update.my_chat_member.new_chat_member.status
    chat_id = update.effective_chat.id
    if status in ["left", "kicked"]:
        remove_group(chat_id)
        print(f"🗑 Удалена группа {chat_id} — бот удалён")

app.add_handler(ChatMemberHandler(handle_membership, chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER))

print("🤖 Бот запущен!")
app.run_polling()