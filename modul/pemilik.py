import asyncio
import os
import sys

import discord
from dotenv import find_dotenv

from modul.inti import PEMILIK_ID, client, tree
from modul.kantor.aksi import aksi_segarkan_diri


@tree.command(
    name="refresh",
    description="Segarkan bot: muat ulang pengaturan dan fitur tambahan (khusus pemilik)",
)
async def refresh(interaction: discord.Interaction):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  await interaction.response.defer(ephemeral=True)
  hasil = await aksi_segarkan_diri()
  await tree.sync()
  await interaction.followup.send(hasil, ephemeral=True)


@tree.command(
    name="restart",
    description="Nyalakan ulang bot sepenuhnya (khusus pemilik)",
)
async def restart(interaction: discord.Interaction):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  await interaction.response.send_message(
      "Bot dinyalakan ulang, tunggu sekitar 10 detik.", ephemeral=True
  )
  await asyncio.sleep(1)
  await client.close()
  os.execv(sys.executable, [sys.executable] + sys.argv)


@tree.command(
    name="cekenv",
    description="Periksa apakah isi .env sudah terbaca bot (khusus pemilik)",
)
async def cekenv(interaction: discord.Interaction):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  jalur = find_dotenv()
  di_file = set()
  if jalur:
    try:
      with open(jalur, encoding="utf-8") as f:
        for baris in f:
          baris = baris.strip()
          if baris and not baris.startswith("#") and "=" in baris:
            di_file.add(baris.split("=", 1)[0].strip())
    except OSError:
      pass
  kunci = [
      "DISCORD_TOKEN",
      "SMTP_USER",
      "SMTP_PASSWORD",
      "EMAIL_PEMILIK",
      "GITHUB_TOKEN",
  ]
  baris_hasil = [
      f"File .env yang dibaca bot: {jalur or 'tidak ditemukan'}",
      f"Folder kerja bot: {os.getcwd()}",
  ]
  for k in kunci:
    file_ada = "ada" if k in di_file else "tidak ada"
    memori_ada = "terbaca" if os.getenv(k) else "kosong"
    baris_hasil.append(f"{k}: di file {file_ada}, di bot {memori_ada}")
  await interaction.response.send_message(
      "\n".join(baris_hasil), ephemeral=True
  )
