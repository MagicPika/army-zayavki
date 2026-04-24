import discord
from discord.ext import commands
import os, random, asyncio, threading
from flask import Flask, request, jsonify

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("DISCORD_TOKEN")
SECRET = "2122428Matros"

CHANNEL_ID = 1458885875692732438
LOG_CHANNEL_ID = 1458885875692732438

РОЛЬ_НА_ПРОВЕРКЕ = 1474320899598581791
РОЛЬ_ОДОБРЕНО = 1457319043315929267

# ================= ТЕКСТЫ =================
ТЕКСТЫ_ПОЛУЧЕНО = [
    "Заявка принята. Ожидайте решения командования.",
    "Анкета получена. Передано на рассмотрение."
]

ТЕКСТЫ_ОДОБРЕНО = [
    "Вы приняты. Явиться на службу.",
]

ТЕКСТЫ_ОТКЛОНЕНО = [
    "В приёме отказано.",
]

ТЕКСТЫ_УТОЧНИТЬ = [
    "Требуется уточнение данных. Свяжитесь с командованием."
]

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
    def __init__(self, user, message):
        super().__init__(timeout=None)
        self.user = user
        self.message = message

    async def check(self, interaction):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("Нет прав", ephemeral=True)
            return False
        return True

    async def finish(self, interaction, текст, цвет):
        for i in self.children:
            i.disabled = True

        await interaction.message.edit(view=self)

        embed = self.message.embeds[0]
        embed.title = "Решение по заявке"
        embed.description = текст
        embed.color = цвет
        embed.set_footer(text=f"Решение: {interaction.user}")

        await self.message.edit(embed=embed)

        log = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log:
            await log.send(f"{interaction.user.mention} → {текст}")

    # ===== КНОПКИ =====

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button):
        if not await self.check(interaction):
            return

        member = interaction.guild.get_member(self.user.id)

        if member:
            role = interaction.guild.get_role(РОЛЬ_ОДОБРЕНО)
            if role:
                await member.add_roles(role)

            try:
                await member.send(random.choice(ТЕКСТЫ_ОДОБРЕНО))
            except:
                pass

        await interaction.response.defer()
        await self.finish(interaction, f"{self.user.mention} принят", 0x2ecc71)

    @discord.ui.button(label="Отказать", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button):
        if not await self.check(interaction):
            return

        try:
            await self.user.send(random.choice(ТЕКСТЫ_ОТКЛОНЕНО))
        except:
            pass

        await interaction.response.defer()
        await self.finish(interaction, f"{self.user.mention} отклонён", 0xe74c3c)

    @discord.ui.button(label="Уточнить", style=discord.ButtonStyle.secondary)
    async def clarify(self, interaction: discord.Interaction, button):
        if not await self.check(interaction):
            return

        try:
            await self.user.send(random.choice(ТЕКСТЫ_УТОЧНИТЬ))
        except:
            pass

        await interaction.response.defer()
        await self.finish(interaction, f"{self.user.mention} требуется уточнение", 0xf1c40f)

# ================= ОБРАБОТКА =================
async def обработать_заявку(discord_id, author_name, fields):
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    user = await bot.fetch_user(discord_id)

    avatar = user.avatar.url if user.avatar else user.default_avatar.url

    embed = discord.Embed(
        title=f"Заявка в армию — {author_name}",
        color=0x2c3e50,
        timestamp=discord.utils.utcnow()
    )

    embed.set_thumbnail(url=avatar)
    embed.add_field(name="Статус", value="На рассмотрении", inline=False)
    embed.add_field(name="Заявитель", value=f"<@{discord_id}>", inline=False)

    for f in fields:
        embed.add_field(name=f.get("name"), value=f.get("value"), inline=False)

    msg = await channel.send(embed=embed)

    await channel.send("Действие:", view=Кнопки(user, msg))

    guild = channel.guild
    member = guild.get_member(discord_id)

    if member:
        role = guild.get_role(РОЛЬ_НА_ПРОВЕРКЕ)
        if role:
            await member.add_roles(role)

    try:
        await user.send(random.choice(ТЕКСТЫ_ПОЛУЧЕНО))
    except:
        pass

# ================= RUN =================
def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask).start()

bot.run(TOKEN)
