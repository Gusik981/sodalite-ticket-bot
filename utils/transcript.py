import io
import html
from datetime import datetime
import discord


async def generate_html_transcript(channel: discord.TextChannel) -> io.BytesIO:
    """
    Генерирует красивый HTML-транскрипт сообщений из указанного тикет-канала в стиле Discord.
    """
    messages = []
    async for msg in channel.history(limit=1000, oldest_first=True):
        messages.append(msg)

    html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Транскрипт - {html.escape(channel.name)}</title>
    <style>
        body {{
            background-color: #313338;
            color: #dbdee1;
            font-family: 'gg sans', 'Segoe UI', Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 20px;
        }}
        .header {{
            border-bottom: 1px solid #3f4147;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 5px 0;
            color: #f2f3f5;
            font-size: 22px;
        }}
        .header p {{
            margin: 0;
            color: #949ba4;
            font-size: 14px;
        }}
        .message-group {{
            display: flex;
            margin-bottom: 16px;
            align-items: flex-start;
        }}
        .avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            margin-right: 16px;
            object-fit: cover;
        }}
        .message-content {{
            flex: 1;
            min-width: 0;
        }}
        .author-line {{
            margin-bottom: 4px;
        }}
        .author-name {{
            font-weight: 600;
            color: #f2f3f5;
            font-size: 15px;
            margin-right: 8px;
        }}
        .bot-tag {{
            background-color: #5865f2;
            color: #ffffff;
            font-size: 10px;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 700;
            vertical-align: middle;
            margin-right: 6px;
        }}
        .timestamp {{
            color: #949ba4;
            font-size: 12px;
        }}
        .text {{
            font-size: 14px;
            line-height: 1.4;
            word-wrap: break-word;
            white-space: pre-wrap;
            color: #dbdee1;
        }}
        .embed {{
            border-left: 4px solid #5865f2;
            background-color: #2b2d31;
            padding: 10px 14px;
            border-radius: 4px;
            margin-top: 8px;
            max-width: 520px;
        }}
        .embed-title {{
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 4px;
            font-size: 14px;
        }}
        .embed-desc {{
            font-size: 13px;
            color: #dbdee1;
        }}
        .attachment {{
            margin-top: 8px;
        }}
        .attachment a {{
            color: #00a8fc;
            text-decoration: none;
            font-size: 13px;
        }}
        .attachment a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Транскрипт тикета: #{html.escape(channel.name)}</h1>
        <p>Сервер: {html.escape(channel.guild.name)} | Сообщений: {len(messages)} | Создан: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
    </div>
"""

    for msg in messages:
        author_avatar = msg.author.display_avatar.url if msg.author.display_avatar else "https://cdn.discordapp.com/embed/avatars/0.png"
        bot_badge = '<span class="bot-tag">БОТ</span>' if msg.author.bot else ''
        time_str = msg.created_at.strftime('%d.%m.%Y %H:%M')

        escaped_content = html.escape(msg.content or '')

        embeds_html = ""
        for emb in msg.embeds:
            title_html = f'<div class="embed-title">{html.escape(emb.title)}</div>' if emb.title else ""
            desc_html = f'<div class="embed-desc">{html.escape(emb.description)}</div>' if emb.description else ""
            border_color = f"#{emb.color.value:06x}" if emb.color else "#5865f2"
            embeds_html += f'<div class="embed" style="border-left-color: {border_color};">{title_html}{desc_html}</div>'

        attach_html = ""
        for att in msg.attachments:
            attach_html += f'<div class="attachment">📎 <a href="{att.url}" target="_blank">{html.escape(att.filename)}</a> ({att.size // 1024} KB)</div>'

        html_content += f"""
    <div class="message-group">
        <img class="avatar" src="{author_avatar}" alt="Avatar">
        <div class="message-content">
            <div class="author-line">
                <span class="author-name">{html.escape(msg.author.display_name)}</span>
                {bot_badge}
                <span class="timestamp">{time_str}</span>
            </div>
            <div class="text">{escaped_content}</div>
            {embeds_html}
            {attach_html}
        </div>
    </div>
"""

    html_content += """
</body>
</html>
"""

    buffer = io.BytesIO(html_content.encode('utf-8'))
    buffer.seek(0)
    return buffer
