import asyncio
import contextlib
from datetime import timezone
import random
import re

import discord
from discord import app_commands

from modul.ai import panggil_agen_groq
from modul.ai_alat import alat_kirim_email_pemilik
from modul.balasan import EKSTENSI_BAHASA, buat_file, ekstrak_blok_kode
from modul.inti import PEMILIK_ID, bersihkan_error, data, simpan_data, tree
from modul.kantor.aksi import (
    aksi_bersihkan_sampah,
    aksi_buat_repo_github,
    aksi_segarkan_diri,
    tulis_email_groq,
)
from modul.kantor.dasar import (
    AKSI_KANTOR,
    FOKUS_RONDE,
    GAYA_CHAT,
    PERAN_KANTOR,
    WATAK_AGEN,
    anggota_tim,
    bersihkan_gaya,
    bersihkan_markdown,
    bersihkan_placeholder,
    catat_kantor,
    galat_groq,
    sekarang_wib,
    terlalu_mirip,
)
from modul.kantor.jadwal import deteksi_waktu, tambah_jadwal
from modul.kantor.repo import (
    AKSI_REPO,
    AKSI_RISIKO,
    jalankan_repo,
    kumpulkan_data_nyata,
    riset_web,
    siapkan_repo,
)


class TombolSetuju(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=300)
    self.hasil = None
    self.selesai = asyncio.Event()

  async def interaction_check(self, interaction: discord.Interaction):
    if interaction.user.id != PEMILIK_ID:
      await interaction.response.send_message(
          "Tombol ini khusus pemilik bot.", ephemeral=True
      )
      return False
    return True

  async def putuskan(self, interaction, nilai, teks):
    self.hasil = nilai
    for item in self.children:
      item.disabled = True
    await interaction.response.edit_message(content=teks, view=self)
    self.selesai.set()
    self.stop()

  @discord.ui.button(label="Setuju", style=discord.ButtonStyle.success)
  async def setuju(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await self.putuskan(
        interaction, True, "**@chatai**: Disetujui bos, aksi dijalankan."
    )

  @discord.ui.button(label="Tolak", style=discord.ButtonStyle.danger)
  async def tolak(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await self.putuskan(
        interaction, False, "**@chatai**: Ditolak bos, aksi dibatalkan."
    )

  async def on_timeout(self):
    self.selesai.set()


async def minta_persetujuan(interaction, uraian):
  tampilan = TombolSetuju()
  await catat_kantor("chatai", f"Menunggu persetujuan bos: {uraian}", "approval")
  pesan = await interaction.followup.send(
      f"**@chatai**: Menunggu persetujuan bos: {uraian}"[:1900],
      view=tampilan,
      allowed_mentions=discord.AllowedMentions.none(),
      wait=True,
  )
  await tampilan.selesai.wait()
  if tampilan.hasil is None:
    try:
      await pesan.edit(
          content="**@chatai**: Tidak ada jawaban dari bos, aksi dibatalkan.",
          view=None,
      )
    except Exception:
      pass
  await catat_kantor(
      "chatai",
      "Disetujui bos" if tampilan.hasil else "Aksi tidak disetujui",
      "persetujuan",
  )
  return bool(tampilan.hasil)


@tree.command(
    name="kantor",
    description="Tim agen AI berdiskusi untuk mengevaluasi tugas dan bisa menjalankan aksi",
)
@app_commands.describe(
    tugas="Masalah atau perintah untuk tim, misalnya bersihkan sampah atau tambah fitur",
    ronde="Berapa kali tim saling menanggapi (1 sampai 4)",
    eksekusi="Jalankan aksi yang diputuskan tim (khusus pemilik bot)",
)
async def kantor(
    interaction: discord.Interaction,
    tugas: str = "Evaluasi sistem operasional hari ini.",
    ronde: app_commands.Range[int, 1, 4] = 2,
    eksekusi: bool = False,
):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  await interaction.response.send_message(
      "Control Room diaktifkan. Tim sedang berdiskusi, mohon tunggu sebentar."
  )
  await jalankan_kantor(interaction, tugas, ronde, eksekusi)


async def jalankan_kantor(interaction, tugas, ronde, eksekusi):
  transkrip = []
  tanpa_ping = discord.AllowedMentions.none()
  bahan_nyata = await asyncio.to_thread(kumpulkan_data_nyata, tugas)
  await catat_kantor("sistem", f"Tugas dari bos: {tugas}", "tugas")
  riwayat_tugas = data.setdefault("riwayat_tugas", [])
  riwayat_tugas.append(tugas[:200])
  del riwayat_tugas[:-10]
  simpan_data()
  nama_agen = {
      "Marketing Manager": "pranowo",
      "Software House Manager": "manager",
  }
  gaya_chat = GAYA_CHAT
  watak = WATAK_AGEN

  def mengetik():
    if interaction.channel is None:
      return contextlib.nullcontext()
    return interaction.channel.typing()

  async def jeda_berpikir(teks=""):
    await asyncio.sleep(random.uniform(3, 6) + min(3, len(teks) / 60))

  berhenti = False
  for nomor in range(ronde):
    if berhenti:
      break
    if nomor == 0:
      fokus = FOKUS_RONDE[0]
    elif nomor == ronde - 1:
      fokus = FOKUS_RONDE[3]
    else:
      fokus = FOKUS_RONDE[min(nomor, 2)]
    for peran in PERAN_KANTOR:
      nama = nama_agen[peran]
      riwayat = "\n".join(f"{nama_agen[p]}: {t}" for p, t in transkrip)[-2000:]
      if bahan_nyata:
        info_data = (
            f"Data nyata yang tersedia:\n{bahan_nyata}\nGunakan hanya data"
            " ini, jangan mengarang isi repo atau kode."
        )
      else:
        info_data = (
            "Tidak ada data repo atau kode yang dilampirkan. Jangan"
            " berpura-pura sudah melihatnya, dan jangan minta user mengirim"
            " berkas, cukup bahas rencananya."
        )
      catatan = data.get("catatan_agen", {}).get(nama, [])[-3:]
      info_catatan = (
          "Catatan pribadimu dari pengalaman sebelumnya:\n- "
          + "\n- ".join(catatan)
          + "\n\n"
          if catatan
          else ""
      )
      tugas_agen = (
          f"Topik dari user: {tugas}\n\nWaktu sekarang:"
          f" {sekarang_wib():%H:%M} WIB.\nAnggota tim saat ini:"
          f" {anggota_tim()}.\nAksi yang benar-benar tersedia untuk Chat AI:"
          f" {'; '.join(AKSI_KANTOR.values())}.\n\n{info_data}\n\n{info_catatan}"
          f"Obrolan sejauh ini:\n"
          f"{riwayat or '(belum ada)'}\n\nSekarang giliranmu sebagai {nama}."
          f" Fokus giliran ini: {fokus} Tulis satu pesan chat singkat."
      )
      suhu = 0.85
      balasan = ""
      galat_ai = False
      async with mengetik():
        for percobaan in range(3):
          balasan = bersihkan_gaya(
              await asyncio.to_thread(
                  panggil_agen_groq,
                  peran,
                  tugas_agen,
                  f"{gaya_chat} {watak[nama]}",
                  45,
                  800,
                  suhu,
              )
          )
          if galat_groq(balasan):
            galat_ai = True
            berhenti = True
            break
          if not transkrip or not terlalu_mirip(
              balasan, [t for _, t in transkrip[-4:]]
          ):
            break
          tugas_agen += (
              "\n\nJawabanmu tadi terlalu mirip dengan obrolan yang sudah"
              " ada. Tulis ulang dengan hal baru yang berbeda."
          )
          suhu = 0.95
        else:
          berhenti = True
        if not berhenti:
          await jeda_berpikir(balasan)
      if berhenti:
        if galat_ai:
          await interaction.followup.send(
              "**@sistem**: Layanan AI sedang bermasalah, diskusi dihentikan"
              " lebih awal.",
              allowed_mentions=tanpa_ping,
          )
        break
      transkrip.append((peran, balasan))
      await interaction.followup.send(
          f"**@{nama}**: {balasan}"[:1900], allowed_mentions=tanpa_ping
      )
      await catat_kantor(nama, balasan)

  daftar_aksi = ", ".join(AKSI_KANTOR)
  riwayat = "\n".join(f"{nama_agen[p]}: {t}" for p, t in transkrip)[-2500:]
  async with mengetik():
    keputusan = await asyncio.to_thread(
        panggil_agen_groq,
        "Koordinator Operasional",
        (
            f"Perintah asli dari user: {tugas}\n\nObrolan tim:\n{riwayat}\n\n"
            "Tulis keputusan akhir tim dalam 1 sampai 2 kalimat sederhana."
            " Tulis sebagai rencana yang akan dikerjakan, jangan klaim ada"
            " yang sudah terkirim atau selesai, karena pelaksanaannya"
            " dilakukan sesudah ini oleh rekan lain. Kalau perintah menyebut"
            " jam pengiriman, tulis bahwa pengiriman akan dijadwalkan pada"
            " jam itu. Kalau permintaan tidak cocok dengan aksi yang tersedia,"
            " tulis bahwa itu belum bisa dikerjakan."
        ),
        (
            "Setelah itu, di baris baru, tulis AKSI: diikuti nama aksi dari"
            f" daftar ({daftar_aksi}) dipisah koma, atau AKSI: tidak_ada. Pilih"
            " aksi hanya jika perintah asli user jelas memintanya."
        ),
        60,
        700,
    )
    await jeda_berpikir(keputusan)
  if galat_groq(keputusan):
    keputusan = (
        "Keputusan belum bisa dibuat karena layanan AI sedang bermasalah.\n"
        "AKSI: tidak_ada"
    )
  cocok = re.search(r"AKSI:\s*(.+)", keputusan)
  terpilih = []
  if cocok:
    for nama in re.findall(r"[a-z_]+", cocok.group(1).lower()):
      if nama in AKSI_KANTOR and nama not in terpilih:
        terpilih.append(nama)
  ringkasan = bersihkan_gaya(re.sub(r"\n?.*AKSI:.*", "", keputusan).strip())
  await interaction.followup.send(
      f"**@keputusan**: {ringkasan}"[:1900], allowed_mentions=tanpa_ping
  )
  await catat_kantor("keputusan", ringkasan, "keputusan")

  if terpilih and not eksekusi:
    await interaction.followup.send(
        "Aksi yang diusulkan tim: "
        + ", ".join(terpilih)
        + ". Jalankan ulang perintah dengan opsi eksekusi aktif (khusus"
        " pemilik bot) kalau mau dilaksanakan."
    )

  konteks = {
      "guild": interaction.guild,
      "channel": interaction.channel,
      "member": interaction.user,
  }

  hasil_riset = []

  async def jalankan_aksi(nama, rincian=None):
    try:
      if nama in AKSI_REPO:
        return await asyncio.to_thread(jalankan_repo, nama, rincian)
      if nama == "riset_web":
        teks_riset = await asyncio.to_thread(riset_web, tugas)
        if galat_groq(teks_riset):
          return "Riset gagal karena layanan pencarian sedang bermasalah."
        teks_riset = bersihkan_placeholder(
            bersihkan_markdown(bersihkan_gaya(teks_riset))
        )[:1500]
        hasil_riset.append(teks_riset)
        return "Hasil riset: " + teks_riset
      if nama == "bersihkan_sampah":
        return await asyncio.to_thread(aksi_bersihkan_sampah)
      if nama == "segarkan_diri":
        return await aksi_segarkan_diri()
      bahan = ringkasan
      if bahan_nyata:
        bahan += f"\n\nData nyata:\n{bahan_nyata}"
      if nama == "buat_repo_github":
        return await asyncio.to_thread(aksi_buat_repo_github, tugas, bahan)
      bahan_email = bahan_nyata
      if hasil_riset:
        bahan_email += "\n\nHasil riset:\n" + "\n".join(hasil_riset)
      subjek, isi = await asyncio.to_thread(tulis_email_groq, tugas, bahan_email)
      waktu_kirim = deteksi_waktu(tugas, sekarang_wib())
      if waktu_kirim is not None:
        if waktu_kirim <= sekarang_wib():
          return (
              "Jam pengiriman yang diminta sudah lewat, jadi email belum"
              " dijadwalkan. Sebutkan jam yang masih akan datang."
          )
        nomor_jadwal = tambah_jadwal({
            "jenis": "email",
            "waktu": waktu_kirim.astimezone(timezone.utc).isoformat(),
            "subjek": subjek,
            "isi": isi,
            "channel_id": interaction.channel_id,
        })
        return (
            f"Siap, email dijadwalkan terkirim {waktu_kirim:%d/%m %H:%M} WIB"
            f" (jadwal nomor {nomor_jadwal}). Subjeknya: {subjek}"
        )
      hasil = await alat_kirim_email_pemilik(konteks, subjek, isi)
      if hasil.get("berhasil"):
        return f"Beres, email sudah terkirim ke email bos. Subjeknya: {subjek}"
      return f"Email gagal dikirim: {hasil.get('error')}"
    except Exception as e:
      return f"Gagal menjalankan {nama}: {bersihkan_error(e)}"

  if eksekusi and interaction.user.id == PEMILIK_ID:
    async with mengetik():
      await jeda_berpikir()
    await interaction.followup.send(
        "**@pranowo**: @chatai, tolong eksekusi keputusan tadi ya, sesuai request"
        " bos.",
        allowed_mentions=tanpa_ping,
    )
    async with mengetik():
      await jeda_berpikir()
    await interaction.followup.send(
        "**@manager**: Detailnya ada di keputusan tadi. Kabari kami kalau udah"
        " beres ya.",
        allowed_mentions=tanpa_ping,
    )
    if terpilih:
      terpilih.sort(key=lambda n: n != "riset_web")
      for nama in terpilih:
        rincian = None
        uraian = f"{AKSI_KANTOR[nama]}. Permintaan: {tugas[:150]}"
        if nama in AKSI_REPO:
          async with mengetik():
            uraian_repo, rincian = await asyncio.to_thread(
                siapkan_repo, nama, tugas
            )
          if uraian_repo is None:
            await interaction.followup.send(
                f"**@chatai**: {rincian}"[:1900], allowed_mentions=tanpa_ping
            )
            await catat_kantor("chatai", rincian, "info")
            continue
          uraian = uraian_repo
        if nama in AKSI_RISIKO:
          setuju = await minta_persetujuan(interaction, uraian)
          if not setuju:
            batal = "Aksi dibatalkan karena tidak disetujui."
            await interaction.followup.send(
                f"**@chatai**: {batal}", allowed_mentions=tanpa_ping
            )
            await catat_kantor("chatai", batal, "aksi")
            continue
        await catat_kantor("chatai", f"Mengerjakan: {AKSI_KANTOR[nama]}", "kerja")
        async with mengetik():
          hasil = await jalankan_aksi(nama, rincian)
          await jeda_berpikir(hasil)
        await interaction.followup.send(
            f"**@chatai**: {hasil}"[:1900], allowed_mentions=tanpa_ping
        )
        await catat_kantor("chatai", hasil, "aksi")
    else:
      pesan_jujur = (
          "Aku belum punya aksi untuk permintaan ini, jadi belum ada yang"
          " dikerjakan. Aksi yang tersedia: "
          + "; ".join(AKSI_KANTOR.values())
          + "."
      )
      await interaction.followup.send(
          f"**@chatai**: {pesan_jujur}"[:1900], allowed_mentions=tanpa_ping
      )
      await catat_kantor("chatai", pesan_jujur, "info")
  elif eksekusi:
    await interaction.followup.send(
        "Perintah dari tim tidak dijalankan karena hanya pemilik bot yang"
        " boleh mengeksekusi.",
        allowed_mentions=tanpa_ping,
    )

  blok = []
  for _, teks in transkrip:
    blok.extend(ekstrak_blok_kode(teks))
  lampiran = []
  for bahasa, kode in blok[:3]:
    if kode.strip():
      path = buat_file(bahasa or "draft", EKSTENSI_BAHASA.get(bahasa, "txt"), kode)
      lampiran.append(discord.File(path))
  if lampiran:
    await interaction.followup.send(
        "Draft kode dari tim dilampirkan. Ini belum diterapkan ke bot, cek"
        " dulu sebelum dipakai.",
        files=lampiran,
    )
