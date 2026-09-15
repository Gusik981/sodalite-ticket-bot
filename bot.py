import asyncio
import json
import logging
import os
import sys
import discord
from discord.ext import commands

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SodaliteDLC-Bot")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config() -> dict:
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            logger.warning(f"Не удалось прочитать config.json: {e}")

    # По умолчанию для сервера Sodalite DLC
    cfg.setdefault("guild_id", 1284717549535363212)
    cfg.setdefault("support_role_id", 1548007523024506960)  # Роль @Developer

    # Переменные окружения имеют приоритет (для облачных хостингов и GitHub)
    if os.getenv("DISCORD_TOKEN"):
        cfg["token"] = os.getenv("DISCORD_TOKEN")
    elif os.getenv("TOKEN"):
        cfg["token"] = os.getenv("TOKEN")

    if os.getenv("GUILD_ID"):
        try:
            cfg["guild_id"] = int(os.getenv("GUILD_ID"))
        except ValueError:
            pass

    if os.getenv("SUPPORT_ROLE_ID"):
        try:
            cfg["support_role_id"] = int(os.getenv("SUPPORT_ROLE_ID"))
        except ValueError:
            pass

    if os.getenv("TICKET_CATEGORY_ID"):
        try:
            cfg["ticket_category_id"] = int(os.getenv("TICKET_CATEGORY_ID"))
        except ValueError:
            pass

    if os.getenv("LOG_CHANNEL_ID"):
        try:
            cfg["log_channel_id"] = int(os.getenv("LOG_CHANNEL_ID"))
        except ValueError:
            pass

    return cfg


class TicketBot(commands.Bot):
    def __init__(self, config: dict):
        self.config = config

        # Базовые интенты не требуют ручного включения Privileged Intents на портале
        intents = discord.Intents.default()
        if config.get("privileged_intents", False):
            intents.message_content = True
            intents.members = True

        super().__init__(
            command_prefix=config.get("prefix", "!"),
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # Загрузка модуля тикетов
        await self.load_extension("cogs.tickets")
        logger.info("Модуль cogs.tickets успешно загружен.")

        # Синхронизация слэш-команд (если включено в конфиге)
        if self.config.get("sync_commands", False):
            guild_id = self.config.get("guild_id", 0)
            if guild_id and int(guild_id) != 0:
                guild = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info(f"Синхронизировано {len(synced)} слэш-команд для сервера ID: {guild_id}")
            else:
                synced = await self.tree.sync()
                logger.info(f"Глобально синхронизировано {len(synced)} слэш-команд.")
        else:
            logger.info("Синхронизация команд пропущена (команды уже зарегистрированы). Используйте !sync для обновления.")

    async def on_ready(self):
        logger.info("=" * 60)
        logger.info(f"Бот успешно запущен как: {self.user} (ID: {self.user.id})")
        logger.info(f"Подключен к серверам: {len(self.guilds)}")

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="Sodalite DLC | /ticket-panel"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

        permissions = discord.Permissions(
            manage_channels=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            view_channel=True,
            use_application_commands=True
        )
        invite_url = discord.utils.oauth_url(self.user.id, permissions=permissions)
        logger.info("Ссылка для добавления бота на ваш Discord-сервер:")
        logger.info(invite_url)
        logger.info("=" * 60)


async def main():
    config = load_config()
    token = config.get("token", "").strip()

    if not token or token == "YOUR_BOT_TOKEN_HERE":
        logger.error("=" * 60)
        logger.error("ОШИБКА: Токен бота не найден!")
        logger.error("Проверьте, что в GitHub Settings -> Secrets -> Actions добавлен секрет DISCORD_TOKEN.")
        logger.error("=" * 60)
        sys.exit(1)

    bot = TicketBot(config)
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен.")
