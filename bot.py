import os

import modul.acara
import modul.bantuan
import modul.banner
import modul.ekstensi
import modul.github
import modul.id_lagu
import modul.kantor.jadwal
import modul.kantor.laporan
import modul.kantor.rapat
import modul.kantor.staf
import modul.kantor.web
import modul.obrolan
import modul.pemilik
import modul.pengaturan
import modul.pengingat
import modul.perintah_kustom
import modul.premium
import modul.setup_server
import modul.spotify
import modul.suara
import modul.tiket
import modul.toko
import modul.umum
import modul.unduhan
import modul.warna
from modul.ekstensi import muat_semua_ekstensi
from modul.inti import client
from modul.sinkron import atur_visibilitas_perintah


atur_visibilitas_perintah()
muat_semua_ekstensi()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
  print("ERROR: DISCORD_TOKEN tidak ditemukan di file .env!")
else:
  client.run(TOKEN)
