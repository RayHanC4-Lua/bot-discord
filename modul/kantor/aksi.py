import base64
import json
import os
import re
import time
import urllib.parse

from dotenv import load_dotenv
import requests

from modul.ai import kirim_groq, panggil_agen_groq
from modul.ekstensi import MODEL_KODE, muat_ulang_ekstensi
from modul.inti import (
    COOLDOWN_CHAT,
    RIWAYAT_CHAT,
    client,
    data,
    muat_data,
    presensi_default,
)
from modul.kantor.dasar import (
    ada_placeholder,
    bersihkan_markdown,
    bersihkan_placeholder,
    bungkus_email,
)


def aksi_bersihkan_sampah():
  batas = time.time() - 3600
  jumlah = 0
  ukuran = 0
  for folder in ("unduhan", "file_ai"):
    if not os.path.isdir(folder):
      continue
    for nama in os.listdir(folder):
      path = os.path.join(folder, nama)
      try:
        if os.path.isfile(path) and os.path.getmtime(path) < batas:
          ukuran += os.path.getsize(path)
          os.remove(path)
          jumlah += 1
      except OSError:
        continue
  return f"Sampah dibersihkan: {jumlah} file lama, sekitar {ukuran // 1024} KB."


async def aksi_segarkan_diri():
  load_dotenv(override=True)
  baru = muat_data()
  data.clear()
  data.update(baru)
  RIWAYAT_CHAT.clear()
  COOLDOWN_CHAT.clear()
  await client.change_presence(activity=presensi_default())
  jumlah = muat_ulang_ekstensi()
  return (
      "Bot disegarkan: pengaturan dimuat ulang, riwayat chat dan cooldown"
      f" dikosongkan, {jumlah} fitur tambahan dimuat ulang."
  )


PETUNJUK_PROYEK = (
    "Kamu menyusun proyek kecil yang siap diunggah ke GitHub sesuai permintaan"
    " pemilik. Format jawaban wajib persis begini: baris pertama REPO: nama-repo"
    " (huruf kecil, angka, tanda minus), baris kedua DESKRIPSI: satu kalimat,"
    " lalu tiap file ditulis dengan baris ### FILE: jalur/file.ext diikuti satu"
    " blok kode markdown berisi isi file. Wajib ada README.md berbahasa"
    " Indonesia, dan README.md tidak boleh berisi blok kode bersarang. Maksimal"
    " 8 file. Jangan tulis komentar di dalam kode. Jangan menyertakan token,"
    " kata sandi, atau file .env."
)


def susun_proyek_groq(tugas, ringkasan):
  hasil = kirim_groq(
      {
          "model": MODEL_KODE,
          "messages": [
              {"role": "system", "content": PETUNJUK_PROYEK},
              {
                  "role": "user",
                  "content": (
                      f"Permintaan pemilik: {tugas}\n\nKeputusan tim:"
                      f" {ringkasan}"
                  ),
              },
          ],
          "temperature": 0.3,
          "max_completion_tokens": 5000,
      },
      timeout=150,
  )
  nama = re.search(r"REPO:\s*([A-Za-z0-9._-]+)", hasil)
  deskripsi = re.search(r"DESKRIPSI:\s*(.+)", hasil)
  berkas = re.findall(
      r"###\s*FILE:\s*(\S+)\s*\n```[^\n]*\n(.*?)```", hasil, re.DOTALL
  )
  return (
      nama.group(1).lower() if nama else "proyek-bot",
      deskripsi.group(1).strip() if deskripsi else "Dibuat oleh bot Discord",
      berkas,
  )


def aksi_buat_repo_github(tugas, ringkasan):
  token = os.getenv("GITHUB_TOKEN")
  if not token:
    return "GITHUB_TOKEN belum diisi di file .env, jadi repo belum bisa dibuat."
  nama, deskripsi, berkas = susun_proyek_groq(tugas, ringkasan)
  aman = []
  for jalur, isi in berkas:
    jalur = jalur.strip().replace("\\", "/")
    bagian = jalur.split("/")
    if jalur.startswith("/") or ".." in bagian:
      continue
    if bagian[-1].lower().startswith(".env") or len(isi) > 200000:
      continue
    aman.append((jalur, isi))
  aman = aman[:8]
  if not aman:
    return "AI belum berhasil menyusun file proyek. Coba jelaskan permintaan lebih rinci."
  header = {
      "Authorization": f"Bearer {token}",
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
  }
  respons = None
  for percobaan in range(2):
    nama_coba = nama if percobaan == 0 else f"{nama}-{int(time.time()) % 10000}"
    respons = requests.post(
        "https://api.github.com/user/repos",
        headers=header,
        json={"name": nama_coba, "description": deskripsi[:300], "private": True},
        timeout=30,
    )
    if respons.status_code == 201:
      break
    if respons.status_code != 422:
      break
  if respons is None or respons.status_code != 201:
    return f"GitHub menolak pembuatan repo: {respons.text[:200]}"
  info = respons.json()
  terunggah = 0
  for jalur, isi in aman:
    r = requests.put(
        f"https://api.github.com/repos/{info['full_name']}/contents/"
        f"{urllib.parse.quote(jalur)}",
        headers=header,
        json={
            "message": f"Tambah {jalur}",
            "content": base64.b64encode(isi.encode("utf-8")).decode("ascii"),
        },
        timeout=30,
    )
    if r.status_code in (200, 201):
      terunggah += 1
  return (
      f"Repo privat sudah dibuat: {info['html_url']} dengan {terunggah} dari"
      f" {len(aman)} file terunggah."
  )


def tulis_email_groq(tugas, ringkasan):
  instruksi = (
      "Balas hanya satu objek JSON dengan kunci subjek dan isi, tanpa teks"
      " lain. Isi hanya berisi badan email dalam Bahasa Indonesia yang sopan,"
      " singkat, dan jelas. Jangan menulis sapaan pembuka maupun tanda tangan,"
      " karena keduanya ditambahkan otomatis. Jangan memakai placeholder"
      " seperti [Nama], dan jangan membuat tautan, nama orang, atau tim yang"
      " tidak ada. Hanya pakai fakta dari permintaan dan data yang diberikan."
      " Penerima email adalah pemilik bot sendiri."
  )
  tugas_email = (
      f"Permintaan pemilik: {tugas}\n\nData nyata yang tersedia:"
      f" {ringkasan or '(tidak ada data tambahan)'}\n\nTulis email sesuai"
      " permintaan itu. Jangan menyatakan ada sesuatu yang sudah"
      " diimplementasikan, dikerjakan, atau selesai, karena tidak ada data"
      " bahwa itu terjadi."
  )
  subjek, isi = "", ""
  for _ in range(2):
    hasil = panggil_agen_groq(
        "Asisten Penulis Email", tugas_email, instruksi, 150, 1200, 0.5
    )
    cocok = re.search(r"\{.*\}", hasil, re.DOTALL)
    if not cocok:
      continue
    try:
      obj = json.loads(cocok.group(0), strict=False)
    except ValueError:
      continue
    subjek = bersihkan_placeholder(str(obj.get("subjek", "")))
    isi = bersihkan_markdown(str(obj.get("isi", ""))).strip()
    if subjek and isi and not ada_placeholder(subjek + isi):
      break
    tugas_email += (
        "\n\nEmail sebelumnya masih berisi placeholder atau data palsu."
        " Tulis ulang tanpa itu."
    )
  isi = bersihkan_placeholder(isi)
  if not subjek or len(isi) < 15:
    subjek = "Pesan dari Kantor RyHanC"
    isi = tugas
  return subjek, bungkus_email(isi)
