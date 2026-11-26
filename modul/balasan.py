import asyncio
import os
import re

import discord


EKSTENSI_BAHASA = {
    "python": "py",
    "py": "py",
    "html": "html",
    "htm": "html",
    "javascript": "js",
    "js": "js",
    "typescript": "ts",
    "ts": "ts",
    "css": "css",
    "json": "json",
    "bash": "sh",
    "sh": "sh",
    "shell": "sh",
    "sql": "sql",
    "yaml": "yml",
    "yml": "yml",
    "markdown": "md",
    "md": "md",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "c++": "cpp",
    "php": "php",
    "xml": "xml",
    "txt": "txt",
    "text": "txt",
    "plaintext": "txt",
}
POLA_BLOK_KODE = re.compile(r"```([a-zA-Z0-9+_-]*)\n(.*?)```", re.DOTALL)
PANJANG_FILE_OTOMATIS = 350
BATAS_TEKS_LANGSUNG = 4500


def ekstrak_blok_kode(teks):
  return [
      (b.strip().lower(), k.strip("\n"))
      for b, k in POLA_BLOK_KODE.findall(teks)
  ]


def buat_file(nama_dasar, ekstensi, isi):
  waktu = discord.utils.utcnow().strftime("%Y%m%d-%H%M%S")
  aman = re.sub(r"[^a-zA-Z0-9_-]", "", nama_dasar)[:30] or "ai"
  nama_file = f"{aman}-{waktu}.{ekstensi}"
  path = os.path.join("file_ai", nama_file)
  with open(path, "w", encoding="utf-8") as f:
    f.write(isi)
  return path


def siapkan_balasan(jawaban):
  blok = ekstrak_blok_kode(jawaban)
  lampiran = []
  besar = [(b, k) for b, k in blok if len(k) >= PANJANG_FILE_OTOMATIS]
  if besar:
    sisa_teks = POLA_BLOK_KODE.sub("", jawaban).strip()
    for bahasa, kode in besar[:5]:
      ekstensi = EKSTENSI_BAHASA.get(bahasa, "txt")
      path = buat_file(bahasa or "kode", ekstensi, kode)
      lampiran.append(discord.File(path))
    teks_chat = (
        sisa_teks[:1800] if sisa_teks else "Nih, sudah aku buatkan filenya."
    )
    teks_chat += f"\n\nAku lampirkan {len(lampiran)} file di bawah ya."
    return teks_chat, lampiran
  if len(jawaban) > BATAS_TEKS_LANGSUNG:
    path = buat_file("balasan", "md", jawaban)
    lampiran.append(discord.File(path))
    teks_chat = (
        jawaban[:600].rstrip()
        + "...\n\nJawabannya panjang, aku lampirkan lengkapnya di file ya."
    )
    return teks_chat, lampiran
  return jawaban[:4500], lampiran


def pecah_balasan(teks, maks=450, batas_pesan=6):
  paragraf = [p.strip() for p in re.split(r"\n\s*\n", teks) if p.strip()]
  potongan = []
  for p in paragraf:
    while len(p) > 1900:
      potongan.append(p[:1900])
      p = p[1900:]
    potongan.append(p)
  hasil = []
  buf = ""
  for p in potongan:
    if buf and len(buf) + len(p) + 2 > maks:
      hasil.append(buf)
      buf = p
    else:
      buf = f"{buf}\n\n{p}" if buf else p
  if buf:
    hasil.append(buf)
  while len(hasil) > batas_pesan:
    gabung = hasil[-2] + "\n\n" + hasil[-1]
    if len(gabung) > 1900:
      break
    hasil[-2:] = [gabung]
  return hasil or [teks[:1900]]


async def kirim_bertahap(message, teks, lampiran, tanpa_ping):
  bagian = pecah_balasan(teks)
  for i, isi in enumerate(bagian):
    terakhir = i == len(bagian) - 1
    kwargs = {"allowed_mentions": tanpa_ping}
    if terakhir and lampiran:
      kwargs["files"] = lampiran
    if i == 0:
      await message.reply(isi, mention_author=False, **kwargs)
    else:
      async with message.channel.typing():
        await asyncio.sleep(min(2.5, 0.8 + len(isi) / 250))
      await message.channel.send(isi, **kwargs)
