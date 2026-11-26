import discord

from modul.inti import PEMILIK_ID, tree


PERINTAH_OWNER = [
    "tambahfitur",
    "hapusfitur",
    "cekenv",
    "pushgithub",
    "rapikanrepo",
    "uploadbot",
    "refresh",
    "restart",
    "setpremium",
    "hapuspremium",
    "premiumlist",
    "pricelistset",
    "pricelistdel",
    "kantor",
    "staf",
    "pecat",
    "usulan",
    "laporan",
    "jadwal",
    "batalkanjadwal",
]
KATEGORI_OWNER = "Khusus Owner"

HELP_KATEGORI = {
    "Umum dan Info Bot": [
        ("help", "Lihat semua fitur dan perintah bot"),
        ("ping", "Cek apakah bot aktif"),
        ("stats", "Lihat statistik bot"),
        ("pricelist", "Lihat paket dan harga premium bot ini"),
        ("premiumstatus", "Cek status premium server ini"),
    ],
    "Media dan Musik": [
        ("download", "Download video atau audio dari link atau judul"),
        ("spotify", "Ubah link lagu Spotify jadi MP3"),
        ("tambahid", "Tambah ID lagu ke daftar"),
        ("hapusid", "Hapus ID lagu dari daftar"),
        ("id", "Lihat semua ID lagu yang tersimpan"),
        ("pilihid", "Pilih satu lagu untuk menyalin ID-nya saja"),
    ],
    "Chat AI dan Pengingat": [
        ("chat", "Mulai sesi ngobrol dengan AI di channel ini"),
        ("endchat", "Hentikan sesi chat AI dan hapus riwayatnya"),
        ("ingatkan", "Buat pengingat WIB, bisa pakai tanggal dan gambar"),
        ("listingat", "Lihat pengingat server ini, atau pengingat pribadi di DM"),
        ("hapusingat", "Hapus pengingat berdasarkan ID"),
    ],
    "Pengaturan Server dan Moderasi": [
        ("setup", "Buat struktur channel dan role (admin, premium)"),
        ("hapussetup", "Hapus channel dan role buatan setup (admin, premium)"),
        ("gayanama", "Ubah gaya nama channel buatan setup (admin, premium)"),
        ("pengaturan", "Lihat pengaturan bot di server ini (admin)"),
        ("reset", "Matikan salah satu fitur di server ini (admin)"),
        ("setwelcome", "Atur pesan sambutan di channel ini (admin)"),
        ("setbanner", "Atur gambar welcome khusus server ini (admin, premium)"),
        ("hapusbanner", "Kembalikan welcome ke bawaan bot (admin)"),
        ("setautorole", "Role otomatis untuk member baru (admin)"),
        ("setjoinvoice", "Atur voice Join to Create (admin)"),
        ("colorpanel", "Kirim panel warna nama untuk member (admin)"),
        ("stickyset", "Pasang pesan sticky di channel ini (admin)"),
        ("stickyhapus", "Matikan pesan sticky di channel ini (admin)"),
        ("setlog", "Jadikan channel ini Security Log (admin)"),
        ("setantispam", "Blokir link dari member baru (admin)"),
        ("purge", "Hapus banyak pesan sekaligus (moderator)"),
    ],
    "Custom Command": [
        ("addcmd", "Buat custom command teks baru (admin)"),
        ("delcmd", "Hapus custom command teks (admin)"),
        ("cc", "Jalankan custom command"),
    ],
    "Toko dan Tiket": [
        ("harga", "Lihat daftar harga"),
        ("hargaset", "Tambah atau ubah harga item (admin)"),
        ("hargahapus", "Hapus item dari daftar harga (admin)"),
        ("tiketpanel", "Kirim panel tiket order dan report (admin, premium)"),
        ("testi", "Kirim testimoni ke channel ini"),
    ],
    KATEGORI_OWNER: [
        ("tambahfitur", "Minta AI membuat fitur baru"),
        ("hapusfitur", "Copot fitur buatan AI"),
        ("cekenv", "Periksa isi .env yang terbaca bot"),
        ("pushgithub", "Kirim atau perbarui satu file di repo GitHub"),
        ("rapikanrepo", "Kirim README, requirements, dan gitignore ke repo"),
        ("uploadbot", "Kirim semua kode bot ke repo GitHub"),
        ("refresh", "Muat ulang pengaturan dan fitur tambahan"),
        ("restart", "Nyalakan ulang bot"),
        ("setpremium", "Beri status premium ke server"),
        ("hapuspremium", "Cabut status premium server"),
        ("premiumlist", "Lihat semua server premium"),
        ("pricelistset", "Tambah atau ubah paket harga premium"),
        ("pricelistdel", "Hapus paket harga premium"),
        ("kantor", "Diskusi tim agen AI dan eksekusi aksi"),
        ("staf", "Lihat anggota tim agen AI"),
        ("pecat", "Keluarkan anggota rekrutan tim"),
        ("usulan", "Lihat usulan fitur dari tim"),
        ("laporan", "Kirim laporan kantor ke email"),
        ("jadwal", "Lihat pekerjaan terjadwal"),
        ("batalkanjadwal", "Batalkan pekerjaan terjadwal"),
    ],
}


def perintah_ada(nama):
  return nama in PERINTAH_OWNER or tree.get_command(nama) is not None


def kategori_help(pemilik):
  hasil = {}
  for nama, daftar in HELP_KATEGORI.items():
    if nama == KATEGORI_OWNER and not pemilik:
      continue
    isi = [(cmd, ket) for cmd, ket in daftar if perintah_ada(cmd)]
    if isi:
      hasil[nama] = isi
  return hasil


def embed_help_beranda(kategori):
  embed = discord.Embed(
      title="Bantuan RyHanC",
      description=(
          "Satu bot untuk membangun dan mengelola server komunitas maupun"
          " jualan.\n\nPilih kategori di menu bawah untuk melihat daftar"
          " perintahnya."
      ),
      color=discord.Color.blurple(),
  )
  for nama, daftar in kategori.items():
    embed.add_field(name=nama, value=f"{len(daftar)} perintah", inline=True)
  embed.set_footer(text="ryhanc.wtf")
  return embed


def embed_help_kategori(kategori, nama):
  isi = "\n".join(f"**/{cmd}**\n{ket}" for cmd, ket in kategori[nama])
  embed = discord.Embed(
      title=f"Bantuan - {nama}",
      description=isi[:4000],
      color=discord.Color.blurple(),
  )
  if nama == KATEGORI_OWNER:
    embed.set_footer(text="Hanya muncul di server pribadi pemilik bot")
  else:
    embed.set_footer(
        text="Perintah bertanda admin hanya terlihat oleh admin server"
    )
  return embed


class HelpSelect(discord.ui.Select):

  def __init__(self, kategori):
    self.kategori = kategori
    opsi = [
        discord.SelectOption(
            label="Beranda",
            value="__beranda__",
            description="Kembali ke halaman utama",
        )
    ]
    for nama in kategori:
      opsi.append(discord.SelectOption(label=nama, value=nama))
    super().__init__(placeholder="Pilih kategori perintah", options=opsi)

  async def callback(self, interaction: discord.Interaction):
    pilihan = self.values[0]
    if pilihan == "__beranda__":
      embed = embed_help_beranda(self.kategori)
    else:
      embed = embed_help_kategori(self.kategori, pilihan)
    await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):

  def __init__(self, kategori):
    super().__init__(timeout=180)
    self.add_item(HelpSelect(kategori))


@tree.command(name="help", description="Lihat semua fitur dan perintah bot")
async def help_command(interaction: discord.Interaction):
  kategori = kategori_help(interaction.user.id == PEMILIK_ID)
  await interaction.response.send_message(
      embed=embed_help_beranda(kategori),
      view=HelpView(kategori),
      ephemeral=True,
  )
