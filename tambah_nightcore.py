import os
import sys

PASANGAN = [
    (
        """def spotify_unduh_mp3(kata_cari, mutu, judul="", artis=""):""",
        """SPOTIFY_NIGHTCORE = "aresample=44100,asetrate=55125,aresample=44100"


def spotify_unduh_mp3(kata_cari, mutu, judul="", artis="", efek=""):""",
    ),
    (
        """      with yt_dlp.YoutubeDL(opsi) as ydl:
        info = ydl.extract_info(alamat, download=True)""",
        """      if efek == "nightcore":
        opsi["postprocessor_args"] = {
            "extractaudio": ["-af", SPOTIFY_NIGHTCORE]
        }
      with yt_dlp.YoutubeDL(opsi) as ydl:
        info = ydl.extract_info(alamat, download=True)""",
    ),
    (
        """def spotify_unduh_bertahap(kata_cari, batas, judul="", artis=""):""",
        """def spotify_unduh_bertahap(kata_cari, batas, judul="", artis="", efek=""):""",
    ),
    (
        """    path = spotify_unduh_mp3(kata_cari, mutu, judul, artis)""",
        """    path = spotify_unduh_mp3(kata_cari, mutu, judul, artis, efek)""",
    ),
    (
        """spotify_unduh_bertahap, kata_cari, batas_upload(interaction), judul, artis""",
        """spotify_unduh_bertahap,
        kata_cari,
        batas_upload(interaction),
        judul,
        artis,
        efek.value if efek else "",""",
    ),
    (
        """@app_commands.describe(link="Link satu lagu dari Spotify")
async def spotify_mp3(interaction: discord.Interaction, link: str):""",
        """@app_commands.describe(
    link="Link satu lagu dari Spotify", efek="Efek audio, kosongkan untuk asli"
)
@app_commands.choices(
    efek=[app_commands.Choice(name="Nightcore", value="nightcore")]
)
async def spotify_mp3(
    interaction: discord.Interaction,
    link: str,
    efek: app_commands.Choice[str] = None,
):""",
    ),
    (
        """f"{nama[:150]} ({mutu} kbps)", file=discord.File(path)""",
        """f"{nama[:150]} ({mutu} kbps{', nightcore' if efek else ''})",
        file=discord.File(path),""",
    ),
]


def main():
  target = sys.argv[1] if len(sys.argv) > 1 else "bot.py"
  if not os.path.exists(target):
    print(f"File {target} tidak ditemukan. Jalankan dari folder bot.")
    return
  with open(target, encoding="utf-8") as f:
    sumber = f.read()
  if "SPOTIFY_NIGHTCORE" in sumber:
    print("Efek nightcore sudah terpasang, tidak ada yang diubah.")
    return
  for nomor, (lama, _) in enumerate(PASANGAN, start=1):
    jumlah = sumber.count(lama)
    if jumlah != 1:
      print(f"Titik ganti nomor {nomor} ditemukan {jumlah} kali. Dibatalkan.")
      return
  for lama, baru in PASANGAN:
    sumber = sumber.replace(lama, baru, 1)
  with open(target, "w", encoding="utf-8") as f:
    f.write(sumber)
  print("Selesai. Opsi efek nightcore sudah ditambahkan ke /spotify.")


main()
