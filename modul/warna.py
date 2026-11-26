import discord
from discord import app_commands

from modul.inti import bersihkan_error, data, simpan_data, tree


WARNA_ROLE = [
    ("Yellow", 0xF1C40F, "💛"),
    ("Green", 0x2ECC71, "💚"),
    ("Orange", 0xE67E22, "🧡"),
    ("Grey", 0x95A5A6, "🥶"),
    ("White", 0xFFFFFE, "🤍"),
    ("Pink", 0xFF69B4, "🥷"),
    ("Red", 0xE74C3C, "❤️"),
    ("Purple", 0x9B59B6, "💜"),
    ("Navy", 0x34495E, "💙"),
    ("Blue", 0x3498DB, "🥵"),
    ("Light Pink", 0xFFC0CB, "🩷"),
]


class WarnaTombol(discord.ui.Button):

  def __init__(self, role_id, label, emoji=None):
    super().__init__(
        label=label,
        style=discord.ButtonStyle.secondary,
        custom_id=f"warna_{role_id}",
        emoji=emoji,
    )
    self.role_id = role_id

  async def callback(self, interaction: discord.Interaction):
    guild = interaction.guild
    role = guild.get_role(self.role_id)
    if role is None:
      await interaction.response.send_message(
          "Role warna ini sudah dihapus dari server.", ephemeral=True
      )
      return
    nama_warna = {n for n, _, _ in WARNA_ROLE}
    try:
      if role in interaction.user.roles:
        await interaction.user.remove_roles(role)
        await interaction.response.send_message(
            f"Warna {role.name} dilepas.", ephemeral=True
        )
        return
      lama = [
          r
          for r in interaction.user.roles
          if r.name in nama_warna and r.id != role.id
      ]
      if lama:
        await interaction.user.remove_roles(*lama)
      await interaction.user.add_roles(role)
      await interaction.response.send_message(
          f"Warna namamu sekarang {role.name}.", ephemeral=True
      )
    except discord.Forbidden:
      await interaction.response.send_message(
          "Gagal. Posisikan role Bot di atas semua role warna pada pengaturan"
          " server.",
          ephemeral=True,
      )
    except Exception as e:
      await interaction.response.send_message(
          f"Gagal: {bersihkan_error(e)}", ephemeral=True
      )


class WarnaView(discord.ui.View):

  def __init__(self, pasangan):
    super().__init__(timeout=None)
    for entri in pasangan:
      role_id, label = entri[0], entri[1]
      emoji = entri[2] if len(entri) > 2 else None
      self.add_item(WarnaTombol(role_id, label, emoji))


@tree.command(
    name="colorpanel",
    description="Buat role warna nama dan kirim panel tombolnya",
)
@app_commands.checks.has_permissions(administrator=True)
async def colorpanel(interaction: discord.Interaction):
  if not interaction.guild.me.guild_permissions.manage_roles:
    await interaction.response.send_message(
        "Bot butuh izin Manage Roles.", ephemeral=True
    )
    return
  await interaction.response.defer()
  guild = interaction.guild
  pasangan = []
  for nama, kode, emoji in WARNA_ROLE:
    role = discord.utils.get(guild.roles, name=nama)
    if role is None:
      try:
        role = await guild.create_role(
            name=nama, color=discord.Color(kode), reason="panel warna"
        )
      except Exception:
        continue
    pasangan.append((role.id, nama, emoji))
  if not pasangan:
    await interaction.followup.send(
        "Gagal membuat role warna.", ephemeral=True
    )
    return
  embed = discord.Embed(
      title="Warna Nama",
      description=(
          "Klik tombol untuk mengubah warna namamu. Warna lama otomatis"
          " dilepas. Klik warna yang sama untuk melepasnya."
      ),
      color=discord.Color.blurple(),
  )
  tampilan = WarnaView(pasangan)
  pesan = await interaction.followup.send(
      embed=embed, view=tampilan, wait=True
  )
  data["color_panels"].append({
      "message_id": pesan.id,
      "roles": [
          {"id": rid, "label": lab, "emoji": emo} for rid, lab, emo in pasangan
      ],
  })
  simpan_data()
