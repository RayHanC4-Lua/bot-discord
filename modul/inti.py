from datetime import datetime, timedelta, timezone
import json
import os
import re

import discord
from discord import app_commands
from dotenv import load_dotenv


load_dotenv()
os.makedirs("unduhan", exist_ok=True)
os.makedirs("file_ai", exist_ok=True)

PEMILIK_ID = 1438447727477391381
TINGKAT_VIDEO = [720, 480, 360, 240, 144]
TINGKAT_AUDIO = [192, 128, 96, 64]
CONFIG_FILE = os.getenv("CONFIG_PATH", "bot_config.json")
FILE_BG = "background.png"
FILE_FONT = "font.ttf"
BANNER_DIR = os.path.join(os.path.dirname(CONFIG_FILE) or ".", "banners")
FOLDER_BOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(BANNER_DIR, exist_ok=True)


def path_banner(guild_id):
  return os.path.join(BANNER_DIR, f"{guild_id}.png")


def berkas_kode_bot():
  hasil = [os.path.join(FOLDER_BOT, "bot.py")]
  for akar, folder, nama_berkas in os.walk(os.path.join(FOLDER_BOT, "modul")):
    folder[:] = sorted(f for f in folder if f != "__pycache__")
    hasil += [
        os.path.join(akar, n) for n in sorted(nama_berkas) if n.endswith(".py")
    ]
  return [b for b in hasil if os.path.isfile(b)]


POLA_LINK = re.compile(r"(https?://|discord\.gg/|www\.)", re.IGNORECASE)


def muat_data():
  isi = {}
  if os.path.exists(CONFIG_FILE):
    try:
      with open(CONFIG_FILE, "r") as f:
        isi = json.load(f)
    except Exception:
      isi = {}
  isi.setdefault("log_channels", {})
  isi.setdefault("custom_commands", {})
  isi.setdefault("button_roles", [])
  isi.setdefault("welcome", {})
  isi.setdefault("autorole", {})
  isi.setdefault("antispam", {})
  isi.setdefault("harga", {})
  isi.setdefault("premium", {})
  isi.setdefault("pricelist", [])
  isi.setdefault("sticky", {})
  isi.setdefault("joinvoice", {})
  isi.setdefault("voice_sementara", [])
  isi.setdefault("color_panels", [])
  isi.setdefault("gaya_nama", {})
  return isi


def simpan_data():
  with open(CONFIG_FILE, "w") as f:
    json.dump(data, f, indent=4)


data = muat_data()
sedang_purge = set()
WAKTU_MULAI = None

AI_BASE_URL = os.getenv("AI_BASE_URL", "http://localhost:8080/v1").rstrip("/")
AI_API_KEY = os.getenv("AI_API_KEY", "not-needed")
AI_MODEL = os.getenv("AI_MODEL", "local-model")

KODE_ULANG = {429, 500, 502, 503, 504}
MAKS_ULANG_HTTP = 3
RIWAYAT_CHAT = {}
BATAS_RIWAYAT = 10
COOLDOWN_CHAT = {}
SESI_CHAT_AKTIF = set()


GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

RPC_ASSET_KEY = None


def presensi_default():
  kwargs = {"type": discord.ActivityType.playing, "name": "RyHanC"}
  if WAKTU_MULAI:
    kwargs["timestamps"] = {"start": int(WAKTU_MULAI.timestamp())}
  if client.application_id:
    kwargs["application_id"] = client.application_id
  if RPC_ASSET_KEY:
    kwargs["assets"] = {"large_image": RPC_ASSET_KEY, "large_text": "RyHanC"}
  return discord.Activity(**kwargs)


intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def cek_premium(guild_id):
  info = data["premium"].get(str(guild_id))
  if not info:
    return False, None
  sampai = info.get("sampai")
  if sampai is None:
    return True, None
  batas = datetime.fromisoformat(sampai)
  if discord.utils.utcnow() > batas:
    return False, None
  return True, batas


def bersihkan_error(e):
  return re.sub(r"\x1b\[[0-9;]*m", "", str(e))[:180]


MAKS_LANGKAH_AGEN = 5
TUGAS_AI = set()
ZONA_WIB = timezone(timedelta(hours=7))

DUMMY_PRODUK = [
    {"nama": "1000 Robux", "harga": "Rp 130.000", "stok": 25},
    {"nama": "500 Robux", "harga": "Rp 68.000", "stok": 40},
    {"nama": "Gamepass Premium", "harga": "Rp 45.000", "stok": 12},
    {"nama": "Jasa Desain Baju Roblox", "harga": "Rp 25.000", "stok": 5},
    {"nama": "Jasa Website Sederhana", "harga": "Rp 350.000", "stok": 3},
]


def teks_uptime():
  if not WAKTU_MULAI:
    return "tidak diketahui"
  detik = int((discord.utils.utcnow() - WAKTU_MULAI).total_seconds())
  hari, sisa = divmod(detik, 86400)
  jam, sisa = divmod(sisa, 3600)
  return f"{hari} hari {jam} jam {sisa // 60} menit"


def cari_member(guild, kunci, bawaan):
  if not kunci:
    return bawaan
  kunci = str(kunci).strip().lstrip("@").lower()
  angka = re.sub(r"\D", "", kunci)
  if len(angka) >= 15:
    ketemu = guild.get_member(int(angka))
    if ketemu:
      return ketemu
  for m in guild.members:
    if kunci in (m.name.lower(), m.display_name.lower()):
      return m
  for m in guild.members:
    if kunci in m.name.lower() or kunci in m.display_name.lower():
      return m
  return None


async def kirim_log(guild, embed):
  if guild is None:
    return
  channel_id = data["log_channels"].get(str(guild.id))
  if not channel_id:
    return
  channel = guild.get_channel(int(channel_id))
  if channel is None:
    return
  try:
    await channel.send(embed=embed)
  except Exception:
    pass
