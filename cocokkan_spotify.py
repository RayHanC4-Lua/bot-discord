import os
import re
import sys

FUNGSI = r'''SPOTIFY_ABAIKAN = {
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


def spotify_unduh_mp3(kata_cari, mutu, judul="", artis=""):
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
      if not kandidat:
        galat.append(f"{nama}: tidak ada hasil yang cocok")
        continue
      alamat = kandidat[0].get("url") or kandidat[0].get("webpage_url")
      opsi = opsi_dasar()
      opsi["format"] = "bestaudio/best"
      opsi["postprocessors"] = [{
          "key": "FFmpegExtractAudio",
          "preferredcodec": "mp3",
          "preferredquality": str(mutu),
      }]
      with yt_dlp.YoutubeDL(opsi) as ydl:
        info = ydl.extract_info(alamat, download=True)
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


def spotify_unduh_bertahap(kata_cari, batas, judul="", artis=""):
  for mutu in TINGKAT_AUDIO:
    path = spotify_unduh_mp3(kata_cari, mutu, judul, artis)
    if os.path.getsize(path) <= batas:
      return path, mutu
    os.remove(path)
  raise Exception(
      "File tetap melebihi batas upload walau mutu sudah paling rendah."
  )
'''

PANGGILAN_LAMA = "spotify_unduh_bertahap, kata_cari, batas_upload(interaction)"
PANGGILAN_BARU = (
    "spotify_unduh_bertahap, kata_cari, batas_upload(interaction), judul, artis"
)


def main():
  target = sys.argv[1] if len(sys.argv) > 1 else "bot.py"
  if not os.path.exists(target):
    print(f"File {target} tidak ditemukan. Jalankan dari folder bot.")
    return
  with open(target, encoding="utf-8") as f:
    sumber = f.read()
  if "def spotify_cocok" in sumber:
    print("Pencocokan sudah terpasang, tidak ada yang diubah.")
    return
  if PANGGILAN_LAMA not in sumber:
    print("Pemanggilan fungsi unduh tidak ditemukan. Dibatalkan.")
    return
  pola = re.compile(
      r'def spotify_unduh_mp3\(.*?(?=\n\n@tree\.command\(name="spotify")',
      re.DOTALL,
  )
  if not pola.search(sumber):
    print("Titik ganti tidak ditemukan. Dibatalkan.")
    return
  sumber = pola.sub(lambda _: FUNGSI.rstrip() + "\n", sumber, count=1)
  sumber = sumber.replace(PANGGILAN_LAMA, PANGGILAN_BARU, 1)
  with open(target, "w", encoding="utf-8") as f:
    f.write(sumber)
  print("Selesai. Pencocokan judul dan artis sudah ditambahkan.")


main()
