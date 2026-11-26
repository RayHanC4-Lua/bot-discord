import os
import re
import sys

FUNGSI = r'''def spotify_unduh_mp3(kata_cari, mutu):
  sumber = [
      ("YouTube", f"ytsearch1:{kata_cari}"),
      ("SoundCloud", "scsearch1:" + re.sub(r"\s+audio$", "", kata_cari)),
  ]
  galat = []
  for nama, target in sumber:
    opsi = opsi_dasar()
    opsi["format"] = "bestaudio/best"
    opsi["postprocessors"] = [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": str(mutu),
    }]
    try:
      with yt_dlp.YoutubeDL(opsi) as ydl:
        info = ydl.extract_info(target, download=True)
        entri = info.get("entries")
        if entri is not None:
          entri = [e for e in entri if e]
          if not entri:
            raise Exception("lagu tidak ditemukan")
          info = entri[0]
        path = info["requested_downloads"][0]["filepath"]
    except Exception as e:
      galat.append(f"{nama}: {bersihkan_error(e)[:70]}")
      continue
    if nama == "SoundCloud" and (info.get("duration") or 0) <= 45:
      if os.path.exists(path):
        os.remove(path)
      galat.append("SoundCloud: hasil hanya cuplikan")
      continue
    return path
  raise Exception("; ".join(galat))
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
  if "scsearch1" in sumber:
    print("Cadangan SoundCloud sudah terpasang, tidak ada yang diubah.")
    return
  pola = re.compile(
      r"def spotify_unduh_mp3\(kata_cari, mutu\):.*?(?=\ndef spotify_unduh_bertahap)",
      re.DOTALL,
  )
  if not pola.search(sumber):
    print("Titik ganti tidak ditemukan. Dibatalkan.")
    return
  sumber = pola.sub(lambda _: FUNGSI.rstrip() + "\n\n", sumber, count=1)
  with open(target, "w", encoding="utf-8") as f:
    f.write(sumber)
  print("Selesai. Cadangan SoundCloud sudah ditambahkan.")


main()
