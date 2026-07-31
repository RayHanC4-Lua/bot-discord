import os
import re
import json
import time
import asyncio
import urllib.request
import urllib.parse
import discord
from discord import app_commands
from dotenv import load_dotenv
import yt_dlp
import io
from PIL import Image, ImageDraw, ImageFont

load_dotenv()
os.makedirs("unduhan", exist_ok=True)

PEMILIK_ID = 1438447727477391381
TINGKAT_VIDEO = [720, 480, 360, 240, 144]
TINGKAT_AUDIO = [192, 128, 96, 64]
CONFIG_FILE = os.getenv("CONFIG_PATH", "bot_config.json")
FILE_BG = "background.png"
FILE_FONT = "font.ttf"
BANNER_DIR = os.path.join(os.path.dirname(CONFIG_FILE) or ".", "banners")
os.makedirs(BANNER_DIR, exist_ok=True)

def path_banner(guild_id):
    return os.path.join(BANNER_DIR, f"{guild_id}.png")
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

intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
lagu_terakhir = None

class DynamicRoleView(discord.ui.View):
    def __init__(self, role_id: int, label: str = "Ambil/Lepas Role"):
        super().__init__(timeout=None)
        self.role_id = role_id
        tombol = discord.ui.Button(label=label, style=discord.ButtonStyle.primary, custom_id=f"rt_{role_id}")
        tombol.callback = self.tombol_diklik
        self.add_item(tombol)

    async def tombol_diklik(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        if not role:
            await interaction.response.send_message("Role tidak ditemukan di server ini.", ephemeral=True)
            return
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"Role **{role.name}** berhasil dicabut.", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"Role **{role.name}** berhasil diambil.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Gagal. Posisikan role Bot di atas role tersebut pada pengaturan server.", ephemeral=True)

def bersihkan_error(e):
    return re.sub(r"\x1b\[[0-9;]*m", "", str(e))[:180]

def format_durasi(detik):
    if not detik:
        return "tidak diketahui"
    jam, sisa = divmod(int(detik), 3600)
    menit, dtk = divmod(sisa, 60)
    if jam:
        return f"{jam}:{menit:02d}:{dtk:02d}"
    return f"{menit}:{dtk:02d}"

def link_threads(url):
    url_bawah = url.lower()
    return "threads.net" in url_bawah or "threads.com" in url_bawah

def link_tiktok(url):
    url_bawah = url.lower()
    return "tiktok.com" in url_bawah or "vxtiktok.com" in url_bawah

def unduh_tiktok(url):
    api = "https://www.tikwm.com/api/?url=" + urllib.parse.quote(url, safe="")
    permintaan = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(permintaan, timeout=30) as respons:
        hasil = json.loads(respons.read().decode("utf-8", "ignore"))
    if hasil.get("code") != 0 or not hasil.get("data"):
        raise Exception("TikTok gagal via API. Kemungkinan link privat atau bukan video.")
    isi = hasil["data"]
    link = isi.get("play") or isi.get("wmplay")
    if not link:
        raise Exception("Link video TikTok tidak ditemukan di respons API.")
    if link.startswith("/"):
        link = "https://www.tikwm.com" + link
    path = f"unduhan/tiktok_{int(time.time())}.mp4"
    permintaan_video = urllib.request.Request(link, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(permintaan_video, timeout=120) as sumber, open(path, "wb") as berkas:
        berkas.write(sumber.read())
    return path, isi

def opsi_dasar():
    opsi = {
        "outtmpl": "unduhan/%(title).60s.%(ext)s",
        "noplaylist": True,
        "restrictfilenames": True,
        "quiet": True,
        "js_runtimes": {"node": {}},
    }
    if os.path.exists("cookies.txt"):
        opsi["cookiefile"] = "cookies.txt"
    return opsi

def unduh_threads(url):
    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Upgrade-Insecure-Requests": "1",
    }
    dasar = url.split("?")[0].rstrip("/")
    pola = [
        r'"video_versions"\s*:\s*\[\s*\{[^\]]*?"url"\s*:\s*"([^"]+)"',
        r'"playable_url(?:_quality_hd)?"\s*:\s*"([^"]+)"',
        r'property="og:video(?::secure_url)?"\s+content="([^"]+)"',
    ]
    for alamat in (url, dasar + "/embed/"):
        permintaan = urllib.request.Request(alamat, headers=header)
        try:
            with urllib.request.urlopen(permintaan, timeout=30) as respons:
                halaman = respons.read().decode("utf-8", "ignore")
        except Exception:
            continue
        for p in pola:
            hasil = re.search(p, halaman)
            if hasil:
                link = json.loads('"' + hasil.group(1) + '"').replace("&amp;", "&")
                path = f"unduhan/threads_{int(time.time())}.mp4"
                permintaan_video = urllib.request.Request(link, headers={"User-Agent": header["User-Agent"]})
                with urllib.request.urlopen(permintaan_video, timeout=120) as sumber, open(path, "wb") as berkas:
                    berkas.write(sumber.read())
                return path
    raise Exception("Video tidak ketemu di halaman Threads. Kemungkinan post privat atau bukan video.")

def ambil_info(target):
    if not target.startswith("http"):
        target = f"ytsearch1:{target}"
    with yt_dlp.YoutubeDL(opsi_dasar()) as ydl:
        info = ydl.extract_info(target, download=False)
    if "entries" in info:
        info = info["entries"][0]
    return info

def unduh(target, audio_saja, mutu):
    opsi = opsi_dasar()
    if audio_saja:
        opsi["format"] = "bestaudio/best"
        opsi["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": str(mutu),
        }]
    else:
        opsi["format"] = f"bestvideo[height<={mutu}]+bestaudio/best[height<={mutu}]/best"
        opsi["merge_output_format"] = "mp4"
    if not target.startswith("http"):
        target = f"ytsearch1:{target}"
    with yt_dlp.YoutubeDL(opsi) as ydl:
        info = ydl.extract_info(target, download=True)
        if "entries" in info:
            info = info["entries"][0]
        return info["requested_downloads"][0]["filepath"]

def unduh_bertahap(target, audio_saja, mutu_awal, batas):
    daftar = TINGKAT_AUDIO if audio_saja else TINGKAT_VIDEO
    for mutu in [m for m in daftar if m <= mutu_awal]:
        path = unduh(target, audio_saja, mutu)
        if os.path.getsize(path) <= batas:
            return path, mutu
        os.remove(path)
    raise Exception("File tetap melebihi batas upload walau sudah diturunkan ke mutu paling rendah.")

def batas_upload(interaction):
    return interaction.guild.filesize_limit if interaction.guild else 10 * 1024 * 1024

class PilihFormat(discord.ui.View):
    def __init__(self, target, pemilik):
        super().__init__(timeout=180)
        self.target = target
        self.pemilik = pemilik
        self.pesan = None

    async def interaction_check(self, interaction):
        if interaction.user.id != self.pemilik:
            await interaction.response.send_message("Tombol ini bukan punyamu.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for anak in self.children:
            anak.disabled = True
        if self.pesan:
            try:
                await self.pesan.edit(view=self)
            except Exception:
                pass

    async def jalankan(self, interaction, audio_saja, mutu):
        for anak in self.children:
            anak.disabled = True
        await interaction.response.edit_message(content="Sedang diunduh, tunggu sebentar.", view=self)
        self.stop()
        try:
            path, hasil = await asyncio.to_thread(unduh_bertahap, self.target, audio_saja, mutu, batas_upload(interaction))
        except Exception as e:
            await interaction.followup.send(f"Gagal download: {bersihkan_error(e)}")
            return
        label = f"{hasil} kbps" if audio_saja else f"{hasil}p"
        await interaction.followup.send(f"Selesai ({label}).", file=discord.File(path))
        os.remove(path)

    @discord.ui.button(label="Video 720p", style=discord.ButtonStyle.primary)
    async def video_tinggi(self, interaction: discord.Interaction, tombol: discord.ui.Button):
        await self.jalankan(interaction, False, 720)

    @discord.ui.button(label="Video 480p", style=discord.ButtonStyle.secondary)
    async def video_rendah(self, interaction: discord.Interaction, tombol: discord.ui.Button):
        await self.jalankan(interaction, False, 480)

    @discord.ui.button(label="MP3", style=discord.ButtonStyle.success)
    async def audio(self, interaction: discord.Interaction, tombol: discord.ui.Button):
        await self.jalankan(interaction, True, 192)

def buat_banner(nama, urutan, avatar_bytes, bg_path=None):
    lebar, tinggi = 1024, 400
    sumber_bg = bg_path if (bg_path and os.path.exists(bg_path)) else FILE_BG
    if os.path.exists(sumber_bg):
        bg = Image.open(sumber_bg).convert("RGB").resize((lebar, tinggi))
    else:
        bg = Image.new("RGB", (lebar, tinggi), (30, 30, 40))
    gambar = ImageDraw.Draw(bg)

    ukuran_foto = 150
    foto = Image.open(io.BytesIO(avatar_bytes)).convert("RGB").resize((ukuran_foto, ukuran_foto))
    topeng = Image.new("L", (ukuran_foto, ukuran_foto), 0)
    ImageDraw.Draw(topeng).ellipse((0, 0, ukuran_foto, ukuran_foto), fill=255)
    pos_x = (lebar - ukuran_foto) // 2
    pos_y = 30
    cincin = 7
    gambar.ellipse((pos_x - cincin, pos_y - cincin, pos_x + ukuran_foto + cincin, pos_y + ukuran_foto + cincin), fill=(255, 255, 255))
    bg.paste(foto, (pos_x, pos_y), topeng)

    try:
        font_besar = ImageFont.truetype(FILE_FONT, 100)
        font_nama = ImageFont.truetype(FILE_FONT, 58)
        font_kecil = ImageFont.truetype(FILE_FONT, 38)
    except Exception:
        font_besar = ImageFont.load_default()
        font_nama = ImageFont.load_default()
        font_kecil = ImageFont.load_default()

    def tulis_tengah(teks, font, y, warna=(255, 255, 255)):
        kotak = gambar.textbbox((0, 0), teks, font=font)
        lebar_teks = kotak[2] - kotak[0]
        x = (lebar - lebar_teks) // 2
        gambar.text((x + 3, y + 3), teks, font=font, fill=(0, 0, 0))
        gambar.text((x, y), teks, font=font, fill=warna)

    tulis_tengah("WELCOME", font_besar, 215)
    tulis_tengah(nama[:20], font_nama, 320, (255, 220, 120))
    tulis_tengah(f"Member ke-{urutan}", font_kecil, 355)

    hasil = io.BytesIO()
    bg.save(hasil, format="PNG")
    hasil.seek(0)
    return hasil

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

@client.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return
    info_sticky = data["sticky"].get(str(message.channel.id))
    if info_sticky:
        try:
            if info_sticky.get("terakhir"):
                try:
                    lama = await message.channel.fetch_message(int(info_sticky["terakhir"]))
                    await lama.delete()
                except Exception:
                    pass
            embed_sticky = discord.Embed(description=info_sticky["pesan"], color=discord.Color.blurple())
            baru = await message.channel.send(embed=embed_sticky)
            info_sticky["terakhir"] = baru.id
            simpan_data()
        except Exception:
            pass
    menit = data["antispam"].get(str(message.guild.id), 0)
    if not menit:
        return
    if message.author.guild_permissions.manage_messages:
        return
    if not message.author.joined_at:
        return
    umur = (discord.utils.utcnow() - message.author.joined_at).total_seconds() / 60
    if umur >= menit:
        return
    if not POLA_LINK.search(message.content):
        return
    try:
        await message.delete()
    except Exception:
        return
    embed = discord.Embed(title="Link member baru dihapus", color=discord.Color.dark_orange(), timestamp=discord.utils.utcnow())
    embed.add_field(name="User", value=f"{message.author.mention} ({message.author.name})", inline=False)
    embed.add_field(name="Channel", value=message.channel.mention)
    embed.add_field(name="Isi", value=message.content[:900] or "-", inline=False)
    await kirim_log(message.guild, embed)
    try:
        peringatan = await message.channel.send(f"{message.author.mention} member baru belum boleh mengirim link.")
        await asyncio.sleep(6)
        await peringatan.delete()
    except Exception:
        pass

@client.event
async def on_message_delete(message):
    if message.author.bot or message.guild is None:
        return
    if message.channel.id in sedang_purge:
        return
    embed = discord.Embed(title="Pesan dihapus", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="User", value=f"{message.author.mention} ({message.author.name})", inline=False)
    embed.add_field(name="Channel", value=message.channel.mention)
    embed.add_field(name="Isi", value=(message.content or "tidak ada teks")[:900], inline=False)
    await kirim_log(message.guild, embed)

@client.event
async def on_message_edit(before, after):
    if before.author.bot or before.guild is None or before.content == after.content:
        return
    embed = discord.Embed(title="Pesan diedit", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
    embed.add_field(name="User", value=f"{before.author.mention} ({before.author.name})", inline=False)
    embed.add_field(name="Channel", value=before.channel.mention)
    embed.add_field(name="Sebelum", value=(before.content or "-")[:900], inline=False)
    embed.add_field(name="Sesudah", value=(after.content or "-")[:900], inline=False)
    await kirim_log(before.guild, embed)

@client.event
async def on_member_join(member):
    embed = discord.Embed(title="Member masuk server", color=discord.Color.green(), timestamp=discord.utils.utcnow())
    embed.add_field(name="User", value=f"{member.mention} ({member.name})")
    embed.add_field(name="User ID", value=str(member.id))
    embed.add_field(name="Akun dibuat", value=discord.utils.format_dt(member.created_at, "R"), inline=False)
    await kirim_log(member.guild, embed)

    role_id = data["autorole"].get(str(member.guild.id))
    if role_id:
        role = member.guild.get_role(int(role_id))
        if role:
            try:
                await member.add_roles(role)
            except Exception:
                pass

    sambutan = data["welcome"].get(str(member.guild.id))
    if sambutan:
        channel = member.guild.get_channel(int(sambutan["channel"]))
        if channel:
            teks = sambutan["pesan"]
            teks = teks.replace("{user}", member.mention)
            teks = teks.replace("{server}", member.guild.name)
            teks = teks.replace("{jumlah}", str(member.guild.member_count))
            berkas = None
            try:
                avatar = await member.display_avatar.replace(size=256, format="png").read()
                data_gambar = await asyncio.to_thread(buat_banner, member.display_name, member.guild.member_count, avatar, path_banner(member.guild.id))
                berkas = discord.File(data_gambar, filename="welcome.png")
            except Exception:
                berkas = None
            try:
                if berkas:
                    await channel.send(content=teks[:2000], file=berkas)
                else:
                    await channel.send(teks[:2000])
            except Exception:
                pass

@client.event
async def on_member_remove(member):
    embed = discord.Embed(title="Member keluar atau dikick", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="User", value=f"{member.name}")
    embed.add_field(name="User ID", value=str(member.id))
    await kirim_log(member.guild, embed)

@client.event
async def on_member_update(before, after):
    if before.roles == after.roles:
        return
    embed = discord.Embed(title="Perubahan role member", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Target member", value=after.mention)
    ditambah = [r.mention for r in after.roles if r not in before.roles]
    dihapus = [r.mention for r in before.roles if r not in after.roles]
    if ditambah:
        embed.add_field(name="Role diberikan", value=", ".join(ditambah), inline=False)
    if dihapus:
        embed.add_field(name="Role dicabut", value=", ".join(dihapus), inline=False)
    await kirim_log(after.guild, embed)

@client.event
async def on_presence_update(before, after):
    global lagu_terakhir
    if after.id != PEMILIK_ID:
        return
    spotify_act = None
    for activity in after.activities:
        if isinstance(activity, discord.Spotify):
            spotify_act = activity
            break
    if spotify_act:
        if spotify_act.track_id == lagu_terakhir:
            return
        lagu_terakhir = spotify_act.track_id
        detik = int(spotify_act.duration.total_seconds())
        info_lagu = f"{spotify_act.title} - {spotify_act.artist} | {spotify_act.album} | {detik // 60}:{detik % 60:02d}"
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=info_lagu[:128]))
    else:
        if lagu_terakhir is None:
            return
        lagu_terakhir = None
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/help | ryhanc.wtf"))

@client.event
async def on_ready():
    global WAKTU_MULAI
    if WAKTU_MULAI is None:
        WAKTU_MULAI = discord.utils.utcnow()
    await tree.sync()
    for br in data.get("button_roles", []):
        client.add_view(DynamicRoleView(br["role_id"], br["label"]), message_id=br["message_id"])
    client.add_view(TiketPanelView())
    client.add_view(TiketCloseView())
    for cp in data.get("color_panels", []):
        try:
            client.add_view(WarnaView([(r["id"], r["label"]) for r in cp["roles"]]), message_id=cp["message_id"])
        except Exception:
            pass
    tersisa = []
    for cid in list(data.get("voice_sementara", [])):
        ch = client.get_channel(int(cid))
        if ch is None:
            continue
        if len(ch.members) == 0:
            try:
                await ch.delete(reason="bersih voice sementara")
            except Exception:
                pass
            continue
        tersisa.append(cid)
    data["voice_sementara"] = tersisa
    simpan_data()
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/help | ryhanc.wtf"))
    print(f"Bot online sebagai {client.user}")

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        pesan = "Kamu tidak punya izin untuk memakai perintah ini."
    else:
        pesan = f"Error: {error}"
    if interaction.response.is_done():
        await interaction.followup.send(pesan[:1900], ephemeral=True)
    else:
        await interaction.response.send_message(pesan[:1900], ephemeral=True)

async def isi_cc(interaction: discord.Interaction, current: str):
    daftar = data["custom_commands"].get(str(interaction.guild_id), {})
    cocok = [n for n in sorted(daftar) if current.lower() in n]
    return [app_commands.Choice(name=n, value=n) for n in cocok[:25]]

async def kabari_pemilik(judul, guild, warna):
    try:
        pemilik = await client.fetch_user(PEMILIK_ID)
    except Exception:
        return
    embed = discord.Embed(title=judul, color=warna, timestamp=discord.utils.utcnow())
    embed.add_field(name="Server", value=f"{guild.name} ({guild.id})", inline=False)
    embed.add_field(name="Member", value=str(guild.member_count or 0))
    embed.add_field(name="Total server sekarang", value=str(len(client.guilds)))
    try:
        await pemilik.send(embed=embed)
    except Exception:
        pass

@client.event
async def on_guild_join(guild):
    await kabari_pemilik("Bot masuk server baru", guild, discord.Color.green())

@client.event
async def on_guild_remove(guild):
    await kabari_pemilik("Bot dikeluarkan dari server", guild, discord.Color.red())

@tree.command(name="stats", description="Lihat statistik bot")
async def stats(interaction: discord.Interaction):
    total_server = len(client.guilds)
    total_member = sum(g.member_count or 0 for g in client.guilds)
    unik = len({m.id for g in client.guilds for m in g.members if not m.bot})
    if WAKTU_MULAI:
        detik = int((discord.utils.utcnow() - WAKTU_MULAI).total_seconds())
        hari, sisa = divmod(detik, 86400)
        jam, sisa = divmod(sisa, 3600)
        menit = sisa // 60
        uptime = f"{hari}h {jam}j {menit}m"
    else:
        uptime = "tidak diketahui"
    embed = discord.Embed(title="Statistik bot", color=discord.Color.blurple(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Server", value=str(total_server))
    embed.add_field(name="Total member", value=str(total_member))
    embed.add_field(name="User unik", value=str(unik))
    embed.add_field(name="Ping", value=f"{round(client.latency * 1000)} ms")
    embed.add_field(name="Uptime", value=uptime)
    await interaction.response.send_message(embed=embed)

GAYA_NAMA = {
    "polos": {"kategori": "{n}", "teks": "{n}", "suara": "{n}"},
    "bintang": {"kategori": "\u2726\u2501\u2501\u2501\u2501\u2501 \u22c6\uff61\u00b0\u2727 {n} \u2727\u00b0\uff61\u22c6 \u2501\u2501\u2501\u2501\u2501\u2726", "teks": "\u22c6\uff61\u00b0\u2727-{n}-\u2727\u00b0\uff61\u22c6", "suara": "\u22c6\uff61\u00b0\u2727 {n} \u2727\u00b0\uff61\u22c6"},
    "lembut": {"kategori": "\u0b68\u0b67 \u22c6 {n} \u22c6 \u0b68\u0b67", "teks": "\u02da\u208a\u2027-{n}-\u2027\u208a\u02da", "suara": "\u02da\u208a\u2027 {n} \u2027\u208a\u02da"},
    "tegas": {"kategori": "\u25b0\u25b0\u25b0\u25b0 {n} \u25b0\u25b0\u25b0\u25b0", "teks": "\u2317-{n}", "suara": "\u2317 {n}"},
}

def rias_nama(nama, jenis, gaya):
    pola = GAYA_NAMA.get(gaya, GAYA_NAMA["polos"])[jenis]
    return pola.format(n=nama)[:95]

PILIHAN_GAYA = [
    app_commands.Choice(name="Polos tanpa hiasan", value="polos"),
    app_commands.Choice(name="Bintang", value="bintang"),
    app_commands.Choice(name="Lembut", value="lembut"),
    app_commands.Choice(name="Tegas", value="tegas"),
]

PRESET_SETUP = {
    "jualan": {
        "teks": {
            "INFORMATION": ["portal", "announcement", "rules", "link-invite", "giveaway"],
            "STOCK INFORMATION": ["flash-sale", "item-limited", "value-changes"],
            "ROBUX": ["robux-vilog", "robux-community"],
            "TRANSACTION": ["order", "cashout", "payment"],
            "REPUTATION": ["rating-server", "leaderboard", "order-log"],
            "TESTIMONI": ["testimoni-robux", "testimoni-limited", "testimoni-gift"],
            "PUBLIC": ["chat", "bot-command", "market-public"],
        },
        "suara": {},
        "role": [
            ("Admin", discord.Color.red(), True),
            ("Moderator", discord.Color.orange(), True),
            ("Member", discord.Color.blue(), False),
            ("Pembeli", discord.Color.green(), False),
        ],
    },
    "komunitas": {
        "teks": {
            "INFORMASI": ["rules", "announcement", "information", "update-server"],
            "ROLES": ["display-roles", "warna-nama", "seting-voice"],
            "KOMUNITAS": ["general", "media-share", "bot-command", "suggestions"],
            "ROBLOX": ["game-update", "screenshot", "clip-highlight", "cari-teman-main", "showcase-karya"],
            "EVENT": ["event-info", "giveaway"],
            "SUPPORT": ["help", "bug-report"],
        },
        "suara": {
            "VOICE AREA": ["Join to Create", "General 1", "General 2", "Main Bareng", "AFK"],
            "MUSIC AREA": ["Music 1", "Music 2"],
        },
        "role": [
            ("Admin", discord.Color.red(), True),
            ("Moderator", discord.Color.orange(), True),
            ("Member", discord.Color.blue(), False),
            ("Roblox Developer", discord.Color.purple(), False),
            ("Content Creator", discord.Color.teal(), False),
            ("Event Winner", discord.Color.gold(), False),
        ],
    },
}

@tree.command(name="setup", description="Buat struktur channel dan role sesuai tipe server")
@app_commands.choices(tipe=[
    app_commands.Choice(name="Server jualan", value="jualan"),
    app_commands.Choice(name="Komunitas Roblox", value="komunitas"),
])
@app_commands.choices(gaya=PILIHAN_GAYA)
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, tipe: app_commands.Choice[str], gaya: app_commands.Choice[str] = None):
    if not interaction.guild.me.guild_permissions.manage_channels or not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message("Bot butuh izin Manage Channels dan Manage Roles. Aktifkan dulu di pengaturan server.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    preset = PRESET_SETUP[tipe.value]
    kode_gaya = gaya.value if gaya else "polos"
    guild = interaction.guild
    dibuat = []
    for nama, warna, terpisah in preset["role"]:
        ada = discord.utils.get(guild.roles, name=nama)
        if ada is None:
            try:
                await guild.create_role(name=nama, color=warna, hoist=terpisah, reason="setup bot")
                dibuat.append(f"role {nama}")
            except Exception:
                pass
    for nama_kat, daftar_channel in preset["teks"].items():
        tampil_kat = rias_nama(nama_kat, "kategori", kode_gaya)
        kategori = discord.utils.get(guild.categories, name=tampil_kat) or discord.utils.get(guild.categories, name=nama_kat)
        if kategori is None:
            try:
                kategori = await guild.create_category(tampil_kat, reason="setup bot")
                data["gaya_nama"][str(kategori.id)] = nama_kat
                dibuat.append(f"kategori {nama_kat}")
            except Exception:
                continue
        for nama_ch in daftar_channel:
            tampil_ch = rias_nama(nama_ch, "teks", kode_gaya)
            sudah_ada = discord.utils.get(kategori.channels, name=nama_ch) or discord.utils.get(kategori.channels, name=tampil_ch.lower().replace(" ", "-"))
            if sudah_ada is None:
                try:
                    ch_baru = await guild.create_text_channel(tampil_ch, category=kategori, reason="setup bot")
                    data["gaya_nama"][str(ch_baru.id)] = nama_ch
                    dibuat.append(f"channel {nama_ch}")
                except Exception:
                    pass
    for nama_kat, daftar_suara in preset["suara"].items():
        tampil_kat = rias_nama(nama_kat, "kategori", kode_gaya)
        kategori = discord.utils.get(guild.categories, name=tampil_kat) or discord.utils.get(guild.categories, name=nama_kat)
        if kategori is None:
            try:
                kategori = await guild.create_category(tampil_kat, reason="setup bot")
                data["gaya_nama"][str(kategori.id)] = nama_kat
                dibuat.append(f"kategori {nama_kat}")
            except Exception:
                continue
        for nama_vc in daftar_suara:
            tampil_vc = rias_nama(nama_vc, "suara", kode_gaya)
            sudah_ada = discord.utils.get(kategori.voice_channels, name=nama_vc) or discord.utils.get(kategori.voice_channels, name=tampil_vc)
            if sudah_ada is None:
                try:
                    vc_baru = await guild.create_voice_channel(tampil_vc, category=kategori, reason="setup bot")
                    data["gaya_nama"][str(vc_baru.id)] = nama_vc
                    dibuat.append(f"voice {nama_vc}")
                    if nama_vc == "Join to Create":
                        data["joinvoice"][str(guild.id)] = {"hub": vc_baru.id}
                except Exception:
                    pass
    simpan_data()
    if dibuat:
        ringkas = "\n".join(dibuat[:40])
        await interaction.followup.send(f"Setup {tipe.name} selesai. Yang dibuat:\n{ringkas}", ephemeral=True)
    else:
        await interaction.followup.send("Semua struktur sudah ada, tidak ada yang perlu dibuat.", ephemeral=True)

@tree.command(name="hapussetup", description="Hapus channel dan role yang dibuat oleh setup")
@app_commands.choices(tipe=[
    app_commands.Choice(name="Server jualan", value="jualan"),
    app_commands.Choice(name="Komunitas Roblox", value="komunitas"),
])
@app_commands.checks.has_permissions(administrator=True)
async def hapussetup(interaction: discord.Interaction, tipe: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)
    preset = PRESET_SETUP[tipe.value]
    guild = interaction.guild
    dihapus = 0
    nama_channel = {c for daftar in preset["teks"].values() for c in daftar}
    nama_suara = {v for daftar in preset["suara"].values() for v in daftar}
    nama_kategori = set(preset["teks"].keys()) | set(preset["suara"].keys())
    nama_role = {r[0] for r in preset["role"]}
    id_polos = {int(cid): nm for cid, nm in data.get("gaya_nama", {}).items()}
    for channel in list(guild.channels):
        if isinstance(channel, discord.CategoryChannel):
            continue
        polos = id_polos.get(channel.id, channel.name)
        if polos in nama_channel or polos in nama_suara:
            try:
                await channel.delete(reason="hapus setup")
                data["gaya_nama"].pop(str(channel.id), None)
                dihapus += 1
            except Exception:
                pass
    for kategori in list(guild.categories):
        polos = id_polos.get(kategori.id, kategori.name)
        if polos in nama_kategori:
            try:
                await kategori.delete(reason="hapus setup")
                data["gaya_nama"].pop(str(kategori.id), None)
                dihapus += 1
            except Exception:
                pass
    for role in list(guild.roles):
        if role.name in nama_role and role < guild.me.top_role:
            try:
                await role.delete(reason="hapus setup")
                dihapus += 1
            except Exception:
                pass
    await interaction.followup.send(f"{dihapus} channel, kategori, dan role hasil setup dihapus.", ephemeral=True)

TIKET_TIPE = [
    ("order", "Order"),
    ("report", "Report"),
]

async def buka_tiket(interaction, kode, label):
    guild = interaction.guild
    if not guild.me.guild_permissions.manage_channels:
        await interaction.response.send_message("Bot butuh izin Manage Channels untuk membuat tiket.", ephemeral=True)
        return
    kategori = discord.utils.get(guild.categories, name="TIKET")
    if kategori is None:
        try:
            kategori = await guild.create_category("TIKET", reason="kategori tiket")
        except Exception:
            await interaction.response.send_message("Gagal membuat kategori TIKET.", ephemeral=True)
            return
    for ch in kategori.text_channels:
        if ch.topic and f"pemilik:{interaction.user.id}" in ch.topic and f"tipe:{kode}" in ch.topic:
            await interaction.response.send_message(f"Kamu sudah punya tiket {label} yang terbuka: {ch.mention}", ephemeral=True)
            return
    role_admin = discord.utils.get(guild.roles, name="Admin")
    role_mod = discord.utils.get(guild.roles, name="Moderator")
    izin = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
    }
    if role_admin:
        izin[role_admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    if kode == "report" and role_mod:
        izin[role_mod] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    nama = f"{kode}-{interaction.user.name}"[:90]
    try:
        channel = await guild.create_text_channel(nama, category=kategori, overwrites=izin, topic=f"pemilik:{interaction.user.id}|tipe:{kode}", reason="tiket baru")
    except Exception as e:
        await interaction.response.send_message(f"Gagal membuat tiket: {bersihkan_error(e)}", ephemeral=True)
        return
    if kode == "report":
        deskripsi = f"Halo {interaction.user.mention}, jelaskan laporanmu di sini. Sertakan nama pengguna yang dilaporkan dan bukti seperti screenshot atau video kalau ada. Tim akan segera menindaklanjuti."
    else:
        deskripsi = f"Halo {interaction.user.mention}, silakan jelaskan pesanan atau pertanyaanmu di sini. Admin akan segera membantu."
    embed = discord.Embed(title=f"Tiket {label}", description=deskripsi, color=discord.Color.green(), timestamp=discord.utils.utcnow())
    penyebut = []
    if role_admin:
        penyebut.append(role_admin.mention)
    if kode == "report" and role_mod:
        penyebut.append(role_mod.mention)
    await channel.send(content=f"{interaction.user.mention} {' '.join(penyebut)}", embed=embed, view=TiketCloseView())
    await interaction.response.send_message(f"Tiket berhasil dibuat: {channel.mention}", ephemeral=True)

class TiketTombol(discord.ui.Button):
    def __init__(self, kode, label):
        gaya = discord.ButtonStyle.danger if kode == "report" else discord.ButtonStyle.primary
        super().__init__(label=label, style=gaya, custom_id=f"tiket_buka:{kode}")
        self.kode = kode
        self.label_tiket = label

    async def callback(self, interaction: discord.Interaction):
        await buka_tiket(interaction, self.kode, self.label_tiket)

class TiketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for kode, label in TIKET_TIPE:
            self.add_item(TiketTombol(kode, label))

class TiketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Tutup Tiket", style=discord.ButtonStyle.danger, custom_id="tiket_tutup")
    async def tutup(self, interaction: discord.Interaction, tombol: discord.ui.Button):
        channel = interaction.channel
        pemilik_ok = False
        if channel.topic:
            pemilik_ok = f"pemilik:{interaction.user.id}" in channel.topic
        if not (interaction.user.guild_permissions.manage_channels or pemilik_ok):
            await interaction.response.send_message("Hanya admin atau pembuat tiket yang bisa menutup tiket ini.", ephemeral=True)
            return
        await interaction.response.send_message("Menyimpan transcript, tiket ditutup dalam 5 detik.")
        try:
            baris = []
            async for pesan in channel.history(limit=500, oldest_first=True):
                waktu = pesan.created_at.strftime("%Y-%m-%d %H:%M")
                isi_pesan = pesan.content or ""
                if pesan.embeds:
                    isi_pesan += " [embed]"
                if pesan.attachments:
                    isi_pesan += " " + " ".join(a.url for a in pesan.attachments)
                baris.append(f"[{waktu}] {pesan.author}: {isi_pesan}")
            teks_transcript = "\n".join(baris) if baris else "Tiket kosong."
            berkas = discord.File(io.BytesIO(teks_transcript.encode("utf-8")), filename=f"transcript-{channel.name}.txt")
            embed_log = discord.Embed(title="Transcript tiket", color=discord.Color.dark_grey(), timestamp=discord.utils.utcnow())
            embed_log.add_field(name="Channel", value=channel.name, inline=False)
            embed_log.add_field(name="Ditutup oleh", value=interaction.user.mention)
            id_log = data["log_channels"].get(str(channel.guild.id))
            if id_log:
                ch_log = channel.guild.get_channel(int(id_log))
                if ch_log:
                    await ch_log.send(embed=embed_log, file=berkas)
        except Exception:
            pass
        await asyncio.sleep(5)
        try:
            await channel.delete(reason="tiket ditutup")
        except Exception:
            pass

@tree.command(name="tiketpanel", description="Kirim panel tombol tiket order dan report")
@app_commands.checks.has_permissions(administrator=True)
async def tiketpanel(interaction: discord.Interaction):
    embed = discord.Embed(title="Order dan Report", description="Klik tombol sesuai kebutuhanmu untuk membuka tiket privat.", color=discord.Color.blurple())
    embed.add_field(name="Order", value="Order jasa, item, atau tanya-tanya. Dilihat kamu dan Admin.", inline=False)
    embed.add_field(name="Report", value="Laporkan pelanggaran, bug, atau masalah member. Dilihat kamu, Admin, dan Moderator.", inline=False)
    await interaction.response.send_message(embed=embed, view=TiketPanelView())

class TestiModal(discord.ui.Modal, title="Kirim Testimoni"):
    def __init__(self, channel_target):
        super().__init__()
        self.channel_target = channel_target

    rating = discord.ui.TextInput(label="Rating 1 sampai 5", placeholder="contoh: 5", max_length=1)
    komentar = discord.ui.TextInput(label="Komentar", style=discord.TextStyle.paragraph, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            angka = int(str(self.rating))
        except Exception:
            angka = 0
        angka = max(0, min(5, angka))
        bintang = "★" * angka + "☆" * (5 - angka)
        embed = discord.Embed(description=str(self.komentar), color=discord.Color.gold(), timestamp=discord.utils.utcnow())
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Rating", value=f"{bintang} ({angka}/5)")
        try:
            await self.channel_target.send(embed=embed)
            await interaction.response.send_message("Terima kasih, testimoni kamu sudah dikirim.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Gagal mengirim: {bersihkan_error(e)}", ephemeral=True)

@tree.command(name="testi", description="Kirim testimoni ke channel ini")
async def testi(interaction: discord.Interaction):
    await interaction.response.send_modal(TestiModal(interaction.channel))

@tree.command(name="hargaset", description="Tambah atau ubah harga sebuah item")
@app_commands.describe(item="Nama item, contoh: 1000 Robux VILOG", harga="Harga, contoh: Rp 130.000")
@app_commands.checks.has_permissions(administrator=True)
async def hargaset(interaction: discord.Interaction, item: str, harga: str):
    gid = str(interaction.guild_id)
    data["harga"].setdefault(gid, {})[item[:80]] = harga[:80]
    simpan_data()
    await interaction.response.send_message(f"Harga disimpan: {item} = {harga}", ephemeral=True)

@tree.command(name="hargahapus", description="Hapus satu item dari daftar harga")
@app_commands.checks.has_permissions(administrator=True)
async def hargahapus(interaction: discord.Interaction, item: str):
    gid = str(interaction.guild_id)
    daftar = data["harga"].get(gid, {})
    if item not in daftar:
        await interaction.response.send_message("Item itu tidak ada di daftar harga.", ephemeral=True)
        return
    daftar.pop(item)
    simpan_data()
    await interaction.response.send_message(f"Item {item} dihapus dari daftar harga.", ephemeral=True)

@tree.command(name="harga", description="Lihat daftar harga")
async def harga(interaction: discord.Interaction):
    gid = str(interaction.guild_id)
    daftar = data["harga"].get(gid, {})
    if not daftar:
        await interaction.response.send_message("Daftar harga masih kosong.")
        return
    embed = discord.Embed(title="Daftar Harga", color=discord.Color.green(), timestamp=discord.utils.utcnow())
    for item, nilai in list(daftar.items())[:25]:
        embed.add_field(name=item, value=nilai, inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="stickyset", description="Pasang pesan sticky yang selalu muncul di bawah channel ini")
@app_commands.checks.has_permissions(administrator=True)
async def stickyset(interaction: discord.Interaction, pesan: str):
    data["sticky"][str(interaction.channel_id)] = {"pesan": pesan, "terakhir": None}
    simpan_data()
    await interaction.response.send_message("Sticky message dipasang di channel ini.", ephemeral=True)

@tree.command(name="stickyhapus", description="Matikan pesan sticky di channel ini")
@app_commands.checks.has_permissions(administrator=True)
async def stickyhapus(interaction: discord.Interaction):
    info = data["sticky"].pop(str(interaction.channel_id), None)
    simpan_data()
    if info and info.get("terakhir"):
        try:
            lama = await interaction.channel.fetch_message(int(info["terakhir"]))
            await lama.delete()
        except Exception:
            pass
    await interaction.response.send_message("Sticky message dimatikan.", ephemeral=True)

WARNA_ROLE = [
    ("Yellow", 0xF1C40F),
    ("Green", 0x2ECC71),
    ("Orange", 0xE67E22),
    ("Grey", 0x95A5A6),
    ("White", 0xFFFFFE),
    ("Pink", 0xFF69B4),
    ("Red", 0xE74C3C),
    ("Purple", 0x9B59B6),
    ("Navy", 0x34495E),
    ("Blue", 0x3498DB),
    ("Light Pink", 0xFFC0CB),
]

class WarnaTombol(discord.ui.Button):
    def __init__(self, role_id, label):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, custom_id=f"warna_{role_id}")
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        role = guild.get_role(self.role_id)
        if role is None:
            await interaction.response.send_message("Role warna ini sudah dihapus dari server.", ephemeral=True)
            return
        nama_warna = {n for n, _ in WARNA_ROLE}
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"Warna {role.name} dilepas.", ephemeral=True)
                return
            lama = [r for r in interaction.user.roles if r.name in nama_warna and r.id != role.id]
            if lama:
                await interaction.user.remove_roles(*lama)
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Warna namamu sekarang {role.name}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Gagal. Posisikan role Bot di atas semua role warna pada pengaturan server.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Gagal: {bersihkan_error(e)}", ephemeral=True)

class WarnaView(discord.ui.View):
    def __init__(self, pasangan):
        super().__init__(timeout=None)
        for role_id, label in pasangan:
            self.add_item(WarnaTombol(role_id, label))

@tree.command(name="colorpanel", description="Buat role warna nama dan kirim panel tombolnya")
@app_commands.checks.has_permissions(administrator=True)
async def colorpanel(interaction: discord.Interaction):
    if not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message("Bot butuh izin Manage Roles.", ephemeral=True)
        return
    await interaction.response.defer()
    guild = interaction.guild
    pasangan = []
    for nama, kode in WARNA_ROLE:
        role = discord.utils.get(guild.roles, name=nama)
        if role is None:
            try:
                role = await guild.create_role(name=nama, color=discord.Color(kode), reason="panel warna")
            except Exception:
                continue
        pasangan.append((role.id, nama))
    if not pasangan:
        await interaction.followup.send("Gagal membuat role warna.", ephemeral=True)
        return
    embed = discord.Embed(title="Warna Nama", description="Klik tombol untuk mengubah warna namamu. Warna lama otomatis dilepas. Klik warna yang sama untuk melepasnya.", color=discord.Color.blurple())
    tampilan = WarnaView(pasangan)
    pesan = await interaction.followup.send(embed=embed, view=tampilan, wait=True)
    data["color_panels"].append({"message_id": pesan.id, "roles": [{"id": rid, "label": lab} for rid, lab in pasangan]})
    simpan_data()

@tree.command(name="setjoinvoice", description="Tentukan voice channel Join to Create")
@app_commands.describe(channel="Voice channel yang jadi pintu masuk")
@app_commands.checks.has_permissions(administrator=True)
async def setjoinvoice(interaction: discord.Interaction, channel: discord.VoiceChannel):
    data["joinvoice"][str(interaction.guild_id)] = {"hub": channel.id}
    simpan_data()
    await interaction.response.send_message(f"{channel.name} sekarang jadi Join to Create. Member yang masuk ke sana otomatis dibuatkan voice sendiri.", ephemeral=True)

@client.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    info = data["joinvoice"].get(str(member.guild.id))
    if info and after.channel is not None and after.channel.id == int(info["hub"]):
        try:
            izin = {member: discord.PermissionOverwrite(manage_channels=True, move_members=True, mute_members=True)}
            baru = await member.guild.create_voice_channel(f"Room {member.display_name}"[:90], category=after.channel.category, overwrites=izin, reason="voice sementara")
            await member.move_to(baru)
            data["voice_sementara"].append(baru.id)
            simpan_data()
        except Exception:
            pass
    if before.channel is not None and before.channel.id in data["voice_sementara"] and len(before.channel.members) == 0:
        try:
            await before.channel.delete(reason="voice sementara kosong")
        except Exception:
            pass
        try:
            data["voice_sementara"].remove(before.channel.id)
            simpan_data()
        except Exception:
            pass

@tree.command(name="gayanama", description="Ubah gaya nama channel dan kategori yang dibuat setup")
@app_commands.choices(tipe=[
    app_commands.Choice(name="Server jualan", value="jualan"),
    app_commands.Choice(name="Komunitas Roblox", value="komunitas"),
])
@app_commands.choices(gaya=PILIHAN_GAYA)
@app_commands.checks.has_permissions(administrator=True)
async def gayanama(interaction: discord.Interaction, tipe: app_commands.Choice[str], gaya: app_commands.Choice[str]):
    if not interaction.guild.me.guild_permissions.manage_channels:
        await interaction.response.send_message("Bot butuh izin Manage Channels.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    preset = PRESET_SETUP[tipe.value]
    guild = interaction.guild
    nama_teks = {c for daftar in preset["teks"].values() for c in daftar}
    nama_suara = {v for daftar in preset["suara"].values() for v in daftar}
    nama_kategori = set(preset["teks"].keys()) | set(preset["suara"].keys())
    id_polos = {int(cid): nm for cid, nm in data.get("gaya_nama", {}).items()}
    diubah = 0
    for kategori in list(guild.categories):
        polos = id_polos.get(kategori.id)
        if polos is None and kategori.name in nama_kategori:
            polos = kategori.name
        if polos is None:
            continue
        baru = rias_nama(polos, "kategori", gaya.value)
        if baru == kategori.name:
            continue
        try:
            await kategori.edit(name=baru, reason="ubah gaya nama")
            data["gaya_nama"][str(kategori.id)] = polos
            diubah += 1
        except Exception:
            pass
    for channel in list(guild.channels):
        if isinstance(channel, discord.CategoryChannel):
            continue
        polos = id_polos.get(channel.id)
        if polos is None:
            if channel.name in nama_teks:
                polos = channel.name
            elif channel.name in nama_suara:
                polos = channel.name
        if polos is None:
            continue
        jenis = "suara" if isinstance(channel, discord.VoiceChannel) else "teks"
        baru = rias_nama(polos, jenis, gaya.value)
        try:
            await channel.edit(name=baru, reason="ubah gaya nama")
            data["gaya_nama"][str(channel.id)] = polos
            diubah += 1
        except Exception:
            pass
    simpan_data()
    if diubah:
        await interaction.followup.send(f"{diubah} channel dan kategori diubah ke gaya {gaya.name}.", ephemeral=True)
    else:
        await interaction.followup.send("Tidak ada yang diubah. Pastikan channelnya memang dibuat lewat setup dan tipe presetnya benar.", ephemeral=True)

@tree.command(name="setbanner", description="Atur gambar background welcome khusus server ini")
@app_commands.describe(gambar="Upload gambar, idealnya rasio 1024x400")
@app_commands.checks.has_permissions(administrator=True)
async def setbanner(interaction: discord.Interaction, gambar: discord.Attachment):
    if not gambar.content_type or not gambar.content_type.startswith("image/"):
        await interaction.response.send_message("File harus berupa gambar PNG atau JPG.", ephemeral=True)
        return
    if gambar.size > 8 * 1024 * 1024:
        await interaction.response.send_message("Ukuran gambar maksimal 8 MB.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        data_byte = await gambar.read()
        def simpan():
            img = Image.open(io.BytesIO(data_byte)).convert("RGB").resize((1024, 400))
            img.save(path_banner(interaction.guild_id), format="PNG")
        await asyncio.to_thread(simpan)
    except Exception as e:
        await interaction.followup.send(f"Gagal memproses gambar: {bersihkan_error(e)}", ephemeral=True)
        return
    try:
        avatar = await interaction.user.display_avatar.replace(size=256, format="png").read()
        preview = await asyncio.to_thread(buat_banner, interaction.user.display_name, interaction.guild.member_count, avatar, path_banner(interaction.guild_id))
        await interaction.followup.send("Background welcome khusus server ini berhasil diatur. Ini contoh tampilannya:", file=discord.File(preview, filename="preview.png"), ephemeral=True)
    except Exception:
        await interaction.followup.send("Background welcome khusus server ini berhasil diatur.", ephemeral=True)

@tree.command(name="hapusbanner", description="Kembalikan background welcome ke bawaan bot")
@app_commands.checks.has_permissions(administrator=True)
async def hapusbanner(interaction: discord.Interaction):
    p = path_banner(interaction.guild_id)
    if os.path.exists(p):
        try:
            os.remove(p)
        except Exception:
            pass
        await interaction.response.send_message("Background welcome dikembalikan ke bawaan bot.", ephemeral=True)
    else:
        await interaction.response.send_message("Server ini belum punya background khusus.", ephemeral=True)

HELP_KATEGORI = {
    "Setup dan Tampilan": [
        ("/setup", "Bikin struktur channel dan role otomatis (admin)"),
        ("/gayanama", "Ubah gaya hiasan nama channel (admin)"),
        ("/colorpanel", "Kirim panel warna nama untuk member (admin)"),
        ("/setbanner", "Atur gambar welcome khusus server ini (admin)"),
        ("/hapusbanner", "Kembalikan welcome ke bawaan bot (admin)"),
        ("/setwelcome", "Atur pesan sambutan member baru (admin)"),
        ("/setjoinvoice", "Atur voice Join to Create (admin)"),
        ("/hapussetup", "Hapus channel dan role buatan setup (admin)"),
    ],
    "Moderasi dan Log": [
        ("/setlog", "Daftarkan channel security log (admin)"),
        ("/setantispam", "Blokir link dari member baru (admin)"),
        ("/purge", "Hapus banyak pesan sekaligus (admin)"),
        ("/pengaturan", "Lihat pengaturan bot di server ini"),
        ("/reset", "Matikan salah satu fitur (admin)"),
    ],
    "Member dan Role": [
        ("/setautorole", "Role otomatis untuk member baru (admin)"),
        ("/giverole", "Beri role ke member (admin)"),
        ("/takerole", "Cabut role dari member (admin)"),
        ("/buttonrole", "Buat tombol ambil role mandiri (admin)"),
    ],
    "Tiket dan Jualan": [
        ("/tiketpanel", "Kirim panel tiket order dan report (admin)"),
        ("/harga", "Lihat daftar harga"),
        ("/hargaset", "Tambah atau ubah harga (admin)"),
        ("/hargahapus", "Hapus item dari daftar harga (admin)"),
        ("/testi", "Kirim testimoni ke channel ini"),
    ],
    "Utilitas": [
        ("/download", "Download video atau mp3 dari link atau judul"),
        ("/cc", "Jalankan custom command"),
        ("/addcmd", "Buat custom command baru (admin)"),
        ("/delcmd", "Hapus custom command (admin)"),
        ("/stickyset", "Pasang pesan sticky di channel (admin)"),
        ("/stickyhapus", "Matikan pesan sticky (admin)"),
        ("/stats", "Statistik bot"),
        ("/ping", "Cek apakah bot aktif"),
    ],
}

def embed_help_beranda():
    embed = discord.Embed(title="Bantuan RyHanC", description="Satu bot untuk membangun dan mengelola server komunitas maupun jualan.\n\nPilih kategori di menu bawah untuk melihat daftar perintahnya.", color=discord.Color.blurple())
    for nama in HELP_KATEGORI:
        embed.add_field(name=nama, value=f"{len(HELP_KATEGORI[nama])} perintah", inline=True)
    embed.set_footer(text="ryhanc.wtf")
    return embed

def embed_help_kategori(nama):
    daftar = HELP_KATEGORI[nama]
    isi = "\n".join(f"**{cmd}**\n{ket}" for cmd, ket in daftar)
    embed = discord.Embed(title=f"Bantuan - {nama}", description=isi[:4000], color=discord.Color.blurple())
    embed.set_footer(text="Tanda (admin) berarti hanya bisa dipakai admin")
    return embed

class HelpSelect(discord.ui.Select):
    def __init__(self):
        opsi = [discord.SelectOption(label="Beranda", value="__beranda__", description="Kembali ke halaman utama")]
        for nama in HELP_KATEGORI:
            opsi.append(discord.SelectOption(label=nama, value=nama))
        super().__init__(placeholder="Pilih kategori perintah", options=opsi)

    async def callback(self, interaction: discord.Interaction):
        pilihan = self.values[0]
        if pilihan == "__beranda__":
            await interaction.response.edit_message(embed=embed_help_beranda(), view=self.view)
        else:
            await interaction.response.edit_message(embed=embed_help_kategori(pilihan), view=self.view)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpSelect())

@tree.command(name="help", description="Lihat semua fitur dan perintah bot")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message(embed=embed_help_beranda(), view=HelpView(), ephemeral=True)

@tree.command(name="ping", description="Cek apakah bot aktif")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! Bot aktif.")

@tree.command(name="setlog", description="Mendaftarkan channel ini sebagai pusat Security Log")
@app_commands.checks.has_permissions(administrator=True)
async def setlog(interaction: discord.Interaction):
    data["log_channels"][str(interaction.guild_id)] = interaction.channel_id
    simpan_data()
    await interaction.response.send_message(f"Channel {interaction.channel.mention} didaftarkan sebagai Security Log.", ephemeral=True)

@tree.command(name="setwelcome", description="Atur pesan sambutan di channel ini")
@app_commands.describe(pesan="Boleh pakai {user}, {server}, dan {jumlah}")
@app_commands.checks.has_permissions(administrator=True)
async def setwelcome(interaction: discord.Interaction, pesan: str):
    data["welcome"][str(interaction.guild_id)] = {"channel": interaction.channel_id, "pesan": pesan}
    simpan_data()
    await interaction.response.send_message(f"Pesan sambutan diatur di {interaction.channel.mention}.", ephemeral=True)

@tree.command(name="setautorole", description="Role yang otomatis diberikan ke member baru")
@app_commands.checks.has_permissions(administrator=True)
async def setautorole(interaction: discord.Interaction, role: discord.Role):
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message("Posisi role Bot harus di atas role tersebut.", ephemeral=True)
        return
    data["autorole"][str(interaction.guild_id)] = role.id
    simpan_data()
    await interaction.response.send_message(f"Member baru otomatis dapat role {role.mention}.", ephemeral=True)

@tree.command(name="setantispam", description="Blokir link dari member yang baru masuk")
@app_commands.describe(menit="Lama proteksi dalam menit sejak member masuk, isi 0 untuk mematikan")
@app_commands.checks.has_permissions(administrator=True)
async def setantispam(interaction: discord.Interaction, menit: app_commands.Range[int, 0, 10080]):
    if menit == 0:
        data["antispam"].pop(str(interaction.guild_id), None)
        simpan_data()
        await interaction.response.send_message("Anti spam link dimatikan.", ephemeral=True)
        return
    data["antispam"][str(interaction.guild_id)] = menit
    simpan_data()
    await interaction.response.send_message(f"Member yang umurnya di bawah {menit} menit tidak bisa mengirim link.", ephemeral=True)

@tree.command(name="pengaturan", description="Lihat pengaturan bot di server ini")
async def pengaturan(interaction: discord.Interaction):
    gid = str(interaction.guild_id)
    embed = discord.Embed(title="Pengaturan server", color=discord.Color.blurple())

    log_id = data["log_channels"].get(gid)
    embed.add_field(name="Security log", value=f"<#{log_id}>" if log_id else "mati", inline=False)

    sambutan = data["welcome"].get(gid)
    embed.add_field(name="Welcome", value=f"<#{sambutan['channel']}>" if sambutan else "mati", inline=False)

    role_id = data["autorole"].get(gid)
    embed.add_field(name="Auto role", value=f"<@&{role_id}>" if role_id else "mati", inline=False)

    menit = data["antispam"].get(gid)
    embed.add_field(name="Anti spam link", value=f"{menit} menit pertama" if menit else "mati", inline=False)

    hub = data["joinvoice"].get(gid)
    embed.add_field(name="Join to Create", value=f"<#{hub['hub']}>" if hub else "mati", inline=False)

    jumlah = len(data["custom_commands"].get(gid, {}))
    embed.add_field(name="Custom command", value=f"{jumlah} perintah", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="reset", description="Matikan salah satu fitur di server ini")
@app_commands.choices(fitur=[
    app_commands.Choice(name="Security log", value="log_channels"),
    app_commands.Choice(name="Welcome", value="welcome"),
    app_commands.Choice(name="Auto role", value="autorole"),
    app_commands.Choice(name="Anti spam link", value="antispam"),
    app_commands.Choice(name="Join to Create", value="joinvoice"),
])
@app_commands.checks.has_permissions(administrator=True)
async def reset(interaction: discord.Interaction, fitur: app_commands.Choice[str]):
    data[fitur.value].pop(str(interaction.guild_id), None)
    simpan_data()
    await interaction.response.send_message(f"Fitur {fitur.name} dimatikan.", ephemeral=True)

@tree.command(name="purge", description="Hapus sejumlah pesan terakhir di channel ini")
@app_commands.describe(jumlah="Jumlah pesan, maksimal 100")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(interaction: discord.Interaction, jumlah: app_commands.Range[int, 1, 100]):
    await interaction.response.defer(ephemeral=True)
    sedang_purge.add(interaction.channel_id)
    try:
        dihapus = await interaction.channel.purge(limit=jumlah)
    except discord.Forbidden:
        sedang_purge.discard(interaction.channel_id)
        await interaction.followup.send("Bot tidak punya izin Manage Messages di channel ini.", ephemeral=True)
        return
    except Exception as e:
        sedang_purge.discard(interaction.channel_id)
        await interaction.followup.send(f"Gagal: {bersihkan_error(e)}", ephemeral=True)
        return
    sedang_purge.discard(interaction.channel_id)
    await interaction.followup.send(f"{len(dihapus)} pesan dihapus.", ephemeral=True)
    embed = discord.Embed(title="Purge pesan", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Oleh", value=interaction.user.mention)
    embed.add_field(name="Channel", value=interaction.channel.mention)
    embed.add_field(name="Jumlah", value=str(len(dihapus)))
    await kirim_log(interaction.guild, embed)

@tree.command(name="addcmd", description="Membuat custom command teks baru")
@app_commands.checks.has_permissions(administrator=True)
async def addcmd(interaction: discord.Interaction, nama: str, respon: str):
    nama_cmd = nama.lower().replace("/", "").strip()
    if not nama_cmd or " " in nama_cmd or len(nama_cmd) > 30:
        await interaction.response.send_message("Nama tidak boleh kosong, tidak boleh ada spasi, maksimal 30 huruf.", ephemeral=True)
        return
    data["custom_commands"].setdefault(str(interaction.guild_id), {})[nama_cmd] = respon
    simpan_data()
    await interaction.response.send_message(f"Custom command disimpan. Panggil dengan /cc nama: {nama_cmd}", ephemeral=True)

@tree.command(name="delcmd", description="Menghapus custom command teks")
@app_commands.autocomplete(nama=isi_cc)
@app_commands.checks.has_permissions(administrator=True)
async def delcmd(interaction: discord.Interaction, nama: str):
    daftar = data["custom_commands"].get(str(interaction.guild_id), {})
    nama_cmd = nama.lower().replace("/", "").strip()
    if nama_cmd not in daftar:
        await interaction.response.send_message(f"Custom command {nama_cmd} tidak ditemukan.", ephemeral=True)
        return
    daftar.pop(nama_cmd)
    simpan_data()
    await interaction.response.send_message(f"Custom command {nama_cmd} berhasil dihapus.", ephemeral=True)

@tree.command(name="cc", description="Menjalankan custom command yang telah dibuat")
@app_commands.autocomplete(nama=isi_cc)
async def cc(interaction: discord.Interaction, nama: str):
    daftar = data["custom_commands"].get(str(interaction.guild_id), {})
    respon = daftar.get(nama.lower().strip())
    if respon:
        await interaction.response.send_message(respon[:2000])
    else:
        await interaction.response.send_message(f"Perintah {nama} tidak terdaftar.", ephemeral=True)

@tree.command(name="giverole", description="Memberikan role kepada member tertentu")
@app_commands.checks.has_permissions(administrator=True)
async def giverole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    try:
        await member.add_roles(role)
        await interaction.response.send_message(f"Role {role.mention} diberikan kepada {member.mention}.")
    except discord.Forbidden:
        await interaction.response.send_message("Gagal. Posisikan role Bot di atas role tersebut.", ephemeral=True)

@tree.command(name="takerole", description="Mencabut role dari member tertentu")
@app_commands.checks.has_permissions(administrator=True)
async def takerole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    try:
        await member.remove_roles(role)
        await interaction.response.send_message(f"Role {role.mention} dicabut dari {member.mention}.")
    except discord.Forbidden:
        await interaction.response.send_message("Gagal. Posisikan role Bot di atas role tersebut.", ephemeral=True)

@tree.command(name="buttonrole", description="Membuat pesan tombol ambil atau lepas role mandiri")
@app_commands.checks.has_permissions(administrator=True)
async def buttonrole(interaction: discord.Interaction, role: discord.Role, pesan: str, label: str):
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message("Posisi role Bot harus di atas role tersebut.", ephemeral=True)
        return
    await interaction.response.defer()
    view = DynamicRoleView(role.id, label)
    pesan_terkirim = await interaction.followup.send(pesan, view=view, wait=True)
    data["button_roles"].append({
        "message_id": pesan_terkirim.id,
        "role_id": role.id,
        "label": label,
    })
    simpan_data()

@tree.command(name="download", description="Download video atau mp3 dari link, atau cari lagu dari judulnya")
async def download(interaction: discord.Interaction, url: str):
    if "spotify" in url.lower():
        await interaction.response.send_message("Spotify dikunci DRM jadi tidak bisa didownload. Kirim judul lagunya saja, nanti dicarikan dari YouTube.")
        return

    await interaction.response.defer()

    if link_threads(url):
        try:
            path = await asyncio.to_thread(unduh_threads, url)
        except Exception as e:
            await interaction.followup.send(f"Gagal download: {bersihkan_error(e)}")
            return
        ukuran = os.path.getsize(path)
        if ukuran > batas_upload(interaction):
            await interaction.followup.send(f"File {ukuran // 1048576} MB, melebihi batas upload di sini.")
            os.remove(path)
            return
        await interaction.followup.send("Selesai (Threads).", file=discord.File(path))
        os.remove(path)
        return

    if link_tiktok(url):
        try:
            path, isi = await asyncio.to_thread(unduh_tiktok, url)
        except Exception as e:
            await interaction.followup.send(f"Gagal download: {bersihkan_error(e)}")
            return
        ukuran = os.path.getsize(path)
        if ukuran > batas_upload(interaction):
            await interaction.followup.send(f"File {ukuran // 1048576} MB, melebihi batas upload di sini.")
            os.remove(path)
            return
        judul = (isi.get("title") or "TikTok")[:150]
        await interaction.followup.send(f"Selesai (TikTok): {judul}", file=discord.File(path))
        os.remove(path)
        return

    try:
        info = await asyncio.to_thread(ambil_info, url)
    except Exception as e:
        await interaction.followup.send(f"Gagal ambil info: {bersihkan_error(e)}")
        return

    embed = discord.Embed(title=(info.get("title") or "Tanpa judul")[:250], url=info.get("webpage_url"))
    embed.add_field(name="Durasi", value=format_durasi(info.get("duration")))
    embed.add_field(name="Sumber", value=(info.get("uploader") or info.get("extractor_key") or "tidak diketahui")[:100])
    if info.get("thumbnail"):
        embed.set_thumbnail(url=info["thumbnail"])

    tampilan = PilihFormat(info.get("webpage_url") or url, interaction.user.id)
    tampilan.pesan = await interaction.followup.send(embed=embed, view=tampilan, wait=True)

token = os.getenv("DISCORD_TOKEN")
if not token:
    raise SystemExit("Token tidak ditemukan. Pastikan file .env berisi DISCORD_TOKEN.")

client.run(token)
