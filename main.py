import discord
from discord.ext import commands
import os, threading
from flask import Flask, request, jsonify

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("DISCORD_TOKEN")
SECRET = "2122428Matros"

CHANNEL_ID = 1342349362600218624

РОЛЬ_НА_ПРОВЕРКЕ = 1474320899598581791
РОЛЬ_ОДОБРЕНО = 1457319043315929267

# ================= СТАТУСЫ =================
СТАТУСЫ = {
    "WAIT": ("🟣 На рассмотрении", 0x5865F2),
    "PROCESS": ("🟡 В обработке", 0xF1C40F),
    "OK": ("🟢 Принят", 0x2ECC71),
    "NO": ("🔴 Отказ", 0xE74C3C),
    "CLARIFY": ("🔵 Требуется уточнение", 0x3498DB),
}

# ================= BOT =================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= FLASK =================
app = Flask(__name__)

@app.route("/zayavka", methods=["POST"])
def принимать_заявку():
    if request.headers.get("Authorization") != f"Bearer {SECRET}":
        return jsonify({"error": "bad key"}), 401

    data = request.json or {}
    discord_id = int(data.get("discordId"))
    author_name = data.get("authorName", "Без имени")
    fields = data.get("fields", [])

    bot.loop.create_task(обработать_заявку(discord_id, author_name, fields))
    return jsonify({"ok": True})

# ================= КНОПКИ =================
class Кнопки(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user
        self.message = None

    async def set_status(self, interaction, key, финал=False):
        текст, цвет = СТАТУСЫ[key]

        embed = self.message.embeds[0]

        for i, field in enumerate(embed.fields):
            if field.name == "Статус":
                embed.set_field_at(i, name="Статус", value=текст, inline=False)
                break

        embed.color = цвет
        embed.set_footer(text=f"Решил: {interaction.user}")

        if финал:
            await interaction.message.edit(embed=embed, view=None)
        else:
            await interaction.message.edit(embed=embed)

    # ===== КНОПКИ =====

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button):
        member = interaction.guild.get_member(self.user.id)
        if member:
            role = interaction.guild.get_role(РОЛЬ_ОДОБРЕНО)
            if role:
                await member.add_roles(role)

        await interaction.response.defer()
        await self.set_status(interaction, "OK", финал=True)

    @discord.ui.button(label="Отказать", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        await self.set_status(interaction, "NO", финал=True)

    @discord.ui.button(label="Уточнить", style=discord.ButtonStyle.secondary)
    async def clarify(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        await self.set_status(interaction, "CLARIFY", финал=False)

# ================= ОБРАБОТКА =================
async def обработать_заявку(discord_id, author_name, fields):
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    user = await bot.fetch_user(discord_id)
    avatar = user.avatar.url if user.avatar else user.default_avatar.url

    текст, цвет = СТАТУСЫ["WAIT"]

    embed = discord.Embed(
        title=f"Заявка — {author_name}",
        color=цвет,
        timestamp=discord.utils.utcnow()
    )

    embed.set_thumbnail(url=avatar)
    embed.add_field(name="Статус", value=текст, inline=False)
    embed.add_field(name="Заявитель", value=f"<@{discord_id}>", inline=False)

    for f in fields:
        embed.add_field(name=f.get("name"), value=f.get("value"), inline=False)

    view = Кнопки(user)
    msg = await channel.send(embed=embed, view=view)

    view.message = msg

    guild = channel.guild
    member = guild.get_member(discord_id)

    if member:
        role = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
        if role:
            await member.add_roles(role)

# ================= RUN =================
def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask).start()

bot.run(TOKEN)
