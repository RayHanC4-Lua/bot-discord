import asyncio
from datetime import datetime, timezone
import os
import re

import discord

from modul.ai import panggil_agen_groq
from modul.ai_alat import alat_kirim_email_pemilik
from modul.inti import (
    PEMILIK_ID,
    bersihkan_error,
    client,
    data,
    simpan_data,
    tree,
)
from modul.kantor.dasar import (
    anggota_tim,
    bersihkan_gaya,
    bersihkan_markdown,
    bersihkan_placeholder,
    bungkus_email,
    catat_kantor,
    galat_groq,
    kirim_ke_pemilik,
    sekarang_wib,
)


async def buat_laporan():
  sejak = data.get("laporan_terakhir_waktu")
  aktivitas = [
      a
      for a in data.get("aktivitas", [])
      if (not sejak or a["waktu"] > sejak) and a["jenis"] != "laporan"
  ]
  aksi = [a for a in aktivitas if a["jenis"] == "aksi"][-10:]
  obrolan = [a for a in aktivitas if a["jenis"] in ("rutin", "obrolan")][-20:]
  rekrut = [a for a in aktivitas if a["jenis"] == "rekrut"]
  usulan = [a for a in aktivitas if a["jenis"] == "usulan"]
  bagian = []
  bagian.append(
      "Tindakan nyata:\n"
      + (
          "\n".join(f"- {a['teks']}" for a in aksi)
          if aksi
          else "- Tidak ada tindakan nyata sejak laporan terakhir."
      )
  )
  if obrolan:
    ringkas = await asyncio.to_thread(
        panggil_agen_groq,
        "Chat AI, penulis laporan kantor",
        "Obrolan tim:\n"
        + "\n".join(f"{a['agen']}: {a['teks'][:200]}" for a in obrolan),
        (
            "Ringkas dalam 2 sampai 3 poin singkat apa yang dibicarakan. Tulis"
            " sebagai pembahasan atau ide, bukan pekerjaan yang sudah selesai,"
            " dan jangan menambah detail yang tidak ada di obrolan. Awali tiap"
            " poin dengan tanda strip. Tanpa emoji."
        ),
        80,
        1500,
        0.3,
    )
    if galat_groq(ringkas):
      ringkas = "- Ringkasan obrolan tidak tersedia karena layanan AI bermasalah."
    bagian.append(
        "Yang dibahas (ide, bukan pekerjaan selesai):\n"
        + bersihkan_placeholder(bersihkan_markdown(bersihkan_gaya(ringkas)))
    )
  catatan = [
      f"- {nama.capitalize()}: {daftar[-1]}"
      for nama, daftar in data.get("catatan_agen", {}).items()
      if daftar
  ]
  if catatan:
    bagian.append("Catatan belajar terbaru:\n" + "\n".join(catatan))
  if usulan:
    bagian.append(
        "Usulan fitur:\n"
        + "\n".join(
            "- " + a["teks"].replace("Usulan fitur: ", "", 1) for a in usulan
        )
    )
  if rekrut:
    bagian.append(
        "Anggota baru:\n" + "\n".join(f"- {a['teks']}" for a in rekrut)
    )
  bagian.append(f"Anggota tim saat ini: {anggota_tim()}.")
  bagian.append(f"Jadwal yang menunggu: {len(data.get('jadwal', []))}.")
  return "\n\n".join(bagian)


async def kirim_laporan(label):
  sekarang = sekarang_wib()
  isi = await buat_laporan()
  subjek = f"Laporan Kantor RyHanC, {label} {sekarang:%d/%m}"
  pemilik = type("Pemilik", (), {"id": PEMILIK_ID})()
  try:
    hasil = await alat_kirim_email_pemilik(
        {"member": pemilik}, subjek, bungkus_email(isi)
    )
    status = (
        "Laporan terkirim ke email bos."
        if hasil.get("berhasil")
        else f"Email laporan gagal: {hasil.get('error')}"
    )
  except Exception as e:
    status = f"Email laporan gagal: {bersihkan_error(e)}"
  data["laporan_terakhir_waktu"] = datetime.now(timezone.utc).isoformat()
  simpan_data()
  await catat_kantor("chatai", f"{subjek}. {status}", "laporan")
  await kirim_ke_pemilik(f"**Laporan {label}**\n{isi}\n\n{status}"[:1900])
  return status


async def loop_laporan():
  await client.wait_until_ready()
  while not client.is_closed():
    try:
      sekarang = sekarang_wib()
      terkirim = data.setdefault("laporan_kirim", [])
      for slot in os.getenv("KANTOR_LAPORAN_JAM", "08:00,20:00").split(","):
        slot = slot.strip()
        if not re.fullmatch(r"\d{1,2}:\d{2}", slot):
          continue
        jam, menit = map(int, slot.split(":"))
        target = sekarang.replace(hour=jam, minute=menit, second=0, microsecond=0)
        kunci = f"{sekarang:%Y-%m-%d} {jam:02d}:{menit:02d}"
        selisih = (sekarang - target).total_seconds()
        if 0 <= selisih < 5400 and kunci not in terkirim:
          terkirim.append(kunci)
          del terkirim[:-10]
          simpan_data()
          await kirim_laporan("pagi" if jam < 15 else "malam")
    except Exception as e:
      print(f"Laporan error: {bersihkan_error(e)}")
    await asyncio.sleep(60)


@tree.command(
    name="laporan", description="Kirim laporan kantor sekarang ke email (khusus pemilik)"
)
async def laporan(interaction: discord.Interaction):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  await interaction.response.defer(ephemeral=True)
  status = await kirim_laporan("manual")
  await interaction.followup.send(status, ephemeral=True)
