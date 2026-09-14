import os


# =========================
# Telegram Bot Configuration
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Telegram numeric ID of the bot owner
OWNER_ID = 8988535531


# =========================
# Database Configuration
# =========================

DATABASE_PATH = os.getenv("DATABASE_PATH", "educational_bot.db")


# =========================
# Bot Settings
# =========================

# How many seconds after sending a video it should be deleted
VIDEO_DELETE_SECONDS = 20


# =========================
# Channel Configuration
# =========================

# Main educational channel.
# We will set this from the admin panel later.
MAIN_CHANNEL_ID = os.getenv("MAIN_CHANNEL_ID", "")

# Public username/link of the main channel can also be configured later.
MAIN_CHANNEL_USERNAME = os.getenv("MAIN_CHANNEL_USERNAME", "")


# =========================
# Application Settings
# =========================

BOT_NAME = "OnlyDevilBot"

DEBUG = os.getenv("DEBUG", "false").lower() == "true"