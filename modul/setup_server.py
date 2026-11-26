import discord
from discord import app_commands

from modul.inti import cek_premium, data, simpan_data, tree


GAYA_NAMA = {
    "polos": {"kategori": "{n}", "teks": "{n}", "suara": "{n}"},
    "bintang": {
        "kategori": (
            "✦━━━ ⋆⸜°ɞ {n} ɞ°⸝⋆ ━━━✦"
        ),
        "teks": "⋆⸜°ɞ-{n}-ɞ°⸝⋆",
        "suara": "⋆⸜°ɞ {n} ɞ°⸝⋆",
    },
    "lembut": {
        "kategori": "ʚɞ ⋆ {n} ⋆ ʚɞ",
        "teks": "˚₊·-{n}-·₊˚",
        "suara": "˚₊· {n} ·₊˚",
    },
    "tegas": {
        "kategori": "████ {n} ████",
        "teks": "⍗-{n}",
        "suara": "⍗ {n}",
    },
}


def rias_nama(nama, jenis, gaya):
  pola = GAYA_NAMA.get(gaya, GAYA_NAMA["polos"])[jenis]
  return pola.format(n=nama)[:95]


PILIHAN_GAYA = [
    app_commands.Choice(name="Polos tanpa hiasan", value="polos"),
    app_commands.Choice(name="Bintang", value="bintang"),
    app_commands.Choice(name="Lembut", value="lembut"),
    app_commands.Choice(name="Tegas", value="tegas"),
]

PRESET_SETUP = {
    "jualan": {
        "teks": {
            "INFORMATION": [
                "portal",
                "announcement",
                "rules",
                "link-invite",
                "giveaway",
            ],
            "STOCK INFORMATION": [
                "flash-sale",
                "item-limited",
                "value-changes",
            ],
            "ROBUX": ["robux-vilog", "robux-community"],
            "TRANSACTION": ["order", "cashout", "payment"],
            "REPUTATION": ["rating-server", "leaderboard", "order-log"],
            "TESTIMONI": ["testimoni-robux", "testimoni-limited", "testimoni-gift"],
            "PUBLIC": ["chat", "bot-command", "market-public"],
        },
        "suara": {},
        "role": [
            ("Admin", discord.Color.red(), True),
            ("Moderator", discord.Color.orange(), True),
            ("Member", discord.Color.blue(), False),
            ("Pembeli", discord.Color.green(), False),
        ],
    },
    "komunitas": {
        "teks": {
            "INFORMASI": ["rules", "announcement", "information", "update-server"],
            "ROLES": ["display-roles", "warna-nama", "seting-voice"],
            "KOMUNITAS": ["general", "media-share", "bot-command", "suggestions"],
            "ROBLOX": [
                "game-update",
                "screenshot",
                "clip-highlight",
                "cari-teman-main",
                "showcase-karya",
            ],
            "EVENT": ["event-info", "giveaway"],
            "SUPPORT": ["help", "bug-report"],
        },
        "suara": {
            "VOICE AREA": [
                "Join to Create",
                "General 1",
                "General 2",
                "Main Bareng",
                "AFK",
            ],
            "MUSIC AREA": ["Music 1", "Music 2"],
        },
        "role": [
            ("Admin", discord.Color.red(), True),
            ("Moderator", discord.Color.orange(), True),
            ("Member", discord.Color.blue(), False),
            ("Roblox Developer", discord.Color.purple(), False),
            ("Content Creator", discord.Color.teal(), False),
            ("Event Winner", discord.Color.gold(), False),
        ],
    },
}


@tree.command(
    name="setup", description="Buat struktur channel dan role sesuai tipe server"
)
@app_commands.choices(tipe=[
    app_commands.Choice(name="Server jualan", value="jualan"),
    app_commands.Choice(name="Komunitas Roblox", value="komunitas"),
])
@app_commands.choices(gaya=PILIHAN_GAYA)
@app_commands.checks.has_permissions(administrator=True)
async def setup(
    interaction: discord.Interaction,
    tipe: app_commands.Choice[str],
    gaya: app_commands.Choice[str] = None,
):
  aktif, _ = cek_premium(interaction.guild_id)
  if not aktif:
    await interaction.response.send_message(
        "Fitur /setup khusus server premium. Hubungi owner bot untuk upgrade.",
        ephemeral=True,
    )
    return
  if (
      not interaction.guild.me.guild_permissions.manage_channels
      or not interaction.guild.me.guild_permissions.manage_roles
  ):
    await interaction.response.send_message(
        "Bot butuh izin Manage Channels dan Manage Roles. Aktifkan dulu di"
        " pengaturan server.",
        ephemeral=True,
    )
    return
  await interaction.response.defer(ephemeral=True)
  preset = PRESET_SETUP[tipe.value]
  kode_gaya = gaya.value if gaya else "polos"
  guild = interaction.guild
  dibuat = []
  for nama, warna, terpisah in preset["role"]:
    ada = discord.utils.get(guild.roles, name=nama)
    if ada is None:
      try:
        await guild.create_role(
            name=nama, color=warna, hoist=terpisah, reason="setup bot"
        )
        dibuat.append(f"role {nama}")
      except Exception:
        pass
  for nama_kat, daftar_channel in preset["teks"].items():
    tampil_kat = rias_nama(nama_kat, "kategori", kode_gaya)
    kategori = discord.utils.get(guild.categories, name=tampil_kat) or discord.utils.get(
        guild.categories, name=nama_kat
    )
    if kategori is None:
      try:
        kategori = await guild.create_category(tampil_kat, reason="setup bot")
        data["gaya_nama"][str(kategori.id)] = nama_kat
        dibuat.append(f"kategori {nama_kat}")
      except Exception:
        continue
    for nama_ch in daftar_channel:
      tampil_ch = rias_nama(nama_ch, "teks", kode_gaya)
      sudah_ada = discord.utils.get(kategori.channels, name=nama_ch) or discord.utils.get(
          kategori.channels, name=tampil_ch.lower().replace(" ", "-")
      )
      if sudah_ada is None:
        try:
          ch_baru = await guild.create_text_channel(
              tampil_ch, category=kategori, reason="setup bot"
          )
          data["gaya_nama"][str(ch_baru.id)] = nama_ch
          dibuat.append(f"channel {nama_ch}")
        except Exception:
          pass
  for nama_kat, daftar_suara in preset["suara"].items():
    tampil_kat = rias_nama(nama_kat, "kategori", kode_gaya)
    kategori = discord.utils.get(guild.categories, name=tampil_kat) or discord.utils.get(
        guild.categories, name=nama_kat
    )
    if kategori is None:
      try:
        kategori = await guild.create_category(tampil_kat, reason="setup bot")
        data["gaya_nama"][str(kategori.id)] = nama_kat
        dibuat.append(f"kategori {nama_kat}")
      except Exception:
        continue
    for nama_vc in daftar_suara:
      tampil_vc = rias_nama(nama_vc, "suara", kode_gaya)
      sudah_ada = discord.utils.get(
          kategori.voice_channels, name=nama_vc
      ) or discord.utils.get(kategori.voice_channels, name=tampil_vc)
      if sudah_ada is None:
        try:
          vc_baru = await guild.create_voice_channel(
              tampil_vc, category=kategori, reason="setup bot"
          )
          data["gaya_nama"][str(vc_baru.id)] = nama_vc
          dibuat.append(f"voice {nama_vc}")
          if nama_vc == "Join to Create":
            data["joinvoice"][str(guild.id)] = {"hub": vc_baru.id}
        except Exception:
          pass
  simpan_data()
  if dibuat:
    ringkas = "\n".join(dibuat[:40])
    await interaction.followup.send(
        f"Setup {tipe.name} selesai. Yang dibuat:\n{ringkas}", ephemeral=True
    )
  else:
    await interaction.followup.send(
        "Semua struktur sudah ada, tidak ada yang perlu dibuat.", ephemeral=True
    )


@tree.command(
    name="hapussetup", description="Hapus channel dan role yang dibuat oleh setup"
)
@app_commands.choices(tipe=[
    app_commands.Choice(name="Server jualan", value="jualan"),
    app_commands.Choice(name="Komunitas Roblox", value="komunitas"),
])
@app_commands.checks.has_permissions(administrator=True)
async def hapussetup(
    interaction: discord.Interaction, tipe: app_commands.Choice[str]
):
  aktif, _ = cek_premium(interaction.guild_id)
  if not aktif:
    await interaction.response.send_message(
        "Fitur /hapussetup khusus server premium. Hubungi owner bot untuk"
        " upgrade.",
        ephemeral=True,
    )
    return
  await interaction.response.defer(ephemeral=True)
  preset = PRESET_SETUP[tipe.value]
  guild = interaction.guild
  dihapus = 0
  nama_channel = {c for daftar in preset["teks"].values() for c in daftar}
  nama_suara = {v for daftar in preset["suara"].values() for v in daftar}
  nama_kategori = set(preset["teks"].keys()) | set(preset["suara"].keys())
  nama_role = {r[0] for r in preset["role"]}
  id_polos = {int(cid): nm for cid, nm in data.get("gaya_nama", {}).items()}
  for channel in list(guild.channels):
    if isinstance(channel, discord.CategoryChannel):
      continue
    polos = id_polos.get(channel.id, channel.name)
    if polos in nama_channel or polos in nama_suara:
      try:
        await channel.delete(reason="hapus setup")
        data["gaya_nama"].pop(str(channel.id), None)
        dihapus += 1
      except Exception:
        pass
  for kategori in list(guild.categories):
    polos = id_polos.get(kategori.id, kategori.name)
    if polos in nama_kategori:
      try:
        await kategori.delete(reason="hapus setup")
        data["gaya_nama"].pop(str(kategori.id), None)
        dihapus += 1
      except Exception:
        pass
  for role in list(guild.roles):
    if role.name in nama_role and role < guild.me.top_role:
      try:
        await role.delete(reason="hapus setup")
        dihapus += 1
      except Exception:
        pass
  await interaction.followup.send(
      f"{dihapus} channel, kategori, dan role hasil setup dihapus.",
      ephemeral=True,
  )


@tree.command(
    name="gayanama",
    description="Ubah gaya nama channel dan kategori yang dibuat setup",
)
@app_commands.choices(tipe=[
    app_commands.Choice(name="Server jualan", value="jualan"),
    app_commands.Choice(name="Komunitas Roblox", value="komunitas"),
])
@app_commands.choices(gaya=PILIHAN_GAYA)
@app_commands.checks.has_permissions(administrator=True)
async def gayanama(
    interaction: discord.Interaction,
    tipe: app_commands.Choice[str],
    gaya: app_commands.Choice[str],
):
  aktif, _ = cek_premium(interaction.guild_id)
  if not aktif:
    await interaction.response.send_message(
        "Fitur /gayanama khusus server premium. Hubungi owner bot untuk"
        " upgrade.",
        ephemeral=True,
    )
    return
  if not interaction.guild.me.guild_permissions.manage_channels:
    await interaction.response.send_message(
        "Bot butuh izin Manage Channels.", ephemeral=True
    )
    return
  await interaction.response.defer(ephemeral=True)
  preset = PRESET_SETUP[tipe.value]
  guild = interaction.guild
  nama_teks = {c for daftar in preset["teks"].values() for c in daftar}
  nama_suara = {v for daftar in preset["suara"].values() for v in daftar}
  nama_kategori = set(preset["teks"].keys()) | set(preset["suara"].keys())
  id_polos = {int(cid): nm for cid, nm in data.get("gaya_nama", {}).items()}
  diubah = 0
  for kategori in list(guild.categories):
    polos = id_polos.get(kategori.id)
    if polos is None and kategori.name in nama_kategori:
      polos = kategori.name
    if polos is None:
      continue
    baru = rias_nama(polos, "kategori", gaya.value)
    if baru == kategori.name:
      continue
    try:
      await kategori.edit(name=baru, reason="ubah gaya nama")
      data["gaya_nama"][str(kategori.id)] = polos
      diubah += 1
    except Exception:
      pass
  for channel in list(guild.channels):
    if isinstance(channel, discord.CategoryChannel):
      continue
    polos = id_polos.get(channel.id)
    if polos is None:
      if channel.name in nama_teks:
        polos = channel.name
      elif channel.name in nama_suara:
        polos = channel.name
    if polos is None:
      continue
    jenis = "suara" if isinstance(channel, discord.VoiceChannel) else "teks"
    baru = rias_nama(polos, jenis, gaya.value)
    try:
      await channel.edit(name=baru, reason="ubah gaya nama")
      data["gaya_nama"][str(channel.id)] = polos
      diubah += 1
    except Exception:
      pass
  simpan_data()
  if diubah:
    await interaction.followup.send(
        f"{diubah} channel dan kategori diubah ke gaya {gaya.name}.",
        ephemeral=True,
    )
  else:
    await interaction.followup.send(
        "Tidak ada yang diubah. Pastikan channelnya memang dibuat lewat setup"
        " dan tipe presetnya benar.",
        ephemeral=True,
    )
