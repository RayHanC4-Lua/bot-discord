import asyncio
from datetime import datetime, timedelta, timezone
import re

import discord
from discord import app_commands

from modul.ai_alat import alat_kirim_email_pemilik
from modul.inti import (
    PEMILIK_ID,
    bersihkan_error,
    client,
    data,
    simpan_data,
    tree,
)
from modul.kantor.dasar import WIB, catat_kantor, kirim_ke_kanal


def deteksi_waktu(teks, sekarang):
  t = teks.lower()
  rel = re.search(r"(\d+)\s*(menit|jam)\s*(?:lagi|dari sekarang)", t)
  if rel:
    n = int(rel.group(1))
    if rel.group(2) == "menit":
      return sekarang + timedelta(minutes=n)
    return sekarang + timedelta(hours=n)
  cocok = [
      m
      for m in re.finditer(r"(?:jam|pukul)\s*(\d{1,2})(?:[:.](\d{2}))?", t)
      if "sekarang" not in t[max(0, m.start() - 14) : m.start()]
  ]
  if not cocok:
    return None
  m = cocok[-1]
  jam = int(m.group(1))
  menit = int(m.group(2) or 0)
  if jam < 12 and re.search(r"sore|malam", t[m.end() : m.end() + 12]):
    jam += 12
  if jam > 23 or menit > 59:
    return None
  hari = 1 if "besok" in t else (2 if "lusa" in t else 0)
  return sekarang.replace(
      hour=jam, minute=menit, second=0, microsecond=0
  ) + timedelta(days=hari)


def tambah_jadwal(job):
  daftar = data.setdefault("jadwal", [])
  job["id"] = max([j["id"] for j in daftar] + [0]) + 1
  daftar.append(job)
  simpan_data()
  return job["id"]


async def jalankan_jadwal(job, terlambat):
  if terlambat > 1800:
    pesan = (
        f"Jadwal nomor {job['id']} terlewat karena bot sedang mati, jadi"
        " email tidak dikirim."
    )
  else:
    pemilik = type("Pemilik", (), {"id": PEMILIK_ID})()
    try:
      hasil = await alat_kirim_email_pemilik(
          {"member": pemilik}, job["subjek"], job["isi"]
      )
      if hasil.get("berhasil"):
        pesan = (
            "Pengingat terkirim ke email bos sesuai jadwal. Subjeknya:"
            f" {job['subjek']}"
        )
      else:
        pesan = f"Pengingat gagal dikirim: {hasil.get('error')}"
    except Exception as e:
      pesan = f"Pengingat gagal dikirim: {bersihkan_error(e)}"
  await catat_kantor("chatai", pesan, "aksi")
  await kirim_ke_kanal(job.get("channel_id"), f"**@chatai**: {pesan}")


async def loop_penjadwal():
  await client.wait_until_ready()
  while not client.is_closed():
    try:
      sekarang = datetime.now(timezone.utc)
      for job in list(data.get("jadwal", [])):
        waktu = datetime.fromisoformat(job["waktu"])
        if waktu <= sekarang:
          data["jadwal"].remove(job)
          simpan_data()
          await jalankan_jadwal(job, (sekarang - waktu).total_seconds())
    except Exception as e:
      print(f"Penjadwal error: {bersihkan_error(e)}")
    await asyncio.sleep(20)


@tree.command(
    name="jadwal", description="Lihat pekerjaan terjadwal (khusus pemilik)"
)
async def jadwal(interaction: discord.Interaction):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  daftar = data.get("jadwal", [])
  if not daftar:
    await interaction.response.send_message(
        "Belum ada pekerjaan terjadwal.", ephemeral=True
    )
    return
  baris = []
  for j in daftar:
    waktu = datetime.fromisoformat(j["waktu"]).astimezone(WIB)
    baris.append(f"Nomor {j['id']}: {waktu:%d/%m %H:%M} WIB, email, {j['subjek']}")
  await interaction.response.send_message("\n".join(baris)[:1900], ephemeral=True)


@tree.command(
    name="batalkanjadwal", description="Batalkan pekerjaan terjadwal (khusus pemilik)"
)
@app_commands.describe(nomor="Nomor jadwal dari perintah /jadwal")
async def batalkanjadwal(interaction: discord.Interaction, nomor: int):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  daftar = data.get("jadwal", [])
  sisa = [j for j in daftar if j["id"] != nomor]
  if len(sisa) == len(daftar):
    await interaction.response.send_message(
        "Nomor jadwal itu tidak ditemukan.", ephemeral=True
    )
    return
  data["jadwal"] = sisa
  simpan_data()
  await interaction.response.send_message(
      f"Jadwal nomor {nomor} dibatalkan.", ephemeral=True
  )
