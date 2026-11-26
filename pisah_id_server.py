import sys

BERKAS = "bot.py"
BLOK_ID = 'SERVER_ID_LAMA = 1464581081822138370\n\n\ndef gudang_id_lagu(guild_id, user_id):\n  lama = data.get("id_fitur")\n  if isinstance(lama, dict) and isinstance(lama.get("daftar"), list):\n    tujuan = data.setdefault("id_lagu", {}).setdefault(str(SERVER_ID_LAMA), [])\n    for entri in lama["daftar"]:\n      if entri not in tujuan:\n        tujuan.append(entri)\n    data.pop("id_fitur", None)\n    simpan_data()\n  if guild_id:\n    return data.setdefault("id_lagu", {}).setdefault(str(guild_id), [])\n  return data.setdefault("id_lagu_pribadi", {}).setdefault(str(user_id), [])\n\n\ndef pecah_id_lagu(entri):\n  teks = str(entri).strip()\n  cocok = re.match(r"(\\d+)", teks)\n  if cocok:\n    nomor = cocok.group(1)\n    nama = teks[len(nomor):].strip(" -:|")\n    return nomor, nama\n  if " - " in teks:\n    nomor, nama = teks.split(" - ", 1)\n    return nomor.strip(), nama.strip()\n  return teks, ""\n\n\nasync def isi_id_lagu(interaction: discord.Interaction, current: str):\n  daftar = gudang_id_lagu(interaction.guild_id, interaction.user.id)\n  kunci = current.lower()\n  return [\n      app_commands.Choice(name=str(e)[:100], value=str(e)[:100])\n      for e in daftar\n      if kunci in str(e).lower()\n  ][:25]\n\n\n@tree.command(name="tambahid", description="Tambah ID lagu ke daftar")\n@app_commands.describe(\n    id_lagu="ID lagu, boleh ditambah nama, contoh: 1234567890 - Judul Lagu"\n)\nasync def tambahid(interaction: discord.Interaction, id_lagu: str):\n  daftar = gudang_id_lagu(interaction.guild_id, interaction.user.id)\n  id_lagu = id_lagu.strip()[:150]\n  if not id_lagu:\n    await interaction.response.send_message("ID lagu kosong.", ephemeral=True)\n    return\n  if id_lagu in daftar:\n    await interaction.response.send_message(\n        f"`{id_lagu}` sudah ada di daftar.", ephemeral=True\n    )\n    return\n  if len(daftar) >= 200:\n    await interaction.response.send_message(\n        "Daftar sudah berisi 200 lagu. Hapus beberapa dulu dengan /hapusid.",\n        ephemeral=True,\n    )\n    return\n  daftar.append(id_lagu)\n  simpan_data()\n  tempat = "daftar server ini" if interaction.guild_id else "daftar pribadimu"\n  await interaction.response.send_message(\n      f"`{id_lagu}` ditambahkan ke {tempat}.", ephemeral=True\n  )\n\n\n@tree.command(name="hapusid", description="Hapus ID lagu dari daftar")\n@app_commands.describe(id_lagu="Pilih dari daftar atau ketik ID lagunya")\n@app_commands.autocomplete(id_lagu=isi_id_lagu)\nasync def hapusid(interaction: discord.Interaction, id_lagu: str):\n  daftar = gudang_id_lagu(interaction.guild_id, interaction.user.id)\n  target = id_lagu.strip()\n  cocok = next((e for e in daftar if str(e)[:100] == target), None)\n  if cocok is None:\n    cocok = next(\n        (e for e in daftar if pecah_id_lagu(e)[0] == target), None\n    )\n  if cocok is None:\n    await interaction.response.send_message(\n        f"`{target}` tidak ditemukan di daftar ini.", ephemeral=True\n    )\n    return\n  daftar.remove(cocok)\n  simpan_data()\n  await interaction.response.send_message(\n      f"`{cocok}` dihapus dari daftar.", ephemeral=True\n  )\n\n\n@tree.command(name="id", description="Lihat semua ID lagu yang tersimpan")\nasync def lihat_id_lagu(interaction: discord.Interaction):\n  daftar = gudang_id_lagu(interaction.guild_id, interaction.user.id)\n  if not daftar:\n    await interaction.response.send_message(\n        "Belum ada ID lagu yang tersimpan di sini.", ephemeral=True\n    )\n    return\n  judul = "ID lagu server ini" if interaction.guild_id else "ID lagu pribadimu"\n  baris = [f"{i}. {e}" for i, e in enumerate(daftar, start=1)]\n  await interaction.response.send_message(\n      (f"{judul}:\\n" + "\\n".join(baris))[:1900], ephemeral=True\n  )\n\n\nclass PilihIdSelect(discord.ui.Select):\n\n  def __init__(self, daftar):\n    self.daftar = daftar\n    opsi = []\n    for i, entri in enumerate(daftar[:25]):\n      nomor, nama = pecah_id_lagu(entri)\n      opsi.append(\n          discord.SelectOption(\n              label=(nama or nomor)[:100],\n              value=str(i),\n              description=nomor[:100],\n          )\n      )\n    super().__init__(placeholder="Pilih lagu", options=opsi)\n\n  async def callback(self, interaction: discord.Interaction):\n    nomor, nama = pecah_id_lagu(self.daftar[int(self.values[0])])\n    await interaction.response.send_message(\n        f"{nama or \'ID lagu\'}:\\n```\\n{nomor}\\n```", ephemeral=True\n    )\n\n\nclass PilihIdView(discord.ui.View):\n\n  def __init__(self, daftar):\n    super().__init__(timeout=300)\n    self.add_item(PilihIdSelect(daftar))\n\n\n@tree.command(\n    name="pilihid",\n    description="Pilih satu lagu untuk menyalin ID-nya saja",\n)\nasync def pilihid(interaction: discord.Interaction):\n  daftar = list(gudang_id_lagu(interaction.guild_id, interaction.user.id))\n  if not daftar:\n    await interaction.response.send_message(\n        "Belum ada ID lagu yang tersimpan di sini.", ephemeral=True\n    )\n    return\n  catatan = ""\n  if len(daftar) > 25:\n    catatan = f" Yang tampil 25 pertama dari {len(daftar)} lagu."\n  await interaction.response.send_message(\n      "Pilih lagu, nanti ID-nya dikirim sendirian supaya gampang disalin."\n      + catatan,\n      view=PilihIdView(daftar),\n      ephemeral=True,\n  )\n'

with open(BERKAS, encoding="utf-8") as f:
  teks = f.read()

if "def gudang_id_lagu" in teks:
  print("Patch ini sudah pernah dipasang, tidak ada yang diubah.")
  sys.exit(0)

masalah = []
tanda = "\natur_visibilitas_perintah()\n"
if teks.count(tanda) != 1:
  masalah.append("baris atur_visibilitas_perintah, jalankan sembunyikan_perintah.py dulu")
for nama in ("tambahid", "hapusid", "id", "pilihid"):
  if f'name="{nama}"' in teks:
    masalah.append(f"perintah /{nama} sudah ada di bot.py")

if masalah:
  print("Dibatalkan, tidak ada yang diubah. Titik yang tidak cocok:")
  for m in masalah:
    print("-", m)
  sys.exit(1)

teks = teks.replace(tanda, "\n" + BLOK_ID + "\n" + tanda)

try:
  compile(teks, BERKAS, "exec")
except SyntaxError as e:
  print(f"Dibatalkan, hasil patch tidak valid di baris {e.lineno}.")
  sys.exit(1)

with open(BERKAS, "w", encoding="utf-8") as f:
  f.write(teks)
print("Selesai. Daftar ID lagu sekarang terpisah per server dan pribadi di DM.")
