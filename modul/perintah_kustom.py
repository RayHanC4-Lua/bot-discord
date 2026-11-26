import discord
from discord import app_commands

from modul.inti import data, simpan_data, tree


async def isi_cc(interaction: discord.Interaction, current: str):
  daftar = data["custom_commands"].get(str(interaction.guild_id), {})
  cocok = [n for n in sorted(daftar) if current.lower() in n]
  return [app_commands.Choice(name=n, value=n) for n in cocok[:25]]


@tree.command(name="addcmd", description="Membuat custom command teks baru")
@app_commands.checks.has_permissions(administrator=True)
async def addcmd(interaction: discord.Interaction, nama: str, respon: str):
  nama_cmd = nama.lower().replace("/", "").strip()
  if not nama_cmd or " " in nama_cmd or len(nama_cmd) > 30:
    await interaction.response.send_message(
        (
            "Nama tidak boleh kosong, tidak boleh ada spasi, maksimal 30"
            " huruf."
        ),
        ephemeral=True,
    )
    return
  data["custom_commands"].setdefault(str(interaction.guild_id), {})[
      nama_cmd
  ] = respon
  simpan_data()
  await interaction.response.send_message(
      f"Custom command disimpan. Panggil dengan /cc nama: {nama_cmd}",
      ephemeral=True,
  )


@tree.command(name="delcmd", description="Menghapus custom command teks")
@app_commands.autocomplete(nama=isi_cc)
@app_commands.checks.has_permissions(administrator=True)
async def delcmd(interaction: discord.Interaction, nama: str):
  daftar = data["custom_commands"].get(str(interaction.guild_id), {})
  nama_cmd = nama.lower().replace("/", "").strip()
  if nama_cmd not in daftar:
    await interaction.response.send_message(
        f"Custom command {nama_cmd} tidak ditemukan.", ephemeral=True
    )
    return
  daftar.pop(nama_cmd)
  simpan_data()
  await interaction.response.send_message(
      f"Custom command {nama_cmd} berhasil dihapus.", ephemeral=True
  )


@tree.command(name="cc", description="Menjalankan custom command")
@app_commands.autocomplete(nama=isi_cc)
async def cc(interaction: discord.Interaction, nama: str):
  daftar = data["custom_commands"].get(str(interaction.guild_id), {})
  nama_cmd = nama.lower().replace("/", "").strip()
  respon = daftar.get(nama_cmd)
  if not respon:
    await interaction.response.send_message(
        "Custom command tidak ditemukan.", ephemeral=True
    )
    return
  await interaction.response.send_message(respon)
