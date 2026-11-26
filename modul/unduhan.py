import asyncio
import json
import os
import re
import time
import urllib.parse
import urllib.request

import discord
from discord import app_commands
import yt_dlp

from modul.inti import TINGKAT_AUDIO, TINGKAT_VIDEO, bersihkan_error, tree


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
  permintaan_video = urllib.request.Request(
      link, headers={"User-Agent": "Mozilla/5.0"}
  )
  with urllib.request.urlopen(
      permintaan_video, timeout=300
  ) as sumber, open(path, "wb") as berkas:
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
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/126.0 Safari/537.36"
      ),
      "Accept": (
          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
      ),
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
        permintaan_video = urllib.request.Request(
            link, headers={"User-Agent": header["User-Agent"]}
        )
        with urllib.request.urlopen(
            permintaan_video, timeout=300
        ) as sumber, open(path, "wb") as berkas:
          berkas.write(sumber.read())
        return path
  raise Exception(
      "Video tidak ketemu di halaman Threads. Kemungkinan post privat atau"
      " bukan video."
  )


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
    opsi["format"] = (
        f"bestvideo[height<={mutu}]+bestaudio/best[height<={mutu}]/best"
    )
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
  raise Exception(
      "File tetap melebihi batas upload walau sudah diturunkan ke mutu paling"
      " rendah."
  )


def batas_upload(interaction):
  return (
      interaction.guild.filesize_limit if interaction.guild else 10 * 1024 * 1024
  )


class PilihFormat(discord.ui.View):

  def __init__(self, target, pemilik):
    super().__init__(timeout=300)
    self.target = target
    self.pemilik = pemilik
    self.pesan = None

  async def interaction_check(self, interaction):
    if interaction.user.id != self.pemilik:
      await interaction.response.send_message(
          "Tombol ini bukan punyamu.", ephemeral=True
      )
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
    await interaction.response.edit_message(
        content="Sedang diunduh, tunggu sebentar.", view=self
    )
    self.stop()
    try:
      path, hasil = await asyncio.to_thread(
          unduh_bertahap,
          self.target,
          audio_saja,
          mutu,
          batas_upload(interaction),
      )
    except Exception as e:
      await interaction.followup.send(f"Gagal download: {bersihkan_error(e)}")
      return
    label = f"{hasil} kbps" if audio_saja else f"{hasil}p"
    await interaction.followup.send(
        f"Selesai ({label}).", file=discord.File(path)
    )
    os.remove(path)

  @discord.ui.button(label="Video 720p", style=discord.ButtonStyle.primary)
  async def video_tinggi(
      self, interaction: discord.Interaction, tombol: discord.ui.Button
  ):
    await self.jalankan(interaction, False, 720)

  @discord.ui.button(label="Video 480p", style=discord.ButtonStyle.secondary)
  async def video_rendah(
      self, interaction: discord.Interaction, tombol: discord.ui.Button
  ):
    await self.jalankan(interaction, False, 480)

  @discord.ui.button(label="MP3", style=discord.ButtonStyle.success)
  async def audio(
      self, interaction: discord.Interaction, tombol: discord.ui.Button
  ):
    await self.jalankan(interaction, True, 192)


@tree.command(name="download", description="Download video atau audio dari link/judul")
@app_commands.describe(target="Link video atau judul pencarian")
async def download(interaction: discord.Interaction, target: str):
  await interaction.response.defer(ephemeral=True)
  try:
    info = await asyncio.to_thread(ambil_info, target)
  except Exception as e:
    await interaction.followup.send(f"Gagal mengambil info: {bersihkan_error(e)}")
    return
  
  judul = info.get("title", "Media")
  durasi = info.get("duration", 0)
  thumb = info.get("thumbnail")
  
  embed = discord.Embed(
      title="Pilih Format Download",
      description=f"**Judul:** {judul}\n**Durasi:** {format_durasi(durasi)}",
      color=discord.Color.blurple()
  )
  if thumb:
    embed.set_thumbnail(url=thumb)
    
  tampilan = PilihFormat(target, interaction.user.id)
  pesan = await interaction.followup.send(embed=embed, view=tampilan, wait=True)
  tampilan.pesan = pesan
