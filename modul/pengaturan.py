import discord
from discord import app_commands

from modul.inti import (
    bersihkan_error,
    data,
    kirim_log,
    sedang_purge,
    simpan_data,
    tree,
)


@tree.command(
    name="stickyset",
    description="Pasang pesan sticky yang selalu muncul di bawah channel ini",
)
@app_commands.checks.has_permissions(administrator=True)
async def stickyset(interaction: discord.Interaction, pesan: str):
  data["sticky"][str(interaction.channel_id)] = {
      "pesan": pesan,
      "terakhir": None,
  }
  simpan_data()
  await interaction.response.send_message(
      "Sticky message dipasang di channel ini.", ephemeral=True
  )


@tree.command(
    name="stickyhapus", description="Matikan pesan sticky di channel ini"
)
@app_commands.checks.has_permissions(administrator=True)
async def stickyhapus(interaction: discord.Interaction):
  info = data["sticky"].pop(str(interaction.channel_id), None)
  simpan_data()
  if info and info.get("terakhir"):
    try:
      lama = await interaction.channel.fetch_message(int(info["terakhir"]))
      await lama.delete()
    except Exception:
      pass
  await interaction.response.send_message(
      "Sticky message dimatikan.", ephemeral=True
  )


@tree.command(
    name="setlog",
    description="Mendaftarkan channel ini sebagai pusat Security Log",
)
@app_commands.checks.has_permissions(administrator=True)
async def setlog(interaction: discord.Interaction):
  data["log_channels"][str(interaction.guild_id)] = interaction.channel_id
  simpan_data()
  await interaction.response.send_message(
      f"Channel {interaction.channel.mention} didaftarkan sebagai Security Log.",
      ephemeral=True,
  )


@tree.command(name="setwelcome", description="Atur pesan sambutan di channel ini")
@app_commands.describe(pesan="Boleh pakai {user}, {server}, dan {jumlah}")
@app_commands.checks.has_permissions(administrator=True)
async def setwelcome(interaction: discord.Interaction, pesan: str):
  data["welcome"][str(interaction.guild_id)] = {
      "channel": interaction.channel_id,
      "pesan": pesan,
  }
  simpan_data()
  await interaction.response.send_message(
      f"Pesan sambutan diatur di {interaction.channel.mention}.", ephemeral=True
  )


@tree.command(
    name="setautorole", description="Role yang otomatis diberikan ke member baru"
)
@app_commands.checks.has_permissions(administrator=True)
async def setautorole(interaction: discord.Interaction, role: discord.Role):
  if role >= interaction.guild.me.top_role:
    await interaction.response.send_message(
        "Posisi role Bot harus di atas role tersebut.", ephemeral=True
    )
    return
  data["autorole"][str(interaction.guild_id)] = role.id
  simpan_data()
  await interaction.response.send_message(
      f"Member baru otomatis dapat role {role.mention}.", ephemeral=True
  )


@tree.command(
    name="setantispam", description="Blokir link dari member yang baru masuk"
)
@app_commands.describe(
    menit=(
        "Lama proteksi dalam menit sejak member masuk, isi 0 untuk mematikan"
    )
)
@app_commands.checks.has_permissions(administrator=True)
async def setantispam(
    interaction: discord.Interaction, menit: app_commands.Range[int, 0, 10080]
):
  if menit == 0:
    data["antispam"].pop(str(interaction.guild_id), None)
    simpan_data()
    await interaction.response.send_message(
        "Anti spam link dimatikan.", ephemeral=True
    )
    return
  data["antispam"][str(interaction.guild_id)] = menit
  simpan_data()
  await interaction.response.send_message(
      f"Member yang umurnya di bawah {menit} menit tidak bisa mengirim link.",
      ephemeral=True,
  )


@tree.command(name="pengaturan", description="Lihat pengaturan bot di server ini")
async def pengaturan(interaction: discord.Interaction):
  gid = str(interaction.guild_id)
  embed = discord.Embed(
      title="Pengaturan server", color=discord.Color.blurple()
  )

  log_id = data["log_channels"].get(gid)
  embed.add_field(
      name="Security log",
      value=f"<#{log_id}>" if log_id else "mati",
      inline=False,
  )

  sambutan = data["welcome"].get(gid)
  embed.add_field(
      name="Welcome",
      value=f"<#{sambutan['channel']}>" if sambutan else "mati",
      inline=False,
  )

  role_id = data["autorole"].get(gid)
  embed.add_field(
      name="Auto role",
      value=f"<@&{role_id}>" if role_id else "mati",
      inline=False,
  )

  menit = data["antispam"].get(gid)
  embed.add_field(
      name="Anti spam link",
      value=f"{menit} menit pertama" if menit else "mati",
      inline=False,
  )

  hub = data["joinvoice"].get(gid)
  embed.add_field(
      name="Join to Create",
      value=f"<#{hub['hub']}>" if hub else "mati",
      inline=False,
  )

  jumlah = len(data["custom_commands"].get(gid, {}))
  embed.add_field(
      name="Custom command", value=f"{jumlah} perintah", inline=False
  )

  await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="reset", description="Matikan salah satu fitur di server ini")
@app_commands.choices(fitur=[
    app_commands.Choice(name="Security log", value="log_channels"),
    app_commands.Choice(name="Welcome", value="welcome"),
    app_commands.Choice(name="Auto role", value="autorole"),
    app_commands.Choice(name="Anti spam link", value="antispam"),
    app_commands.Choice(name="Join to Create", value="joinvoice"),
])
@app_commands.checks.has_permissions(administrator=True)
async def reset(
    interaction: discord.Interaction, fitur: app_commands.Choice[str]
):
  data[fitur.value].pop(str(interaction.guild_id), None)
  simpan_data()
  await interaction.response.send_message(
      f"Fitur {fitur.name} dimatikan.", ephemeral=True
  )


@tree.command(
    name="purge", description="Hapus sejumlah pesan terakhir di channel ini"
)
@app_commands.describe(jumlah="Jumlah pesan, maksimal 100")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(
    interaction: discord.Interaction, jumlah: app_commands.Range[int, 1, 100]
):
  await interaction.response.defer(ephemeral=True)
  sedang_purge.add(interaction.channel_id)
  try:
    dihapus = await interaction.channel.purge(limit=jumlah)
  except discord.Forbidden:
    sedang_purge.discard(interaction.channel_id)
    await interaction.followup.send(
        "Bot tidak punya izin Manage Messages di channel ini.", ephemeral=True
    )
    return
  except Exception as e:
    sedang_purge.discard(interaction.channel_id)
    await interaction.followup.send(
        f"Gagal: {bersihkan_error(e)}", ephemeral=True
    )
    return
  sedang_purge.discard(interaction.channel_id)
  await interaction.followup.send(f"{len(dihapus)} pesan dihapus.", ephemeral=True)
  embed = discord.Embed(
      title="Purge pesan",
      color=discord.Color.dark_red(),
      timestamp=discord.utils.utcnow(),
  )
  embed.add_field(name="Oleh", value=interaction.user.mention)
  embed.add_field(name="Channel", value=interaction.channel.mention)
  embed.add_field(name="Jumlah", value=str(len(dihapus)))
  await kirim_log(interaction.guild, embed)
