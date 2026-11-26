from datetime import timedelta

import discord
from discord import app_commands

from modul.inti import PEMILIK_ID, cek_premium, client, data, simpan_data, tree


@tree.command(
    name="setpremium",
    description="Beri status premium ke sebuah server (khusus owner)",
)
@app_commands.describe(
    server_id="ID server yang diberi premium",
    hari="Lama premium dalam hari, isi 0 untuk permanen",
)
async def setpremium(
    interaction: discord.Interaction,
    server_id: str,
    hari: app_commands.Range[int, 0, 3650],
):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Hanya owner bot yang bisa memakai perintah ini.", ephemeral=True
    )
    return
  try:
    gid = int(server_id)
  except ValueError:
    await interaction.response.send_message(
        "Server ID harus berupa angka.", ephemeral=True
    )
    return
  sampai = (
      None
      if hari == 0
      else (discord.utils.utcnow() + timedelta(days=hari)).isoformat()
  )
  data["premium"][str(gid)] = {"sampai": sampai}
  simpan_data()
  guild = client.get_guild(gid)
  nama = guild.name if guild else f"ID {gid}"
  keterangan = (
      "permanen" if hari == 0 else f"{hari} hari (sampai {sampai[:10]})"
  )
  await interaction.response.send_message(
      f"Premium diberikan ke {nama}: {keterangan}.", ephemeral=True
  )


@tree.command(
    name="hapuspremium",
    description="Cabut status premium sebuah server (khusus owner)",
)
@app_commands.describe(server_id="ID server yang dicabut premiumnya")
async def hapuspremium(interaction: discord.Interaction, server_id: str):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Hanya owner bot yang bisa memakai perintah ini.", ephemeral=True
    )
    return
  if data["premium"].pop(server_id, None) is None:
    await interaction.response.send_message(
        "Server itu tidak sedang premium.", ephemeral=True
    )
    return
  simpan_data()
  await interaction.response.send_message(
      "Premium server itu sudah dicabut.", ephemeral=True
  )


@tree.command(name="premiumstatus", description="Cek status premium server ini")
async def premiumstatus(interaction: discord.Interaction):
  aktif, batas = cek_premium(interaction.guild_id)
  if not aktif:
    await interaction.response.send_message(
        "Server ini belum premium.", ephemeral=True
    )
    return
  keterangan = (
      "permanen, tidak ada batas waktu"
      if batas is None
      else f"sampai {discord.utils.format_dt(batas, 'F')}"
  )
  await interaction.response.send_message(
      f"Server ini premium, {keterangan}.", ephemeral=True
  )


@tree.command(
    name="premiumlist",
    description="Lihat semua server yang sedang premium (khusus owner)",
)
async def premiumlist(interaction: discord.Interaction):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Hanya owner bot yang bisa memakai perintah ini.", ephemeral=True
    )
    return
  if not data["premium"]:
    await interaction.response.send_message(
        "Belum ada server premium.", ephemeral=True
    )
    return
  baris = []
  for gid_str, info in list(data["premium"].items()):
    aktif, batas = cek_premium(gid_str)
    if not aktif:
      continue
    guild = client.get_guild(int(gid_str))
    nama = guild.name if guild else gid_str
    ket = "permanen" if batas is None else discord.utils.format_dt(batas, "d")
    baris.append(f"{nama} - {ket}")
  teks = "\n".join(baris) if baris else "Tidak ada yang aktif saat ini."
  await interaction.response.send_message(
      f"Server premium aktif:\n{teks[:1900]}", ephemeral=True
  )
