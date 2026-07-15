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

load_dotenv()
os.makedirs("unduhan", exist_ok=True)

PEMILIK_ID = 1438447727477391381
TINGKAT_VIDEO = [720, 480, 360, 240, 144]
TINGKAT_AUDIO = [192, 128, 96, 64]
CONFIG_FILE = os.getenv("CONFIG_PATH", "bot_config.json")
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
            try:
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
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Musik"))

@client.event
async def on_ready():
    global WAKTU_MULAI
    if WAKTU_MULAI is None:
        WAKTU_MULAI = discord.utils.utcnow()
    await tree.sync()
    for br in data.get("button_roles", []):
        client.add_view(DynamicRoleView(br["role_id"], br["label"]), message_id=br["message_id"])
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Musik"))
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

STRUKTUR_SETUP = {
    "INFORMASI": ["pengumuman", "peraturan", "role-info"],
    "KOMUNITAS": ["obrolan-umum", "media-sharing", "santai"],
    "JUALAN": ["katalog", "cara-order", "testimoni", "open-order"],
    "UJI BOT": ["perintah-bot", "log-bot"],
}
ROLE_SETUP = [
    ("Admin", discord.Color.red(), True),
    ("Moderator", discord.Color.orange(), True),
    ("Member", discord.Color.blue(), False),
    ("Pembeli", discord.Color.green(), False),
]

@tree.command(name="setup", description="Buat struktur channel dan role untuk komunitas, jualan, dan uji bot")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    if not interaction.guild.me.guild_permissions.manage_channels or not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message("Bot butuh izin Manage Channels dan Manage Roles. Aktifkan dulu di pengaturan server.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    dibuat = []
    for nama, warna, terpisah in ROLE_SETUP:
        ada = discord.utils.get(guild.roles, name=nama)
        if ada is None:
            try:
                await guild.create_role(name=nama, color=warna, hoist=terpisah, reason="setup bot")
                dibuat.append(f"role {nama}")
            except Exception:
                pass
    for nama_kat, daftar_channel in STRUKTUR_SETUP.items():
        kategori = discord.utils.get(guild.categories, name=nama_kat)
        if kategori is None:
            try:
                kategori = await guild.create_category(nama_kat, reason="setup bot")
                dibuat.append(f"kategori {nama_kat}")
            except Exception:
                continue
        for nama_ch in daftar_channel:
            sudah_ada = discord.utils.get(kategori.channels, name=nama_ch)
            if sudah_ada is None:
                try:
                    await guild.create_text_channel(nama_ch, category=kategori, reason="setup bot")
                    dibuat.append(f"channel {nama_ch}")
                except Exception:
                    pass
    if dibuat:
        ringkas = "\n".join(dibuat[:40])
        await interaction.followup.send(f"Setup selesai. Yang dibuat:\n{ringkas}", ephemeral=True)
    else:
        await interaction.followup.send("Semua struktur sudah ada, tidak ada yang perlu dibuat.", ephemeral=True)

@tree.command(name="hapussetup", description="Hapus channel dan role yang dibuat oleh setup")
@app_commands.checks.has_permissions(administrator=True)
async def hapussetup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    dihapus = 0
    nama_channel = {c for daftar in STRUKTUR_SETUP.values() for c in daftar}
    nama_kategori = set(STRUKTUR_SETUP.keys())
    nama_role = {r[0] for r in ROLE_SETUP}
    for channel in list(guild.channels):
        if channel.name in nama_channel and not isinstance(channel, discord.CategoryChannel):
            try:
                await channel.delete(reason="hapus setup")
                dihapus += 1
            except Exception:
                pass
    for kategori in list(guild.categories):
        if kategori.name in nama_kategori:
            try:
                await kategori.delete(reason="hapus setup")
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

    jumlah = len(data["custom_commands"].get(gid, {}))
    embed.add_field(name="Custom command", value=f"{jumlah} perintah", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="reset", description="Matikan salah satu fitur di server ini")
@app_commands.choices(fitur=[
    app_commands.Choice(name="Security log", value="log_channels"),
    app_commands.Choice(name="Welcome", value="welcome"),
    app_commands.Choice(name="Auto role", value="autorole"),
    app_commands.Choice(name="Anti spam link", value="antispam"),
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
