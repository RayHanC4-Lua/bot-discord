import difflib
import json
import os
import re
import urllib.parse

import requests

from modul.ai import kirim_groq, panggil_agen_groq
from modul.balasan import ekstrak_blok_kode
from modul.ekstensi import MODEL_KODE
from modul.github import push_ke_github
from modul.inti import berkas_kode_bot, bersihkan_error
from modul.kantor.dasar import galat_groq


def kumpulkan_data_nyata(tugas):
  teks = tugas.lower()
  bagian = []
  if re.search(r"bot\.py|kode bot|source code|kode sumber|kodemu", teks):
    try:
      berkas = berkas_kode_bot()
      sumber = ""
      for jalur in berkas:
        with open(jalur, encoding="utf-8") as f:
          sumber += f.read() + "\n"
      perintah = sorted(set(re.findall(r'name="([a-z_]+)"', sumber)))
      fungsi = re.findall(r"^(?:async )?def (\w+)", sumber, re.MULTILINE)
      bagian.append(
          f"Kode bot: {len(berkas)} berkas,"
          f" {len(sumber.splitlines())} baris,"
          f" {len(sumber) // 1024} KB, {len(fungsi)} fungsi. Perintah slash"
          f" (perkiraan): {', '.join(perintah)}. Contoh nama fungsi:"
          f" {', '.join(fungsi[:40])}."
      )
    except OSError as e:
      bagian.append(f"Gagal membaca kode bot: {bersihkan_error(e)}")
  token = os.getenv("GITHUB_TOKEN")
  header = {
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
  }
  if token:
    header["Authorization"] = f"Bearer {token}"
  cocok = re.search(r"github\.com/([\w.-]+)/([\w.-]+)", tugas)
  if cocok:
    pemilik, nama = cocok.group(1), cocok.group(2).removesuffix(".git")
    dasar = f"https://api.github.com/repos/{pemilik}/{nama}"
    try:
      info = requests.get(dasar, headers=header, timeout=20)
      if info.status_code != 200:
        bagian.append(f"Repo {pemilik}/{nama} tidak bisa dibaca (kode {info.status_code}).")
      else:
        d = info.json()
        cabang = d.get("default_branch", "main")
        pohon = requests.get(
            f"{dasar}/git/trees/{cabang}?recursive=1", headers=header, timeout=20
        )
        daftar = []
        if pohon.status_code == 200:
          daftar = [
              f"{x['path']} ({x.get('size', 0)} B)"
              for x in pohon.json().get("tree", [])
              if x.get("type") == "blob"
          ][:60]
        baca = requests.get(
            f"{dasar}/readme",
            headers={**header, "Accept": "application/vnd.github.raw"},
            timeout=20,
        )
        readme = baca.text[:1500] if baca.status_code == 200 else "(tidak ada README)"
        bagian.append(
            f"Repo {d.get('full_name')}: {d.get('description') or '-'}, bahasa"
            f" {d.get('language')}, terakhir diperbarui {d.get('pushed_at')}."
            f" File: {'; '.join(daftar) or '-'}. README: {readme}"
        )
    except Exception as e:
      bagian.append(f"Gagal membaca repo: {bersihkan_error(e)}")
  elif "repo" in teks and token:
    try:
      r = requests.get(
          "https://api.github.com/user/repos?sort=updated&per_page=10",
          headers=header,
          timeout=20,
      )
      if r.status_code == 200:
        baris = [
            f"{x['full_name']} ({'privat' if x['private'] else 'publik'},"
            f" {x.get('language') or '-'}): {x.get('description') or '-'}"
            for x in r.json()
        ]
        bagian.append("Repo terbaru di GitHub pemilik: " + " | ".join(baris))
      else:
        bagian.append(f"Daftar repo tidak bisa dibaca (kode {r.status_code}).")
    except Exception as e:
      bagian.append(f"Gagal membaca daftar repo: {bersihkan_error(e)}")
  return "\n".join(bagian)[:3500]


AKSI_REPO = {"arsipkan_repo", "hapus_repo", "edit_file_repo"}
AKSI_RISIKO = {"kirim_email_pemilik", "buat_repo_github", "bersihkan_sampah"} | AKSI_REPO


def header_github():
  return {
      "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
  }


def ekstrak_target(tugas):
  hasil = panggil_agen_groq(
      "Asisten Ekstraksi",
      f"Permintaan: {tugas}",
      (
          "Balas hanya satu objek JSON dengan kunci repo (nama repo atau"
          " pemilik/repo yang disebut jelas di permintaan, kosongkan kalau"
          " tidak ada), jalur (jalur file di repo kalau disebut, kosongkan"
          " kalau tidak), dan instruksi (perubahan yang diminta pada file,"
          " kosongkan kalau tidak ada). Jangan menebak."
      ),
      60,
      600,
      0.1,
  )
  cocok = re.search(r"\{.*\}", hasil, re.DOTALL)
  if not cocok:
    return {}
  try:
    obj = json.loads(cocok.group(0), strict=False)
  except ValueError:
    return {}
  return obj if isinstance(obj, dict) else {}


def siapkan_repo(nama_aksi, tugas):
  if not os.getenv("GITHUB_TOKEN"):
    return None, "GITHUB_TOKEN belum diisi di file .env."
  target = ekstrak_target(tugas)
  repo = str(target.get("repo") or "").strip()
  jalur = str(target.get("jalur") or "").strip().lstrip("/")
  instruksi = str(target.get("instruksi") or "").strip()
  if (
      not re.fullmatch(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)?", repo)
      or repo.split("/")[-1].lower() not in tugas.lower()
  ):
    return None, (
        "Nama repo tidak jelas di permintaanmu, jadi tidak ada yang diubah."
        " Tulis nama repo persis seperti di GitHub."
    )
  header = header_github()
  if "/" not in repo:
    akun = requests.get("https://api.github.com/user", headers=header, timeout=30)
    if akun.status_code != 200:
      return None, f"Token GitHub ditolak (kode {akun.status_code})."
    repo = f"{akun.json()['login']}/{repo}"
  info = requests.get(f"https://api.github.com/repos/{repo}", headers=header, timeout=30)
  if info.status_code != 200:
    return None, f"Repo {repo} tidak ditemukan atau token tidak punya akses."
  if nama_aksi == "arsipkan_repo":
    return f"ARSIPKAN repo {repo} (jadi hanya-baca, bisa dipulihkan).", {"repo": repo}
  if nama_aksi == "hapus_repo":
    return (
        f"HAPUS PERMANEN repo {repo}. Tidak bisa dibatalkan.",
        {"repo": repo},
    )
  if not jalur or ".." in jalur.split("/") or not instruksi:
    return None, "Sebutkan nama file dan perubahan yang diinginkan."
  asli = requests.get(
      f"https://api.github.com/repos/{repo}/contents/{urllib.parse.quote(jalur)}",
      headers={**header, "Accept": "application/vnd.github.raw"},
      timeout=30,
  )
  if asli.status_code != 200:
    return None, f"File {jalur} tidak ditemukan di repo {repo}."
  if len(asli.text) > 20000:
    return None, "File terlalu besar untuk diubah otomatis (maksimal 20 ribu karakter)."
  hasil = kirim_groq(
      {
          "model": MODEL_KODE,
          "messages": [
              {
                  "role": "system",
                  "content": (
                      "Ubah file sesuai instruksi. Balas hanya isi file lengkap"
                      " hasil akhir dalam satu blok kode, tanpa penjelasan."
                      " Jangan menulis komentar baru dan jangan menyertakan"
                      " token, kata sandi, atau key."
                  ),
              },
              {
                  "role": "user",
                  "content": f"Instruksi: {instruksi}\n\nIsi file {jalur}:\n{asli.text}",
              },
          ],
          "temperature": 0.2,
          "max_completion_tokens": 6000,
      },
      timeout=150,
  )
  if galat_groq(hasil):
    return None, "Gagal menulis perubahan karena layanan AI sedang bermasalah."
  blok = ekstrak_blok_kode(hasil)
  baru = blok[0][1] if blok else hasil
  if not baru.strip():
    return None, "AI tidak menghasilkan isi file baru."
  selisih = list(
      difflib.unified_diff(asli.text.splitlines(), baru.splitlines(), lineterm="", n=0)
  )
  tambah = sum(1 for s in selisih if s.startswith("+") and not s.startswith("+++"))
  hapus = sum(1 for s in selisih if s.startswith("-") and not s.startswith("---"))
  if tambah + hapus == 0:
    return None, "Tidak ada perubahan yang dihasilkan, file dibiarkan apa adanya."
  return (
      f"UBAH file {jalur} di repo {repo}: {instruksi[:120]}. Perubahan:"
      f" +{tambah} dan -{hapus} baris.",
      {"repo": repo, "jalur": jalur, "baru": baru},
  )


def jalankan_repo(nama_aksi, rincian):
  header = header_github()
  repo = rincian["repo"]
  if nama_aksi == "arsipkan_repo":
    res = requests.patch(
        f"https://api.github.com/repos/{repo}",
        headers=header,
        json={"archived": True},
        timeout=30,
    )
    if res.status_code == 200:
      return (
          f"Repo {repo} sudah diarsipkan (hanya-baca). Bisa dipulihkan lewat"
          " Settings di GitHub."
      )
    return f"Gagal mengarsipkan {repo}: kode {res.status_code}, {res.text[:150]}"
  if nama_aksi == "hapus_repo":
    res = requests.delete(
        f"https://api.github.com/repos/{repo}", headers=header, timeout=30
    )
    if res.status_code == 204:
      return f"Repo {repo} sudah dihapus permanen."
    if res.status_code in (403, 404):
      return (
          f"Repo {repo} belum dihapus (kode {res.status_code}). Token GitHub"
          " butuh izin delete_repo. Tambahkan izin itu di pengaturan token,"
          " lalu coba lagi."
      )
    return f"Gagal menghapus {repo}: kode {res.status_code}, {res.text[:150]}"
  return push_ke_github(
      repo,
      rincian["jalur"],
      rincian["baru"].encode("utf-8"),
      f"Ubah {rincian['jalur']} via kantor",
      "",
  )


def riset_web(pertanyaan):
  return kirim_groq(
      {
          "model": os.getenv("GROQ_MODEL_RISET", "groq/compound-mini"),
          "messages": [
              {
                  "role": "system",
                  "content": (
                      "Cari informasi terbaru di internet lalu jawab dalam"
                      " Bahasa Indonesia secara ringkas (maksimal 150 kata)"
                      " dan sebut nama sumbernya. Jangan mengarang. Kalau tidak"
                      " ketemu, katakan tidak ketemu. Tanpa emoji."
                  ),
              },
              {"role": "user", "content": pertanyaan},
          ],
          "temperature": 0.3,
          "max_completion_tokens": 1500,
          "tanpa_effort": True,
      },
      timeout=120,
  )
