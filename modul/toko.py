import discord
from discord import app_commands

from modul.inti import PEMILIK_ID, bersihkan_error, data, simpan_data, tree


class TestiModal(discord.ui.Modal, title="Kirim Testimoni"):

  def __init__(self, channel_target):
    super().__init__()
    self.channel_target = channel_target

  rating = discord.ui.TextInput(
      label="Rating 1 sampai 5", placeholder="contoh: 5", max_length=1
  )
  komentar = discord.ui.TextInput(
      label="Komentar", style=discord.TextStyle.paragraph, max_length=500
  )

  async def on_submit(self, interaction: discord.Interaction):
    try:
      angka = int(str(self.rating))
    except Exception:
      angka = 0
    angka = max(0, min(5, angka))
    bintang = "★" * angka + "☆" * (5 - angka)
    embed = discord.Embed(
        description=str(self.komentar),
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_author(
        name=str(interaction.user), icon_url=interaction.user.display_avatar.url
    )
    embed.add_field(name="Rating", value=f"{bintang} ({angka}/5)")
    try:
      await self.channel_target.send(embed=embed)
      await interaction.response.send_message(
          "Terima kasih, testimoni kamu sudah dikirim.", ephemeral=True
      )
    except Exception as e:
      await interaction.response.send_message(
          f"Gagal mengirim: {bersihkan_error(e)}", ephemeral=True
      )


@tree.command(name="testi", description="Kirim testimoni ke channel ini")
async def testi(interaction: discord.Interaction):
  await interaction.response.send_modal(TestiModal(interaction.channel))


@tree.command(name="hargaset", description="Tambah atau ubah harga sebuah item")
@app_commands.describe(
    item="Nama item, contoh: 1000 Robux VILOG", harga="Harga, contoh: Rp 130.000"
)
@app_commands.checks.has_permissions(administrator=True)
async def hargaset(interaction: discord.Interaction, item: str, harga: str):
  gid = str(interaction.guild_id)
  data["harga"].setdefault(gid, {})[item[:80]] = harga[:80]
  simpan_data()
  await interaction.response.send_message(
      f"Harga disimpan: {item} = {harga}", ephemeral=True
  )


@tree.command(
    name="hargahapus", description="Hapus satu item dari daftar harga"
)
@app_commands.checks.has_permissions(administrator=True)
async def hargahapus(interaction: discord.Interaction, item: str):
  gid = str(interaction.guild_id)
  daftar = data["harga"].get(gid, {})
  if item not in daftar:
    await interaction.response.send_message(
        "Item itu tidak ada di daftar harga.", ephemeral=True
    )
    return
  daftar.pop(item)
  simpan_data()
  await interaction.response.send_message(
      f"Item {item} dihapus dari daftar harga.", ephemeral=True
  )


@tree.command(name="harga", description="Lihat daftar harga")
async def harga(interaction: discord.Interaction):
  gid = str(interaction.guild_id)
  daftar = data["harga"].get(gid, {})
  if not daftar:
    await interaction.response.send_message("Daftar harga masih kosong.")
    return
  embed = discord.Embed(
      title="Daftar Harga",
      color=discord.Color.green(),
      timestamp=discord.utils.utcnow(),
  )
  for item, nilai in list(daftar.items())[:25]:
    embed.add_field(name=item, value=nilai, inline=False)
  await interaction.response.send_message(embed=embed)


@tree.command(name="pricelist", description="Lihat paket dan harga premium bot ini")
async def pricelist(interaction: discord.Interaction):
  if not data["pricelist"]:
    await interaction.response.send_message(
        "Daftar harga premium belum diatur. Hubungi owner bot."
    )
    return
  embed = discord.Embed(
      title="Paket Premium RyHanC",
      description=(
          "Fitur premium: /setup, /hapussetup, /tiketpanel, /gayanama,"
          " /setbanner"
      ),
      color=discord.Color.gold(),
  )
  for item in data["pricelist"]:
    embed.add_field(
        name=f"{item['nama']} - {item['harga']}",
        value=item.get("keterangan") or "\u200b",
        inline=False,
    )
  await interaction.response.send_message(embed=embed)


@tree.command(
    name="pricelistset",
    description="Tambah atau ubah paket harga premium (khusus owner)",
)
@app_commands.describe(
    nama="Nama paket, misal: Bulanan",
    harga="Harga, misal: Rp 25.000",
    keterangan="Opsional, detail tambahan",
)
async def pricelistset(
    interaction: discord.Interaction,
    nama: str,
    harga: str,
    keterangan: str = None,
):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Hanya owner bot yang bisa memakai perintah ini.", ephemeral=True
    )
    return
  daftar = data["pricelist"]
  for item in daftar:
    if item["nama"].lower() == nama.lower():
      item["harga"] = harga
      item["keterangan"] = keterangan
      simpan_data()
      await interaction.response.send_message(
          f"Paket {nama} diperbarui.", ephemeral=True
      )
      return
  daftar.append({"nama": nama, "harga": harga, "keterangan": keterangan})
  simpan_data()
  await interaction.response.send_message(
      f"Paket {nama} ditambahkan.", ephemeral=True
  )


@tree.command(
    name="pricelistdel", description="Hapus paket harga premium (khusus owner)"
)
@app_commands.describe(nama="Nama paket yang mau dihapus")
async def pricelistdel(interaction: discord.Interaction, nama: str):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Hanya owner bot yang bisa memakai perintah ini.", ephemeral=True
    )
    return
  daftar = data["pricelist"]
  sebelum = len(daftar)
  data["pricelist"] = [
      item for item in daftar if item["nama"].lower() != nama.lower()
  ]
  if len(data["pricelist"]) == sebelum:
    await interaction.response.send_message(
        "Paket dengan nama itu tidak ditemukan.", ephemeral=True
    )
    return
  simpan_data()
  await interaction.response.send_message(
      f"Paket {nama} dihapus.", ephemeral=True
  )
