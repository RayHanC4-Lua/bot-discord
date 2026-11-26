import asyncio
from email.message import EmailMessage
import os
import smtplib

import discord

from modul.inti import (
    DUMMY_PRODUK,
    PEMILIK_ID,
    cari_member,
    cek_premium,
    client,
    data,
    teks_uptime,
)


async def alat_cek_statistik_server(konteks):
  guild = konteks["guild"]
  manusia = [m for m in guild.members if not m.bot]
  return {
      "ping_bot_ms": round(client.latency * 1000),
      "uptime_bot": teks_uptime(),
      "total_server_yang_dimasuki_bot": len(client.guilds),
      "server_ini": {
          "nama": guild.name,
          "jumlah_member": guild.member_count,
          "member_manusia": len(manusia),
          "member_online": sum(
              1 for m in manusia if m.status != discord.Status.offline
          ),
          "jumlah_bot": len(guild.members) - len(manusia),
          "channel_teks": len(guild.text_channels),
          "channel_suara": len(guild.voice_channels),
          "jumlah_role": len(guild.roles),
          "level_boost": guild.premium_tier,
      },
  }


async def alat_cari_harga_atau_produk(konteks, kata_kunci=""):
  gid = str(konteks["guild"].id)
  kandidat = []
  for item, nilai in data["harga"].get(gid, {}).items():
    kandidat.append({"nama": item, "harga": nilai, "sumber": "daftar harga server"})
  for paket in data["pricelist"]:
    kandidat.append({
        "nama": paket.get("nama"),
        "harga": paket.get("harga"),
        "keterangan": paket.get("keterangan"),
        "sumber": "paket premium bot",
    })
  catatan = None
  if not kandidat:
    kandidat = [dict(p, sumber="data contoh") for p in DUMMY_PRODUK]
    catatan = "Server ini belum punya daftar harga, jadi ini hanya data contoh."
  kata = str(kata_kunci or "").lower().split()
  cocok = [k for k in kandidat if all(w in str(k["nama"]).lower() for w in kata)]
  hasil = {"jumlah_ditemukan": len(cocok), "hasil": cocok[:15]}
  if not cocok:
    hasil["nama_yang_tersedia"] = [str(k["nama"]) for k in kandidat[:25]]
  if catatan:
    hasil["catatan"] = catatan
  return hasil


async def alat_info_user(konteks, nama=""):
  guild = konteks["guild"]
  member = cari_member(guild, nama, konteks["member"])
  if member is None:
    return {"error": f"Member dengan nama {nama} tidak ditemukan di server ini."}
  role = [r.name for r in reversed(member.roles) if r.name != "@everyone"]
  return {
      "username": member.name,
      "nama_tampilan": member.display_name,
      "id": member.id,
      "adalah_bot": member.bot,
      "akun_dibuat": member.created_at.strftime("%d-%m-%Y"),
      "bergabung_ke_server": member.joined_at.strftime("%d-%m-%Y")
      if member.joined_at
      else None,
      "status": str(member.status),
      "role_tertinggi": member.top_role.name,
      "daftar_role": role[:15],
      "jumlah_role": len(role),
  }


async def alat_info_channel(konteks, nama=""):
  guild = konteks["guild"]
  kunci = str(nama or "").strip().lstrip("#").lower()
  if kunci:
    ch = discord.utils.find(lambda c: c.name.lower() == kunci, guild.channels)
    if ch is None:
      ch = discord.utils.find(lambda c: kunci in c.name.lower(), guild.channels)
  else:
    ch = konteks["channel"]
  if ch is None:
    return {"error": f"Channel {nama} tidak ditemukan di server ini."}
  hasil = {
      "nama": ch.name,
      "id": ch.id,
      "tipe": str(ch.type),
      "kategori": ch.category.name if getattr(ch, "category", None) else None,
      "dibuat": ch.created_at.strftime("%d-%m-%Y"),
      "topik": getattr(ch, "topic", None),
      "slowmode_detik": getattr(ch, "slowmode_delay", None),
      "nsfw": getattr(ch, "nsfw", None),
  }
  if isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
    hasil["jumlah_di_voice"] = len(ch.members)
    hasil["batas_user"] = ch.user_limit or "tanpa batas"
  return hasil


async def alat_cek_status_premium(konteks):
  aktif, batas = cek_premium(konteks["guild"].id)
  if not aktif:
    return {"premium": False}
  return {
      "premium": True,
      "berlaku_sampai": batas.strftime("%d-%m-%Y") if batas else "permanen",
  }


def skema(deskripsi, properti=None):
  return {"deskripsi": deskripsi, "properties": properti or {}}


async def alat_kirim_email_pemilik(konteks, subjek="", isi=""):
  member = konteks.get("member")
  if member is None or member.id != PEMILIK_ID:
    return {"error": "Alat ini khusus pemilik bot."}
  host = os.getenv("SMTP_HOST", "smtp.gmail.com")
  port = int(os.getenv("SMTP_PORT", "465"))
  akun = os.getenv("SMTP_USER")
  sandi = os.getenv("SMTP_PASSWORD")
  tujuan = os.getenv("EMAIL_PEMILIK")
  kosong = [
      n
      for n, v in (
          ("SMTP_USER", akun),
          ("SMTP_PASSWORD", sandi),
          ("EMAIL_PEMILIK", tujuan),
      )
      if not v
  ]
  if kosong:
    return {
        "error": (
            "Bot belum membaca " + ", ".join(kosong) + " dari file .env."
            " Jalankan /cekenv untuk memeriksa."
        )
    }
  pesan = EmailMessage()
  pesan["From"] = akun
  pesan["To"] = tujuan
  pesan["Subject"] = (subjek or "Pesan dari bot")[:200]
  pesan.set_content((isi or "(kosong)")[:5000])

  def kirim():
    if port == 465:
      with smtplib.SMTP_SSL(host, port, timeout=30) as server:
        server.login(akun, sandi)
        server.send_message(pesan)
    else:
      with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(akun, sandi)
        server.send_message(pesan)

  await asyncio.to_thread(kirim)
  return {"berhasil": True, "tujuan": "email pemilik"}


ALAT_AI = {
    "cek_statistik_server": {
        "fungsi": alat_cek_statistik_server,
        "skema": skema(
            "Melihat ping bot, uptime, jumlah member, channel, role, dan status"
            " server Discord ini."
        ),
    },
    "cari_harga_atau_produk": {
        "fungsi": alat_cari_harga_atau_produk,
        "skema": skema(
            "Mencari harga atau produk dari daftar harga server dan paket"
            " premium bot. Kosongkan kata_kunci untuk melihat semuanya.",
            {
                "kata_kunci": {
                    "type": "string",
                    "description": (
                        "Nama produk atau kata kunci, contoh: robux"
                    ),
                }
            },
        ),
    },
    "info_user": {
        "fungsi": alat_info_user,
        "skema": skema(
            "Melihat info seorang member: tanggal akun dibuat, tanggal join,"
            " role, dan status. Kosongkan nama untuk user yang bertanya.",
            {
                "nama": {
                    "type": "string",
                    "description": "Username, nama tampilan, atau ID member",
                }
            },
        ),
    },
    "info_channel": {
        "fungsi": alat_info_channel,
        "skema": skema(
            "Melihat info sebuah channel: tipe, kategori, topik, slowmode."
            " Kosongkan nama untuk channel tempat percakapan ini.",
            {
                "nama": {
                    "type": "string",
                    "description": "Nama channel tanpa tanda pagar",
                }
            },
        ),
    },
    "cek_status_premium": {
        "fungsi": alat_cek_status_premium,
        "skema": skema(
            "Mengecek apakah server ini berstatus premium dan sampai kapan."
        ),
    },
    "kirim_email_pemilik": {
        "fungsi": alat_kirim_email_pemilik,
        "skema": skema(
            "Mengirim email ke alamat email pemilik bot. Hanya berfungsi jika"
            " yang meminta adalah pemilik bot.",
            {
                "subjek": {
                    "type": "string",
                    "description": "Judul email",
                },
                "isi": {
                    "type": "string",
                    "description": "Isi email dalam teks biasa",
                },
            },
        ),
    },
}

TOOLS_AI = [
    {
        "type": "function",
        "function": {
            "name": nama,
            "description": alat["skema"]["deskripsi"],
            "parameters": {
                "type": "object",
                "properties": alat["skema"]["properties"],
            },
        },
    }
    for nama, alat in ALAT_AI.items()
]
