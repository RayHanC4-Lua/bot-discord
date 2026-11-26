import sys

BERKAS = "bot.py"
BARU = 'def gudang_id_lagu(guild_id, user_id):\n  berubah = False\n  lama_semua = []\n  lama = data.get("id_fitur")\n  if isinstance(lama, dict) and isinstance(lama.get("daftar"), list):\n    lama_semua.extend(lama["daftar"])\n    data.pop("id_fitur", None)\n    berubah = True\n  for kunci in ("id_lagu", "id_lagu_pribadi"):\n    nilai = data.get(kunci)\n    if isinstance(nilai, dict):\n      for k in list(nilai):\n        if not isinstance(nilai[k], list):\n          nilai[k] = []\n          berubah = True\n    else:\n      if isinstance(nilai, list):\n        lama_semua.extend(nilai)\n      data[kunci] = {}\n      berubah = True\n  if lama_semua:\n    tujuan = data["id_lagu"].setdefault(str(SERVER_ID_LAMA), [])\n    for entri in lama_semua:\n      if isinstance(entri, (str, int)) and str(entri) not in map(str, tujuan):\n        tujuan.append(str(entri))\n  if berubah:\n    simpan_data()\n  if guild_id:\n    return data["id_lagu"].setdefault(str(guild_id), [])\n  return data["id_lagu_pribadi"].setdefault(str(user_id), [])\n'

with open(BERKAS, encoding="utf-8") as f:
  teks = f.read()

if "lama_semua = []" in teks:
  print("Perbaikan ini sudah pernah dipasang, tidak ada yang diubah.")
  sys.exit(0)

awal = teks.find("def gudang_id_lagu(guild_id, user_id):\n")
akhir = teks.find("\n\ndef pecah_id_lagu(", awal)
if awal < 0 or akhir < 0 or teks.count("def gudang_id_lagu(") != 1:
  print("Dibatalkan, fungsi gudang_id_lagu tidak ditemukan. Jalankan pisah_id_server.py dulu.")
  sys.exit(1)

teks = teks[:awal] + BARU.rstrip("\n") + "\n" + teks[akhir:]

try:
  compile(teks, BERKAS, "exec")
except SyntaxError as e:
  print(f"Dibatalkan, hasil tidak valid di baris {e.lineno}.")
  sys.exit(1)

with open(BERKAS, "w", encoding="utf-8") as f:
  f.write(teks)
print("Selesai. Data id_lagu lama dipindah ke format per server.")
