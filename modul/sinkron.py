import discord

from modul.bantuan import PERINTAH_OWNER
from modul.inti import bersihkan_error, tree


SERVER_PRIBADI = [
    discord.Object(id=1464581081822138370),
    discord.Object(id=1526640729810800810),
]
IZIN_PERINTAH_ADMIN = {
    "setup": "administrator",
    "hapussetup": "administrator",
    "gayanama": "administrator",
    "pengaturan": "manage_guild",
    "reset": "administrator",
    "setwelcome": "administrator",
    "setbanner": "administrator",
    "hapusbanner": "administrator",
    "setautorole": "administrator",
    "setjoinvoice": "administrator",
    "colorpanel": "administrator",
    "stickyset": "administrator",
    "stickyhapus": "administrator",
    "setlog": "administrator",
    "setantispam": "administrator",
    "purge": "manage_messages",
    "addcmd": "administrator",
    "delcmd": "administrator",
    "hargaset": "administrator",
    "hargahapus": "administrator",
    "tiketpanel": "administrator",
}


def khusus_server(cmd):
  try:
    cmd.guild_only = True
  except AttributeError:
    pass


def atur_visibilitas_perintah():
  for nama in PERINTAH_OWNER:
    cmd = tree.get_command(nama)
    if cmd is None:
      continue
    tree.remove_command(nama)
    cmd.default_permissions = discord.Permissions(administrator=True)
    khusus_server(cmd)
    tree.add_command(cmd, guilds=SERVER_PRIBADI)
  for nama, izin in IZIN_PERINTAH_ADMIN.items():
    cmd = tree.get_command(nama)
    if cmd is None:
      continue
    cmd.default_permissions = discord.Permissions(**{izin: True})
    khusus_server(cmd)


async def sinkron_perintah():
  try:
    await tree.sync()
  except Exception as e:
    print(f"Sinkron perintah global gagal: {bersihkan_error(e)}")
  for server in SERVER_PRIBADI:
    try:
      await tree.sync(guild=server)
    except Exception as e:
      print(f"Sinkron perintah server {server.id} gagal: {bersihkan_error(e)}")
