import asyncio
from datetime import datetime, timezone
import hmac
import os
import time

import requests

from modul.inti import PEMILIK_ID, bersihkan_error, client
from modul.kantor.rapat import jalankan_kantor


class KirimanWeb:

  def __init__(self, kanal):
    self.kanal = kanal

  async def send(self, *args, **kwargs):
    kwargs.pop("wait", None)
    kwargs.pop("ephemeral", None)
    return await self.kanal.send(*args, **kwargs)


class InteraksiWeb:

  def __init__(self, kanal, pemilik):
    self.channel = kanal
    self.channel_id = kanal.id
    self.guild = getattr(kanal, "guild", None)
    self.user = pemilik
    self.followup = KirimanWeb(kanal)


def ambil_perintah_web():
  alamat = os.getenv("SUPABASE_URL").rstrip("/")
  kunci = os.getenv("SUPABASE_SERVICE_KEY")
  res = requests.get(
      f"{alamat}/rest/v1/kantor_perintah?status=eq.baru&order=id.asc&limit=1",
      headers={"apikey": kunci, "Authorization": f"Bearer {kunci}"},
      timeout=10,
  )
  if res.status_code != 200:
    return None
  daftar = res.json()
  return daftar[0] if daftar else None


def tandai_perintah(nomor, status):
  alamat = os.getenv("SUPABASE_URL").rstrip("/")
  kunci = os.getenv("SUPABASE_SERVICE_KEY")
  requests.patch(
      f"{alamat}/rest/v1/kantor_perintah?id=eq.{nomor}",
      headers={
          "apikey": kunci,
          "Authorization": f"Bearer {kunci}",
          "Content-Type": "application/json",
          "Prefer": "return=minimal",
      },
      json={"status": status},
      timeout=10,
  )


async def jalankan_dari_web(teks):
  pemilik = await client.fetch_user(PEMILIK_ID)
  kanal_id = os.getenv("KANTOR_CHANNEL_ID")
  kanal = client.get_channel(int(kanal_id)) if kanal_id else None
  if kanal is None:
    kanal = pemilik.dm_channel or await pemilik.create_dm()
  await kanal.send(
      "Control Room diaktifkan dari halaman web. Tim sedang berdiskusi."
  )
  await jalankan_kantor(InteraksiWeb(kanal, pemilik), teks, 2, True)


async def loop_perintah_web():
  await client.wait_until_ready()
  kode = os.getenv("KANTOR_KODE")
  if not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY") and kode):
    return
  terakhir = 0.0
  while not client.is_closed():
    try:
      baris = await asyncio.to_thread(ambil_perintah_web)
      if baris:
        dibuat = datetime.fromisoformat(baris["dibuat"].replace("Z", "+00:00"))
        umur = (datetime.now(timezone.utc) - dibuat).total_seconds()
        if not hmac.compare_digest(str(baris.get("kode", "")), kode):
          status = "ditolak"
        elif umur > 600:
          status = "kedaluwarsa"
        elif time.time() - terakhir < 30:
          status = "terlalu_cepat"
        else:
          status = "diproses"
        await asyncio.to_thread(tandai_perintah, baris["id"], status)
        if status == "diproses":
          terakhir = time.time()
          await jalankan_dari_web(baris["teks"])
          await asyncio.to_thread(tandai_perintah, baris["id"], "selesai")
    except Exception as e:
      print(f"Perintah web error: {bersihkan_error(e)}")
    await asyncio.sleep(5)
