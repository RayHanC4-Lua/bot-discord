import asyncio
from datetime import datetime, timezone
import json
import os
import random
import re

import discord
from discord import app_commands

from modul.ai import panggil_agen_groq
from modul.inti import (
    PEMILIK_ID,
    bersihkan_error,
    client,
    data,
    simpan_data,
    tree,
)
from modul.kantor.dasar import (
    AKSI_KANTOR,
    GAYA_CHAT,
    RESERVED_NAMA,
    TOPIK_RUTIN,
    anggota_tim,
    bersihkan_gaya,
    catat_belajar,
    catat_kantor,
    daftar_staf,
    fakta_nyata,
    galat_groq,
    kirim_ke_kanal,
    sekarang_wib,
    terlalu_mirip,
    watak_agen,
)


async def coba_rekrut(ringkas, kanal_id):
  staf = data.setdefault("staf", [])
  maks = int(os.getenv("KANTOR_MAKS_STAF", "3"))
  if len(staf) >= maks:
    return
  terakhir = data.get("rekrut_terakhir")
  if terakhir:
    umur = datetime.now(timezone.utc) - datetime.fromisoformat(terakhir)
    if umur.total_seconds() < 20 * 3600:
      return
  if random.random() > 0.35:
    return
  hasil = await asyncio.to_thread(
      panggil_agen_groq,
      "Software House Manager",
      f"Obrolan tadi:\n{ringkas}\n\nAnggota tim saat ini: {anggota_tim()}."
      " Perlukah tim merekrut satu anggota baru agar pekerjaan lebih lengkap?",
      (
          "Jika perlu, balas hanya objek JSON dengan kunci nama (satu kata"
          " huruf kecil, 3 sampai 12 huruf), peran (maksimal 4 kata, misalnya"
          " Analis Konten), sudut_pandang (satu kalimat), dan alasan (satu"
          " kalimat). Jika tidak perlu, balas {\"perlu\": false}."
      ),
      60,
      600,
      0.6,
  )
  cocok = re.search(r"\{.*\}", hasil, re.DOTALL)
  if not cocok:
    return
  try:
    obj = json.loads(cocok.group(0), strict=False)
  except ValueError:
    return
  if obj.get("perlu") is False:
    return
  nama = str(obj.get("nama", "")).strip().lower()
  if (
      not re.fullmatch(r"[a-z]{3,12}", nama)
      or nama in RESERVED_NAMA
      or any(s["nama"] == nama for s in staf)
  ):
    return
  peran = bersihkan_gaya(str(obj.get("peran", "")))[:40]
  sudut = bersihkan_gaya(str(obj.get("sudut_pandang", "")))[:160]
  alasan = bersihkan_gaya(str(obj.get("alasan", "")))[:160]
  if not peran or not sudut:
    return
  staf.append({
      "nama": nama,
      "peran": peran,
      "sudut": sudut,
      "alasan": alasan,
      "waktu": datetime.now(timezone.utc).isoformat(),
  })
  data["rekrut_terakhir"] = datetime.now(timezone.utc).isoformat()
  simpan_data()
  sapaan = (
      f"Halo semua, aku {nama.capitalize()}, {peran}. Aku bergabung karena"
      f" {alasan or 'tim butuh sudut pandang baru'}."
  )
  await catat_kantor(nama, sapaan, "rekrut")
  await kirim_ke_kanal(kanal_id, f"**@{nama}**: {sapaan}")


async def satu_siklus_rutin():
  if 0 <= sekarang_wib().hour < 6:
    return
  kanal_id = os.getenv("KANTOR_CHANNEL_ID")
  fakta = fakta_nyata()
  fakta_teks = "\n".join(f"- {f}" for f in fakta) or "(belum ada tindakan nyata)"
  tugas_lama = data.get("riwayat_tugas", [])[-3:]
  if tugas_lama and random.random() < 0.5:
    topik = "tindak lanjut tugas bos: " + random.choice(tugas_lama)
  else:
    topik = random.choice(TOPIK_RUTIN)
  peserta = [
      ("Marketing Manager", "pranowo"),
      ("Software House Manager", "manager"),
  ] + [(s["peran"], s["nama"]) for s in daftar_staf()]
  obrolan = []
  await catat_kantor("sistem", f"Obrolan santai di kantor tentang: {topik}", "rutin")
  for giliran in range(min(3 + len(daftar_staf()), 6)):
    peran, nama = peserta[giliran % len(peserta)]
    riwayat = "\n".join(f"{n}: {t}" for n, t in obrolan)[-1500:]
    catatan = data.get("catatan_agen", {}).get(nama, [])[-3:]
    info_catatan = (
        "Catatan pribadimu dari pengalaman sebelumnya:\n- "
        + "\n- ".join(catatan)
        + "\n\n"
        if catatan
        else ""
    )
    tugas_agen = (
        f"Topik obrolan santai di kantor (bukan perintah dari bos): {topik}"
        f"\n\nWaktu sekarang: {sekarang_wib():%H:%M} WIB.\nAnggota tim saat"
        f" ini: {anggota_tim()}.\nTindakan yang benar-benar terjadi"
        f" belakangan ini:\n{fakta_teks}\nAksi yang benar-benar tersedia:"
        f" {'; '.join(AKSI_KANTOR.values())}.\nJangan menyebut fitur,"
        " dashboard, integrasi, atau pekerjaan yang tidak ada di daftar itu."
        f"\n\n{info_catatan}Obrolan sejauh ini:\n"
        f"{riwayat or '(belum ada)'}\n\nSekarang giliranmu sebagai {nama}."
        " Kalian belum mengerjakan apa pun secara nyata, jadi bicarakan ide,"
        " rencana, atau pertanyaan, bukan hasil kerja yang diklaim selesai,"
        " dan jangan menyebut teknologi atau nama alat yang tidak ada di bot"
        " ini. Tulis satu pesan chat singkat yang menambah hal baru."
    )
    balasan = bersihkan_gaya(
        await asyncio.to_thread(
            panggil_agen_groq,
            peran,
            tugas_agen,
            f"{GAYA_CHAT} {watak_agen(nama)}",
            45,
            800,
            0.9,
        )
    )
    if galat_groq(balasan):
      return
    if obrolan and terlalu_mirip(balasan, [t for _, t in obrolan[-3:]]):
      break
    obrolan.append((nama, balasan))
    await asyncio.sleep(random.uniform(4, 8))
    await catat_kantor(nama, balasan, "rutin")
    await kirim_ke_kanal(kanal_id, f"**@{nama}**: {balasan}")
  if len(obrolan) < 2:
    return
  ringkas = "\n".join(f"{n}: {t}" for n, t in obrolan)
  for peran, nama in (peserta[:5] if fakta else []):
    catatan_baru = bersihkan_gaya(
        await asyncio.to_thread(
            panggil_agen_groq,
            peran,
            f"Obrolan tadi:\n{ringkas}\n\nFakta tindakan nyata:\n{fakta_teks}"
            "\n\nTulis satu kalimat catatan belajar pribadimu yang bersumber"
            " dari fakta tindakan nyata itu, bukan dari ide di obrolan.",
            "Tulis satu kalimat saja, tanpa emoji.",
            30,
            500,
            0.7,
        )
    )
    if not galat_groq(catatan_baru):
      catat_belajar(nama, catatan_baru)
  if "ide fitur" in topik.lower() or random.random() < 0.25:
    ide = bersihkan_gaya(
        await asyncio.to_thread(
            panggil_agen_groq,
            "Software House Manager",
            f"Obrolan tadi:\n{ringkas}\n\nRangkum satu usulan fitur konkret"
            " untuk bot Discord dalam satu kalimat.",
            "Tulis satu kalimat saja, tanpa emoji.",
            35,
            500,
            0.7,
        )
    )
    if not galat_groq(ide):
      usulan = data.setdefault("usulan", [])
      usulan.append({"waktu": sekarang_wib().isoformat(), "teks": ide})
      del usulan[:-10]
      await catat_kantor("manager", f"Usulan fitur: {ide}", "usulan")
      await kirim_ke_kanal(kanal_id, f"**@manager**: Usulan fitur: {ide}")
  await coba_rekrut(ringkas, kanal_id)
  simpan_data()


async def loop_rutinitas():
  await client.wait_until_ready()
  menit = int(os.getenv("KANTOR_RUTIN_MENIT", "60"))
  if menit <= 0:
    return
  await asyncio.sleep(120)
  while not client.is_closed():
    try:
      await satu_siklus_rutin()
    except Exception as e:
      print(f"Rutinitas kantor error: {bersihkan_error(e)}")
    await asyncio.sleep(menit * 60 + random.uniform(0, 300))


@tree.command(
    name="usulan", description="Lihat usulan fitur dari tim (khusus pemilik)"
)
async def usulan(interaction: discord.Interaction):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  daftar = data.get("usulan", [])
  if not daftar:
    await interaction.response.send_message(
        "Belum ada usulan dari tim.", ephemeral=True
    )
    return
  baris = [
      f"{i}. {u['teks']}" for i, u in enumerate(reversed(daftar[-10:]), start=1)
  ]
  await interaction.response.send_message(
      "Usulan terbaru (paling baru di atas). Kalau cocok, jalankan"
      " /tambahfitur dengan usulan itu.\n" + "\n".join(baris)[:1700],
      ephemeral=True,
  )


@tree.command(name="staf", description="Lihat anggota tim, termasuk yang direkrut sendiri (khusus pemilik)")
async def staf(interaction: discord.Interaction):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  baris = [f"Anggota tim: {anggota_tim()}."]
  for s in daftar_staf():
    baris.append(f"{s['nama']}: {s['peran']}. Alasan: {s['alasan']}")
  await interaction.response.send_message("\n".join(baris)[:1900], ephemeral=True)


@tree.command(name="pecat", description="Keluarkan anggota rekrutan tim (khusus pemilik)")
@app_commands.describe(nama="Nama anggota dari perintah /staf")
async def pecat(interaction: discord.Interaction, nama: str):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  nama = nama.strip().lower()
  sisa = [s for s in daftar_staf() if s["nama"] != nama]
  if len(sisa) == len(daftar_staf()):
    await interaction.response.send_message(
        "Anggota itu tidak ditemukan di daftar rekrutan.", ephemeral=True
    )
    return
  data["staf"] = sisa
  data.get("catatan_agen", {}).pop(nama, None)
  simpan_data()
  await interaction.response.send_message(
      f"{nama.capitalize()} sudah dikeluarkan dari tim.", ephemeral=True
  )
