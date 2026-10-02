# bot-discord

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

3. Isi PEMILIK_ID di bot.py dengan ID Discord pemilik bot.

4. Jalankan bot:

```
python bot.py
```

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
