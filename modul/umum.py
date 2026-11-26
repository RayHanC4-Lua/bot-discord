import discord

from modul import inti
from modul.inti import client, tree


@tree.command(name="stats", description="Lihat statistik bot")
async def stats(interaction: discord.Interaction):
  total_server = len(client.guilds)
  total_member = sum(g.member_count or 0 for g in client.guilds)
  unik = len({m.id for g in client.guilds for m in g.members if not m.bot})
  if inti.WAKTU_MULAI:
    detik = int((discord.utils.utcnow() - inti.WAKTU_MULAI).total_seconds())
    hari, sisa = divmod(detik, 86400)
    jam, sisa = divmod(sisa, 3600)
    menit = sisa // 60
    uptime = f"{hari}h {jam}j {menit}m"
  else:
    uptime = "tidak diketahui"
  embed = discord.Embed(
      title="Statistik bot",
      color=discord.Color.blurple(),
      timestamp=discord.utils.utcnow(),
  )
  embed.add_field(name="Server", value=str(total_server))
  embed.add_field(name="Total member", value=str(total_member))
  embed.add_field(name="User unik", value=str(unik))
  embed.add_field(name="Ping", value=f"{round(client.latency * 1000)} ms")
  embed.add_field(name="Uptime", value=uptime)
  await interaction.response.send_message(embed=embed)


@tree.command(name="ping", description="Cek apakah bot aktif")
async def ping(interaction: discord.Interaction):
  await interaction.response.send_message("Pong! Bot aktif.")
