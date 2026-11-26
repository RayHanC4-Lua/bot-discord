import re

import discord
from discord import app_commands

from modul.inti import data, simpan_data, tree


SERVER_ID_LAMA = 1464581081822138370


def gudang_id_lagu(guild_id, user_id):
  berubah = False
  lama_semua = []
  lama = data.get("id_fitur")
  if isinstance(lama, dict) and isinstance(lama.get("daftar"), list):
    lama_semua.extend(lama["daftar"])
    data.pop("id_fitur", None)
    berubah = True
  for kunci in ("id_lagu", "id_lagu_pribadi"):
    nilai = data.get(kunci)
    if isinstance(nilai, dict):
      for k in list(nilai):
        if not isinstance(nilai[k], list):
          nilai[k] = []
          berubah = True
    else:
      if isinstance(nilai, list):
        lama_semua.extend(nilai)
      data[kunci] = {}
      berubah = True
  if lama_semua:
    tujuan = data["id_lagu"].setdefault(str(SERVER_ID_LAMA), [])
    for entri in lama_semua:
      if isinstance(entri, (str, int)) and str(entri) not in map(str, tujuan):
        tujuan.append(str(entri))
  if berubah:
    simpan_data()
  if guild_id:
    return data["id_lagu"].setdefault(str(guild_id), [])
  return data["id_lagu_pribadi"].setdefault(str(user_id), [])


def pecah_id_lagu(entri):
  teks = str(entri).strip()
  cocok = re.match(r"(\d+)", teks)
  if cocok:
    nomor = cocok.group(1)
    nama = teks[len(nomor):].strip(" -:|")
    return nomor, nama
  if " - " in teks:
    nomor, nama = teks.split(" - ", 1)
    return nomor.strip(), nama.strip()
  return teks, ""


async def isi_id_lagu(interaction: discord.Interaction, current: str):
  daftar = gudang_id_lagu(interaction.guild_id, interaction.user.id)
  kunci = current.lower()
  return [
      app_commands.Choice(name=str(e)[:100], value=str(e)[:100])
      for e in daftar
      if kunci in str(e).lower()
  ][:25]


@tree.command(name="tambahid", description="Tambah ID lagu ke daftar")
@app_commands.describe(
    id_lagu="ID lagu, boleh ditambah nama, contoh: 1234567890 - Judul Lagu"
)
async def tambahid(interaction: discord.Interaction, id_lagu: str):
  daftar = gudang_id_lagu(interaction.guild_id, interaction.user.id)
  id_lagu = id_lagu.strip()[:150]
  if not id_lagu:
    await interaction.response.send_message("ID lagu kosong.", ephemeral=True)
    return
  if id_lagu in daftar:
    await interaction.response.send_message(
        f"`{id_lagu}` sudah ada di daftar.", ephemeral=True
    )
    return
  if len(daftar) >= 200:
    await interaction.response.send_message(
        "Daftar sudah berisi 200 lagu. Hapus beberapa dulu dengan /hapusid.",
        ephemeral=True,
    )
    return
  daftar.append(id_lagu)
  simpan_data()
  tempat = "daftar server ini" if interaction.guild_id else "daftar pribadimu"
  await interaction.response.send_message(
      f"`{id_lagu}` ditambahkan ke {tempat}.", ephemeral=True
  )


@tree.command(name="hapusid", description="Hapus ID lagu dari daftar")
@app_commands.describe(id_lagu="Pilih dari daftar atau ketik ID lagunya")
@app_commands.autocomplete(id_lagu=isi_id_lagu)
async def hapusid(interaction: discord.Interaction, id_lagu: str):
  daftar = gudang_id_lagu(interaction.guild_id, interaction.user.id)
  target = id_lagu.strip()
  cocok = next((e for e in daftar if str(e)[:100] == target), None)
  if cocok is None:
    cocok = next(
        (e for e in daftar if pecah_id_lagu(e)[0] == target), None
    )
  if cocok is None:
    await interaction.response.send_message(
        f"`{target}` tidak ditemukan di daftar ini.", ephemeral=True
    )
    return
  daftar.remove(cocok)
  simpan_data()
  await interaction.response.send_message(
      f"`{cocok}` dihapus dari daftar.", ephemeral=True
  )


@tree.command(name="id", description="Lihat semua ID lagu yang tersimpan")
async def lihat_id_lagu(interaction: discord.Interaction):
  daftar = gudang_id_lagu(interaction.guild_id, interaction.user.id)
  if not daftar:
    await interaction.response.send_message(
        "Belum ada ID lagu yang tersimpan di sini.", ephemeral=True
    )
    return
  judul = "ID lagu server ini" if interaction.guild_id else "ID lagu pribadimu"
  baris = [f"{i}. {e}" for i, e in enumerate(daftar, start=1)]
  await interaction.response.send_message(
      (f"{judul}:\n" + "\n".join(baris))[:1900], ephemeral=True
  )


class PilihIdSelect(discord.ui.Select):

  def __init__(self, daftar):
    self.daftar = daftar
    opsi = []
    for i, entri in enumerate(daftar[:25]):
      nomor, nama = pecah_id_lagu(entri)
      opsi.append(
          discord.SelectOption(
              label=(nama or nomor)[:100],
              value=str(i),
              description=nomor[:100],
          )
      )
    super().__init__(placeholder="Pilih lagu", options=opsi)

  async def callback(self, interaction: discord.Interaction):
    nomor, nama = pecah_id_lagu(self.daftar[int(self.values[0])])
    await interaction.response.send_message(
        f"{nama or 'ID lagu'}:\n```\n{nomor}\n```", ephemeral=True
    )


class PilihIdView(discord.ui.View):

  def __init__(self, daftar):
    super().__init__(timeout=300)
    self.add_item(PilihIdSelect(daftar))


@tree.command(
    name="pilihid",
    description="Pilih satu lagu untuk menyalin ID-nya saja",
)
async def pilihid(interaction: discord.Interaction):
  daftar = list(gudang_id_lagu(interaction.guild_id, interaction.user.id))
  if not daftar:
    await interaction.response.send_message(
        "Belum ada ID lagu yang tersimpan di sini.", ephemeral=True
    )
    return
  catatan = ""
  if len(daftar) > 25:
    catatan = f" Yang tampil 25 pertama dari {len(daftar)} lagu."
  await interaction.response.send_message(
      "Pilih lagu, nanti ID-nya dikirim sendirian supaya gampang disalin."
      + catatan,
      view=PilihIdView(daftar),
      ephemeral=True,
  )
