import os
import re
import sys

BLOK = r'''SPOTIFY_HEADER = {
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
  if res.status_code != 200:
    raise Exception(
        f"Halaman Spotify tidak bisa dibuka (kode {res.status_code})."
    )
  if "/track/" not in res.url:
    raise Exception(
        "Link harus berupa satu lagu Spotify, bukan album atau playlist."
    )
  judul = spotify_meta(res.text, "og:title")
  deskripsi = spotify_meta(res.text, "og:description")
  if not judul:
    raise Exception("Judul lagu tidak ditemukan di halaman Spotify.")
  artis = ""
  if deskripsi:
    artis = deskripsi.split("\u00b7")[0].strip()
  return judul, artis


def spotify_unduh_mp3(kata_cari, mutu):
  opsi = opsi_dasar()
  opsi["format"] = "bestaudio/best"
  opsi["postprocessors"] = [{
      "key": "FFmpegExtractAudio",
      "preferredcodec": "mp3",
      "preferredquality": str(mutu),
  }]
  with yt_dlp.YoutubeDL(opsi) as ydl:
    info = ydl.extract_info(f"ytsearch1:{kata_cari}", download=True)
    if "entries" in info:
      info = info["entries"][0]
    return info["requested_downloads"][0]["filepath"]


def spotify_unduh_bertahap(kata_cari, batas):
  for mutu in TINGKAT_AUDIO:
    path = spotify_unduh_mp3(kata_cari, mutu)
    if os.path.getsize(path) <= batas:
      return path, mutu
    os.remove(path)
  raise Exception(
      "File tetap melebihi batas upload walau mutu sudah paling rendah."
  )


@tree.command(name="spotify", description="Ubah link lagu Spotify jadi MP3")
@app_commands.describe(link="Link satu lagu dari Spotify")
async def spotify_mp3(interaction: discord.Interaction, link: str):
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
        spotify_unduh_bertahap, kata_cari, batas_upload(interaction)
    )
  except Exception as e:
    await interaction.followup.send(f"Gagal mengunduh: {bersihkan_error(e)}")
    return
  nama = f"{judul} - {artis}" if artis else judul
  try:
    await interaction.followup.send(
        f"{nama[:150]} ({mutu} kbps)", file=discord.File(path)
    )
  finally:
    if os.path.exists(path):
      os.remove(path)


'''


def main():
  target = sys.argv[1] if len(sys.argv) > 1 else "bot.py"
  if not os.path.exists(target):
    print(f"File {target} tidak ditemukan. Jalankan dari folder bot.")
    return
  with open(target, encoding="utf-8") as f:
    sumber = f.read()
  if "def spotify_baca" in sumber:
    print("Fitur /spotify sudah terpasang di bot.py, tidak ada yang diubah.")
    return
  if not re.search(r"^import html$", sumber, re.MULTILINE):
    if "import hmac\n" not in sumber:
      print("Titik sisip import tidak ditemukan. Dibatalkan.")
      return
    sumber = sumber.replace("import hmac\n", "import hmac\nimport html\n", 1)
  titik = re.search(r"^muat_semua_ekstensi\(\)[ \t]*$", sumber, re.MULTILINE)
  if not titik:
    print("Titik sisip perintah tidak ditemukan. Dibatalkan.")
    return
  sumber = sumber[: titik.start()] + BLOK + sumber[titik.start():]
  bantuan = re.search(
      r'^(\s*)\("/download", "[^"]*"\),\n', sumber, re.MULTILINE
  )
  if bantuan:
    sisip = f'{bantuan.group(1)}("/spotify", "Ubah link lagu Spotify jadi MP3"),\n'
    sumber = sumber[: bantuan.end()] + sisip + sumber[bantuan.end():]
  with open(target, "w", encoding="utf-8") as f:
    f.write(sumber)
  print("Selesai. Fitur /spotify sudah ditambahkan ke bot.py.")


main()
