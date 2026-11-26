import ast
import asyncio
import importlib.util
import os
import time

import discord
from discord import app_commands

from modul.ai import kirim_groq
from modul.balasan import buat_file, ekstrak_blok_kode
from modul.inti import (
    PEMILIK_ID,
    bersihkan_error,
    client,
    data,
    simpan_data,
    tree,
)


EKSTENSI_DIR = "ekstensi"
os.makedirs(EKSTENSI_DIR, exist_ok=True)
EKSTENSI_PERINTAH = {}
MODEL_KODE = os.getenv("GROQ_MODEL_KODE", "openai/gpt-oss-120b")
LARANGAN_KODE = [
    "subprocess",
    "os.system",
    "os.popen",
    "os._exit",
    "sys.exit",
    "eval(",
    "exec(",
    "__import__",
    "shutil",
    "environ",
    "getenv",
    "load_dotenv",
    "DISCORD_TOKEN",
    "GROQ_API_KEY",
    "AI_API_KEY",
    ".env",
    "client.run",
    "client.extensions",
    "reload_extension",
    "load_extension",
    "commands.Bot",
]
PETUNJUK_EKSTENSI = (
    "Kamu menulis ekstensi untuk bot Discord berbasis discord.py 2.x. Keluarkan"
    " tepat satu blok kode python yang berisi satu fungsi biasa (bukan async)"
    " bernama pasang(client, tree, data, simpan_data). client adalah"
    " discord.Client biasa (bukan commands.Bot, jadi tidak ada extensions,"
    " cogs, load_extension, atau reload_extension), tree adalah"
    " app_commands.CommandTree, data adalah dict"
    " pengaturan bot, dan simpan_data() menyimpan data itu ke file. Fitur"
    " dibuat sebagai slash command lewat dekorator tree.command di dalam"
    " fungsi pasang. Untuk menyimpan data fitur, pakai"
    " data.setdefault('nama_fitur', {}) lalu panggil simpan_data(). Import di"
    " bagian atas file hanya dari: discord, asyncio, json, re, random,"
    " datetime, time, math, requests, aiohttp. Semua teks untuk user memakai"
    " Bahasa Indonesia. Jangan tulis komentar dan jangan pakai emoji di dalam"
    " kode. Jangan membaca"
    " token, variabel lingkungan, atau file .env. Jangan memakai subprocess,"
    " eval, exec, os.system, atau shutil. Berikan blok kode dan satu kalimat"
    " penjelasan singkat."
)


def panggil_groq_kode(permintaan, catatan=""):
  tugas = f"Permintaan fitur dari pemilik bot: {permintaan}"
  if catatan:
    tugas += f"\n\n{catatan}"
  return kirim_groq(
      {
          "model": MODEL_KODE,
          "messages": [
              {"role": "system", "content": PETUNJUK_EKSTENSI},
              {"role": "user", "content": tugas},
          ],
          "temperature": 0.3,
          "max_completion_tokens": 4000,
      },
      timeout=150,
  )


def ekstrak_kode_python(teks):
  blok = ekstrak_blok_kode(teks)
  for bahasa, kode in blok:
    if bahasa in ("python", "py"):
      return kode
  return blok[0][1] if blok else None


def periksa_kode(kode):
  try:
    ast.parse(kode)
  except SyntaxError as e:
    return f"Kode punya kesalahan penulisan di baris {e.lineno}"
  for kata in LARANGAN_KODE:
    if kata in kode:
      return f"Kode memakai hal yang dilarang: {kata}"
  if "def pasang" not in kode:
    return "Fungsi pasang tidak ditemukan"
  return None


def muat_ekstensi(nama_file):
  path = os.path.join(EKSTENSI_DIR, nama_file)
  nama = nama_file[:-3]
  sebelum = {c.name for c in tree.get_commands()}
  try:
    spec = importlib.util.spec_from_file_location(f"ekstensi_{nama}", path)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    modul.pasang(client, tree, data, simpan_data)
  except Exception:
    for c in {c.name for c in tree.get_commands()} - sebelum:
      tree.remove_command(c)
    raise
  baru = sorted({c.name for c in tree.get_commands()} - sebelum)
  EKSTENSI_PERINTAH[nama] = baru
  return baru


def muat_semua_ekstensi():
  for nama_file in sorted(os.listdir(EKSTENSI_DIR)):
    if nama_file.endswith(".py"):
      try:
        muat_ekstensi(nama_file)
      except Exception as e:
        print(f"Ekstensi {nama_file} gagal dimuat: {bersihkan_error(e)}")
        path = os.path.join(EKSTENSI_DIR, nama_file)
        try:
          os.replace(path, path + ".gagal")
        except OSError:
          pass


def muat_ulang_ekstensi():
  for daftar in list(EKSTENSI_PERINTAH.values()):
    for perintah in daftar:
      tree.remove_command(perintah)
  EKSTENSI_PERINTAH.clear()
  muat_semua_ekstensi()
  return len(EKSTENSI_PERINTAH)


class PasangFitur(discord.ui.View):

  def __init__(self, kode, nama_file):
    super().__init__(timeout=600)
    self.kode = kode
    self.nama_file = nama_file

  async def interaction_check(self, interaction: discord.Interaction):
    if interaction.user.id != PEMILIK_ID:
      await interaction.response.send_message(
          "Tombol ini khusus pemilik bot.", ephemeral=True
      )
      return False
    return True

  async def matikan_tombol(self, interaction):
    for item in self.children:
      item.disabled = True
    await interaction.message.edit(view=self)
    self.stop()

  @discord.ui.button(label="Pasang", style=discord.ButtonStyle.success)
  async def pasang(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.defer()
    await self.matikan_tombol(interaction)
    path = os.path.join(EKSTENSI_DIR, self.nama_file)
    with open(path, "w", encoding="utf-8") as f:
      f.write(self.kode)
    try:
      perintah = muat_ekstensi(self.nama_file)
      await tree.sync()
    except Exception as e:
      if os.path.exists(path):
        os.remove(path)
      await interaction.followup.send(
          f"Fitur gagal dipasang dan sudah dibatalkan otomatis, bot tetap"
          f" aman. Penyebab: {bersihkan_error(e)}"
      )
      return
    daftar = ", ".join(f"/{p}" for p in perintah) or "tidak ada perintah baru"
    await interaction.followup.send(
        f"Fitur terpasang tanpa restart. Perintah baru: {daftar}. Kalau"
        " belum muncul, tutup dan buka lagi Discord kamu."
    )

  @discord.ui.button(label="Batal", style=discord.ButtonStyle.danger)
  async def batal(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_message("Draft fitur dibatalkan.")
    await self.matikan_tombol(interaction)


@tree.command(
    name="tambahfitur",
    description="Minta AI membuat fitur baru untuk bot (khusus pemilik)",
)
@app_commands.describe(permintaan="Fitur apa yang kamu mau, jelaskan sebebasnya")
async def tambahfitur(interaction: discord.Interaction, permintaan: str):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  await interaction.response.defer()
  kode = None
  masalah = "Tidak ada blok kode"
  catatan = ""
  for _ in range(3):
    balasan = await asyncio.to_thread(panggil_groq_kode, permintaan, catatan)
    if balasan.startswith(("Error API", "Exception error")):
      await interaction.followup.send(balasan[:1800])
      return
    kode = ekstrak_kode_python(balasan)
    masalah = periksa_kode(kode) if kode else "Tidak ada blok kode"
    if not masalah:
      break
    catatan = (
        f"Percobaan sebelumnya ditolak karena: {masalah}. Perbaiki dan kirim"
        f" ulang kode lengkapnya.\n\nKode sebelumnya:\n{kode or balasan[:3000]}"
    )
    kode = None
  if not kode:
    await interaction.followup.send(
        f"AI belum berhasil membuat kode yang valid ({masalah}). Coba jelaskan"
        " permintaanmu dengan lebih rinci."
    )
    return
  nama_file = f"fitur_{int(time.time())}.py"
  path = buat_file("fitur", "py", kode)
  await interaction.followup.send(
      "Draft fitur sudah siap dan lolos pemeriksaan dasar. Tekan Pasang untuk"
      " mengaktifkan langsung tanpa restart, atau Batal.",
      file=discord.File(path),
      view=PasangFitur(kode, nama_file),
  )


async def isi_ekstensi(interaction: discord.Interaction, current: str):
  return [
      app_commands.Choice(name=f"{n} ({', '.join(p) or '-'})"[:100], value=n)
      for n, p in EKSTENSI_PERINTAH.items()
      if current.lower() in n.lower()
  ][:25]


@tree.command(
    name="hapusfitur", description="Copot fitur buatan AI (khusus pemilik)"
)
@app_commands.autocomplete(nama=isi_ekstensi)
async def hapusfitur(interaction: discord.Interaction, nama: str):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  if nama not in EKSTENSI_PERINTAH:
    await interaction.response.send_message(
        "Fitur itu tidak ditemukan.", ephemeral=True
    )
    return
  await interaction.response.defer(ephemeral=True)
  for perintah in EKSTENSI_PERINTAH.pop(nama):
    tree.remove_command(perintah)
  path = os.path.join(EKSTENSI_DIR, f"{nama}.py")
  if os.path.exists(path):
    os.remove(path)
  await tree.sync()
  await interaction.followup.send(f"Fitur {nama} sudah dicopot.", ephemeral=True)
