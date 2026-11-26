import discord
from discord import app_commands

from modul.inti import client, data, simpan_data, tree


@tree.command(
    name="setjoinvoice", description="Tentukan voice channel Join to Create"
)
@app_commands.describe(channel="Voice channel yang jadi pintu masuk")
@app_commands.checks.has_permissions(administrator=True)
async def setjoinvoice(
    interaction: discord.Interaction, channel: discord.VoiceChannel
):
  data["joinvoice"][str(interaction.guild_id)] = {"hub": channel.id}
  simpan_data()
  await interaction.response.send_message(
      f"{channel.name} sekarang jadi Join to Create. Member yang masuk ke"
      " sana otomatis dibuatkan voice sendiri.",
      ephemeral=True,
  )


@client.event
async def on_voice_state_update(member, before, after):
  if member.bot:
    return
  info = data["joinvoice"].get(str(member.guild.id))
  if (
      info
      and after.channel is not None
      and after.channel.id == int(info["hub"])
  ):
    try:
      izin = {
          member: discord.PermissionOverwrite(
              manage_channels=True, move_members=True, mute_members=True
          )
      }
      baru = await member.guild.create_voice_channel(
          f"Room {member.display_name}"[:90],
          category=after.channel.category,
          overwrites=izin,
          reason="voice sementara",
      )
      await member.move_to(baru)
      data["voice_sementara"].append(baru.id)
      simpan_data()
    except Exception:
      pass
  if (
      before.channel is not None
      and before.channel.id in data["voice_sementara"]
      and len(before.channel.members) == 0
  ):
    try:
      await before.channel.delete(reason="voice sementara kosong")
    except Exception:
      pass
    try:
      data["voice_sementara"].remove(before.channel.id)
      simpan_data()
    except Exception:
      pass
