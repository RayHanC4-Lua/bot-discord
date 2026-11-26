import asyncio
import base64
import hashlib
import os
import re
import urllib.parse

import discord
from discord import app_commands
import requests

from modul.inti import (
    FOLDER_BOT,
    PEMILIK_ID,
    berkas_kode_bot,
    bersihkan_error,
    tree,
)


POLA_RAHASIA = {
    "key Groq": r"gsk_[A-Za-z0-9]{20,}",
    "token GitHub": r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,})",
    "key Google": r"AIza[0-9A-Za-z_-]{20,}",
    "key Gemini": r"AQ\.[A-Za-z0-9_-]{30,}",
    "token Discord": r"[MN][A-Za-z0-9_-]{23,}\.[\w-]{6}\.[\w-]{27,}",
    "key API": r"sk-[A-Za-z0-9]{20,}",
}


def cari_rahasia(konten):
  teks = konten.decode("utf-8", "ignore")
  return [n for n, pola in POLA_RAHASIA.items() if re.search(pola, teks)]


def sha_blob_git(konten):
  return hashlib.sha1(b"blob %d\0" % len(konten) + konten).hexdigest()


def push_ke_github(repo, jalur, konten, pesan, cabang, lewati_sama=False):
  token = os.getenv("GITHUB_TOKEN")
  if not token:
    return "GITHUB_TOKEN belum diisi di file .env."
  otomatis = False
  rahasia = cari_rahasia(konten)
  if rahasia:
    return (
        "Dibatalkan karena file berisi rahasia ("
        + ", ".join(rahasia)
        + "). Pindahkan ke file .env dulu, lalu coba lagi."
    )
  header = {
      "Authorization": f"Bearer {token}",
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
  }
  if "/" not in repo:
    akun = requests.get("https://api.github.com/user", headers=header, timeout=30)
    if akun.status_code != 200:
      return f"Token GitHub ditolak (kode {akun.status_code}). Periksa GITHUB_TOKEN."
    repo = f"{akun.json()['login']}/{repo}"
    otomatis = True
  jalur = jalur.strip().replace("\\", "/").lstrip("/")
  bagian = jalur.split("/")
  if not jalur or ".." in bagian or bagian[-1].lower().startswith(".env"):
    return "Jalur file tidak valid atau tidak diizinkan."
  cek_repo = requests.get(
      f"https://api.github.com/repos/{repo}", headers=header, timeout=30
  )
  if cek_repo.status_code == 404:
    return (
        f"Repo {repo} tidak ditemukan. Cek ejaan nama repo, atau token belum"
        " punya akses ke repo itu (token classic perlu scope repo)."
        + (
            " Ingat: kolom repo diisi nama repo (misalnya botdc), bukan nama"
            " akun GitHub."
            if otomatis
            else ""
        )
    )
  if cek_repo.status_code != 200:
    return f"Repo {repo} tidak bisa dibaca (kode {cek_repo.status_code})."
  catatan_cabang = ""
  if cabang:
    cek_cabang = requests.get(
        f"https://api.github.com/repos/{repo}/branches/{urllib.parse.quote(cabang)}",
        headers=header,
        timeout=30,
    )
    if cek_cabang.status_code == 404:
      bawaan = cek_repo.json().get("default_branch", "main")
      acuan = requests.get(
          f"https://api.github.com/repos/{repo}/git/ref/heads/{urllib.parse.quote(bawaan)}",
          headers=header,
          timeout=30,
      )
      if acuan.status_code != 200:
        return (
            f"Cabang {cabang} belum ada dan tidak bisa dibuat. Kalau repo masih"
            " kosong, kosongkan kolom cabang."
        )
      buat = requests.post(
          f"https://api.github.com/repos/{repo}/git/refs",
          headers=header,
          json={
              "ref": f"refs/heads/{cabang}",
              "sha": acuan.json()["object"]["sha"],
          },
          timeout=30,
      )
      if buat.status_code != 201:
        return f"Gagal membuat cabang {cabang}: kode {buat.status_code}."
      catatan_cabang = f" (cabang baru {cabang} dibuat dari {bawaan})"
  url = (
      f"https://api.github.com/repos/{repo}/contents/"
      f"{urllib.parse.quote(jalur)}"
  )
  ada = requests.get(
      url,
      headers=header,
      params={"ref": cabang} if cabang else {},
      timeout=30,
  )
  isi_kirim = {
      "message": pesan,
      "content": base64.b64encode(konten).decode("ascii"),
  }
  if cabang:
    isi_kirim["branch"] = cabang
  aksi = "dibuat"
  if ada.status_code == 200:
    if isinstance(ada.json(), list):
      return "Jalur itu adalah folder, bukan file."
    if lewati_sama and ada.json().get("sha") == sha_blob_git(konten):
      return "Tidak ada perubahan."
    isi_kirim["sha"] = ada.json()["sha"]
    aksi = "diperbarui"
  elif ada.status_code != 404:
    return f"Gagal memeriksa repo {repo} (kode {ada.status_code})."
  respons = requests.put(url, headers=header, json=isi_kirim, timeout=60)
  if respons.status_code in (200, 201):
    return f"File {aksi}: {respons.json()['content']['html_url']}{catatan_cabang}"
  return f"GitHub menolak: kode {respons.status_code}, {respons.text[:200]}"


@tree.command(
    name="pushgithub",
    description="Kirim atau perbarui satu file di repo GitHub (khusus pemilik)",
)
@app_commands.describe(
    repo="Nama repo milikmu, atau pemilik/repo",
    jalur="Lokasi file di repo, contoh: src/index.html",
    isi="Isi teks file (kosongkan kalau memakai lampiran)",
    berkas="Lampiran file sebagai ganti isi teks",
    lokal="Nama file di folder bot untuk dikirim, contoh: bot.py",
    pesan="Pesan commit",
    cabang="Nama cabang (kosongkan untuk cabang bawaan)",
)
async def pushgithub(
    interaction: discord.Interaction,
    repo: str,
    jalur: str = "",
    isi: str = "",
    berkas: discord.Attachment = None,
    lokal: str = "",
    pesan: str = "",
    cabang: str = "",
):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  if berkas is None and not isi and not lokal:
    await interaction.response.send_message(
        "Isi teks file, lampirkan file, atau isi nama file lokal dulu ya.",
        ephemeral=True,
    )
    return
  konten_lokal = None
  if lokal:
    folder = FOLDER_BOT
    penuh = os.path.realpath(os.path.join(folder, lokal))
    nama_lokal = os.path.basename(penuh).lower()
    if (
        not penuh.startswith(folder + os.sep)
        or not os.path.isfile(penuh)
        or nama_lokal.startswith(".env")
        or nama_lokal.endswith((".pem", ".key"))
    ):
      await interaction.response.send_message(
          "File lokal itu tidak ditemukan di folder bot atau tidak diizinkan.",
          ephemeral=True,
      )
      return
    if os.path.getsize(penuh) > 5 * 1024 * 1024:
      await interaction.response.send_message(
          "File lokal terlalu besar, maksimal 5 MB.", ephemeral=True
      )
      return
    with open(penuh, "rb") as f:
      konten_lokal = f.read()
    jalur = jalur or os.path.relpath(penuh, folder).replace(os.sep, "/")
  jalur = jalur or (berkas.filename if berkas else "")
  if not jalur:
    await interaction.response.send_message(
        "Isi jalur file di repo, contoh: src/index.html.", ephemeral=True
    )
    return
  if berkas is not None and berkas.size > 5 * 1024 * 1024:
    await interaction.response.send_message(
        "Lampiran terlalu besar, maksimal 5 MB.", ephemeral=True
    )
    return
  await interaction.response.defer()
  if konten_lokal is not None:
    konten = konten_lokal
  elif berkas is not None:
    konten = await berkas.read()
  else:
    konten = isi.encode("utf-8")
  try:
    hasil = await asyncio.to_thread(
        push_ke_github,
        repo.strip(),
        jalur,
        konten,
        pesan or f"Update {jalur} via bot",
        cabang.strip(),
    )
  except Exception as e:
    hasil = f"Gagal mengirim ke GitHub: {bersihkan_error(e)}"
  await interaction.followup.send(hasil[:1900])


README_REPO = """# bot-discord

Bot Discord multifungsi berbasis discord.py. Berjalan di Termux (Android) dan memakai model AI lokal atau layanan AI online.

## Fitur utama

- Chat AI di channel memakai model lokal (llama.server) atau Gemini
- Tim agen AI lewat /kantor: dua agen berdiskusi, mengambil keputusan, lalu menjalankan aksi
- Aksi otomatis: bersihkan file lama, segarkan bot, kirim email ke pemilik, buat repo GitHub
- Fitur tambahan buatan AI lewat /tambahfitur, langsung aktif tanpa restart
- Kirim file ke GitHub lewat /pushgithub, /uploadbot, dan /rapikanrepo
- Pengaturan server seperti log, welcome, autorole, antispam, sticky message, dan pricelist

## Persiapan

1. Pasang paket yang dibutuhkan:

```
pip install -r requirements.txt
```

2. Buat file .env di folder yang sama dengan bot.py. File ini tidak boleh diunggah ke GitHub. Isinya:

```
DISCORD_TOKEN=
GROQ_API_KEY=
GEMINI_API_KEY=
GEMINI_MODEL=
AI_BASE_URL=
AI_API_KEY=
AI_MODEL=
SMTP_USER=
SMTP_PASSWORD=
EMAIL_PEMILIK=
GITHUB_TOKEN=
```

3. Isi PEMILIK_ID di modul/inti.py dengan ID Discord pemilik bot.

4. Jalankan bot:

```
python bot.py
```

## Struktur kode

- bot.py: titik masuk, memuat semua modul lalu menjalankan bot
- modul/inti.py: konfigurasi, data, client, dan fungsi bantu umum
- modul/acara.py: event Discord seperti pesan, member, dan on_ready
- modul/ai.py, ai_alat.py, obrolan.py, balasan.py: chat AI beserta alatnya
- modul/kantor/: tim agen AI (rapat /kantor, staf, jadwal, laporan, aksi)
- modul lainnya: satu file per fitur, misalnya tiket, toko, pengingat, spotify

## Perintah khusus pemilik

- /kantor: diskusi tim agen AI, bisa dengan opsi eksekusi
- /tambahfitur dan /hapusfitur: tambah atau copot fitur buatan AI
- /refresh dan /restart: segarkan atau nyalakan ulang bot
- /cekenv: periksa apakah isi .env sudah terbaca
- /pushgithub, /uploadbot, /rapikanrepo: kirim file ke GitHub

## Keamanan

- Jangan menaruh token atau key di dalam kode, semuanya lewat file .env
- File .gitignore sudah mengecualikan .env dan data bot
- Perintah pengiriman ke GitHub menolak file yang berisi pola key atau token
"""

REQUIREMENTS_REPO = """discord.py
python-dotenv
Pillow
requests
yt-dlp
"""

GITIGNORE_REPO = """.env
bot_config.json
__pycache__/
*.pyc
unduhan/
file_ai/
banners/
ekstensi/
*.log
"""

BERKAS_REPO = [
    ("README.md", README_REPO, "Tambah README"),
    ("requirements.txt", REQUIREMENTS_REPO, "Tambah daftar paket"),
    (".gitignore", GITIGNORE_REPO, "Tambah gitignore"),
]


@tree.command(
    name="rapikanrepo",
    description="Kirim README, requirements.txt, dan .gitignore ke repo GitHub (khusus pemilik)",
)
@app_commands.describe(
    repo="Nama repo saja, contoh: bot-discord",
    cabang="Nama cabang (opsional)",
)
async def rapikanrepo(
    interaction: discord.Interaction, repo: str, cabang: str = ""
):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  await interaction.response.defer()
  baris = []
  for jalur, isi, pesan in BERKAS_REPO:
    try:
      hasil = await asyncio.to_thread(
          push_ke_github,
          repo.strip(),
          jalur,
          isi.encode("utf-8"),
          pesan,
          cabang.strip(),
      )
    except Exception as e:
      hasil = f"Gagal: {bersihkan_error(e)}"
    baris.append(f"{jalur}: {hasil}")
    if "tidak ditemukan" in hasil or "ditolak" in hasil:
      break
  await interaction.followup.send("\n".join(baris)[:1900])


@tree.command(
    name="uploadbot",
    description="Kirim semua kode bot (bot.py dan folder modul) ke repo GitHub (khusus pemilik)",
)
@app_commands.describe(
    repo="Nama repo saja, contoh: botdc",
    cabang="Nama cabang (opsional, dibuat otomatis kalau belum ada)",
)
async def uploadbot(
    interaction: discord.Interaction, repo: str, cabang: str = ""
):
  if interaction.user.id != PEMILIK_ID:
    await interaction.response.send_message(
        "Perintah ini khusus pemilik bot.", ephemeral=True
    )
    return
  await interaction.response.defer()
  terkirim = 0
  sama = 0
  gagal = []
  for jalur in berkas_kode_bot():
    relatif = os.path.relpath(jalur, FOLDER_BOT).replace(os.sep, "/")
    try:
      with open(jalur, "rb") as f:
        konten = f.read()
      hasil = await asyncio.to_thread(
          push_ke_github,
          repo.strip(),
          relatif,
          konten,
          f"Update {relatif} via bot",
          cabang.strip(),
          True,
      )
    except Exception as e:
      hasil = f"Gagal mengirim ke GitHub: {bersihkan_error(e)}"
    if hasil.startswith("File "):
      terkirim += 1
    elif hasil == "Tidak ada perubahan.":
      sama += 1
    else:
      gagal.append(f"{relatif}: {hasil}")
      if "tidak ditemukan" in hasil or "ditolak" in hasil:
        break
  ringkasan = f"{terkirim} file terkirim, {sama} file tidak berubah."
  if gagal:
    ringkasan += "\n" + "\n".join(gagal)
  await interaction.followup.send(ringkasan[:1900])
