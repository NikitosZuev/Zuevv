import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from discord import ButtonStyle
import json
import os
import random
import string
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS  # 👈 ДОБАВЛЕНО
import threading

# ========== НАСТРОЙКИ ==========
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = 973197434996031518
PANEL_CHANNEL_ID = 1472867840527827069
RESET_COOLDOWN_HOURS = 12
PREMIUM_ROLE_NAME = "Zuev Premium"
# ===============================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Файлы
KEYS_FILE = "keys.json"
ACTIVATED_FILE = "activated.json"
RESET_LOG_FILE = "resets.json"

def load_json(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

keys_db = load_json(KEYS_FILE)
activated_users = load_json(ACTIVATED_FILE)
reset_log = load_json(RESET_LOG_FILE)

def save_all():
    save_json(KEYS_FILE, keys_db)
    save_json(ACTIVATED_FILE, activated_users)
    save_json(RESET_LOG_FILE, reset_log)

def get_hwid(interaction: discord.Interaction) -> str:
    return f"HWID_{interaction.user.id}"

def get_hwid_by_user_id(user_id: int) -> str:
    return f"HWID_{user_id}"

def is_activated(hwid: str) -> bool:
    return hwid in activated_users

def has_premium_role(member: discord.Member) -> bool:
    return any(role.name == PREMIUM_ROLE_NAME for role in member.roles)

def can_reset_hwid(hwid: str) -> bool:
    if hwid not in reset_log:
        return True
    last = datetime.fromisoformat(reset_log[hwid])
    return datetime.now() - last > timedelta(hours=RESET_COOLDOWN_HOURS)

def is_expired(expires_str):
    if not expires_str:
        return False
    try:
        return datetime.now() > datetime.fromisoformat(expires_str)
    except:
        return False

def format_time_left(expires_str):
    if not expires_str:
        return "бессрочно"
    try:
        expires = datetime.fromisoformat(expires_str)
        if datetime.now() > expires:
            return "истёк"
        delta = expires - datetime.now()
        days = delta.days
        hours = delta.seconds // 3600
        if days > 0:
            return f"{days}д {hours}ч"
        else:
            return f"{hours}ч"
    except:
        return "неизвестно"

# ========== ВЕБ-СЕРВЕР ДЛЯ ROBLOX ==========
app = Flask(__name__)
CORS(app)  # 👈 РАЗРЕШАЕТ ЗАПРОСЫ ИЗ ROBLOX

@app.route('/verify', methods=['POST'])
def verify():
    data = request.json
    key = data.get('key')
    hwid = data.get('hwid')
    
    if not key or not hwid:
        return jsonify({"status": "error", "message": "Missing key or hwid"}), 400
    
    if key in keys_db:
        key_data = keys_db[key]
        
        if is_expired(key_data.get("expires")):
            return jsonify({"status": "error", "message": "Key expired"})
        
        if not key_data["used"]:
            key_data["used"] = True
            key_data["hwid"] = hwid
            activated_users[hwid] = {"active": True, "expires": key_data["expires"]}
            save_all()
            return jsonify({"status": "success", "message": "Key activated"})
        
        elif key_data["hwid"] == hwid:
            if hwid in activated_users:
                exp = activated_users[hwid].get("expires")
                if exp and datetime.now() > datetime.fromisoformat(exp):
                    return jsonify({"status": "error", "message": "Activation expired"})
            return jsonify({"status": "success", "message": "Key valid"})
        else:
            return jsonify({"status": "error", "message": "Key used on another HWID"})
    else:
        return jsonify({"status": "error", "message": "Invalid key"})

@app.route('/check', methods=['POST'])
def check():
    data = request.json
    hwid = data.get('hwid')
    
    if hwid in activated_users:
        exp = activated_users[hwid].get("expires")
        if exp and datetime.now() > datetime.fromisoformat(exp):
            return jsonify({"status": "inactive", "message": "Expired"})
        return jsonify({"status": "active"})
    return jsonify({"status": "inactive"})

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({
        "status": "alive",
        "time": str(datetime.now()),
        "message": "Server is running"
    })

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()
print("✅ Веб-сервер для проверки ключей запущен!")

# ========== МОДАЛКА ДЛЯ КЛЮЧА ==========
class KeyModal(Modal, title="🔑 Активация ключа"):
    key_input = TextInput(
        label="Введи ключ",
        placeholder="ZV-XXXXXX",
        required=True,
        min_length=8,
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value
        hwid = get_hwid(interaction)

        if key not in keys_db:
            await interaction.response.send_message("❌ Неверный ключ!", ephemeral=True)
            return

        key_data = keys_db[key]

        if is_expired(key_data.get("expires")):
            del keys_db[key]
            save_all()
            await interaction.response.send_message("❌ Ключ просрочен!", ephemeral=True)
            return

        if key_data["used"]:
            if key_data["hwid"] == hwid:
                if hwid in activated_users:
                    exp = activated_users[hwid].get("expires")
                    if exp and datetime.now() > datetime.fromisoformat(exp):
                        del activated_users[hwid]
                        save_all()
                        await interaction.response.send_message("❌ Срок истёк. Новый ключ.", ephemeral=True)
                        return
                activated_users[hwid] = {"active": True, "expires": key_data["expires"]}
                save_all()
                await interaction.response.send_message("✅ Доступ восстановлен!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Ключ уже используется!", ephemeral=True)
            return

        key_data["used"] = True
        key_data["hwid"] = hwid
        activated_users[hwid] = {"active": True, "expires": key_data["expires"]}
        save_all()

        expires = datetime.fromisoformat(key_data["expires"])
        days_left = (expires - datetime.now()).days
        await interaction.response.send_message(
            f"✅ Ключ активирован на {days_left} дней!\nТеперь нажми **Get Role** чтобы получить доступ.",
            ephemeral=True
        )

# ========== КОМАНДА /WHITELIST ==========
@bot.tree.command(name="whitelist", description="✅ Выдать премиум вручную (без ключа)")
@app_commands.describe(user="Пользователь", days="Количество дней")
async def whitelist(interaction: discord.Interaction, user: discord.User, days: int = 30):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ Только владелец!", ephemeral=True)
        return

    hwid = get_hwid_by_user_id(user.id)
    expires = (datetime.now() + timedelta(days=days)).isoformat()

    fake_key = f"WHITELIST_{user.id}_{random.randint(1000,9999)}"

    keys_db[fake_key] = {
        "used": True,
        "hwid": hwid,
        "expires": expires,
        "created": datetime.now().isoformat(),
        "whitelist": True
    }

    activated_users[hwid] = {"active": True, "expires": expires}
    save_all()

    embed = discord.Embed(
        title="✅ Whitelist активирован",
        description=(
            f"**Пользователь:** {user.mention}\n"
            f"**HWID:** `{hwid}`\n"
            f"**Срок:** {days} дней\n"
            f"**Истекает:** {expires[:10]}\n\n"
            f"Теперь пользователь может нажать **Get Role** в панели."
        ),
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

    try:
        await user.send(f"✅ Вам выдан премиум на {days} дней!\nНа сервере нажми **Get Role** в панели.")
    except:
        pass

# ========== КОМАНДА /BLACKLIST ==========
@bot.tree.command(name="blacklist", description="⛔ Заблокировать пользователя (ключ удаляется)")
@app_commands.describe(user="Пользователь, которого нужно заблокировать")
async def blacklist(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ Только владелец!", ephemeral=True)
        return

    hwid = get_hwid_by_user_id(user.id)
    deleted_key = None

    for key, data in list(keys_db.items()):
        if data.get("hwid") == hwid:
            deleted_key = key
            del keys_db[key]
            break

    if hwid in activated_users:
        del activated_users[hwid]

    save_all()

    embed = discord.Embed(
        title="⛔ Пользователь заблокирован",
        description=(
            f"**Пользователь:** {user.mention}\n"
            f"**HWID:** `{hwid}`\n"
            f"**Ключ:** `{deleted_key or 'не найден'}`\n"
            f"**Статус:** ключ удалён, активация невозможна"
        ),
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

    try:
        await user.send("⛔ Ваш ключ был **полностью удалён** владельцем. Активация невозможна.")
    except:
        pass

# ========== ПАНЕЛЬ ==========
class ControlPanel(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Redeem Key", style=ButtonStyle.green, custom_id="redeem_btn", row=0)
    async def redeem_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(KeyModal())

    @discord.ui.button(label="📜 Get Script", style=ButtonStyle.blurple, custom_id="script_btn", row=0)
    async def script_btn(self, interaction: discord.Interaction, button: Button):
        if not has_premium_role(interaction.user):
            await interaction.response.send_message("❌ Нужна роль Zuev Premium!", ephemeral=True)
            return
        script = 'loadstring(game:HttpGet("https://your-script.com/loader.lua"))()'
        await interaction.response.send_message(f"```lua\n{script}\n```", ephemeral=True)

    @discord.ui.button(label="👑 Get Role", style=ButtonStyle.gray, custom_id="role_btn", row=1)
    async def role_btn(self, interaction: discord.Interaction, button: Button):
        hwid = get_hwid(interaction)

        if not is_activated(hwid):
            await interaction.response.send_message("❌ Сначала активируй ключ!", ephemeral=True)
            return

        role = discord.utils.get(interaction.guild.roles, name=PREMIUM_ROLE_NAME)
        if not role:
            await interaction.response.send_message("❌ Роль не найдена на сервере!", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("ℹ️ У тебя уже есть эта роль.", ephemeral=True)
            return

        await interaction.user.add_roles(role)
        await interaction.response.send_message("✅ Роль выдана! Теперь доступны все кнопки.", ephemeral=True)

    @discord.ui.button(label="🔄 Reset HWID", style=ButtonStyle.red, custom_id="hwid_btn", row=1)
    async def hwid_btn(self, interaction: discord.Interaction, button: Button):
        if not has_premium_role(interaction.user):
            await interaction.response.send_message("❌ Нужна роль Zuev Premium!", ephemeral=True)
            return

        hwid = get_hwid(interaction)

        if not can_reset_hwid(hwid):
            last = datetime.fromisoformat(reset_log[hwid])
            next_time = last + timedelta(hours=RESET_COOLDOWN_HOURS)
            left = next_time - datetime.now()
            hours = int(left.total_seconds() // 3600)
            minutes = int((left.total_seconds() % 3600) // 60)
            await interaction.response.send_message(
                f"⏳ Сброс HWID через {hours}ч {minutes}мин",
                ephemeral=True
            )
            return

        if hwid in activated_users:
            del activated_users[hwid]
        reset_log[hwid] = datetime.now().isoformat()
        save_all()

        await interaction.response.send_message(
            f"✅ HWID сброшен! Следующий сброс через {RESET_COOLDOWN_HOURS}ч",
            ephemeral=True
        )

    @discord.ui.button(label="📊 Stats", style=ButtonStyle.gray, custom_id="stats_btn", row=2)
    async def stats_btn(self, interaction: discord.Interaction, button: Button):
        if not has_premium_role(interaction.user):
            await interaction.response.send_message("❌ Нужна роль Zuev Premium!", ephemeral=True)
            return

        hwid = get_hwid(interaction)

        if hwid in activated_users:
            exp = activated_users[hwid].get("expires")
            if exp and is_expired(exp):
                status = "❌ Истёк"
            else:
                status = "✅ Активен"
            time_left = format_time_left(exp)
        else:
            status = "❌ Не активирован"
            time_left = "—"

        await interaction.response.send_message(
            f"📊 **Твой статус:**\n"
            f"`{hwid}`\n"
            f"**Статус:** {status}\n"
            f"**Осталось:** {time_left}",
            ephemeral=True
        )

    @discord.ui.button(label="🔑 Generate Key", style=ButtonStyle.green, custom_id="gen_btn", row=2)
    async def gen_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("⛔ Только владелец!", ephemeral=True)
            return

        class GenModal(Modal, title="Создать ключ"):
            days_input = TextInput(
                label="Срок действия (дней)",
                placeholder="30",
                default="30",
                required=True
            )

            async def on_submit(self, modal_interaction: discord.Interaction):
                try:
                    days = int(self.days_input.value)
                except:
                    await modal_interaction.response.send_message("❌ Введи число!", ephemeral=True)
                    return

                key = "ZV-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                expires = (datetime.now() + timedelta(days=days)).isoformat()

                keys_db[key] = {
                    "used": False,
                    "hwid": None,
                    "expires": expires,
                    "created": datetime.now().isoformat()
                }
                save_all()

                await modal_interaction.response.send_message(
                    f"✅ **Ключ создан:**\n`{key}`\n⏳ {days} дней",
                    ephemeral=True
                )

        await interaction.response.send_modal(GenModal())

# ========== СЛЕШ-КОМАНДЫ ==========
@bot.tree.command(name="gen", description="Создать ключ")
async def gen_slash(interaction: discord.Interaction, days: int = 30):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ Только владелец!", ephemeral=True)
        return

    key = "ZV-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    expires = (datetime.now() + timedelta(days=days)).isoformat()

    keys_db[key] = {
        "used": False,
        "hwid": None,
        "expires": expires,
        "created": datetime.now().isoformat()
    }
    save_all()

    await interaction.response.send_message(f"✅ **Ключ:** `{key}`\n⏳ {days} дней", ephemeral=True)

@bot.tree.command(name="keys", description="Все ключи")
async def keys_slash(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ Только владелец!", ephemeral=True)
        return

    if not keys_db:
        await interaction.response.send_message("📭 Нет ключей", ephemeral=True)
        return

    text = "**📋 Ключи:**\n"
    for k, v in keys_db.items():
        status = "✅" if v["used"] else "❌"
        expires = v.get("expires", "бессрочно")[:10]
        hwid = v["hwid"] or "❓"
        text += f"{status} `{k}` | до {expires} | HWID: {hwid}\n"
    await interaction.response.send_message(text[:2000], ephemeral=True)

# ========== !sync ==========
@bot.command()
async def sync(ctx):
    if ctx.author.id != OWNER_ID:
        await ctx.send("⛔ Только владелец!")
        return
    try:
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"✅ Синхронизировано {len(synced)} команд!")
    except Exception as e:
        await ctx.send(f"❌ Ошибка: {e}")

# ========== АВТО-ПАНЕЛЬ ==========
PANEL_MESSAGE_ID = None

@bot.event
async def on_ready():
    print(f"\n✅ Бот запущен как {bot.user}")
    print(f"👑 Владелец: {OWNER_ID}")

    global PANEL_MESSAGE_ID
    channel = bot.get_channel(PANEL_CHANNEL_ID)
    if not channel:
        print("❌ Канал не найден!")
        return

    if PANEL_MESSAGE_ID:
        try:
            old = await channel.fetch_message(PANEL_MESSAGE_ID)
            await old.delete()
        except:
            pass

    embed = discord.Embed(
        title="🛠️ Zuev Control Panel",
        description=(
            "**Welcome to the control panel!**\n\n"
            "This panel is for the project: **Zuev Exclusive**\n"
            "If you're a buyer, click on the buttons below.\n\n"
            f"Sent by the owner • {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Reset HWID cooldown: {RESET_COOLDOWN_HOURS}h • Role: {PREMIUM_ROLE_NAME}")

    msg = await channel.send(embed=embed, view=ControlPanel())
    PANEL_MESSAGE_ID = msg.id
    print(f"✅ Панель в #{channel.name}")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    bot.run(TOKEN)
