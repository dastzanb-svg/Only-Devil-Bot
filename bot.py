import secrets
import html
from typing import Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import (
    BOT_TOKEN,
    OWNER_ID,
    VIDEO_DELETE_SECONDS,
)

from database import db


# ============================================================
# BASIC CONFIGURATION
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is not set. "
        "Set the BOT_TOKEN environment variable before running the bot."
    )


# Temporary states for admin actions
USER_STATES = {}


# ============================================================
# ADMIN HELPERS
# ============================================================

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


def is_admin(user_id: int) -> bool:
    return is_owner(user_id) or db.is_admin(user_id)


def admin_only(user_id: int) -> bool:
    return is_admin(user_id)


# ============================================================
# CODE GENERATORS
# ============================================================

def generate_video_code() -> str:
    while True:
        code = secrets.token_urlsafe(8).replace("-", "").replace("_", "")

        if not db.get_video_by_code(code):
            return code


def generate_topic_code() -> str:
    while True:
        code = secrets.token_urlsafe(8).replace("-", "").replace("_", "")

        if not db.get_topic_by_code(code):
            return code


# ============================================================
# SETTINGS
# ============================================================

def main_channel_id() -> Optional[str]:
    value = db.get_setting("main_channel_id")
    return value if value else None


def main_channel_username() -> Optional[str]:
    value = db.get_setting("main_channel_username")
    return value if value else None


# ============================================================
# ADMIN MENU
# ============================================================

def admin_menu_keyboard() -> InlineKeyboardMarkup:

    keyboard = [
        [
            InlineKeyboardButton(
                "🎬 افزودن ویدیو",
                callback_data="admin_add_video",
            ),
            InlineKeyboardButton(
                "📚 افزودن موضوع",
                callback_data="admin_add_topic",
            ),
        ],
        [
            InlineKeyboardButton(
                "🎞 ویدیوها",
                callback_data="admin_videos",
            ),
            InlineKeyboardButton(
                "📚 موضوع‌ها",
                callback_data="admin_topics",
            ),
        ],
        [
            InlineKeyboardButton(
                "📢 کانال‌های تبلیغاتی",
                callback_data="admin_ads",
            ),
            InlineKeyboardButton(
                "👥 کاربران",
                callback_data="admin_users",
            ),
        ],
        [
            InlineKeyboardButton(
                "👑 مدیریت ادمین‌ها",
                callback_data="admin_admins",
            ),
            InlineKeyboardButton(
                "⚙️ تنظیمات",
                callback_data="admin_settings",
            ),
        ],
        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="admin_stats",
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


async def send_admin_panel(update: Update):

    user = update.effective_user

    if not user or not is_admin(user.id):
        return

    text = (
        "🎛 <b>پنل مدیریت OnlyDevilBot</b>\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:"
    )

    if update.callback_query:

        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )

    elif update.message:

        await update.message.reply_text(
            text=text,
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    if not user:
        return

    # --------------------------------------------------------
    # REGISTER USER
    # --------------------------------------------------------

    db.add_user(
        user_id=user.id,
        first_name=user.first_name,
        username=user.username,
    )

    # --------------------------------------------------------
    # NO DEEP LINK
    # --------------------------------------------------------

    if not context.args:

        if is_admin(user.id):

            await update.message.reply_text(
                "🤖 <b>OnlyDevilBot</b>\n\n"
                "به بات خوش آمدید.\n\n"
                "👑 شما به پنل مدیریت دسترسی دارید.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "🎛 پنل مدیریت",
                            callback_data="open_admin",
                        )
                    ]
                ]),
                parse_mode="HTML",
            )

            return

        await update.message.reply_text(
            "🤖 <b>OnlyDevilBot</b>\n\n"
            "برای دریافت آموزش، از لینک اختصاصی همان موضوع وارد بات شوید.",
            parse_mode="HTML",
        )

        return

    # --------------------------------------------------------
    # DEEP LINK
    # --------------------------------------------------------

    argument = context.args[0]

    # ========================================================
    # TOPIC
    # ========================================================

    if argument.startswith("t_"):

        code = argument[2:]

        topic = db.get_topic_by_code(code)

        if not topic:

            await update.message.reply_text(
                "❌ این لینک موضوع معتبر نیست یا موضوع غیرفعال شده است."
            )

            return

        await check_required_channels_and_send_topic(
            update=update,
            context=context,
            topic=topic,
        )

        return

    # ========================================================
    # VIDEO
    # ========================================================

    if argument.startswith("v_"):

        code = argument[2:]

        video = db.get_video_by_code(code)

        if not video:

            await update.message.reply_text(
                "❌ این لینک ویدیو معتبر نیست یا ویدیو غیرفعال شده است."
            )

            return

        await check_required_channels_and_send_video(
            update=update,
            context=context,
            video=video,
        )

        return

    # --------------------------------------------------------
    # OLD / DIRECT CODE
    # --------------------------------------------------------

    video = db.get_video_by_code(argument)

    if video:

        await check_required_channels_and_send_video(
            update=update,
            context=context,
            video=video,
        )

        return

    topic = db.get_topic_by_code(argument)

    if topic:

        await check_required_channels_and_send_topic(
            update=update,
            context=context,
            topic=topic,
        )

        return

    await update.message.reply_text(
        "❌ لینک واردشده معتبر نیست."
    )


# ============================================================
# MEMBERSHIP CHECK
# ============================================================

async def check_user_membership(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    channel_id: str,
) -> bool:

    try:

        member = await context.bot.get_chat_member(
            chat_id=channel_id,
            user_id=user_id,
        )

        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )

    except Exception as error:

        print(
            f"Membership check error "
            f"(user={user_id}, channel={channel_id}): {error}"
        )

        return False


async def get_required_channels():

    channels = []

    # --------------------------------------------------------
    # MAIN CHANNEL
    # --------------------------------------------------------

    main_id = main_channel_id()

    if main_id:

        channels.append({
            "channel_id": main_id,
            "title": "کانال اصلی",
            "username": main_channel_username(),
            "invite_link": None,
            "is_main": True,
        })

    # --------------------------------------------------------
    # AD CHANNELS
    # --------------------------------------------------------

    ad_channels = db.get_advertising_channels()

    for channel in ad_channels:

        channels.append({
            "channel_id": channel["channel_id"],
            "title": channel["channel_name"] or "کانال تبلیغاتی",
            "username": channel["channel_username"],
            "invite_link": channel["channel_link"],
            "is_main": False,
        })

    return channels


# ============================================================
# BUILD CHANNEL LINK
# ============================================================

def build_channel_link(channel):

    username = channel.get("username")
    invite_link = channel.get("invite_link")

    if username:

        if username.startswith("https://t.me/"):
            return username

        if username.startswith("@"):
            return f"https://t.me/{username[1:]}"

        return f"https://t.me/{username}"

    return invite_link


# ============================================================
# VIDEO MEMBERSHIP CHECK
# ============================================================

async def check_required_channels_and_send_video(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    video,
):

    user = update.effective_user

    if not user:
        return

    channels = await get_required_channels()

    not_joined = []

    for channel in channels:

        joined = await check_user_membership(
            context=context,
            user_id=user.id,
            channel_id=channel["channel_id"],
        )

        if not joined:
            not_joined.append(channel)

    if not_joined:

        keyboard = []

        for channel in not_joined:

            link = build_channel_link(channel)

            if link:

                keyboard.append([
                    InlineKeyboardButton(
                        f"📢 عضویت در {channel['title']}",
                        url=link,
                    )
                ])

        keyboard.append([
            InlineKeyboardButton(
                "✅ بررسی عضویت",
                callback_data=f"check_video_{video['unique_code']}",
            )
        ])

        text = (
            "🔐 <b>عضویت لازم است</b>\n\n"
            "برای دریافت این ویدیو، ابتدا در کانال‌های زیر عضو شوید:\n\n"
        )

        for channel in not_joined:

            text += (
                f"• {html.escape(channel['title'])}\n"
            )

        text += (
            "\nبعد از عضویت، روی «بررسی عضویت» بزنید."
        )

        await update.effective_message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )

        return

    await deliver_video(
        update=update,
        context=context,
        video=video,
    )


# ============================================================
# TOPIC MEMBERSHIP CHECK
# ============================================================

async def check_required_channels_and_send_topic(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    topic,
):

    user = update.effective_user

    if not user:
        return

    channels = await get_required_channels()

    not_joined = []

    for channel in channels:

        joined = await check_user_membership(
            context=context,
            user_id=user.id,
            channel_id=channel["channel_id"],
        )

        if not joined:
            not_joined.append(channel)

    if not_joined:

        keyboard = []

        for channel in not_joined:

            link = build_channel_link(channel)

            if link:

                keyboard.append([
                    InlineKeyboardButton(
                        f"📢 عضویت در {channel['title']}",
                        url=link,
                    )
                ])

        keyboard.append([
            InlineKeyboardButton(
                "✅ بررسی عضویت",
                callback_data=f"check_topic_{topic['unique_code']}",
            )
        ])

        text = (
            "🔐 <b>عضویت لازم است</b>\n\n"
            "برای دریافت این آموزش، ابتدا در کانال‌های زیر عضو شوید:\n\n"
        )

        for channel in not_joined:

            text += (
                f"• {html.escape(channel['title'])}\n"
            )

        text += (
            "\nبعد از عضویت، روی «بررسی عضویت» بزنید."
        )

        await update.effective_message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )

        return

    await deliver_topic(
        update=update,
        context=context,
        topic=topic,
    )


# ============================================================
# SEND SINGLE VIDEO
# ============================================================

async def deliver_video(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    video,
):

    user = update.effective_user

    if not user:
        return

    try:

        title = html.escape(
            video["title"] or "ویدیو"
        )

        description = html.escape(
            video["description"] or ""
        )

        caption = (
            f"🎬 <b>{title}</b>\n\n"
            f"{description}\n\n"
            f"⏱ این ویدیو تا "
            f"{VIDEO_DELETE_SECONDS} ثانیه دیگر "
            f"به‌صورت خودکار حذف می‌شود."
        )

        sent = await context.bot.send_video(
            chat_id=user.id,
            video=video["telegram_file_id"],
            caption=caption,
            parse_mode="HTML",
        )

        db.increment_video_downloads(
            video["id"]
        )

        user_row = db.get_user(user.id)

        if user_row:

            delivery_id = db.add_delivery(
                user_id=user_row["id"],
                video_id=video["id"],
                telegram_message_id=sent.message_id,
            )

            context.job_queue.run_once(
                delete_video_message,
                when=VIDEO_DELETE_SECONDS,
                data={
                    "chat_id": sent.chat_id,
                    "message_id": sent.message_id,
                    "delivery_id": delivery_id,
                },
            )

    except Exception as error:

        print(
            f"Error sending video: {error}"
        )

        try:

            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    "❌ هنگام ارسال ویدیو مشکلی پیش آمد.\n\n"
                    "لطفاً دوباره تلاش کنید."
                ),
            )

        except Exception as send_error:

            print(
                f"Error sending error message: {send_error}"
            )


# ============================================================
# SEND TOPIC
# ============================================================

async def deliver_topic(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    topic,
):

    user = update.effective_user

    if not user:
        return

    try:

        topic_videos = db.get_topic_videos(
            topic["id"]
        )

        if not topic_videos:

            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    "❌ این موضوع در حال حاضر "
                    "هیچ ویدیویی ندارد."
                ),
            )

            return

        # ----------------------------------------------------
        # TOPIC HEADER
        # ----------------------------------------------------

        topic_title = html.escape(
            topic["title"] or "آموزش"
        )

        topic_description = html.escape(
            topic["description"] or ""
        )

        total = len(topic_videos)

        header = (
            f"📚 <b>{topic_title}</b>\n\n"
            f"{topic_description}\n\n"
            f"🎬 تعداد قسمت‌ها: <b>{total}</b>\n\n"
            "⏳ ویدیوها به ترتیب برای شما ارسال می‌شوند."
        )

        await context.bot.send_message(
            chat_id=user.id,
            text=header,
            parse_mode="HTML",
        )

        # Count topic request
        db.increment_topic_downloads(
            topic["id"]
        )

        # ----------------------------------------------------
        # SEND VIDEOS ONE BY ONE
        # ----------------------------------------------------

        for index, video in enumerate(
            topic_videos,
            start=1,
        ):

            try:

                title = html.escape(
                    video["title"] or f"قسمت {index}"
                )

                description = html.escape(
                    video["description"] or ""
                )

                caption = (
                    f"📚 <b>{topic_title}</b>\n"
                    f"🎬 <b>قسمت {index} از {total}</b>\n\n"
                    f"<b>{title}</b>\n\n"
                    f"{description}\n\n"
                    f"⏱ این ویدیو تا "
                    f"{VIDEO_DELETE_SECONDS} ثانیه دیگر "
                    f"به‌صورت خودکار حذف می‌شود."
                )

                sent = await context.bot.send_video(
                    chat_id=user.id,
                    video=video["telegram_file_id"],
                    caption=caption,
                    parse_mode="HTML",
                )

                db.increment_video_downloads(
                    video["id"]
                )

                user_row = db.get_user(user.id)

                if user_row:

                    delivery_id = db.add_delivery(
                        user_id=user_row["id"],
                        video_id=video["id"],
                        telegram_message_id=sent.message_id,
                    )

                    context.job_queue.run_once(
                        delete_video_message,
                        when=VIDEO_DELETE_SECONDS,
                        data={
                            "chat_id": sent.chat_id,
                            "message_id": sent.message_id,
                            "delivery_id": delivery_id,
                        },
                    )

            except Exception as error:

                print(
                    f"Error sending topic video "
                    f"{index}: {error}"
                )

                continue

    except Exception as error:

        print(
            f"Error delivering topic: {error}"
        )

        try:

            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    "❌ هنگام ارسال این آموزش مشکلی پیش آمد."
                ),
            )

        except Exception:
            pass


# ============================================================
# DELETE VIDEO MESSAGE
# ============================================================

async def delete_video_message(
    context: ContextTypes.DEFAULT_TYPE
):

    data = context.job.data

    try:

        await context.bot.delete_message(
            chat_id=data["chat_id"],
            message_id=data["message_id"],
        )

    except Exception as error:

        print(
            f"Error deleting video message: {error}"
        )

    finally:

        try:

            db.mark_delivery_deleted(
                data["delivery_id"]
            )

        except Exception:
            pass


# ============================================================
# ADMIN COMMAND
# ============================================================

async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    if not user or not is_admin(user.id):

        await update.message.reply_text(
            "⛔ شما اجازه دسترسی به پنل مدیریت را ندارید."
        )

        return

    await send_admin_panel(update)


# ============================================================
# CALLBACK ROUTER
# ============================================================

async def callbacks(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    data = query.data

    # ========================================================
    # OPEN ADMIN
    # ========================================================

    if data == "open_admin":

        if not is_admin(user.id):

            await query.edit_message_text(
                "⛔ دسترسی غیرمجاز."
            )

            return

        await send_admin_panel(update)

        return

    # ========================================================
    # CHECK VIDEO
    # ========================================================

    if data.startswith("check_video_"):

        code = data.replace(
            "check_video_",
            "",
            1,
        )

        video = db.get_video_by_code(code)

        if not video:

            await query.edit_message_text(
                "❌ ویدیوی موردنظر پیدا نشد."
            )

            return

        channels = await get_required_channels()

        not_joined = []

        for channel in channels:

            joined = await check_user_membership(
                context=context,
                user_id=user.id,
                channel_id=channel["channel_id"],
            )

            if not joined:
                not_joined.append(channel)

        if not_joined:

            await query.answer(
                "❌ هنوز عضویت شما در همه کانال‌ها تأیید نشده است.",
                show_alert=True,
            )

            return

        await query.edit_message_text(
            "✅ عضویت شما تأیید شد.\n\n"
            "🎬 در حال ارسال ویدیو..."
        )

        await deliver_video(
            update=update,
            context=context,
            video=video,
        )

        return

    # ========================================================
    # CHECK TOPIC
    # ========================================================

    if data.startswith("check_topic_"):

        code = data.replace(
            "check_topic_",
            "",
            1,
        )

        topic = db.get_topic_by_code(code)

        if not topic:

            await query.edit_message_text(
                "❌ موضوع موردنظر پیدا نشد."
            )

            return

        channels = await get_required_channels()

        not_joined = []

        for channel in channels:

            joined = await check_user_membership(
                context=context,
                user_id=user.id,
                channel_id=channel["channel_id"],
            )

            if not joined:
                not_joined.append(channel)

        if not_joined:

            await query.answer(
                "❌ هنوز عضویت شما در همه کانال‌ها تأیید نشده است.",
                show_alert=True,
            )

            return

        await query.edit_message_text(
            "✅ عضویت شما تأیید شد.\n\n"
            "📚 در حال ارسال آموزش..."
        )

        await deliver_topic(
            update=update,
            context=context,
            topic=topic,
        )

        return

    # ========================================================
    # ADMIN ACCESS
    # ========================================================

    if not is_admin(user.id):

        await query.edit_message_text(
            "⛔ دسترسی غیرمجاز."
        )

        return

    # ========================================================
    # BACK
    # ========================================================

    if data == "admin_back":

        await send_admin_panel(update)

        return

    # ========================================================
    # ADD VIDEO
    # ========================================================

    if data == "admin_add_video":

        USER_STATES[user.id] = {
            "state": "waiting_video_title",
        }

        await query.edit_message_text(
            "🎬 <b>افزودن ویدیو</b>\n\n"
            "ابتدا عنوان ویدیو را ارسال کنید:",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # ADD TOPIC
    # ========================================================

    if data == "admin_add_topic":

        USER_STATES[user.id] = {
            "state": "topic_title",
            "videos": [],
        }

        await query.edit_message_text(
            "📚 <b>ساخت موضوع جدید</b>\n\n"
            "ابتدا <b>عنوان موضوع</b> را ارسال کنید.",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # VIDEOS
    # ========================================================

    if data == "admin_videos":

        await show_videos(update)

        return

    # ========================================================
    # TOPICS
    # ========================================================

    if data == "admin_topics":

        await show_topics(update)

        return

    # ========================================================
    # ADS
    # ========================================================

    if data == "admin_ads":

        await show_ads_menu(update)

        return

    # ========================================================
    # USERS
    # ========================================================

    if data == "admin_users":

        count = db.count_users()

        await query.edit_message_text(
            "👥 <b>کاربران</b>\n\n"
            f"تعداد کاربران: <b>{count}</b>",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="admin_back",
                    )
                ]
            ]),
            parse_mode="HTML",
        )

        return

    # ========================================================
    # ADMINS
    # ========================================================

    if data == "admin_admins":

        await show_admins(update)

        return

    # ========================================================
    # SETTINGS
    # ========================================================

    if data == "admin_settings":

        await show_settings(update)

        return

    # ========================================================
    # STATS
    # ========================================================

    if data == "admin_stats":

        stats = db.get_statistics()

        await query.edit_message_text(
            "📊 <b>آمار OnlyDevilBot</b>\n\n"
            f"👥 کاربران: <b>{stats['users']}</b>\n"
            f"🎬 ویدیوها: <b>{stats['videos']}</b>\n"
            f"📚 موضوع‌ها: <b>{stats['topics']}</b>\n\n"
            f"📥 دریافت ویدیوها: "
            f"<b>{stats['video_downloads']}</b>\n"
            f"📚 دریافت موضوع‌ها: "
            f"<b>{stats['topic_downloads']}</b>",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="admin_back",
                    )
                ]
            ]),
            parse_mode="HTML",
        )

        return

    # ========================================================
    # ADD ADMIN
    # ========================================================

    if data == "add_admin":

        if not is_owner(user.id):

            await query.answer(
                "⛔ فقط Owner می‌تواند ادمین اضافه کند.",
                show_alert=True,
            )

            return

        USER_STATES[user.id] = {
            "state": "waiting_admin_id",
        }

        await query.edit_message_text(
            "👑 <b>افزودن ادمین</b>\n\n"
            "ID عددی کاربر را ارسال کنید:",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # REMOVE ADMIN
    # ========================================================

    if data.startswith("remove_admin_"):

        if not is_owner(user.id):

            await query.answer(
                "⛔ فقط Owner می‌تواند ادمین حذف کند.",
                show_alert=True,
            )

            return

        try:

            admin_id = int(
                data.replace(
                    "remove_admin_",
                    "",
                    1,
                )
            )

        except ValueError:

            await query.answer(
                "❌ ID نامعتبر است.",
                show_alert=True,
            )

            return

        if admin_id == OWNER_ID:

            await query.answer(
                "⛔ Owner قابل حذف نیست.",
                show_alert=True,
            )

            return

        db.remove_admin(admin_id)

        await query.answer(
            "✅ ادمین حذف شد."
        )

        await show_admins(update)

        return

    # ========================================================
    # ADD AD CHANNEL
    # ========================================================

    if data == "add_ad_channel":

        USER_STATES[user.id] = {
            "state": "waiting_ad_channel",
        }

        await query.edit_message_text(
            "📢 <b>افزودن کانال تبلیغاتی</b>\n\n"
            "آیدی یا username کانال را ارسال کنید.\n\n"
            "مثال:\n"
            "<code>@ExampleChannel</code>",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # REMOVE AD CHANNEL
    # ========================================================

    if data.startswith("remove_ad_"):

        try:

            channel_db_id = int(
                data.replace(
                    "remove_ad_",
                    "",
                    1,
                )
            )

        except ValueError:

            await query.answer(
                "❌ شناسه نامعتبر.",
                show_alert=True,
            )

            return

        db.deactivate_advertising_channel(
            channel_db_id
        )

        await query.answer(
            "✅ کانال غیرفعال شد."
        )

        await show_ads_menu(update)

        return

    # ========================================================
    # SET MAIN CHANNEL
    # ========================================================

    if data == "set_main_channel":

        USER_STATES[user.id] = {
            "state": "waiting_main_channel",
        }

        await query.edit_message_text(
            "⚙️ <b>تنظیم کانال اصلی</b>\n\n"
            "آیدی یا username کانال را ارسال کنید.\n\n"
            "مثال:\n"
            "<code>@MyChannel</code>",
            parse_mode="HTML",
        )

        return


# ============================================================
# VIDEO LIST
# ============================================================

async def show_videos(update: Update):

    query = update.callback_query

    videos = db.get_all_videos()

    if not videos:

        await query.edit_message_text(
            "🎬 هنوز هیچ ویدیویی ثبت نشده است.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "➕ افزودن ویدیو",
                        callback_data="admin_add_video",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="admin_back",
                    )
                ],
            ]),
        )

        return

    text = "🎬 <b>ویدیوها</b>\n\n"

    for video in videos[:50]:

        status = "✅" if video["is_active"] else "❌"

        text += (
            f"{status} <b>"
            f"{html.escape(video['title'])}"
            f"</b>\n"
            f"📥 دریافت: <b>{video['downloads']}</b>\n"
            f"🔗 <code>{video['unique_code']}</code>\n\n"
        )

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ افزودن ویدیو",
                callback_data="admin_add_video",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="admin_back",
            )
        ],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ============================================================
# TOPIC LIST
# ============================================================

async def show_topics(update: Update):

    query = update.callback_query

    topics = db.get_all_topics()

    if not topics:

        await query.edit_message_text(
            "📚 هنوز هیچ موضوعی ساخته نشده است.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "➕ ساخت موضوع",
                        callback_data="admin_add_topic",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="admin_back",
                    )
                ],
            ]),
        )

        return

    text = "📚 <b>موضوع‌ها</b>\n\n"

    for topic in topics[:50]:

        video_count = db.get_topic_video_count(
            topic["id"]
        )

        status = "✅" if topic["is_active"] else "❌"

        text += (
            f"{status} <b>"
            f"{html.escape(topic['title'])}"
            f"</b>\n"
            f"🎬 قسمت‌ها: <b>{video_count}</b>\n"
            f"📥 دریافت: <b>{topic['downloads']}</b>\n"
            f"🔗 کد: <code>{topic['unique_code']}</code>\n\n"
        )

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ ساخت موضوع",
                callback_data="admin_add_topic",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="admin_back",
            )
        ],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ============================================================
# AD CHANNELS
# ============================================================

async def show_ads_menu(update: Update):

    query = update.callback_query

    channels = db.get_advertising_channels()

    text = "📢 <b>کانال‌های تبلیغاتی</b>\n\n"

    if not channels:

        text += "هنوز کانال تبلیغاتی ثبت نشده است.\n"

    keyboard = []

    for channel in channels:

        text += (
            f"📢 <b>"
            f"{html.escape(channel['channel_name'] or 'بدون نام')}"
            f"</b>\n"
            f"ID: <code>{channel['channel_id']}</code>\n\n"
        )

        keyboard.append([
            InlineKeyboardButton(
                f"🗑 غیرفعال کردن "
                f"{(channel['channel_name'] or 'کانال')[:20]}",
                callback_data=f"remove_ad_{channel['id']}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "➕ افزودن کانال",
            callback_data="add_ad_channel",
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="admin_back",
        )
    ])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ============================================================
# ADMINS
# ============================================================

async def show_admins(update: Update):

    query = update.callback_query
    user = update.effective_user

    admins = db.get_admins()

    text = "👑 <b>مدیریت ادمین‌ها</b>\n\n"

    text += (
        f"👑 <code>{OWNER_ID}</code> — Owner\n"
    )

    keyboard = []

    for admin in admins:

        admin_id = admin["user_id"]

        if admin_id == OWNER_ID:
            continue

        text += (
            f"🛠 <code>{admin_id}</code>\n"
        )

        if is_owner(user.id):

            keyboard.append([
                InlineKeyboardButton(
                    f"➖ حذف {admin_id}",
                    callback_data=f"remove_admin_{admin_id}",
                )
            ])

    if is_owner(user.id):

        keyboard.append([
            InlineKeyboardButton(
                "➕ افزودن ادمین",
                callback_data="add_admin",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="admin_back",
        )
    ])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ============================================================
# SETTINGS
# ============================================================

async def show_settings(update: Update):

    query = update.callback_query

    channel_id = main_channel_id()
    username = main_channel_username()

    text = (
        "⚙️ <b>تنظیمات</b>\n\n"
        "📢 کانال اصلی:\n"
        f"<code>{channel_id or 'تنظیم نشده'}</code>\n\n"
        "🔗 Username:\n"
        f"<code>{username or 'تنظیم نشده'}</code>\n\n"
        f"⏱ زمان حذف ویدیو: "
        f"<b>{VIDEO_DELETE_SECONDS} ثانیه</b>"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "📢 تنظیم کانال اصلی",
                callback_data="set_main_channel",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="admin_back",
            )
        ],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ============================================================
# ADMIN TEXT HANDLER
# ============================================================

async def handle_admin_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    if not user or not is_admin(user.id):
        return

    state_data = USER_STATES.get(user.id)

    if not state_data:
        return

    state = state_data.get("state")

    text = (
        update.message.text.strip()
        if update.message.text
        else ""
    )

    # ========================================================
    # ADMIN ID
    # ========================================================

    if state == "waiting_admin_id":

        if not is_owner(user.id):

            USER_STATES.pop(user.id, None)
            return

        try:

            new_admin_id = int(text)

        except ValueError:

            await update.message.reply_text(
                "❌ لطفاً فقط ID عددی ارسال کنید."
            )

            return

        if new_admin_id == OWNER_ID:

            await update.message.reply_text(
                "👑 این کاربر Owner است."
            )

            USER_STATES.pop(user.id, None)

            return

        db.add_admin(new_admin_id)

        USER_STATES.pop(user.id, None)

        await update.message.reply_text(
            "✅ ادمین با موفقیت اضافه شد.",
            reply_markup=admin_menu_keyboard(),
        )

        return

    # ========================================================
    # SINGLE VIDEO TITLE
    # ========================================================

    if state == "waiting_video_title":

        if not text:

            await update.message.reply_text(
                "❌ عنوان نمی‌تواند خالی باشد."
            )

            return

        USER_STATES[user.id] = {
            "state": "waiting_video_description",
            "title": text,
        }

        await update.message.reply_text(
            "📝 توضیحات ویدیو را ارسال کنید.\n\n"
            "اگر توضیحی ندارد، بنویسید:\n"
            "<code>ندارد</code>",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # SINGLE VIDEO DESCRIPTION
    # ========================================================

    if state == "waiting_video_description":

        description = text

        if description == "ندارد":
            description = ""

        USER_STATES[user.id] = {
            "state": "waiting_video_file",
            "title": state_data["title"],
            "description": description,
        }

        await update.message.reply_text(
            "🎬 حالا فایل <b>ویدیو</b> را ارسال کنید.",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # TOPIC TITLE
    # ========================================================

    if state == "topic_title":

        if not text:

            await update.message.reply_text(
                "❌ عنوان موضوع نمی‌تواند خالی باشد."
            )

            return

        USER_STATES[user.id] = {
            "state": "topic_description",
            "topic_title": text,
            "videos": [],
        }

        await update.message.reply_text(
            "📝 توضیحات موضوع را ارسال کنید.\n\n"
            "اگر توضیحی ندارد، بنویسید:\n"
            "<code>ندارد</code>",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # TOPIC DESCRIPTION
    # ========================================================

    if state == "topic_description":

        description = text

        if description == "ندارد":
            description = ""

        USER_STATES[user.id] = {
            "state": "topic_video_title",
            "topic_title": state_data["topic_title"],
            "topic_description": description,
            "videos": [],
        }

        await update.message.reply_text(
            "🎬 <b>قسمت اول</b>\n\n"
            "عنوان ویدیوی اول را ارسال کنید.\n\n"
            "بعد از تمام کردن موضوع، "
            "برای پایان بنویسید <code>پایان</code>.",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # TOPIC VIDEO TITLE
    # ========================================================

    if state == "topic_video_title":

        if text == "پایان":

            if not state_data.get("videos"):

                await update.message.reply_text(
                    "❌ موضوع حداقل باید یک ویدیو داشته باشد."
                )

                return

            await finalize_topic(
                update=update,
                context=context,
                user_id=user.id,
            )

            return

        if not text:

            await update.message.reply_text(
                "❌ عنوان ویدیو نمی‌تواند خالی باشد."
            )

            return

        USER_STATES[user.id] = {
            **state_data,
            "state": "topic_video_description",
            "current_video_title": text,
        }

        await update.message.reply_text(
            "📝 توضیحات این ویدیو را ارسال کنید.\n\n"
            "اگر توضیحی ندارد، بنویسید:\n"
            "<code>ندارد</code>",
            parse_mode="HTML",
        )

        return

    # ========================================================
    # TOPIC VIDEO DESCRIPTION
    # ========================================================

    if state == "topic_video_description":

        description = text

        if description == "ندارد":
            description = ""

        USER_STATES[user.id] = {
            **state_data,
            "state": "topic_video_file",
            "current_video_description": description,
        }

        await update.message.reply_text(
            "🎬 حالا فایل این قسمت را ارسال کنید."
        )

        return

    # ========================================================
    # MAIN CHANNEL
    # ========================================================

    if state == "waiting_main_channel":

        try:

            chat = await context.bot.get_chat(text)

            if chat.type != "channel":

                await update.message.reply_text(
                    "❌ این شناسه مربوط به یک کانال نیست."
                )

                return

            username = chat.username

            db.set_setting(
                "main_channel_id",
                str(chat.id),
            )

            db.set_setting(
                "main_channel_username",
                f"@{username}" if username else "",
            )

            USER_STATES.pop(user.id, None)

            await update.message.reply_text(
                "✅ کانال اصلی تنظیم شد.\n\n"
                f"📢 {html.escape(chat.title)}\n"
                f"ID: <code>{chat.id}</code>",
                parse_mode="HTML",
                reply_markup=admin_menu_keyboard(),
            )

        except Exception as error:

            print(
                f"Main channel error: {error}"
            )

            await update.message.reply_text(
                "❌ نتوانستم کانال را پیدا کنم.\n\n"
                "مطمئن شوید بات داخل کانال است."
            )

        return

    # ========================================================
    # AD CHANNEL
    # ========================================================

    if state == "waiting_ad_channel":

        try:

            chat = await context.bot.get_chat(text)

            if chat.type != "channel":

                await update.message.reply_text(
                    "❌ این شناسه مربوط به یک کانال نیست."
                )

                return

            username = chat.username

            link = (
                f"https://t.me/{username}"
                if username
                else None
            )

            db.add_advertising_channel(
                channel_id=str(chat.id),
                channel_username=(
                    f"@{username}"
                    if username
                    else None
                ),
                channel_name=chat.title,
                channel_link=link,
            )

            USER_STATES.pop(user.id, None)

            await update.message.reply_text(
                "✅ کانال تبلیغاتی اضافه شد.\n\n"
                f"📢 {html.escape(chat.title)}\n"
                f"ID: <code>{chat.id}</code>",
                parse_mode="HTML",
                reply_markup=admin_menu_keyboard(),
            )

        except Exception as error:

            print(
                f"Advertising channel error: {error}"
            )

            await update.message.reply_text(
                "❌ نتوانستم کانال را پیدا کنم."
            )

        return


# ============================================================
# VIDEO FILE HANDLER
# ============================================================

async def handle_video(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    if not user or not is_admin(user.id):
        return

    state_data = USER_STATES.get(user.id)

    if not state_data:
        return

    # ========================================================
    # SINGLE VIDEO
    # ========================================================

    if state_data.get("state") == "waiting_video_file":

        if not update.message.video:

            return

        file_id = update.message.video.file_id

        code = generate_video_code()

        video_id = db.add_video(
            title=state_data["title"],
            description=state_data.get("description", ""),
            telegram_file_id=file_id,
            unique_code=code,
        )

        USER_STATES.pop(user.id, None)

        bot_info = await context.bot.get_me()

        link = (
            f"https://t.me/"
            f"{bot_info.username}"
            f"?start=v_{code}"
        )

        await update.message.reply_text(
            "🎉 <b>ویدیو با موفقیت ثبت شد!</b>\n\n"
            f"🎬 عنوان: "
            f"<b>{html.escape(state_data['title'])}</b>\n\n"
            f"🔗 لینک اختصاصی:\n"
            f"<code>{link}</code>",
            parse_mode="HTML",
        )

        await update.message.reply_text(
            "🎛 پنل مدیریت:",
            reply_markup=admin_menu_keyboard(),
        )

        return

    # ========================================================
    # TOPIC VIDEO
    # ========================================================

    if state_data.get("state") == "topic_video_file":

        if not update.message.video:

            return

        file_id = update.message.video.file_id

        temp_video = {
            "title": state_data["current_video_title"],
            "description": state_data.get(
                "current_video_description",
                "",
            ),
            "telegram_file_id": file_id,
        }

        videos = state_data.get(
            "videos",
            []
        )

        videos.append(temp_video)

        USER_STATES[user.id] = {
            **state_data,
            "state": "topic_video_title",
            "videos": videos,
        }

        count = len(videos)

        await update.message.reply_text(
            "✅ <b>ویدیو ثبت شد!</b>\n\n"
            f"🎬 تعداد قسمت‌های فعلی: <b>{count}</b>\n\n"
            "برای اضافه کردن قسمت بعدی، "
            "عنوان آن را ارسال کنید.\n\n"
            "یا اگر موضوع تمام شده، بنویسید:\n"
            "<code>پایان</code>",
            parse_mode="HTML",
        )

        return


# ============================================================
# FINALIZE TOPIC
# ============================================================

async def finalize_topic(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
):

    state_data = USER_STATES.get(user_id)

    if not state_data:
        return

    videos = state_data.get(
        "videos",
        []
    )

    if not videos:

        await update.message.reply_text(
            "❌ موضوع هیچ ویدیویی ندارد."
        )

        return

    # --------------------------------------------------------
    # CREATE TOPIC
    # --------------------------------------------------------

    topic_code = generate_topic_code()

    topic_id = db.add_topic(
        title=state_data["topic_title"],
        description=state_data.get(
            "topic_description",
            "",
        ),
        unique_code=topic_code,
    )

    # --------------------------------------------------------
    # SAVE VIDEOS
    # --------------------------------------------------------

    for position, video_data in enumerate(
        videos,
        start=1,
    ):

        video_code = generate_video_code()

        video_id = db.add_video(
            title=video_data["title"],
            description=video_data["description"],
            telegram_file_id=video_data["telegram_file_id"],
            unique_code=video_code,
        )

        db.add_video_to_topic(
            topic_id=topic_id,
            video_id=video_id,
            position=position,
        )

    # --------------------------------------------------------
    # CLEAR STATE
    # --------------------------------------------------------

    USER_STATES.pop(user_id, None)

    # --------------------------------------------------------
    # CREATE DEEP LINK
    # --------------------------------------------------------

    bot_info = await context.bot.get_me()

    link = (
        f"https://t.me/"
        f"{bot_info.username}"
        f"?start=t_{topic_code}"
    )

    await update.message.reply_text(
        "🎉 <b>موضوع با موفقیت ساخته شد!</b>\n\n"
        f"📚 عنوان:\n"
        f"<b>{html.escape(state_data['topic_title'])}</b>\n\n"
        f"🎬 تعداد ویدیو ها: "
        f"<b>{len(videos)}</b>\n\n"
        f"🔗 <b>لینک موضوع:</b>\n"
        f"<code>{link}</code>\n\n"
        "کاربر با باز کردن این لینک، "
        "بعد از تأیید عضویت، تمام قسمت‌ها را "
        "به ترتیب دریافت می‌کند.",
        parse_mode="HTML",
    )

    await update.message.reply_text(
        "🎛 پنل مدیریت:",
        reply_markup=admin_menu_keyboard(),
    )


# ============================================================
# UNKNOWN TEXT
# ============================================================

async def unknown_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    if not user:
        return

    if is_admin(user.id):

        await handle_admin_text(
            update,
            context,
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    print(
        "Exception while handling an update:",
        context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # --------------------------------------------------------
    # COMMANDS
    # --------------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "admin",
            admin_command,
        )
    )

    # --------------------------------------------------------
    # CALLBACKS
    # --------------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            callbacks,
        )
    )

    # --------------------------------------------------------
    # VIDEO UPLOADS
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.VIDEO,
            handle_video,
        )
    )

    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            unknown_text,
        )
    )

    # --------------------------------------------------------
    # ERROR HANDLER
    # --------------------------------------------------------

    application.add_error_handler(
        error_handler
    )

    print(
        "======================================"
    )

    print(
        "OnlyDevilBot is starting..."
    )

    print(
        "======================================"
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
