import asyncio
import html
import json
import os
import re

import discord
from discord import app_commands
import requests
import yt_dlp

from modul.inti import TINGKAT_AUDIO, bersihkan_error, tree
from modul.unduhan import batas_upload, opsi_dasar


SPOTIFY_HEADER = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
SPOTIFY_POLA = re.compile(
    r"https?://(?:open\.spotify\.com/|spotify\.link/|spoti\.fi/)\S+"
)


def spotify_meta(teks, nama):
  pola = [
      rf'<meta[^>]+property="{nama}"[^>]+content="([^"]*)"',
      rf'<meta[^>]+content="([^"]*)"[^>]+property="{nama}"',
  ]
  for p in pola:
    cocok = re.search(p, teks)
    if cocok:
      return html.unescape(cocok.group(1)).strip()
  return ""


def spotify_baca(link):
  res = requests.get(
      link, headers=SPOTIFY_HEADER, timeout=20, allow_redirects=True
  )
  cocok = re.search(r"/track/([A-Za-z0-9]+)", res.url)
  if not cocok:
    raise Exception(
        "Link harus berupa satu lagu Spotify, bukan album atau playlist."
    )
  id_lagu = cocok.group(1)
  judul = ""
  artis = ""
  kode_oembed = 0
  try:
    oe = requests.get(
        "https://open.spotify.com/oembed",
        params={"url": f"https://open.spotify.com/track/{id_lagu}"},
        headers=SPOTIFY_HEADER,
        timeout=20,
    )
    kode_oembed = oe.status_code
    if oe.status_code == 200:
      judul = str(oe.json().get("title", "")).strip()
  except Exception:
    pass
  try:
    em = requests.get(
        f"https://open.spotify.com/embed/track/{id_lagu}",
        headers=SPOTIFY_HEADER,
        timeout=20,
    )
    cari = re.search(
        r"\"artists\":\s*\[\s*\{[^\]]*?\"name\":\s*\"((?:[^\"\\]|\\.)*)\"",
        em.text,
    )
    if cari:
      artis = json.loads('"%s"' % cari.group(1)).strip()
    if not judul:
      cari = re.search(r"\"title\":\s*\"((?:[^\"\\]|\\.)*)\"", em.text)
      if cari:
        judul = json.loads('"%s"' % cari.group(1)).strip()
  except Exception:
    pass
  if not judul or not artis:
    tag = re.search(r"<title>(.*?)</title>", res.text, re.DOTALL)
    if tag:
      teks = html.unescape(tag.group(1)).strip()
      cocok_tag = re.match(
          r"(.+?) - (?:song|single)(?: and lyrics)? by (.+?) \| Spotify", teks
      )
      if cocok_tag:
        judul = judul or cocok_tag.group(1).strip()
        artis = artis or cocok_tag.group(2).strip()
  if not judul:
    judul = spotify_meta(res.text, "og:title")
  if not artis:
    deskripsi = spotify_meta(res.text, "og:description")
    if deskripsi:
      artis = deskripsi.split("\u00b7")[0].strip()
  if not judul:
    raise Exception(
        f"Judul lagu tidak ditemukan (halaman {res.status_code}, oembed"
        f" {kode_oembed})."
    )
  return judul, artis


SPOTIFY_ABAIKAN = {
    "feat", "ft", "featuring", "with", "the", "a", "an", "and", "of",
    "official", "audio", "remastered", "remaster", "version", "prod",
    "video", "lyrics", "lyric",
}
SPOTIFY_BURUK = {
    "cover", "live", "remix", "slowed", "sped", "reverb", "nightcore",
    "karaoke", "instrumental", "mashup",
}


def spotify_kata(teks):
  return re.findall(r"[a-z0-9]+", str(teks).lower())


def spotify_cocok(entri, judul, artis):
  teks = " ".join(
      str(entri.get(k) or "") for k in ("title", "uploader", "channel")
  )
  kata_hasil = set(spotify_kata(teks))
  kata_judul = set(spotify_kata(judul))
  if (set(spotify_kata(entri.get("title"))) & SPOTIFY_BURUK) - kata_judul:
    return False
  inti = re.sub(r"[\(\[].*?[\)\]]", " ", judul)
  wajib = [k for k in spotify_kata(inti) if k not in SPOTIFY_ABAIKAN]
  if not all(k in kata_hasil for k in wajib):
    return False
  if not artis:
    return True
  for nama in artis.split(","):
    inti_nama = [k for k in spotify_kata(nama) if k not in SPOTIFY_ABAIKAN]
    if all(k in kata_hasil for k in inti_nama):
      return True
  return False


SPOTIFY_NIGHTCORE = "aresample=44100,asetrate=55125,aresample=44100"


def spotify_unduh_mp3(kata_cari, mutu, judul="", artis="", efek=""):
  sumber = [
      ("YouTube", "ytsearch5:" + kata_cari),
      ("SoundCloud", "scsearch5:" + re.sub(r"\s+audio$", "", kata_cari)),
  ]
  galat = []
  for nama, target in sumber:
    try:
      opsi_cari = opsi_dasar()
      opsi_cari["extract_flat"] = True
      with yt_dlp.YoutubeDL(opsi_cari) as ydl:
        hasil = ydl.extract_info(target, download=False)
      kandidat = [
          e
          for e in (hasil.get("entries") or [])
          if e and spotify_cocok(e, judul, artis)
      ]
    except Exception as e:
      galat.append(f"{nama}: {bersihkan_error(e)[:70]}")
      continue
    if not kandidat:
      galat.append(f"{nama}: tidak ada hasil yang cocok")
      continue
    for urutan, satu in enumerate(kandidat, start=1):
      alamat = satu.get("url") or satu.get("webpage_url")
      opsi = opsi_dasar()
      opsi["format"] = "bestaudio/best"
      opsi["postprocessors"] = [{
          "key": "FFmpegExtractAudio",
          "preferredcodec": "mp3",
          "preferredquality": str(mutu),
      }]
      if efek == "nightcore":
        opsi["postprocessor_args"] = {
            "extractaudio": ["-af", SPOTIFY_NIGHTCORE]
        }
      try:
        with yt_dlp.YoutubeDL(opsi) as ydl:
          info = ydl.extract_info(alamat, download=True)
          path = info["requested_downloads"][0]["filepath"]
      except Exception as e:
        galat.append(f"{nama} #{urutan}: {bersihkan_error(e)[:60]}")
        continue
      if nama == "SoundCloud" and (info.get("duration") or 0) <= 45:
        if os.path.exists(path):
          os.remove(path)
        galat.append(f"{nama} #{urutan}: hasil hanya cuplikan")
        continue
      return path
  raise Exception("; ".join(galat[:6]))


def spotify_unduh_bertahap(kata_cari, batas, judul="", artis="", efek=""):
  for mutu in TINGKAT_AUDIO:
    path = spotify_unduh_mp3(kata_cari, mutu, judul, artis, efek)
    if os.path.getsize(path) <= batas:
      return path, mutu
    os.remove(path)
  raise Exception(
      "File tetap melebihi batas upload walau mutu sudah paling rendah."
  )


@tree.command(name="spotify", description="Ubah link lagu Spotify jadi MP3")
@app_commands.describe(
    link="Link satu lagu dari Spotify", efek="Efek audio, kosongkan untuk asli"
)
@app_commands.choices(
    efek=[app_commands.Choice(name="Nightcore", value="nightcore")]
)
async def spotify_mp3(
    interaction: discord.Interaction,
    link: str,
    efek: app_commands.Choice[str] = None,
):
  cocok = SPOTIFY_POLA.search(link)
  if not cocok:
    await interaction.response.send_message(
        "Kirim link lagu Spotify, contoh: https://open.spotify.com/track/...",
        ephemeral=True,
    )
    return
  await interaction.response.defer()
  try:
    judul, artis = await asyncio.to_thread(spotify_baca, cocok.group(0))
  except Exception as e:
    await interaction.followup.send(f"Gagal membaca link: {bersihkan_error(e)}")
    return
  kata_cari = f"{artis} {judul} audio".strip()
  try:
    path, mutu = await asyncio.to_thread(
        spotify_unduh_bertahap,
        kata_cari,
        batas_upload(interaction),
        judul,
        artis,
        efek.value if efek else "",
    )
  except Exception as e:
    await interaction.followup.send(f"Gagal mengunduh: {bersihkan_error(e)}")
    return
  nama = f"{judul} - {artis}" if artis else judul
  try:
    await interaction.followup.send(
        f"{nama[:150]} ({mutu} kbps{', nightcore' if efek else ''})",
        file=discord.File(path),
    )
  finally:
    if os.path.exists(path):
      os.remove(path)
