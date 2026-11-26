import asyncio

import discord
from discord import app_commands

from modul import inti
from modul.banner import buat_banner
from modul.inti import (
    PEMILIK_ID,
    POLA_LINK,
    SESI_CHAT_AKTIF,
    TUGAS_AI,
    client,
    data,
    kirim_log,
    path_banner,
    presensi_default,
    sedang_purge,
    simpan_data,
    tree,
)
from modul.kantor.jadwal import loop_penjadwal
from modul.kantor.laporan import loop_laporan
from modul.kantor.staf import loop_rutinitas
from modul.kantor.web import loop_perintah_web
from modul.obrolan import tangani_mention, tangani_sesi_chat
from modul.pengingat import loop_pengingat
from modul.sinkron import sinkron_perintah
from modul.tiket import TiketCloseView, TiketPanelView
from modul.warna import WarnaView


lagu_terakhir = None


class DynamicRoleView(discord.ui.View):

  def __init__(self, role_id: int, label: str = "Ambil/Lepas Role"):
    super().__init__(timeout=None)
    self.role_id = role_id
    tombol = discord.ui.Button(
        label=label,
        style=discord.ButtonStyle.primary,
        custom_id=f"rt_{role_id}",
    )
    tombol.callback = self.tombol_diklik
    self.add_item(tombol)

  async def tombol_diklik(self, interaction: discord.Interaction):
    role = interaction.guild.get_role(self.role_id)
    if not role:
      await interaction.response.send_message(
          "Role tidak ditemukan di server ini.", ephemeral=True
      )
      return
    try:
      if role in interaction.user.roles:
        await interaction.user.remove_roles(role)
        await interaction.response.send_message(
            f"Role **{role.name}** berhasil dicabut.", ephemeral=True
        )
      else:
        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            f"Role **{role.name}** berhasil diambil.", ephemeral=True
        )
    except discord.Forbidden:
      await interaction.response.send_message(
          "Gagal. Posisikan role Bot di atas role tersebut pada pengaturan"
          " server.",
          ephemeral=True,
      )


@client.event
async def on_message(message):
  if message.author.bot or message.guild is None:
    return
  if message.channel.id in SESI_CHAT_AKTIF and message.content.strip():
    tugas = asyncio.create_task(tangani_sesi_chat(message))
    TUGAS_AI.add(tugas)
    tugas.add_done_callback(TUGAS_AI.discard)
    return
  if client.user in message.mentions:
    tugas = asyncio.create_task(tangani_mention(message))
    TUGAS_AI.add(tugas)
    tugas.add_done_callback(TUGAS_AI.discard)
  info_sticky = data["sticky"].get(str(message.channel.id))
  if info_sticky:
    try:
      if info_sticky.get("terakhir"):
        try:
          lama = await message.channel.fetch_message(
              int(info_sticky["terakhir"])
          )
          await lama.delete()
        except Exception:
          pass
      embed_sticky = discord.Embed(
          description=info_sticky["pesan"], color=discord.Color.blurple()
      )
      baru = await message.channel.send(embed=embed_sticky)
      info_sticky["terakhir"] = baru.id
      simpan_data()
    except Exception:
      pass
  menit = data["antispam"].get(str(message.guild.id), 0)
  if not menit:
    return
  if message.author.guild_permissions.manage_messages:
    return
  if not message.author.joined_at:
    return
  umur = (
      discord.utils.utcnow() - message.author.joined_at
  ).total_seconds() / 60
  if umur >= menit:
    return
  if not POLA_LINK.search(message.content):
    return
  try:
    await message.delete()
  except Exception:
    return
  embed = discord.Embed(
      title="Link member baru dihapus",
      color=discord.Color.dark_orange(),
      timestamp=discord.utils.utcnow(),
  )
  embed.add_field(
      name="User",
      value=f"{message.author.mention} ({message.author.name})",
      inline=False,
  )
  embed.add_field(name="Channel", value=message.channel.mention)
  embed.add_field(
      name="Isi", value=message.content[:900] or "-", inline=False
  )
  await kirim_log(message.guild, embed)
  try:
    peringatan = await message.channel.send(
        f"{message.author.mention} member baru belum boleh mengirim link."
    )
    await asyncio.sleep(6)
    await peringatan.delete()
  except Exception:
    pass


@client.event
async def on_message_delete(message):
  if message.author.bot or message.guild is None:
    return
  if message.channel.id in sedang_purge:
    return
  embed = discord.Embed(
      title="Pesan dihapus",
      color=discord.Color.red(),
      timestamp=discord.utils.utcnow(),
  )
  embed.add_field(
      name="User",
      value=f"{message.author.mention} ({message.author.name})",
      inline=False,
  )
  embed.add_field(name="Channel", value=message.channel.mention)
  embed.add_field(
      name="Isi", value=(message.content or "tidak ada teks")[:900], inline=False
  )
  await kirim_log(message.guild, embed)


@client.event
async def on_message_edit(before, after):
  if (
      before.author.bot
      or before.guild is None
      or before.content == after.content
  ):
    return
  embed = discord.Embed(
      title="Pesan diedit",
      color=discord.Color.gold(),
      timestamp=discord.utils.utcnow(),
  )
  embed.add_field(
      name="User",
      value=f"{before.author.mention} ({before.author.name})",
      inline=False,
  )
  embed.add_field(name="Channel", value=before.channel.mention)
  embed.add_field(
      name="Sebelum", value=(before.content or "-")[:900], inline=False
  )
  embed.add_field(
      name="Sesudah", value=(after.content or "-")[:900], inline=False
  )
  await kirim_log(before.guild, embed)


@client.event
async def on_member_join(member):
  embed = discord.Embed(
      title="Member masuk server",
      color=discord.Color.green(),
      timestamp=discord.utils.utcnow(),
  )
  embed.add_field(name="User", value=f"{member.mention} ({member.name})")
  embed.add_field(name="User ID", value=str(member.id))
  embed.add_field(
      name="Akun dibuat",
      value=discord.utils.format_dt(member.created_at, "R"),
      inline=False,
  )
  await kirim_log(member.guild, embed)

  role_id = data["autorole"].get(str(member.guild.id))
  if role_id:
    role = member.guild.get_role(int(role_id))
    if role:
      try:
        await member.add_roles(role)
      except Exception:
        pass

  sambutan = data["welcome"].get(str(member.guild.id))
  if sambutan:
    channel = member.guild.get_channel(int(sambutan["channel"]))
    if channel:
      teks = sambutan["pesan"]
      teks = teks.replace("{user}", member.mention)
      teks = teks.replace("{server}", member.guild.name)
      teks = teks.replace("{jumlah}", str(member.guild.member_count))
      berkas = None
      try:
        avatar = await member.display_avatar.replace(
            size=256, format="png"
        ).read()
        data_gambar = await asyncio.to_thread(
            buat_banner,
            member.display_name,
            member.guild.member_count,
            avatar,
            path_banner(member.guild.id),
        )
        berkas = discord.File(data_gambar, filename="welcome.png")
      except Exception:
        berkas = None
      try:
        if berkas:
          await channel.send(content=teks[:2000], file=berkas)
        else:
          await channel.send(teks[:2000])
      except Exception:
        pass


@client.event
async def on_member_remove(member):
  embed = discord.Embed(
      title="Member keluar atau dikick",
      color=discord.Color.red(),
      timestamp=discord.utils.utcnow(),
  )
  embed.add_field(name="User", value=f"{member.name}")
  embed.add_field(name="User ID", value=str(member.id))
  await kirim_log(member.guild, embed)


@client.event
async def on_member_update(before, after):
  if before.roles == after.roles:
    return
  embed = discord.Embed(
      title="Perubahan role member",
      color=discord.Color.orange(),
      timestamp=discord.utils.utcnow(),
  )
  embed.add_field(name="Target member", value=after.mention)
  ditambah = [r.mention for r in after.roles if r not in before.roles]
  dihapus = [r.mention for r in before.roles if r not in after.roles]
  if ditambah:
    embed.add_field(
        name="Role diberikan", value=", ".join(ditambah), inline=False
    )
  if dihapus:
    embed.add_field(name="Role dicabut", value=", ".join(dihapus), inline=False)
  await kirim_log(after.guild, embed)


@client.event
async def on_presence_update(before, after):
  global lagu_terakhir
  if after.id != PEMILIK_ID:
    return
  spotify_act = None
  for activity in after.activities:
    if isinstance(activity, discord.Spotify):
      spotify_act = activity
      break
  if spotify_act:
    if spotify_act.track_id == lagu_terakhir:
      return
    lagu_terakhir = spotify_act.track_id
    detik = int(spotify_act.duration.total_seconds())
    info_lagu = (
        f"{spotify_act.title} - {spotify_act.artist} | {spotify_act.album} |"
        f" {detik // 60}:{detik % 60:02d}"
    )
    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening, name=info_lagu[:128]
        )
    )
  else:
    if lagu_terakhir is None:
      return
    lagu_terakhir = None
    await client.change_presence(activity=presensi_default())


@client.event
async def on_ready():
  if inti.WAKTU_MULAI is None:
    inti.WAKTU_MULAI = discord.utils.utcnow()
  await sinkron_perintah()
  if not getattr(client, "_tugas_latar", False):
    client._tugas_latar = True
    asyncio.create_task(loop_penjadwal())
    asyncio.create_task(loop_rutinitas())
    asyncio.create_task(loop_laporan())
    asyncio.create_task(loop_perintah_web())
    asyncio.create_task(loop_pengingat())
  for br in data.get("button_roles", []):
    client.add_view(
        DynamicRoleView(br["role_id"], br["label"]), message_id=br["message_id"]
    )
  client.add_view(TiketPanelView())
  client.add_view(TiketCloseView())
  for cp in data.get("color_panels", []):
    try:
      client.add_view(
          WarnaView([(r["id"], r["label"], r.get("emoji")) for r in cp["roles"]]),
          message_id=cp["message_id"],
      )
    except Exception:
      pass
  tersisa = []
  for cid in list(data.get("voice_sementara", [])):
    ch = client.get_channel(int(cid))
    if ch is None:
      continue
    if len(ch.members) == 0:
      try:
        await ch.delete(reason="bersih voice sementara")
      except Exception:
        pass
      continue
    tersisa.append(cid)
  data["voice_sementara"] = tersisa
  simpan_data()
  await client.change_presence(activity=presensi_default())
  print(f"Bot online sebagai {client.user}")


@tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
  if isinstance(error, app_commands.errors.MissingPermissions):
    pesan = "Kamu tidak punya izin untuk memakai perintah ini."
  else:
    pesan = f"Error: {error}"
  if interaction.response.is_done():
    await interaction.followup.send(pesan[:1900], ephemeral=True)
  else:
    await interaction.response.send_message(pesan[:1900], ephemeral=True)


async def kabari_pemilik(judul, guild, warna):
  try:
    pemilik = await client.fetch_user(PEMILIK_ID)
  except Exception:
    return
  embed = discord.Embed(
      title=judul, color=warna, timestamp=discord.utils.utcnow()
  )
  embed.add_field(name="Server", value=f"{guild.name} ({guild.id})", inline=False)
  embed.add_field(name="Member", value=str(guild.member_count or 0))
  embed.add_field(name="Total server sekarang", value=str(len(client.guilds)))
  try:
    await pemilik.send(embed=embed)
  except Exception:
    pass


@client.event
async def on_guild_join(guild):
  await kabari_pemilik("Bot masuk server baru", guild, discord.Color.green())


@client.event
async def on_guild_remove(guild):
  await kabari_pemilik(
      "Bot dikeluarkan dari server", guild, discord.Color.red()
  )
