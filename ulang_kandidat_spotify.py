import os
import re
import sys

FUNGSI = r'''def spotify_unduh_mp3(kata_cari, mutu, judul="", artis="", efek=""):
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
'''


def main():
  target = sys.argv[1] if len(sys.argv) > 1 else "bot.py"
  if not os.path.exists(target):
    print(f"File {target} tidak ditemukan. Jalankan dari folder bot.")
    return
  with open(target, encoding="utf-8") as f:
    sumber = f.read()
  if "def spotify_unduh_mp3" not in sumber:
    print("Fungsi spotify_unduh_mp3 tidak ditemukan. Jalankan terapkan_spotify.py dulu.")
    return
  if "for urutan, satu in enumerate" in sumber:
    print("Perbaikan sudah terpasang, tidak ada yang diubah.")
    return
  pola = re.compile(
      r"def spotify_unduh_mp3\(.*?(?=\ndef spotify_unduh_bertahap)", re.DOTALL
  )
  if not pola.search(sumber):
    print("Titik ganti tidak ditemukan. Dibatalkan.")
    return
  sumber = pola.sub(lambda _: FUNGSI.rstrip() + "\n\n", sumber, count=1)
  with open(target, "w", encoding="utf-8") as f:
    f.write(sumber)
  print("Selesai. /spotify sekarang mencoba semua kandidat berurutan.")


main()
