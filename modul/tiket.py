import asyncio
import io

import discord
from discord import app_commands

from modul.inti import bersihkan_error, cek_premium, data, tree


TIKET_TIPE = [
    ("order", "Order"),
    ("report", "Report"),
]


async def buka_tiket(interaction, kode, label):
  guild = interaction.guild
  if not guild.me.guild_permissions.manage_channels:
    await interaction.response.send_message(
        "Bot butuh izin Manage Channels untuk membuat tiket.", ephemeral=True
    )
    return
  kategori = discord.utils.get(guild.categories, name="TIKET")
  if kategori is None:
    try:
      kategori = await guild.create_category("TIKET", reason="kategori tiket")
    except Exception:
      await interaction.response.send_message(
          "Gagal membuat kategori TIKET.", ephemeral=True
      )
      return
  for ch in kategori.text_channels:
    if (
        ch.topic
        and f"pemilik:{interaction.user.id}" in ch.topic
        and f"tipe:{kode}" in ch.topic
    ):
      await interaction.response.send_message(
          f"Kamu sudah punya tiket {label} yang terbuka: {ch.mention}",
          ephemeral=True,
      )
      return
  role_admin = discord.utils.get(guild.roles, name="Admin")
  role_mod = discord.utils.get(guild.roles, name="Moderator")
  izin = {
      guild.default_role: discord.PermissionOverwrite(view_channel=False),
      interaction.user: discord.PermissionOverwrite(
          view_channel=True,
          send_messages=True,
          attach_files=True,
          read_message_history=True,
      ),
      guild.me: discord.PermissionOverwrite(
          view_channel=True, send_messages=True, manage_channels=True
      ),
  }
  if role_admin:
    izin[role_admin] = discord.PermissionOverwrite(
        view_channel=True, send_messages=True, read_message_history=True
    )
  if kode == "report" and role_mod:
    izin[role_mod] = discord.PermissionOverwrite(
        view_channel=True, send_messages=True, read_message_history=True
    )
  nama = f"{kode}-{interaction.user.name}"[:90]
  try:
    channel = await guild.create_text_channel(
        nama,
        category=kategori,
        overwrites=izin,
        topic=f"pemilik:{interaction.user.id}|tipe:{kode}",
        reason="tiket baru",
    )
  except Exception as e:
    await interaction.response.send_message(
        f"Gagal membuat tiket: {bersihkan_error(e)}", ephemeral=True
    )
    return
  if kode == "report":
    deskripsi = (
        f"Halo {interaction.user.mention}, jelaskan laporanmu di sini. Sertakan"
        " nama pengguna yang dilaporkan dan bukti seperti screenshot atau video"
        " kalau ada. Tim akan segera menindaklanjuti."
    )
  else:
    deskripsi = (
        f"Halo {interaction.user.mention}, silakan jelaskan pesanan atau"
        " pertanyaanmu di sini. Admin akan segera membantu."
    )
  embed = discord.Embed(
      title=f"Tiket {label}",
      description=deskripsi,
      color=discord.Color.green(),
      timestamp=discord.utils.utcnow(),
  )
  penyebut = []
  if role_admin:
    penyebut.append(role_admin.mention)
  if kode == "report" and role_mod:
    penyebut.append(role_mod.mention)
  await channel.send(
      content=f"{interaction.user.mention} {' '.join(penyebut)}",
      embed=embed,
      view=TiketCloseView(),
  )
  await interaction.response.send_message(
      f"Tiket berhasil dibuat: {channel.mention}", ephemeral=True
  )


class TiketTombol(discord.ui.Button):

  def __init__(self, kode, label):
    gaya = (
        discord.ButtonStyle.danger
        if kode == "report"
        else discord.ButtonStyle.primary
    )
    super().__init__(
        label=label, style=gaya, custom_id=f"tiket_buka:{kode}"
    )
    self.kode = kode
    self.label_tiket = label

  async def callback(self, interaction: discord.Interaction):
    await buka_tiket(interaction, self.kode, self.label_tiket)


class TiketPanelView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)
    for kode, label in TIKET_TIPE:
      self.add_item(TiketTombol(kode, label))


class TiketCloseView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label="Tutup Tiket",
      style=discord.ButtonStyle.danger,
      custom_id="tiket_tutup",
  )
  async def tutup(
      self, interaction: discord.Interaction, tombol: discord.ui.Button
  ):
    channel = interaction.channel
    pemilik_ok = False
    if channel.topic:
      pemilik_ok = f"pemilik:{interaction.user.id}" in channel.topic
    if not (
        interaction.user.guild_permissions.manage_channels or pemilik_ok
    ):
      await interaction.response.send_message(
          "Hanya admin atau pembuat tiket yang bisa menutup tiket ini.",
          ephemeral=True,
      )
      return
    await interaction.response.send_message(
        "Menyimpan transcript, tiket ditutup dalam 5 detik."
    )
    try:
      baris = []
      async for pesan in channel.history(limit=500, oldest_first=True):
        waktu = pesan.created_at.strftime("%Y-%m-%d %H:%M")
        isi_pesan = pesan.content or ""
        if pesan.embeds:
          isi_pesan += " [embed]"
        if pesan.attachments:
          isi_pesan += " " + " ".join(a.url for a in pesan.attachments)
        baris.append(f"[{waktu}] {pesan.author}: {isi_pesan}")
      teks_transcript = "\n".join(baris) if baris else "Tiket kosong."
      berkas = discord.File(
          io.BytesIO(teks_transcript.encode("utf-8")),
          filename=f"transcript-{channel.name}.txt",
      )
      embed_log = discord.Embed(
          title="Transcript tiket",
          color=discord.Color.dark_grey(),
          timestamp=discord.utils.utcnow(),
      )
      embed_log.add_field(name="Channel", value=channel.name, inline=False)
      embed_log.add_field(name="Ditutup oleh", value=interaction.user.mention)
      id_log = data["log_channels"].get(str(channel.guild.id))
      if id_log:
        ch_log = channel.guild.get_channel(int(id_log))
        if ch_log:
          await ch_log.send(embed=embed_log, file=berkas)
    except Exception:
      pass
    await asyncio.sleep(5)
    try:
      await channel.delete(reason="tiket ditutup")
    except Exception:
      pass


@tree.command(
    name="tiketpanel", description="Kirim panel tombol tiket order dan report"
)
@app_commands.checks.has_permissions(administrator=True)
async def tiketpanel(interaction: discord.Interaction):
  aktif, _ = cek_premium(interaction.guild_id)
  if not aktif:
    await interaction.response.send_message(
        "Fitur /tiketpanel khusus server premium. Hubungi owner bot untuk"
        " upgrade.",
        ephemeral=True,
    )
    return
  embed = discord.Embed(
      title="Order dan Report",
      description=(
          "Klik tombol sesuai kebutuhanmu untuk membuka tiket privat."
      ),
      color=discord.Color.blurple(),
  )
  embed.add_field(
      name="Order",
      value="Order jasa, item, atau tanya-tanya. Dilihat kamu dan Admin.",
      inline=False,
  )
  embed.add_field(
      name="Report",
      value=(
          "Laporkan pelanggaran, bug, atau masalah member. Dilihat kamu,"
          " Admin, dan Moderator."
      ),
      inline=False,
  )
  await interaction.response.send_message(embed=embed, view=TiketPanelView())
