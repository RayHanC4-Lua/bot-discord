import re

import discord

from modul.ai import cek_cooldown_chat, jalankan_agen, simpan_riwayat
from modul.balasan import kirim_bertahap, siapkan_balasan
from modul.inti import (
    AI_MODEL,
    BATAS_RIWAYAT,
    RIWAYAT_CHAT,
    SESI_CHAT_AKTIF,
    bersihkan_error,
    client,
    tree,
)


async def proses_pesan_ai(message, isi):
  tanpa_ping = discord.AllowedMentions.none()
  isi = isi.strip()[:1500]
  if not isi:
    await message.reply(
        "Halo! Tanyakan apa saja, atau minta aku cek statistik server, harga"
        " produk, info user, dan info channel.",
        mention_author=False,
        allowed_mentions=tanpa_ping,
    )
    return
  if not cek_cooldown_chat(message.author.id):
    return
  konteks = {
      "guild": message.guild,
      "channel": message.channel,
      "member": message.author,
  }
  teks_user = f"{message.author.display_name}: {isi}"
  riwayat = list(
      RIWAYAT_CHAT.get(message.channel.id, [])[-(BATAS_RIWAYAT * 2) :]
  )
  try:
    async with message.channel.typing():
      jawaban, _ = await jalankan_agen(teks_user, riwayat, konteks)
  except Exception as e:
    await message.reply(
        f"Gagal menghubungi AI: {bersihkan_error(e)}",
        mention_author=False,
        allowed_mentions=tanpa_ping,
    )
    return
  simpan_riwayat(message.channel.id, teks_user, jawaban)
  try:
    teks_chat, lampiran = siapkan_balasan(jawaban)
  except Exception as e:
    teks_chat, lampiran = jawaban[:4500], []
  await kirim_bertahap(message, teks_chat, lampiran, tanpa_ping)


async def tangani_mention(message):
  isi = re.sub(rf"<@!?{client.user.id}>", "", message.content)
  await proses_pesan_ai(message, isi)


async def tangani_sesi_chat(message):
  await proses_pesan_ai(message, message.content)


@tree.command(
    name="chat", description="Mulai sesi ngobrol aktif dengan AI di channel ini"
)
async def chat(interaction: discord.Interaction):
  if interaction.channel_id in SESI_CHAT_AKTIF:
    await interaction.response.send_message(
        "Sesi chat di channel ini sudah aktif. Langsung ketik pesan biasa aja.",
        ephemeral=True,
    )
    return
  SESI_CHAT_AKTIF.add(interaction.channel_id)
  await interaction.response.send_message(
      f"Sesi chat aktif di channel ini! Sekarang aku bakal balas semua pesan"
      f" biasa di sini pakai {AI_MODEL} (lokal), tanpa perlu mention atau"
      f" prefix. Ketik `/endchat` kalau mau selesai.",
      allowed_mentions=discord.AllowedMentions.none(),
  )


@tree.command(
    name="endchat",
    description="Hentikan sesi chat AI di channel ini dan hapus riwayatnya",
)
async def endchat(interaction: discord.Interaction):
  aktif = interaction.channel_id in SESI_CHAT_AKTIF
  SESI_CHAT_AKTIF.discard(interaction.channel_id)
  RIWAYAT_CHAT.pop(interaction.channel_id, None)
  if aktif:
    await interaction.response.send_message(
        "Sesi chat di channel ini sudah dihentikan dan riwayatnya dibersihkan.",
        ephemeral=True,
    )
  else:
    await interaction.response.send_message(
        "Riwayat percakapan di channel ini sudah dibersihkan (sesi memang belum"
        " aktif).",
        ephemeral=True,
    )
