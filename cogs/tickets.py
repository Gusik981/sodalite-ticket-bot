import asyncio
import json
import os
import discord
from discord import app_commands
from discord.ext import commands
from utils.transcript import generate_html_transcript

SODALITE_COLOR = discord.Color.from_rgb(46, 81, 162)  # Фирменный синий цвет содалита


class TicketReasonModal(discord.ui.Modal, title="Sodalite DLC | Создание тикета"):
    topic = discord.ui.TextInput(
        label="Тема обращения",
        placeholder="Например: Краш при запуске / Проблема с ключом",
        max_length=100,
        required=True
    )
    details = discord.ui.TextInput(
        label="Подробное описание проблемы",
        style=discord.TextStyle.paragraph,
        placeholder="Опишите вашу проблему подробно (версия, логи, что произошло)...",
        max_length=1500,
        required=True
    )

    def __init__(self, cog, category_name: str):
        super().__init__()
        self.cog = cog
        self.category_name = category_name

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.cog.create_ticket_channel(
            interaction=interaction,
            category_name=self.category_name,
            topic=self.topic.value,
            details=self.details.value
        )


class MediaApplicationModal(discord.ui.Modal, title="Sodalite DLC | Заявка на Медиа"):
    channel_url = discord.ui.TextInput(
        label="Ссылка на ваш канал / соцсеть",
        placeholder="https://youtube.com/@... или twitch.tv/... или tiktok/...",
        max_length=150,
        required=True
    )
    subscribers = discord.ui.TextInput(
        label="Количество подписчиков",
        placeholder="Например: 30",
        max_length=50,
        required=True
    )
    views = discord.ui.TextInput(
        label="Среднее количество просмотров",
        placeholder="Например: 100",
        max_length=50,
        required=True
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        details = (
            f"**Канал:** {self.channel_url.value}\n"
            f"**Подписчики:** {self.subscribers.value}\n"
            f"**Просмотры:** {self.views.value}"
        )
        await self.cog.create_ticket_channel(
            interaction=interaction,
            category_name="Заявка на Медиа",
            topic=f"Медиа-заявка от {interaction.user}",
            details=details,
            is_media=True
        )


class TicketLauncherView(discord.ui.View):
    """Постоянная панель создания тикетов Sodalite DLC."""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.select(
        custom_id="sodalite_ticket_select",
        placeholder="Выберите тему обращения к Sodalite DLC...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(
                label="Техническая помощь / Краши",
                value="tech_support",
                description="Ошибки при запуске, баги клиента, вылеты",
                emoji="🛠️"
            ),
            discord.SelectOption(
                label="Покупка / Ключи / Подписка",
                value="billing_support",
                description="Вопросы оплаты, активация лицензии, продление",
                emoji="💳"
            ),
            discord.SelectOption(
                label="Заявка на Медиа",
                value="media_application",
                description="YouTube, Twitch, TikTok, сотрудничество",
                emoji="🎬"
            ),
            discord.SelectOption(
                label="Вопрос или предложение",
                value="general_question",
                description="Идеи для Sodalite DLC, помощь по функционалу",
                emoji="💡"
            ),
            discord.SelectOption(
                label="Жалоба / Другое",
                value="other_report",
                description="Жалобы или нестандартные вопросы",
                emoji="⚠️"
            ),
        ]
    )
    async def select_category(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_value = select.values[0]
        if selected_value == "media_application":
            modal = MediaApplicationModal(cog=self.cog)
            await interaction.response.send_modal(modal)
            return

        categories = {
            "tech_support": "Техническая помощь / Баги",
            "billing_support": "Оплата / Ключи / Подписка",
            "general_question": "Вопрос / Предложение",
            "other_report": "Жалоба / Другое"
        }
        category_name = categories.get(selected_value, "Поддержка Sodalite DLC")
        modal = TicketReasonModal(cog=self.cog, category_name=category_name)
        await interaction.response.send_modal(modal)


class ManageMemberModal(discord.ui.Modal):
    def __init__(self, cog, action: str):
        title = "Добавить в тикет" if action == "add" else "Исключить из тикета"
        super().__init__(title=title)
        self.cog = cog
        self.action = action

        self.user_input = discord.ui.TextInput(
            label="ID пользователя или @упоминание",
            placeholder="Например: 123456789012345678",
            min_length=3,
            max_length=32,
            required=True
        )
        self.add_item(self.user_input)

    async def on_submit(self, interaction: discord.Interaction):
        raw_val = self.user_input.value.strip().replace("<@", "").replace(">", "").replace("!", "")
        try:
            user_id = int(raw_val)
            member = interaction.guild.get_member(user_id) or await interaction.guild.fetch_member(user_id)
        except Exception:
            await interaction.response.send_message("❌ Не удалось найти пользователя по указанному ID.", ephemeral=True)
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        if self.action == "add":
            await channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
            await interaction.response.send_message(f"✅ Пользователь {member.mention} добавлен в тикет.")
        else:
            await channel.set_permissions(member, overwrite=None)
            await interaction.response.send_message(f"🚫 Пользователь {member.mention} удален из тикета.")


class TicketControlView(discord.ui.View):
    """Постоянная панель управления внутри тикет-канала Sodalite DLC."""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Закрыть тикет",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="soda_btn_close"
    )
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        confirm_view = TicketCloseConfirmView(self.cog)
        await interaction.response.send_message(
            "❓ Вы уверены, что хотите закрыть этот тикет? Переписка будет сохранена в транскрипт.",
            view=confirm_view,
            ephemeral=True
        )

    @discord.ui.button(
        label="Транскрипт",
        style=discord.ButtonStyle.secondary,
        emoji="📜",
        custom_id="soda_btn_transcript"
    )
    async def transcript_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        transcript_file = await generate_html_transcript(interaction.channel)
        discord_file = discord.File(fp=transcript_file, filename=f"transcript-{interaction.channel.name}.html")
        await interaction.followup.send(
            content="📄 Транскрипт тикета Sodalite DLC:",
            file=discord_file,
            ephemeral=True
        )

    @discord.ui.button(
        label="Добавить участника",
        style=discord.ButtonStyle.primary,
        emoji="➕",
        custom_id="soda_btn_add_member"
    )
    async def add_member_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ManageMemberModal(self.cog, action="add"))

    @discord.ui.button(
        label="Удалить участника",
        style=discord.ButtonStyle.secondary,
        emoji="➖",
        custom_id="soda_btn_remove_member"
    )
    async def remove_member_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ManageMemberModal(self.cog, action="remove"))


class TicketCloseConfirmView(discord.ui.View):
    """Подтверждение закрытия тикета."""
    def __init__(self, cog):
        super().__init__(timeout=60)
        self.cog = cog

    @discord.ui.button(
        label="Да, закрыть",
        style=discord.ButtonStyle.danger,
        emoji="✅",
        custom_id="soda_btn_confirm_close"
    )
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.close_ticket(interaction.channel, closed_by=interaction.user)

    @discord.ui.button(
        label="Отмена",
        style=discord.ButtonStyle.secondary,
        emoji="❌",
        custom_id="soda_btn_cancel_close"
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Закрытие тикета отменено.", view=None)


class TicketClosedControlView(discord.ui.View):
    """Постоянная панель управления закрытым тикетом в категории CLOSED TICKETS."""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Удалить навсегда",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="soda_btn_delete_forever"
    )
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🗑️ Удаление канала тикета через 3 секунды...")
        await asyncio.sleep(3)
        try:
            await interaction.channel.delete(reason=f"Тикет окончательно удален {interaction.user}")
        except Exception:
            pass

    @discord.ui.button(
        label="Транскрипт",
        style=discord.ButtonStyle.secondary,
        emoji="📜",
        custom_id="soda_btn_closed_transcript"
    )
    async def transcript_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        transcript_file = await generate_html_transcript(interaction.channel)
        discord_file = discord.File(fp=transcript_file, filename=f"transcript-{interaction.channel.name}.html")
        await interaction.followup.send(
            content="📄 Транскрипт закрытого тикета:",
            file=discord_file,
            ephemeral=True
        )

    @discord.ui.button(
        label="Открыть заново",
        style=discord.ButtonStyle.success,
        emoji="🔓",
        custom_id="soda_btn_reopen"
    )
    async def reopen_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.reopen_ticket(interaction.channel, reopened_by=interaction.user)


class TicketsCog(commands.Cog, name="Tickets"):
    def __init__(self, bot: commands.Bot, config: dict):
        self.bot = bot
        self.config = config

    async def cog_load(self):
        # Регистрируем постоянные Views
        self.bot.add_view(TicketLauncherView(self))
        self.bot.add_view(TicketControlView(self))
        self.bot.add_view(TicketClosedControlView(self))

    async def get_or_create_category(self, guild: discord.Guild) -> discord.CategoryChannel:
        cat_id = self.config.get("ticket_category_id", 1549529612936024155)
        if cat_id:
            cat = guild.get_channel(int(cat_id))
            if isinstance(cat, discord.CategoryChannel):
                return cat

        for cat in guild.categories:
            if "tickets" in cat.name.lower() and "closed" not in cat.name.lower():
                return cat

        return await guild.create_category("🎫・TICKETS・💎")

    async def create_ticket_channel(self, interaction: discord.Interaction, category_name: str, topic: str, details: str, is_media: bool = False):
        guild = interaction.guild
        user = interaction.user

        if not guild:
            await interaction.followup.send("Команда доступна только на сервере.", ephemeral=True)
            return

        # Проверка на наличие уже открытого тикета
        prefix = "media-" if is_media else "soda-"
        existing = discord.utils.find(lambda c: c.name.startswith(f"{prefix}{user.name.lower()[:10]}"), guild.text_channels)
        if existing:
            await interaction.followup.send(
                f"⚠️ У вас уже есть открытый канал: {existing.mention}. Пожалуйста, используйте его.",
                ephemeral=True
            )
            return

        category = await self.get_or_create_category(guild)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                attach_files=True,
                embed_links=True
            ),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )
        }

        support_role_id = self.config.get("support_role_id", 0)
        support_role = guild.get_role(support_role_id) if support_role_id else None
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )

        channel_name = f"media-{user.name[:10].lower()}" if is_media else f"soda-{user.name[:10].lower()}"
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Sodalite DLC | {category_name}: {user} | ID: {user.id}"
        )

        if is_media:
            embed = discord.Embed(
                title="🎬 Sodalite DLC | Заявка на Медиа-сотрудничество",
                description=f"Приветствуем, {user.mention}!\n"
                            f"Ваша заявка на получение **Медиа-статуса** по Sodalite DLC успешно отправлена.\n"
                            f"Администрация и разработчики ознакомятся с вашей анкетой и ответят вам прямо здесь.",
                color=discord.Color.gold()
            )
            embed.add_field(name="📋 Анкета заявителя", value=details, inline=False)
            embed.set_footer(text="Sodalite DLC Media Team • Ожидайте рассмотрения")
        else:
            embed = discord.Embed(
                title=f"💎 Sodalite DLC | {category_name}",
                description=f"Приветствуем, {user.mention}!\n"
                            f"Ваше обращение принято службой поддержки **Sodalite DLC**.\n"
                            f"Опишите все детали, приложите логи и скриншоты при наличии. "
                            f"Специалисты ответят вам в ближайшее время.",
                color=SODALITE_COLOR
            )
            embed.add_field(name="📌 Тема обращения", value=topic, inline=False)
            embed.add_field(name="📝 Описание проблемы", value=details, inline=False)
            embed.set_footer(text="Sodalite DLC Support • Используйте кнопки ниже для управления")

        mention_str = f"{user.mention}"
        if support_role:
            mention_str += f" | {support_role.mention}"

        view = TicketControlView(self)
        await channel.send(content=mention_str, embed=embed, view=view)

        await interaction.followup.send(
            f"✅ Ваш тикет успешно создан: {channel.mention}",
            ephemeral=True
        )

    async def get_closed_category(self, guild: discord.Guild) -> discord.CategoryChannel:
        cat_id = self.config.get("closed_category_id", 1549529968210481293)
        if cat_id:
            cat = guild.get_channel(int(cat_id))
            if isinstance(cat, discord.CategoryChannel):
                return cat

        for cat in guild.categories:
            if "closed" in cat.name.lower() or "закрыт" in cat.name.lower() or "архив" in cat.name.lower():
                return cat

        return await guild.create_category("🔒・CLOSED TICKETS・📁")

    async def close_ticket(self, channel: discord.TextChannel, closed_by: discord.Member | discord.User):
        await channel.send(f"🔒 Тикет закрывается пользователем {closed_by.mention}. Перемещение в архив...")

        # 1. Перемещение в категорию закрытых тикетов и переименование
        closed_category = await self.get_closed_category(channel.guild)
        clean_name = channel.name.replace("soda-", "").replace("closed-", "")
        new_channel_name = f"closed-{clean_name[:12]}"
        try:
            await channel.edit(category=closed_category, name=new_channel_name, sync_permissions=True)
        except Exception:
            pass

        # 2. Полностью запрещаем просмотр канала автору и всем участникам тикета (мгновенно скрывает канал в клиенте)
        for target in list(channel.overwrites.keys()):
            if isinstance(target, discord.Member) and not target.bot:
                try:
                    await channel.set_permissions(target, view_channel=False, send_messages=False)
                except Exception:
                    pass

        # 3. Транскрипт
        transcript_buffer = await generate_html_transcript(channel)
        filename = f"transcript-{channel.name}.html"

        # Лог-канал
        log_channel_id = self.config.get("log_channel_id", 0)
        if log_channel_id:
            log_channel = channel.guild.get_channel(log_channel_id)
            if isinstance(log_channel, discord.TextChannel):
                transcript_buffer.seek(0)
                log_file = discord.File(fp=transcript_buffer, filename=filename)
                log_embed = discord.Embed(
                    title=f"Тикет закрыт: #{channel.name}",
                    color=discord.Color.red()
                )
                log_embed.add_field(name="Закрыл", value=closed_by.mention, inline=True)
                log_embed.add_field(name="Сервер", value=channel.guild.name, inline=True)
                if channel.topic:
                    log_embed.add_field(name="Инфо", value=channel.topic, inline=False)
                await log_channel.send(embed=log_embed, file=log_file)

        # Отправка в ЛС автору
        for target, overwrite in channel.overwrites.items():
            if isinstance(target, discord.Member) and not target.bot and target.id != closed_by.id:
                try:
                    transcript_buffer.seek(0)
                    dm_file = discord.File(fp=transcript_buffer, filename=filename)
                    await target.send(
                        f"Ваш тикет в **Sodalite DLC** ({channel.guild.name}) был закрыт {closed_by}.\n"
                        f"История переписки сохранена в транскрипте ниже:",
                        file=dm_file
                    )
                except Exception:
                    pass

        # 4. Отправляем карточку закрытого тикета с кнопками управления
        closed_embed = discord.Embed(
            title="🔒 Тикет закрыт и перемещён в архив",
            description=f"Тикет был закрыт пользователем {closed_by.mention}.\n"
                        f"Канал перенесён в категорию **`{closed_category.name}`**.\n"
                        f"Автор больше не может отправлять сообщения.\n\n"
                        f"Для окончательного удаления нажмите кнопку **Удалить навсегда** ниже.",
            color=discord.Color.dark_gray()
        )
        closed_embed.set_footer(text="Sodalite DLC • Архив тикетов")
        view = TicketClosedControlView(self)
        await channel.send(embed=closed_embed, view=view)

    async def reopen_ticket(self, channel: discord.TextChannel, reopened_by: discord.Member | discord.User):
        open_category = await self.get_or_create_category(channel.guild)
        clean_name = channel.name.replace("closed-", "").replace("soda-", "")
        new_name = f"soda-{clean_name[:12]}"

        try:
            await channel.edit(category=open_category, name=new_name)
        except Exception:
            pass

        # Восстанавливаем права автору
        for target, overwrite in channel.overwrites.items():
            if isinstance(target, discord.Member) and not target.bot:
                try:
                    await channel.set_permissions(target, send_messages=True, view_channel=True, read_message_history=True, attach_files=True)
                except Exception:
                    pass

        reopen_embed = discord.Embed(
            title="🔓 Тикет снова открыт",
            description=f"Тикет был открыт заново пользователем {reopened_by.mention}!\n"
                        f"Канал возвращён в категорию активных тикетов **`{open_category.name}`**.",
            color=SODALITE_COLOR
        )
        view = TicketControlView(self)
        await channel.send(embed=reopen_embed, view=view)

    @app_commands.command(name="ticket-panel", description="Отправить панель тикетов Sodalite DLC в текущий канал")
    @app_commands.default_permissions(administrator=True)
    async def ticket_panel_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💎 Sodalite DLC | Центр поддержки",
            description="Возникли сложности с запуском, баги, вопросы по подписке или предложения по улучшению **Sodalite DLC**?\n\n"
                        "Выберите нужный раздел в меню ниже, заполните короткую форму, и команда поддержки свяжется с вами!\n\n"
                        "**Правила:**\n"
                        "• Формулируйте проблему четко и развернуто.\n"
                        "• Прикрепляйте логи краша или скриншоты.\n"
                        "• Не спамьте тикетами — это ускорит ответ.",
            color=SODALITE_COLOR
        )
        embed.set_footer(text="Sodalite DLC Support • Выберите категорию в меню ниже ⬇️")

        view = TicketLauncherView(self)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Панель тикетов Sodalite DLC успешно отправлена!", ephemeral=True)

    @app_commands.command(name="ticket-add", description="Добавить пользователя в текущий тикет Sodalite DLC")
    async def ticket_add_command(self, interaction: discord.Interaction, member: discord.Member):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not (channel.name.startswith("soda-") or channel.name.startswith("ticket-")):
            await interaction.response.send_message("❌ Эта команда может использоваться только внутри тикета.", ephemeral=True)
            return

        await channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
        await interaction.response.send_message(f"✅ Пользователь {member.mention} добавлен в тикет.")

    @app_commands.command(name="ticket-remove", description="Исключить пользователя из текущего тикета")
    async def ticket_remove_command(self, interaction: discord.Interaction, member: discord.Member):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not (channel.name.startswith("soda-") or channel.name.startswith("ticket-")):
            await interaction.response.send_message("❌ Эта команда может использоваться только внутри тикета.", ephemeral=True)
            return

        await channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(f"🚫 Пользователь {member.mention} удален из тикета.")

    @app_commands.command(name="ticket-close", description="Закрыть текущий тикет Sodalite DLC")
    async def ticket_close_command(self, interaction: discord.Interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not (channel.name.startswith("soda-") or channel.name.startswith("ticket-")):
            await interaction.response.send_message("❌ Эта команда может использоваться только внутри тикета.", ephemeral=True)
            return

        confirm_view = TicketCloseConfirmView(self)
        await interaction.response.send_message(
            "❓ Вы уверены, что хотите закрыть этот тикет?",
            view=confirm_view,
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    cog = TicketsCog(bot, bot.config)
    await bot.add_cog(cog)
