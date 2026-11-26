import asyncio
from datetime import datetime, timedelta, timezone
import difflib
import os
import re

import discord
import requests

from modul.inti import PEMILIK_ID, client, data, simpan_data


WIB = timezone(timedelta(hours=int(os.getenv("TZ_OFFSET", "7"))))
TOPIK_RUTIN = [
    "tinjau hasil tindakan terakhir tim dan apa yang bisa diperbaiki",
    "rencana tugas rutin yang bisa dikerjakan dengan aksi yang tersedia",
    "cara merapikan repo dan jadwal yang sudah ada",
    "ide pengingat atau laporan yang berguna untuk bos",
]
GAYA_CHAT = (
    "Balas seperti chat singkat antar rekan kerja: santai tapi"
    " profesional, dalam Bahasa Indonesia saja (kata Inggris hanya yang"
    " lazim sekali seperti deadline atau meeting). Cukup 1 sampai 2"
    " kalimat, tanpa poin, judul, atau tabel. Jangan menyalin atau"
    " mengulang kalimat rekanmu maupun kalimat user. Jangan memakai wkwk"
    " atau emoji. Setiap pesan wajib menambah satu hal baru. Jangan menyebut"
    " nama orang, tim, divisi, atau sistem lain di luar daftar anggota tim"
    " yang diberikan, dan jangan mengarang"
    " tenggat, angka, atau aturan hukum yang tidak disebut di perintah user."
    " Selama diskusi belum ada yang dikerjakan, jadi jangan menulis sudah"
    " selesai atau done. Pelaksanaan dilakukan Chat AI setelah keputusan, dan"
    " hanya untuk aksi yang benar-benar tersedia."
)
WATAK_AGEN = {
    "pranowo": (
        "Kamu Pranowo, Marketing Manager. Sudut pandangmu: audiens, pesan,"
        " waktu, dan hasil bagi bisnis."
    ),
    "manager": (
        "Kamu Manager Software House. Sudut pandangmu: langkah teknis,"
        " risiko, dan perkiraan waktu."
    ),
}


def sekarang_wib():
  return datetime.now(WIB)


async def kirim_ke_kanal(kanal_id, teks):
  if not kanal_id:
    return
  kanal = client.get_channel(int(kanal_id))
  if kanal is None:
    return
  try:
    await kanal.send(
        teks[:1900], allowed_mentions=discord.AllowedMentions.none()
    )
  except Exception:
    pass


def catat_belajar(nama, teks):
  daftar = data.setdefault("catatan_agen", {}).setdefault(nama, [])
  daftar.append(teks[:200])
  del daftar[:-8]


def fakta_nyata():
  return [
      a["teks"][:160]
      for a in data.get("aktivitas", [])
      if a["jenis"] == "aksi"
  ][-5:]


def galat_groq(teks):
  return teks.startswith(
      ("Error API", "Exception error", "(agen tidak memberi jawaban)")
  )


RESERVED_NAMA = {"pranowo", "manager", "chatai", "keputusan", "sistem", "rian"}


def daftar_staf():
  return data.get("staf", [])


def anggota_tim():
  baris = [
      "Pranowo (Marketing Manager)",
      "Manager (Software House Manager)",
      "Chat AI (eksekutor)",
  ]
  baris += [f"{s['nama'].capitalize()} ({s['peran']})" for s in daftar_staf()]
  return ", ".join(baris)


def watak_agen(nama):
  if nama in WATAK_AGEN:
    return WATAK_AGEN[nama]
  for s in daftar_staf():
    if s["nama"] == nama:
      return f"Kamu {nama.capitalize()}, {s['peran']}. Sudut pandangmu: {s['sudut']}"
  return ""


async def kirim_ke_pemilik(teks):
  kanal_id = os.getenv("KANTOR_CHANNEL_ID")
  if kanal_id:
    await kirim_ke_kanal(kanal_id, teks)
    return
  try:
    pemilik = await client.fetch_user(PEMILIK_ID)
    await pemilik.send(teks[:1900])
  except Exception:
    pass


PERAN_KANTOR = ["Marketing Manager", "Software House Manager"]
BATAS_EMBED = 3800


def pecah_teks(teks, maks=BATAS_EMBED):
  hasil = []
  sisa = teks.strip()
  while len(sisa) > maks:
    titik = sisa.rfind("\n\n", 0, maks)
    if titik < maks // 2:
      titik = sisa.rfind("\n", 0, maks)
    if titik < maks // 2:
      titik = maks
    hasil.append(sisa[:titik].strip())
    sisa = sisa[titik:].strip()
  if sisa:
    hasil.append(sisa)
  return hasil or ["(kosong)"]


async def kirim_panjang(interaction, judul, teks, warna):
  for i, bagian in enumerate(pecah_teks(teks)):
    judul_embed = judul if i == 0 else f"{judul} (lanjutan {i})"
    embed = discord.Embed(title=judul_embed, description=bagian, color=warna)
    await interaction.followup.send(embed=embed)


POLA_EMOJI = r"[\U0001F300-\U0001FAFF\u2600-\u27BF]"
KATA_SELESAI = r"\b(?:selesai|beres|berhasil|terkirim|sukses)\b"
FOKUS_RONDE = [
    "Sampaikan usulan awalmu.",
    "Tanggapi rekanmu, lalu tambahkan risiko atau hal yang terlewat.",
    "Usulkan langkah konkret dan siapa mengerjakan apa.",
    "Sepakati rencana akhir dengan singkat, tanpa mengulang yang sudah dibahas.",
]


def bersihkan_gaya(teks):
  teks = re.sub(r"\b(?:(?:wk){2,}\w*|(?:ha){2,}h?)\b", "", teks, flags=re.IGNORECASE)
  emoji = re.findall(POLA_EMOJI, teks)
  teks = re.sub(POLA_EMOJI + r"|[\uFE0F\u200D]", "", teks)
  teks = re.sub(r"[ \t]{2,}", " ", teks).strip()
  if emoji and re.search(KATA_SELESAI, teks, re.IGNORECASE):
    teks = f"{teks} {emoji[0]}"
  return teks


def terlalu_mirip(teks, pembanding):
  return any(
      difflib.SequenceMatcher(None, teks.lower(), t.lower()).ratio() > 0.62
      for t in pembanding
  )


def catat_kantor_sinkron(agen, teks, jenis):
  alamat = os.getenv("SUPABASE_URL")
  kunci = os.getenv("SUPABASE_SERVICE_KEY")
  if not alamat or not kunci:
    return
  try:
    requests.post(
        f"{alamat.rstrip('/')}/rest/v1/kantor_pesan",
        headers={
            "apikey": kunci,
            "Authorization": f"Bearer {kunci}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        json={"agen": agen, "teks": teks[:1500], "jenis": jenis},
        timeout=10,
    )
  except Exception:
    pass


async def catat_kantor(agen, teks, jenis="obrolan"):
  aktivitas = data.setdefault("aktivitas", [])
  aktivitas.append({
      "waktu": datetime.now(timezone.utc).isoformat(),
      "agen": agen,
      "teks": teks[:300],
      "jenis": jenis,
  })
  del aktivitas[:-80]
  simpan_data()
  await asyncio.to_thread(catat_kantor_sinkron, agen, teks, jenis)


AKSI_KANTOR = {
    "bersihkan_sampah": "Hapus file unduhan dan file AI yang berumur lebih dari 1 jam",
    "segarkan_diri": "Muat ulang pengaturan, kosongkan riwayat chat, perbarui status bot",
    "kirim_email_pemilik": "Tulis dan kirim email ke alamat email pemilik bot",
    "buat_repo_github": "Susun proyek, buat repo GitHub privat di akun pemilik, lalu unggah filenya",
    "riset_web": "Cari informasi terbaru di internet lalu rangkum hasilnya",
    "arsipkan_repo": "Arsipkan repo GitHub milik pemilik (jadi hanya-baca, bisa dipulihkan)",
    "hapus_repo": "Hapus permanen repo GitHub milik pemilik (butuh izin delete_repo)",
    "edit_file_repo": "Ubah satu file di repo GitHub yang sudah ada sesuai instruksi",
}


def ada_placeholder(teks):
  return bool(
      re.search(
          r"\[[^\]]{1,40}\]|yourrepo|your name|example\.com|yth\. tim",
          teks,
          re.IGNORECASE,
      )
  )


def bersihkan_placeholder(teks):
  teks = re.sub(r"\[[^\]]{1,40}\]", "", teks)
  teks = re.sub(
      r"https?://\S*(?:yourrepo|example\.com|your[-_]?domain)\S*",
      "",
      teks,
      flags=re.IGNORECASE,
  )
  return teks.strip()


def bersihkan_markdown(teks):
  teks = re.sub(r"\*\*|__|`", "", teks)
  return re.sub(r"^#+\s*", "", teks, flags=re.MULTILINE)


def bungkus_email(isi):
  return f"Halo Bos,\n\n{isi.strip()}\n\nSalam,\nChat AI\nKantor RyHanC"
