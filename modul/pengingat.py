import asyncio
from datetime import datetime, timedelta
import os
import random
import re

import discord
from discord import app_commands

from modul.inti import (
    CONFIG_FILE,
    ZONA_WIB,
    bersihkan_error,
    client,
    data,
    simpan_data,
    tree,
)


FOLDER_GAMBAR_INGAT = os.path.join(
    os.path.dirname(CONFIG_FILE) or ".", "pengingat_gambar"
)
os.makedirs(FOLDER_GAMBAR_INGAT, exist_ok=True)
BATAS_PENGINGAT = 30
TANPA_PING_PENGINGAT = discord.AllowedMentions(
    everyone=False, roles=False, users=True
)


def migrasi_pengingat():
  lama = data.get("pengingat")
  pribadi = data.setdefault("pengingat_pribadi", {})
  if isinstance(lama, dict) and all(isinstance(v, list) for v in lama.values()):
    return
  data["pengingat"] = {}
  if isinstance(lama, list):
    for p in lama:
      if not isinstance(p, dict):
        continue
      kanal = None
      try:
        kanal = client.get_channel(int(p.get("channel_id") or 0))
      except (TypeError, ValueError):
        kanal = None
      guild = getattr(kanal, "guild", None)
      if guild is not None:
        p["guild_id"] = guild.id
        data["pengingat"].setdefault(str(guild.id), []).append(p)
      else:
        pribadi.setdefault(str(p.get("user_id")), []).append(p)
  simpan_data()


def gudang_pengingat(guild_id, user_id):
  migrasi_pengingat()
  if guild_id:
    return data["pengingat"].setdefault(str(guild_id), [])
  return data["pengingat_pribadi"].setdefault(str(user_id), [])


def waktu_pengingat(p):
  try:
    w = datetime.fromisoformat(str(p.get("waktu")))
  except ValueError:
    return None
  if w.tzinfo is None:
    w = w.replace(tzinfo=ZONA_WIB)
  return w


def path_gambar_pengingat(p):
  for kunci in ("gambar", "gambar_path", "file_gambar"):
    nilai = p.get(kunci)
    if isinstance(nilai, str) and nilai and os.path.isfile(nilai):
      return nilai
  return None


def hapus_gambar_pengingat(p):
  path = path_gambar_pengingat(p)
  if path:
    try:
      os.remove(path)
    except OSError:
      pass


def hitung_waktu_target(jam, menit, tanggal, sekarang):
  if not tanggal:
    target = sekarang.replace(hour=jam, minute=menit, second=0, microsecond=0)
    if target <= sekarang:
      target += timedelta(days=1)
    return target, None
  cocok = re.fullmatch(
      r"\s*(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{4}))?\s*", tanggal
  )
  if not cocok:
    return None, "Format tanggal salah. Pakai DD-MM atau DD-MM-YYYY, contoh 25-12."
  hari = int(cocok.group(1))
  bulan = int(cocok.group(2))
  tahun = int(cocok.group(3)) if cocok.group(3) else sekarang.year
  try:
    target = datetime(tahun, bulan, hari, jam, menit, tzinfo=ZONA_WIB)
  except ValueError:
    return None, "Tanggal itu tidak ada di kalender. Periksa lagi hari dan bulannya."
  if target <= sekarang:
    if cocok.group(3):
      return None, "Tanggal dan jam itu sudah lewat. Pilih waktu yang akan datang."
    try:
      target = target.replace(year=tahun + 1)
    except ValueError:
      return None, "Tanggal itu tidak ada di tahun depan. Tulis tahunnya langsung."
  return target, None


async def coba_kirim_pengingat(tujuan, teks, path):
  kwargs = {"allowed_mentions": TANPA_PING_PENGINGAT}
  if path:
    kwargs["file"] = discord.File(path)
  try:
    await tujuan.send(teks[:2000], **kwargs)
    return True
  except Exception:
    return False


async def kirim_pengingat(p, telat):
  teks = f"<@{p.get('user_id')}> **Pengingat:** {p.get('pesan', '')}"
  if telat > 300:
    teks += (
        f"\n(terkirim terlambat sekitar {int(telat // 60)} menit karena bot"
        " sempat mati)"
    )
  path = path_gambar_pengingat(p)
  terkirim = False
  cid = p.get("channel_id")
  if cid:
    tujuan = client.get_channel(int(cid))
    if tujuan is None:
      try:
        tujuan = await client.fetch_channel(int(cid))
      except Exception:
        tujuan = None
    if tujuan is not None:
      terkirim = await coba_kirim_pengingat(tujuan, teks, path)
  if not terkirim and p.get("user_id"):
    try:
      user = await client.fetch_user(int(p["user_id"]))
      await coba_kirim_pengingat(user, teks, path)
    except Exception:
      pass
  hapus_gambar_pengingat(p)


async def jalankan_pengingat_jatuh_tempo():
  migrasi_pengingat()
  sekarang = datetime.now(ZONA_WIB)
  semua = list(data["pengingat"].values()) + list(
      data["pengingat_pribadi"].values()
  )
  for daftar in semua:
    for p in list(daftar):
      w = waktu_pengingat(p)
      if w is None:
        daftar.remove(p)
        simpan_data()
        continue
      if w > sekarang:
        continue
      daftar.remove(p)
      simpan_data()
      await kirim_pengingat(p, (sekarang - w).total_seconds())


async def loop_pengingat():
  await client.wait_until_ready()
  while not client.is_closed():
    try:
      await jalankan_pengingat_jatuh_tempo()
    except Exception as e:
      print(f"Pengingat error: {bersihkan_error(e)}")
    await asyncio.sleep(15)


@tree.command(
    name="ingatkan",
    description="Buat pengingat WIB, bisa pakai tanggal dan gambar",
)
@app_commands.describe(
    jam="Jam 0 sampai 23 (WIB)",
    menit="Menit 0 sampai 59",
    pesan="Isi pengingat",
    tanggal="Opsional, format DD-MM atau DD-MM-YYYY",
    gambar="Opsional, gambar yang ikut dikirim saat pengingat berbunyi",
)
async def ingatkan(
    interaction: discord.Interaction,
    jam: app_commands.Range[int, 0, 23],
    menit: app_commands.Range[int, 0, 59],
    pesan: str,
    tanggal: str = None,
    gambar: discord.Attachment = None,
):
  if gambar is not None:
    if not gambar.content_type or not gambar.content_type.startswith("image/"):
      await interaction.response.send_message(
          "Lampiran harus berupa gambar.", ephemeral=True
      )
      return
    if gambar.size > 8 * 1024 * 1024:
      await interaction.response.send_message(
          "Ukuran gambar maksimal 8 MB.", ephemeral=True
      )
      return
  daftar = gudang_pengingat(interaction.guild_id, interaction.user.id)
  if len(daftar) >= BATAS_PENGINGAT:
    tempat = "server ini" if interaction.guild_id else "pengingat pribadimu"
    await interaction.response.send_message(
        f"Batas {BATAS_PENGINGAT} pengingat untuk {tempat} sudah tercapai."
        " Hapus yang lama dulu dengan /hapusingat.",
        ephemeral=True,
    )
    return
  sekarang = datetime.now(ZONA_WIB)
  target, masalah = hitung_waktu_target(jam, menit, tanggal, sekarang)
  if masalah:
    await interaction.response.send_message(masalah, ephemeral=True)
    return
  await interaction.response.defer(ephemeral=True)
  dipakai = {p.get("id") for p in daftar}
  nomor = random.randint(100000, 999999)
  while nomor in dipakai:
    nomor = random.randint(100000, 999999)
  path = None
  if gambar is not None:
    aman = re.sub(r"[^A-Za-z0-9._-]", "", gambar.filename)[-40:] or "gambar.png"
    path = os.path.join(FOLDER_GAMBAR_INGAT, f"{nomor}_{aman}")
    try:
      await gambar.save(path)
    except Exception as e:
      await interaction.followup.send(
          f"Gagal menyimpan gambar: {bersihkan_error(e)}", ephemeral=True
      )
      return
  daftar.append({
      "id": nomor,
      "waktu": target.isoformat(),
      "pesan": pesan[:1500],
      "channel_id": interaction.channel_id,
      "user_id": interaction.user.id,
      "guild_id": interaction.guild_id,
      "gambar": path,
  })
  simpan_data()
  jenis = "server" if interaction.guild_id else "pribadi"
  tambahan = " dengan gambar" if path else ""
  await interaction.followup.send(
      f"Pengingat {jenis}{tambahan} diset untuk {target:%d-%m-%Y %H:%M} WIB"
      f" (ID {nomor}).",
      ephemeral=True,
  )


@tree.command(
    name="listingat",
    description="Lihat pengingat server ini, atau pengingat pribadi di DM",
)
async def listingat(interaction: discord.Interaction):
  daftar = gudang_pengingat(interaction.guild_id, interaction.user.id)
  if not daftar:
    await interaction.response.send_message(
        "Tidak ada pengingat aktif.", ephemeral=True
    )
    return
  urut = sorted(
      daftar,
      key=lambda p: waktu_pengingat(p) or datetime.max.replace(tzinfo=ZONA_WIB),
  )
  baris = []
  for p in urut:
    w = waktu_pengingat(p)
    teks_waktu = f"{w.astimezone(ZONA_WIB):%d-%m-%Y %H:%M}" if w else "?"
    tanda = " (ada gambar)" if path_gambar_pengingat(p) else ""
    pembuat = f" oleh <@{p.get('user_id')}>" if interaction.guild_id else ""
    baris.append(
        f"`{p.get('id')}` {teks_waktu} WIB{pembuat}{tanda}:"
        f" {str(p.get('pesan', ''))[:80]}"
    )
  judul = "Pengingat server ini" if interaction.guild_id else "Pengingat pribadimu"
  await interaction.response.send_message(
      (f"{judul}:\n" + "\n".join(baris))[:1900],
      ephemeral=True,
      allowed_mentions=discord.AllowedMentions.none(),
  )


@tree.command(name="hapusingat", description="Hapus pengingat berdasarkan ID")
@app_commands.describe(id="ID pengingat dari /listingat")
async def hapusingat(interaction: discord.Interaction, id: int):
  daftar = gudang_pengingat(interaction.guild_id, interaction.user.id)
  cocok = next((p for p in daftar if p.get("id") == id), None)
  if cocok is None:
    await interaction.response.send_message(
        f"Pengingat {id} tidak ditemukan di sini.", ephemeral=True
    )
    return
  if interaction.guild_id and cocok.get("user_id") != interaction.user.id:
    izin = getattr(interaction.user, "guild_permissions", None)
    if not (izin and izin.manage_guild):
      await interaction.response.send_message(
          "Kamu hanya bisa menghapus pengingat buatanmu sendiri.",
          ephemeral=True,
      )
      return
  daftar.remove(cocok)
  hapus_gambar_pengingat(cocok)
  simpan_data()
  await interaction.response.send_message(
      f"Pengingat {id} berhasil dihapus.", ephemeral=True
  )
