import asyncio
import io
import os

import discord
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont

from modul.inti import (
    FILE_BG,
    FILE_FONT,
    bersihkan_error,
    cek_premium,
    path_banner,
    tree,
)


def buat_banner(nama, urutan, avatar_bytes, bg_path=None):
  lebar, tinggi = 1024, 400
  sumber_bg = bg_path if (bg_path and os.path.exists(bg_path)) else FILE_BG
  if os.path.exists(sumber_bg):
    bg = Image.open(sumber_bg).convert("RGB").resize((lebar, tinggi))
  else:
    bg = Image.new("RGB", (lebar, tinggi), (30, 30, 40))
  gambar = ImageDraw.Draw(bg)

  ukuran_foto = 150
  foto = (
      Image.open(io.BytesIO(avatar_bytes))
      .convert("RGB")
      .resize((ukuran_foto, ukuran_foto))
  )
  topeng = Image.new("L", (ukuran_foto, ukuran_foto), 0)
  ImageDraw.Draw(topeng).ellipse(
      (0, 0, ukuran_foto, ukuran_foto), fill=255
  )
  pos_x = (lebar - ukuran_foto) // 2
  pos_y = 30
  cincin = 7
  gambar.ellipse(
      (
          pos_x - cincin,
          pos_y - cincin,
          pos_x + ukuran_foto + cincin,
          pos_y + ukuran_foto + cincin,
      ),
      fill=(255, 255, 255),
  )
  bg.paste(foto, (pos_x, pos_y), topeng)

  try:
    font_besar = ImageFont.truetype(FILE_FONT, 100)
    font_nama = ImageFont.truetype(FILE_FONT, 58)
    font_kecil = ImageFont.truetype(FILE_FONT, 38)
  except Exception:
    font_besar = ImageFont.load_default()
    font_nama = ImageFont.load_default()
    font_kecil = ImageFont.load_default()

  def tulis_tengah(teks, font, y, warna=(255, 255, 255)):
    kotak = gambar.textbbox((0, 0), teks, font=font)
    lebar_teks = kotak[2] - kotak[0]
    x = (lebar - lebar_teks) // 2
    gambar.text((x + 3, y + 3), teks, font=font, fill=(0, 0, 0))
    gambar.text((x, y), teks, font=font, fill=warna)

  tulis_tengah("WELCOME", font_besar, 215)
  tulis_tengah(nama[:20], font_nama, 320, (255, 220, 120))
  tulis_tengah(f"Member ke-{urutan}", font_kecil, 355)

  hasil = io.BytesIO()
  bg.save(hasil, format="PNG")
  hasil.seek(0)
  return hasil


@tree.command(
    name="setbanner",
    description="Atur gambar background welcome khusus server ini",
)
@app_commands.describe(gambar="Upload gambar, idealnya rasio 1024x400")
@app_commands.checks.has_permissions(administrator=True)
async def setbanner(
    interaction: discord.Interaction, gambar: discord.Attachment
):
  aktif, _ = cek_premium(interaction.guild_id)
  if not aktif:
    await interaction.response.send_message(
        "Fitur /setbanner khusus server premium. Hubungi owner bot untuk"
        " upgrade.",
        ephemeral=True,
    )
    return
  if not gambar.content_type or not gambar.content_type.startswith("image/"):
    await interaction.response.send_message(
        "File harus berupa gambar PNG atau JPG.", ephemeral=True
    )
    return
  if gambar.size > 8 * 1024 * 1024:
    await interaction.response.send_message(
        "Ukuran gambar maksimal 8 MB.", ephemeral=True
    )
    return
  await interaction.response.defer(ephemeral=True)
  try:
    data_byte = await gambar.read()

    def simpan():
      img = (
          Image.open(io.BytesIO(data_byte))
          .convert("RGB")
          .resize((1024, 400))
      )
      img.save(path_banner(interaction.guild_id), format="PNG")

    await asyncio.to_thread(simpan)
  except Exception as e:
    await interaction.followup.send(
        f"Gagal memproses gambar: {bersihkan_error(e)}", ephemeral=True
    )
    return
  try:
    avatar = await interaction.user.display_avatar.replace(
        size=256, format="png"
    ).read()
    preview = await asyncio.to_thread(
        buat_banner,
        interaction.user.display_name,
        interaction.guild.member_count,
        avatar,
        path_banner(interaction.guild_id),
    )
    await interaction.followup.send(
        "Background welcome khusus server ini berhasil diatur. Ini contoh"
        " tampilannya:",
        file=discord.File(preview, filename="preview.png"),
        ephemeral=True,
    )
  except Exception:
    await interaction.followup.send(
        "Background welcome khusus server ini berhasil diatur.", ephemeral=True
    )


@tree.command(
    name="hapusbanner",
    description="Kembalikan background welcome ke bawaan bot",
)
@app_commands.checks.has_permissions(administrator=True)
async def hapusbanner(interaction: discord.Interaction):
  p = path_banner(interaction.guild_id)
  if os.path.exists(p):
    try:
      os.remove(p)
    except Exception:
      pass
    await interaction.response.send_message(
        "Background welcome dikembalikan ke bawaan bot.", ephemeral=True
    )
  else:
    await interaction.response.send_message(
        "Server ini belum punya background khusus.", ephemeral=True
    )
