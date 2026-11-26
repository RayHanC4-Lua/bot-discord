import os
import re
import sys

FUNGSI = r'''def spotify_baca(link):
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
'''


def main():
  target = sys.argv[1] if len(sys.argv) > 1 else "bot.py"
  if not os.path.exists(target):
    print(f"File {target} tidak ditemukan. Jalankan dari folder bot.")
    return
  with open(target, encoding="utf-8") as f:
    sumber = f.read()
  if "def spotify_baca" not in sumber:
    print("Fungsi spotify_baca tidak ditemukan. Jalankan terapkan_spotify.py dulu.")
    return
  if "open.spotify.com/oembed" in sumber:
    print("Perbaikan sudah terpasang, tidak ada yang diubah.")
    return
  pola = re.compile(
      r"def spotify_baca\(link\):.*?(?=\ndef spotify_unduh_mp3)", re.DOTALL
  )
  if not pola.search(sumber):
    print("Titik ganti tidak ditemukan. Dibatalkan.")
    return
  sumber = pola.sub(lambda _: FUNGSI.rstrip() + "\n\n", sumber, count=1)
  with open(target, "w", encoding="utf-8") as f:
    f.write(sumber)
  print("Selesai. Fungsi spotify_baca sudah diperbaiki.")


main()
