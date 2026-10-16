import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

const RUANG = {
  m: { x0: -12.8, x1: -4.4, z0: -7.1, z1: 2.1, nama: "Ruang Marketing" },
  t: { x0: -4.4, x1: 4.4, z0: -7.1, z1: 2.1, nama: "Ruang Rapat" },
  s: { x0: 4.4, x1: 12.8, z0: -7.1, z1: 2.1, nama: "Software House" },
  e: { x0: -12.8, x1: 12.8, z0: 2.1, z1: 7.1, nama: "Ruang Eksekutor" },
  b: { x0: -12.8, x1: 12.8, z0: 7.1, z1: 12.1, nama: "Ruang Tim Baru" }
};
const PUSAT_MEJA = { x: 0, z: -2.8 };
const SUDUT_KURSI = [-Math.PI / 2, Math.PI / 2, 0, -2.4, 2.4, -0.8, 0.8];
const KURSI = SUDUT_KURSI.map(function (a) {
  return { x: PUSAT_MEJA.x + Math.sin(a) * 2.05, z: PUSAT_MEJA.z + Math.cos(a) * 2.05, arah: a + Math.PI };
});
const RUMAH = {
  m: { x: -8.6, z: -3.3, arah: Math.PI },
  s: { x: 8.6, z: -3.3, arah: Math.PI },
  e: { x: 0, z: 3.35, arah: 0 }
};
const KURSI_B = [];
for (let i = 0; i < 10; i++) {
  const sisi = i % 2;
  KURSI_B.push({ x: -5 + Math.floor(i / 2) * 2.5, z: sisi ? 10.55 : 8.65, arah: sisi ? Math.PI : 0 });
}
const KULIT = ["#c68b62", "#b37650", "#d9a77f", "#9c6542", "#e0b591", "#a86e4a"];
const RAMBUT = ["#1d140e", "#0f0f14", "#5a3a26", "#2a1d16", "#14141c", "#6b4a2b"];
const CELANA = ["#262b38", "#30343c", "#3c4250", "#4a3f33", "#20242e", "#353a46"];
const AGEN = {
  pranowo: { nama: "Pranowo", warna: "#e8a317", ruang: "m", kursi: 0, rambut: RAMBUT[0], kulit: KULIT[0], celana: CELANA[0], gaya: "pendek" },
  manager: { nama: "Manager", warna: "#2f9e6f", ruang: "s", kursi: 1, rambut: RAMBUT[1], kulit: KULIT[1], celana: CELANA[1], gaya: "rapi" },
  chatai: { nama: "Chat AI", warna: "#3b82c4", ruang: "e", kursi: 2, rambut: RAMBUT[2], kulit: KULIT[2], celana: CELANA[2], gaya: "panjang", kacamata: true }
};
const PEKERJA = [
  { k: "pranowo", nama: "Pranowo", peran: "marketing manager", bg: "#ff5a1f", fg: "#14161d" },
  { k: "manager", nama: "Manager", peran: "software house manager", bg: "#1f3dff", fg: "#ffffff" },
  { k: "chatai", nama: "Chat AI", peran: "eksekutor", bg: "#10172e", fg: "#ffffff" },
  { k: "recruit", nama: "Recruit", peran: "analis sumber daya", bg: "#f4efe6", fg: "#14161d" },
  { k: "devops", nama: "Devops", peran: "devops engineer", bg: "#0f8a5f", fg: "#ffffff" },
  { k: "sentiment", nama: "Sentiment", peran: "analis sentimen", bg: "#6a2cff", fg: "#ffffff" }
];
const BATAS_GELEMBUNG = 25000;
const BATAS_BICARA = 6000;
const LAMA_DI_RAPAT = 15000;
const KECEPATAN = 1.5;

const adegan = document.getElementById("adegan");
const lapisan = document.getElementById("lapisan");
const urutanB = [];
const ag = {};
const terbaru = {};
let menunggu = 0;
let kerja = 0;
let idTerakhir = 0;
let ada3D = false;

let renderer, scene, kamera, kontrol, grupB, sunLight;
const dinding = [];
const layar = [];
const lampuLed = [];
const jarumJam = {};
const efek3D = [];
const labelRuang = [];
let papanTulis = null;
let kameraDigeser = false;
const GEO = {};
const MAT = {};
const vSementara = new THREE.Vector3();
const vKepala = new THREE.Vector3();

function benih(a) {
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashWarna(k) {
  return Array.from(k).reduce(function (a, ch) { return a + ch.charCodeAt(0) * 37; }, 0);
}

function warnaAgen(k) {
  return "hsl(" + (hashWarna(k) % 360) + " 55% 52%)";
}

function geo(kunci, buat) {
  if (!GEO[kunci]) GEO[kunci] = buat();
  return GEO[kunci];
}

function mat(kunci, buat) {
  if (!MAT[kunci]) MAT[kunci] = buat();
  return MAT[kunci];
}

function standar(kunci, warna, kasar, logam, tambahan) {
  return mat(kunci, function () {
    return new THREE.MeshStandardMaterial(Object.assign({ color: warna, roughness: kasar, metalness: logam || 0 }, tambahan || {}));
  });
}

function kanvas(w, h, gambar) {
  const cv = document.createElement("canvas");
  cv.width = w;
  cv.height = h;
  gambar(cv.getContext("2d"), w, h);
  return cv;
}

function tekstur(cv, ulangX, ulangY) {
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace;
  if (renderer) t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  if (ulangX) {
    t.wrapS = THREE.RepeatWrapping;
    t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(ulangX, ulangY);
  }
  return t;
}

function gambarKayu(g, w, h, hue, sat, terang, tinggiPapan, s) {
  const acak = benih(s);
  for (let y = 0; y < h; y += tinggiPapan) {
    let x = -Math.floor(acak() * 220);
    while (x < w) {
      const p = 180 + Math.floor(acak() * 220);
      g.fillStyle = "hsl(" + (hue + (acak() - 0.5) * 6) + " " + sat + "% " + (terang + (acak() - 0.5) * 9) + "%)";
      g.fillRect(x, y, p, tinggiPapan);
      for (let i = 0; i < 16; i++) {
        g.strokeStyle = "rgba(50,25,8," + (0.03 + acak() * 0.09) + ")";
        g.lineWidth = 0.6 + acak() * 1.6;
        const yy = y + acak() * tinggiPapan;
        g.beginPath();
        g.moveTo(x, yy);
        g.bezierCurveTo(x + p * 0.3, yy + (acak() - 0.5) * 9, x + p * 0.7, yy + (acak() - 0.5) * 9, x + p, yy + (acak() - 0.5) * 4);
        g.stroke();
      }
      g.fillStyle = "rgba(25,12,4,.45)";
      g.fillRect(x, y, 2, tinggiPapan);
      x += p;
    }
    g.fillStyle = "rgba(25,12,4,.5)";
    g.fillRect(0, y, w, 2);
  }
}

function gambarBintik(g, w, h, dasar, jumlah, kuat, s) {
  const acak = benih(s);
  g.fillStyle = dasar;
  g.fillRect(0, 0, w, h);
  for (let i = 0; i < jumlah; i++) {
    const v = acak();
    g.fillStyle = v > 0.5 ? "rgba(255,255,255," + kuat * acak() + ")" : "rgba(0,0,0," + kuat * acak() + ")";
    g.fillRect(acak() * w, acak() * h, 1 + acak() * 2, 1 + acak() * 2);
  }
}

function gambarBeton(g, w, h, s) {
  const acak = benih(s);
  g.fillStyle = "#5d616b";
  g.fillRect(0, 0, w, h);
  for (let i = 0; i < 60; i++) {
    const x = acak() * w, y = acak() * h, r = 30 + acak() * 120;
    const gr = g.createRadialGradient(x, y, 0, x, y, r);
    const terang = acak() > 0.5;
    gr.addColorStop(0, terang ? "rgba(255,255,255,.07)" : "rgba(0,0,0,.08)");
    gr.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = gr;
    g.fillRect(x - r, y - r, r * 2, r * 2);
  }
  for (let i = 0; i < 9000; i++) {
    g.fillStyle = "rgba(" + (acak() > 0.5 ? "255,255,255" : "0,0,0") + "," + acak() * 0.08 + ")";
    g.fillRect(acak() * w, acak() * h, 1, 1);
  }
  g.strokeStyle = "rgba(0,0,0,.25)";
  g.lineWidth = 2;
  g.strokeRect(0, 0, w, h);
}

function gambarUbin(g, w, h, s) {
  const acak = benih(s);
  const n = 4, u = w / n;
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const l = 86 + (acak() - 0.5) * 4;
      g.fillStyle = "hsl(32 12% " + l + "%)";
      g.fillRect(i * u, j * u, u, u);
      for (let k = 0; k < 5; k++) {
        g.strokeStyle = "rgba(120,110,100," + (0.05 + acak() * 0.08) + ")";
        g.lineWidth = 0.5 + acak();
        g.beginPath();
        const x0 = i * u + acak() * u, y0 = j * u;
        g.moveTo(x0, y0);
        g.bezierCurveTo(x0 + (acak() - 0.5) * u, y0 + u * 0.3, x0 + (acak() - 0.5) * u, y0 + u * 0.7, x0 + (acak() - 0.5) * u * 0.6, y0 + u);
        g.stroke();
      }
    }
  }
  g.fillStyle = "rgba(90,80,70,.55)";
  for (let i = 0; i <= n; i++) {
    g.fillRect(i * u - 1, 0, 2, h);
    g.fillRect(0, i * u - 1, w, 2);
  }
}

function lantai(R, cv, ukuran, kasar, y) {
  const w = R.x1 - R.x0, d = R.z1 - R.z0;
  const t = tekstur(cv, w / ukuran, d / ukuran);
  const me = new THREE.Mesh(new THREE.PlaneGeometry(w, d), new THREE.MeshStandardMaterial({ map: t, roughness: kasar, metalness: 0 }));
  me.rotation.x = -Math.PI / 2;
  me.position.set((R.x0 + R.x1) / 2, y || 0, (R.z0 + R.z1) / 2);
  return me;
}

function kotak(w, h, d, bahan, x, y, z, r) {
  const g = r ? geo("rb" + w + "_" + h + "_" + d + "_" + r, function () { return new RoundedBoxGeometry(w, h, d, 3, r); }) : geo("b" + w + "_" + h + "_" + d, function () { return new THREE.BoxGeometry(w, h, d); });
  const me = new THREE.Mesh(g, bahan);
  me.position.set(x || 0, y || 0, z || 0);
  return me;
}

function silinder(rA, rB, h, bahan, x, y, z, seg) {
  const g = geo("c" + rA + "_" + rB + "_" + h + "_" + (seg || 24), function () { return new THREE.CylinderGeometry(rA, rB, h, seg || 24); });
  const me = new THREE.Mesh(g, bahan);
  me.position.set(x || 0, y || 0, z || 0);
  return me;
}

function bola(r, bahan, x, y, z) {
  const g = geo("s" + r, function () { return new THREE.SphereGeometry(r, 20, 14); });
  const me = new THREE.Mesh(g, bahan);
  me.position.set(x || 0, y || 0, z || 0);
  return me;
}

function bahanDasar() {
  const kayuMeja = new THREE.MeshPhysicalMaterial({
    map: tekstur(kanvas(512, 256, function (g, w, h) { gambarKayu(g, w, h, 30, 42, 52, 256, 11); })),
    roughness: 0.42, clearcoat: 0.35, clearcoatRoughness: 0.35
  });
  MAT.kayuMeja = kayuMeja;
  MAT.kayuGelap = new THREE.MeshPhysicalMaterial({
    map: tekstur(kanvas(512, 256, function (g, w, h) { gambarKayu(g, w, h, 24, 38, 28, 256, 12); })),
    roughness: 0.5, clearcoat: 0.2
  });
  standar("logamGelap", "#25282f", 0.35, 0.85);
  standar("logamTerang", "#c8ccd3", 0.28, 0.9);
  standar("hitamDof", "#16181d", 0.6, 0.1);
  standar("putih", "#efece6", 0.55, 0);
  standar("plester", "#e6dccf", 0.92, 0);
  standar("plint", "#3b3330", 0.6, 0);
  standar("keramik", "#f3efe8", 0.25, 0);
  standar("tanah", "#3a2a1f", 1, 0);
  standar("terakota", "#b8643f", 0.75, 0);
  MAT.kainKursi = new THREE.MeshPhysicalMaterial({ color: "#2e3442", roughness: 0.85, sheen: 1, sheenRoughness: 0.7, sheenColor: new THREE.Color("#7d8aa8") });
  MAT.kainKursiRapat = new THREE.MeshPhysicalMaterial({ color: "#a8552f", roughness: 0.85, sheen: 1, sheenRoughness: 0.7, sheenColor: new THREE.Color("#ffb38a") });
  MAT.kainSofa = new THREE.MeshPhysicalMaterial({ color: "#56677a", roughness: 0.9, sheen: 1, sheenRoughness: 0.6, sheenColor: new THREE.Color("#b8c8d8") });
  MAT.kaca = new THREE.MeshPhysicalMaterial({ color: "#d8ecff", roughness: 0.04, metalness: 0, transparent: true, opacity: 0.16, envMapIntensity: 1.6, depthWrite: false, side: THREE.DoubleSide });
  MAT.kaca.userData.tanpaBayangan = true;
  ["#3f8f4e", "#2f7a43", "#56a55f", "#2a6b3c"].forEach(function (w, i) {
    standar("daun" + i, w, 0.55, 0, { side: THREE.DoubleSide });
  });
}

function buatLayar(jenis, s) {
  const cv = document.createElement("canvas");
  cv.width = 384;
  cv.height = 240;
  const g = cv.getContext("2d");
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  const acak = benih(s);
  const warna = ["#ff7eb6", "#9ad1ff", "#ffd27a", "#8be9a5", "#c8a2ff", "#7fdbff"];
  const baris = [];
  for (let i = 0; i < 48; i++) {
    const potong = [];
    const n = 1 + Math.floor(acak() * 4);
    for (let j = 0; j < n; j++) potong.push({ w: 10 + acak() * 52, c: Math.floor(acak() * warna.length) });
    baris.push({ ind: Math.floor(acak() * 4), potong: potong });
  }
  function gambar(t) {
    if (jenis === "grafik") {
      g.fillStyle = "#0e1624";
      g.fillRect(0, 0, 384, 240);
      g.fillStyle = "#162238";
      g.fillRect(0, 0, 384, 26);
      g.fillStyle = "#ffb35c";
      g.fillRect(12, 9, 60, 8);
      for (let i = 0; i < 3; i++) {
        g.fillStyle = "#1b2a44";
        g.fillRect(12 + i * 122, 36, 112, 46);
        g.fillStyle = warna[i + 1];
        g.fillRect(22 + i * 122, 46, 40, 6);
        g.fillStyle = "#e9eef8";
        g.fillRect(22 + i * 122, 60, 30 + ((Math.floor(t / 900) + i * 7) % 5) * 10, 12);
      }
      g.fillStyle = "#1b2a44";
      g.fillRect(12, 92, 360, 136);
      for (let i = 0; i < 12; i++) {
        const hgt = 30 + (Math.sin(t / 1400 + i * 0.7) * 0.5 + 0.5) * 70;
        g.fillStyle = i % 3 === 0 ? "#ff9a3c" : "#4f7cff";
        g.fillRect(26 + i * 28, 216 - hgt, 16, hgt);
      }
      g.strokeStyle = "#8be9a5";
      g.lineWidth = 3;
      g.beginPath();
      for (let i = 0; i < 14; i++) {
        const yy = 150 - Math.sin(t / 1800 + i * 0.55) * 30 - i * 2;
        if (i === 0) g.moveTo(22 + i * 26, yy);
        else g.lineTo(22 + i * 26, yy);
      }
      g.stroke();
    } else if (jenis === "terminal") {
      g.fillStyle = "#06090a";
      g.fillRect(0, 0, 384, 240);
      const cepat = kerja && Date.now() - kerja < 90000 ? 160 : 700;
      const geser = Math.floor(t / cepat);
      for (let i = 0; i < 16; i++) {
        const b = baris[(geser + i) % baris.length];
        g.fillStyle = "#3ddc84";
        g.fillRect(10, 12 + i * 14, 6, 8);
        let x = 22 + b.ind * 10;
        for (const p of b.potong) {
          g.fillStyle = p.c % 2 ? "#3ddc84" : "#a6f5c8";
          g.globalAlpha = 0.85;
          g.fillRect(x, 13 + i * 14, p.w, 6);
          x += p.w + 6;
        }
        g.globalAlpha = 1;
      }
      if (Math.floor(t / 500) % 2) {
        g.fillStyle = "#3ddc84";
        g.fillRect(22, 12 + 16 * 14, 8, 10);
      }
    } else {
      g.fillStyle = "#0f1420";
      g.fillRect(0, 0, 384, 240);
      g.fillStyle = "#181f2e";
      g.fillRect(0, 0, 384, 22);
      ["#ff5f57", "#febc2e", "#28c840"].forEach(function (w, i) {
        g.fillStyle = w;
        g.beginPath();
        g.arc(12 + i * 14, 11, 4, 0, Math.PI * 2);
        g.fill();
      });
      g.fillStyle = "#131a28";
      g.fillRect(0, 22, 70, 218);
      for (let i = 0; i < 10; i++) {
        g.fillStyle = i === 3 ? "#2a3550" : "#1c2436";
        g.fillRect(8, 32 + i * 18, 54, 10);
      }
      const geser = Math.floor(t / 650);
      for (let i = 0; i < 15; i++) {
        const b = baris[(geser + i) % baris.length];
        g.fillStyle = "#3a4560";
        g.fillRect(78, 30 + i * 14, 12, 6);
        let x = 98 + b.ind * 14;
        for (const p of b.potong) {
          g.fillStyle = warna[p.c];
          g.fillRect(x, 30 + i * 14, p.w, 6);
          x += p.w + 5;
        }
      }
      if (Math.floor(t / 500) % 2) {
        g.fillStyle = "#ffffff";
        g.fillRect(98, 30 + 15 * 14, 2, 10);
      }
    }
    tex.needsUpdate = true;
  }
  gambar(0);
  const bahan = new THREE.MeshBasicMaterial({ map: tex, toneMapped: false, color: new THREE.Color(0.86, 0.86, 0.86) });
  bahan.userData.tanpaBayangan = true;
  const item = { bahan: bahan, gambar: gambar };
  layar.push(item);
  return item;
}

function monitor(layarItem, lebar) {
  const L = lebar || 0.62, T = L * 0.6;
  const g = new THREE.Group();
  g.add(kotak(0.24, 0.02, 0.17, MAT.logamGelap, 0, 0.01, 0, 0.008));
  g.add(kotak(0.04, 0.28, 0.025, MAT.logamGelap, 0, 0.15, -0.02));
  g.add(kotak(L, T, 0.03, MAT.hitamDof, 0, 0.3 + T / 2, 0.0, 0.01));
  const sc = new THREE.Mesh(geo("layar" + L, function () { return new THREE.PlaneGeometry(L - 0.03, T - 0.03); }), layarItem.bahan);
  sc.position.set(0, 0.3 + T / 2, 0.016);
  g.add(sc);
  return g;
}

function laptop(layarItem) {
  const g = new THREE.Group();
  g.add(kotak(0.34, 0.016, 0.24, MAT.logamTerang, 0, 0.008, 0, 0.006));
  const tutup = new THREE.Group();
  tutup.position.set(0, 0.016, -0.12);
  tutup.rotation.x = -0.25;
  tutup.add(kotak(0.34, 0.22, 0.01, MAT.logamTerang, 0, 0.11, 0, 0.004));
  const sc = new THREE.Mesh(geo("layarLaptop", function () { return new THREE.PlaneGeometry(0.31, 0.19); }), layarItem.bahan);
  sc.position.set(0, 0.11, 0.0056);
  tutup.add(sc);
  g.add(tutup);
  return g;
}

function kursiKantor(bahanKain) {
  const g = new THREE.Group();
  for (let i = 0; i < 5; i++) {
    const a = (i / 5) * Math.PI * 2;
    const kaki = kotak(0.3, 0.025, 0.04, MAT.logamGelap, Math.sin(a) * 0.15, 0.06, Math.cos(a) * 0.15);
    kaki.rotation.y = a + Math.PI / 2;
    g.add(kaki);
    g.add(bola(0.025, MAT.hitamDof, Math.sin(a) * 0.29, 0.025, Math.cos(a) * 0.29));
  }
  g.add(silinder(0.025, 0.025, 0.3, MAT.logamTerang, 0, 0.22, 0, 12));
  g.add(kotak(0.5, 0.07, 0.48, bahanKain, 0, 0.42, 0, 0.03));
  g.add(kotak(0.06, 0.4, 0.04, MAT.logamGelap, 0, 0.55, -0.24));
  const sandaran = kotak(0.46, 0.5, 0.07, bahanKain, 0, 0.85, -0.27, 0.03);
  sandaran.rotation.x = -0.08;
  g.add(sandaran);
  g.add(kotak(0.04, 0.03, 0.26, MAT.hitamDof, -0.27, 0.62, -0.02, 0.012));
  g.add(kotak(0.04, 0.03, 0.26, MAT.hitamDof, 0.27, 0.62, -0.02, 0.012));
  g.add(kotak(0.02, 0.18, 0.02, MAT.logamGelap, -0.27, 0.52, -0.08));
  g.add(kotak(0.02, 0.18, 0.02, MAT.logamGelap, 0.27, 0.52, -0.08));
  return g;
}

function tanaman(skala, jenis, s) {
  const acak = benih(s || 3);
  const g = new THREE.Group();
  const pot = jenis === 1 ? MAT.terakota : MAT.keramik;
  g.add(silinder(0.2, 0.15, 0.38, pot, 0, 0.19, 0, 24));
  g.add(silinder(0.185, 0.185, 0.02, MAT.tanah, 0, 0.37, 0, 20));
  const daunGeo = geo("daun", function () {
    const sp = new THREE.SphereGeometry(1, 12, 8);
    sp.scale(0.06, 0.32, 0.014);
    sp.translate(0, 0.3, 0);
    return sp;
  });
  const n = jenis === 2 ? 9 : 14;
  for (let i = 0; i < n; i++) {
    const d = new THREE.Mesh(daunGeo, MAT["daun" + (i % 4)]);
    const a = (i / n) * Math.PI * 2 + acak() * 0.5;
    d.position.set(Math.sin(a) * 0.05, 0.36, Math.cos(a) * 0.05);
    d.rotation.set(Math.cos(a) * (0.25 + acak() * 0.5), a, -Math.sin(a) * (0.25 + acak() * 0.5));
    const sk = jenis === 2 ? 1.6 + acak() * 0.6 : 0.8 + acak() * 0.6;
    d.scale.set(jenis === 2 ? 0.6 : 1.4, sk, 1);
    g.add(d);
  }
  if (jenis !== 2) {
    for (let i = 0; i < 5; i++) {
      const b = bola(0.13, MAT["daun" + (i % 4)], (acak() - 0.5) * 0.25, 0.75 + acak() * 0.35, (acak() - 0.5) * 0.25);
      b.scale.set(1, 0.85, 1);
      g.add(b);
    }
  }
  g.scale.setScalar(skala);
  return g;
}

function mejaKerja(kursi, isi, kursiBahan) {
  const g = new THREE.Group();
  g.position.set(kursi.x, 0, kursi.z);
  g.rotation.y = kursi.arah - Math.PI;
  const m = new THREE.Group();
  m.position.z = -0.78;
  g.add(m);
  m.add(kotak(1.7, 0.045, 0.78, MAT.kayuMeja, 0, 0.74, 0, 0.012));
  m.add(kotak(0.05, 0.72, 0.66, MAT.logamGelap, -0.78, 0.36, 0, 0.01));
  m.add(kotak(0.05, 0.72, 0.66, MAT.logamGelap, 0.78, 0.36, 0, 0.01));
  m.add(kotak(1.5, 0.3, 0.02, MAT.logamGelap, 0, 0.55, -0.3));
  m.add(kotak(0.42, 0.55, 0.6, MAT.putih, 0.55, 0.3, -0.02, 0.015));
  m.add(kotak(0.38, 0.01, 0.01, MAT.logamTerang, 0.55, 0.45, 0.285));
  m.add(kotak(0.38, 0.01, 0.01, MAT.logamTerang, 0.55, 0.25, 0.285));
  if (isi.monitor) {
    const n = isi.monitor.length;
    isi.monitor.forEach(function (l, i) {
      const mo = monitor(l);
      mo.position.set((i - (n - 1) / 2) * 0.66, 0.765, -0.2);
      mo.rotation.y = (i - (n - 1) / 2) * -0.22;
      m.add(mo);
    });
  }
  if (isi.laptop) {
    const lp = laptop(isi.laptop);
    lp.position.set(0, 0.765, 0.02);
    m.add(lp);
  } else {
    m.add(kotak(0.44, 0.018, 0.14, MAT.hitamDof, 0, 0.772, 0.18, 0.006));
    m.add(bola(0.025, MAT.hitamDof, 0.36, 0.775, 0.18));
  }
  m.add(silinder(0.04, 0.035, 0.1, MAT.keramik, -0.65, 0.815, 0.12, 16));
  const tn = tanaman(0.45, 0, kursi.x * 13);
  tn.position.set(-0.72, 0.765, -0.24);
  m.add(tn);
  const k = kursiKantor(kursiBahan || MAT.kainKursi);
  k.rotation.y = Math.PI;
  g.add(k);
  return g;
}

function sofa() {
  const g = new THREE.Group();
  g.add(kotak(2.1, 0.22, 0.9, MAT.kainSofa, 0, 0.2, 0, 0.06));
  g.add(kotak(2.1, 0.6, 0.22, MAT.kainSofa, 0, 0.55, -0.36, 0.08));
  g.add(kotak(0.2, 0.52, 0.9, MAT.kainSofa, -1.0, 0.36, 0, 0.08));
  g.add(kotak(0.2, 0.52, 0.9, MAT.kainSofa, 1.0, 0.36, 0, 0.08));
  for (let i = 0; i < 2; i++) g.add(kotak(0.86, 0.14, 0.66, MAT.kainSofa, -0.44 + i * 0.88, 0.37, 0.08, 0.06));
  for (let i = 0; i < 4; i++) {
    g.add(silinder(0.025, 0.02, 0.1, MAT.kayuGelap, -0.95 + (i % 2) * 1.9, 0.05, -0.35 + Math.floor(i / 2) * 0.7, 10));
  }
  const bantal = kotak(0.4, 0.38, 0.12, standar("bantal", "#e3a35b", 0.9, 0), -0.6, 0.62, -0.18, 0.05);
  bantal.rotation.set(-0.2, 0.15, 0.1);
  g.add(bantal);
  return g;
}

function rakBuku(s) {
  const acak = benih(s);
  const g = new THREE.Group();
  g.add(kotak(1.3, 2.0, 0.04, MAT.kayuGelap, 0, 1.0, -0.17));
  g.add(kotak(0.04, 2.0, 0.38, MAT.kayuGelap, -0.63, 1.0, 0));
  g.add(kotak(0.04, 2.0, 0.38, MAT.kayuGelap, 0.63, 1.0, 0));
  const warna = ["#a8552f", "#2f5d8a", "#e3c27a", "#3e6b4f", "#7a3b52", "#d9d2c3", "#20242e"];
  for (let r = 0; r < 5; r++) {
    const y = 0.04 + r * 0.48;
    g.add(kotak(1.26, 0.03, 0.36, MAT.kayuGelap, 0, y, 0));
    if (r === 4) continue;
    let x = -0.58;
    while (x < 0.5) {
      const t = 0.24 + acak() * 0.14, l = 0.03 + acak() * 0.04;
      if (acak() > 0.85) {
        x += 0.12;
        continue;
      }
      const iw = Math.floor(acak() * warna.length);
      const b = kotak(l, t, 0.24, standar("buku" + iw, warna[iw], 0.8, 0), x + l / 2, y + 0.015 + t / 2, 0.02);
      g.add(b);
      x += l + 0.005;
    }
  }
  return g;
}

function rakServer(i) {
  const g = new THREE.Group();
  g.add(kotak(0.62, 2.0, 0.9, standar("server", "#1b1e25", 0.4, 0.6), 0, 1.0, 0, 0.02));
  for (let u = 0; u < 9; u++) {
    const y = 0.25 + u * 0.19;
    g.add(kotak(0.54, 0.15, 0.02, standar("serverPanel", "#2a2e38", 0.5, 0.5), 0, y, 0.452));
    for (let j = 0; j < 3; j++) {
      const bahan = new THREE.MeshStandardMaterial({ color: "#0a0a0a", emissive: j === 2 ? "#ff9a3c" : "#3ddc84", emissiveIntensity: 1, roughness: 0.3 });
      bahan.userData.tanpaBayangan = true;
      bahan.userData.fase = i * 31 + u * 7 + j * 3;
      lampuLed.push(bahan);
      g.add(kotak(0.022, 0.022, 0.01, bahan, 0.18 + j * 0.035, y, 0.465));
    }
  }
  return g;
}

function lampuLantai(cahaya) {
  const g = new THREE.Group();
  g.add(silinder(0.16, 0.18, 0.03, MAT.logamGelap, 0, 0.015, 0, 24));
  g.add(silinder(0.012, 0.012, 1.5, MAT.logamGelap, 0, 0.77, 0, 10));
  const kap = new THREE.MeshStandardMaterial({ color: "#f5e6cc", emissive: "#ffcf8a", emissiveIntensity: 0.9, roughness: 0.8, side: THREE.DoubleSide });
  kap.userData.tanpaBayangan = true;
  g.add(silinder(0.14, 0.22, 0.28, kap, 0, 1.58, 0, 24));
  if (cahaya) {
    const l = new THREE.PointLight("#ffbf75", 7, 7, 2);
    l.position.set(0, 1.5, 0);
    g.add(l);
  }
  return g;
}

function karpet(r, warnaA, warnaB) {
  const cv = kanvas(512, 512, function (g, w) {
    const c = w / 2;
    for (let i = 0; i < 12; i++) {
      g.fillStyle = i % 2 ? warnaA : warnaB;
      g.beginPath();
      g.arc(c, c, c - i * (c / 12), 0, Math.PI * 2);
      g.fill();
    }
    const acak = benih(77);
    for (let i = 0; i < 20000; i++) {
      g.fillStyle = "rgba(0,0,0," + acak() * 0.12 + ")";
      g.fillRect(acak() * w, acak() * w, 1, 1);
    }
  });
  const me = new THREE.Mesh(new THREE.CircleGeometry(r, 64), new THREE.MeshStandardMaterial({ map: tekstur(cv), roughness: 1 }));
  me.rotation.x = -Math.PI / 2;
  me.position.y = 0.006;
  return me;
}

function gambarLangit(g, w, h) {
  const gr = g.createLinearGradient(0, 0, 0, h);
  gr.addColorStop(0, "#6d8fc9");
  gr.addColorStop(0.45, "#f7d08a");
  gr.addColorStop(0.75, "#f2a65a");
  gr.addColorStop(1, "#e8805a");
  g.fillStyle = gr;
  g.fillRect(0, 0, w, h);
  const mt = g.createRadialGradient(w * 0.62, h * 0.68, 0, w * 0.62, h * 0.68, h * 0.5);
  mt.addColorStop(0, "rgba(255,248,210,1)");
  mt.addColorStop(0.15, "rgba(255,230,160,.9)");
  mt.addColorStop(1, "rgba(255,200,120,0)");
  g.fillStyle = mt;
  g.fillRect(0, 0, w, h);
  const acak = benih(5);
  let x = 0;
  while (x < w) {
    const bw = 20 + acak() * 40, bh = h * (0.12 + acak() * 0.3);
    g.fillStyle = "rgba(58,40,72," + (0.75 + acak() * 0.2) + ")";
    g.fillRect(x, h - bh, bw, bh);
    for (let i = 0; i < 12; i++) {
      if (acak() > 0.6) {
        g.fillStyle = "rgba(255,214,140,.8)";
        g.fillRect(x + 4 + acak() * (bw - 8), h - bh + 6 + acak() * (bh - 12), 3, 3);
      }
    }
    x += bw + 2;
  }
}

function jendela(lebar, tinggi) {
  const g = new THREE.Group();
  const langit = mat("langit", function () {
    const b = new THREE.MeshBasicMaterial({ map: tekstur(kanvas(512, 320, gambarLangit)), toneMapped: false });
    b.userData.tanpaBayangan = true;
    return b;
  });
  const sky = new THREE.Mesh(new THREE.PlaneGeometry(lebar, tinggi), langit);
  sky.position.z = 0.002;
  g.add(sky);
  const kaca = new THREE.Mesh(new THREE.PlaneGeometry(lebar, tinggi), MAT.kaca);
  kaca.position.z = 0.03;
  g.add(kaca);
  const f = 0.06;
  g.add(kotak(lebar + f * 2, f, 0.08, MAT.logamGelap, 0, tinggi / 2 + f / 2, 0.03));
  g.add(kotak(lebar + f * 2, f, 0.08, MAT.logamGelap, 0, -tinggi / 2 - f / 2, 0.03));
  g.add(kotak(f, tinggi, 0.08, MAT.logamGelap, -lebar / 2 - f / 2, 0, 0.03));
  g.add(kotak(f, tinggi, 0.08, MAT.logamGelap, lebar / 2 + f / 2, 0, 0.03));
  g.add(kotak(0.035, tinggi, 0.06, MAT.logamGelap, 0, 0, 0.03));
  g.add(kotak(lebar + 0.3, 0.05, 0.22, MAT.putih, 0, -tinggi / 2 - 0.08, 0.1, 0.01));
  return g;
}

function lukisan(s, w, h) {
  const acak = benih(s);
  const cv = kanvas(256, Math.round((256 * h) / w), function (g, cw, ch) {
    g.fillStyle = "#f1ebe0";
    g.fillRect(0, 0, cw, ch);
    const palet = ["#ff5a1f", "#1f3dff", "#ffb35c", "#14161d", "#2f9e6f", "#e8805a"];
    for (let i = 0; i < 6; i++) {
      g.fillStyle = palet[Math.floor(acak() * palet.length)];
      g.globalAlpha = 0.85;
      if (acak() > 0.5) {
        g.beginPath();
        g.arc(acak() * cw, acak() * ch, 20 + acak() * 60, 0, Math.PI * 2);
        g.fill();
      } else {
        g.fillRect(acak() * cw * 0.7, acak() * ch * 0.7, 30 + acak() * 90, 20 + acak() * 70);
      }
    }
    g.globalAlpha = 1;
  });
  const g = new THREE.Group();
  g.add(kotak(w + 0.08, h + 0.08, 0.04, MAT.hitamDof, 0, 0, 0.02));
  const p = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({ map: tekstur(cv), roughness: 0.8 }));
  p.position.z = 0.042;
  g.add(p);
  return g;
}

function gambarPapan(teks) {
  if (!papanTulis) return;
  const g = papanTulis.g, w = 1024, h = 512;
  g.fillStyle = "#fbfbf8";
  g.fillRect(0, 0, w, h);
  const kilau = g.createLinearGradient(0, 0, w, h);
  kilau.addColorStop(0, "rgba(255,255,255,0)");
  kilau.addColorStop(0.5, "rgba(220,226,235,.35)");
  kilau.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = kilau;
  g.fillRect(0, 0, w, h);
  g.fillStyle = "#c0392b";
  g.font = "700 64px Caveat, 'Comic Sans MS', cursive";
  g.textBaseline = "top";
  g.fillText("Keputusan tim", 48, 30);
  g.strokeStyle = "#c0392b";
  g.lineWidth = 4;
  g.beginPath();
  g.moveTo(48, 104);
  g.quadraticCurveTo(250, 96, 420, 106);
  g.stroke();
  g.fillStyle = "#1d3b8f";
  g.font = "600 46px Caveat, 'Comic Sans MS', cursive";
  const kata = String(teks || "").split(/\s+/);
  const barisTeks = [];
  let kini = "";
  for (const k of kata) {
    const coba = kini ? kini + " " + k : k;
    if (g.measureText(coba).width > w - 110) {
      barisTeks.push(kini);
      kini = k;
    } else kini = coba;
  }
  if (kini) barisTeks.push(kini);
  barisTeks.slice(0, 7).forEach(function (b, i) {
    let tx = b;
    if (i === 6 && barisTeks.length > 7) tx = b + " ...";
    g.fillText(tx, 56, 130 + i * 52);
  });
  papanTulis.tex.needsUpdate = true;
}

function buatPapanTulis() {
  const cv = document.createElement("canvas");
  cv.width = 1024;
  cv.height = 512;
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  papanTulis = { g: cv.getContext("2d"), tex: tex, teks: "Belum ada keputusan." };
  gambarPapan(papanTulis.teks);
  if (document.fonts && document.fonts.load) {
    document.fonts.load("600 46px Caveat").then(function () { gambarPapan(papanTulis.teks); }).catch(function () {});
  }
  const g = new THREE.Group();
  g.add(kotak(3.5, 1.8, 0.05, MAT.logamTerang, 0, 0, 0.025, 0.012));
  const p = new THREE.Mesh(new THREE.PlaneGeometry(3.4, 1.7), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.25 }));
  p.position.z = 0.052;
  g.add(p);
  g.add(kotak(1.2, 0.04, 0.08, MAT.logamTerang, 0.6, -0.92, 0.06));
  g.add(kotak(0.14, 0.025, 0.025, standar("spidol", "#c0392b", 0.4, 0), 0.3, -0.89, 0.07));
  g.add(kotak(0.14, 0.025, 0.025, standar("spidol2", "#1d3b8f", 0.4, 0), 0.5, -0.89, 0.07));
  return g;
}

function jam() {
  const g = new THREE.Group();
  const muka = kanvas(256, 256, function (c) {
    c.fillStyle = "#fbfaf6";
    c.beginPath();
    c.arc(128, 128, 126, 0, Math.PI * 2);
    c.fill();
    c.fillStyle = "#1b1d26";
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2;
      c.save();
      c.translate(128 + Math.sin(a) * 104, 128 - Math.cos(a) * 104);
      c.rotate(a);
      c.fillRect(-3, -12, 6, i % 3 ? 14 : 22);
      c.restore();
    }
  });
  const pinggir = new THREE.Mesh(geo("bingkaiJam", function () { return new THREE.TorusGeometry(0.3, 0.03, 12, 48); }), MAT.logamGelap);
  pinggir.position.z = 0.03;
  g.add(pinggir);
  const m = new THREE.Mesh(new THREE.CircleGeometry(0.3, 48), new THREE.MeshStandardMaterial({ map: tekstur(muka), roughness: 0.4 }));
  m.position.z = 0.02;
  g.add(m);
  function jarum(p, l) {
    const pv = new THREE.Group();
    pv.position.z = 0.04;
    const me = kotak(l, p, 0.008, MAT.hitamDof, 0, p * 2.5, 0);
    me.geometry = geo("jarum" + l + p, function () { const b = new THREE.BoxGeometry(l, p, 0.008); b.translate(0, p / 2, 0); return b; });
    me.position.set(0, 0, 0);
    me.userData.hidup = true;
    pv.userData.hidup = true;
    pv.add(me);
    g.add(pv);
    return pv;
  }
  jarumJam.j = jarum(0.17, 0.018);
  jarumJam.m = jarum(0.25, 0.012);
  jarumJam.d = jarum(0.27, 0.005);
  return g;
}

function tulisanDinding(teks) {
  const cv = kanvas(1024, 256, function (g, w, h) {
    g.clearRect(0, 0, w, h);
    g.fillStyle = "#2b2420";
    g.font = "800 150px 'Plus Jakarta Sans', sans-serif";
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.fillText(teks, w / 2, h / 2 + 8);
  });
  const t = tekstur(cv);
  const me = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 0.6), new THREE.MeshStandardMaterial({ map: t, transparent: true, roughness: 0.4, metalness: 0.3 }));
  me.material.userData.tanpaBayangan = true;
  return me;
}

function buatDinding(cx, cz, w, d, nx, nz, aktif) {
  const g = new THREE.Group();
  g.add(kotak(w, 3, d, MAT.plester, cx, 1.5, cz));
  const tebal = nx ? w : d;
  g.add(kotak(nx ? 0.02 : w, 0.1, nx ? d : 0.02, MAT.plint, cx - nx * (tebal / 2 + 0.01), 0.05, cz - nz * (tebal / 2 + 0.01)));
  g.add(kotak(w + 0.02, 0.04, d + 0.02, MAT.plint, cx, 3.0, cz));
  const item = { g: g, n: new THREE.Vector3(nx, 0, nz), c: new THREE.Vector3(cx, 1.5, cz), aktif: aktif || function () { return true; } };
  dinding.push(item);
  return item;
}

function dindingKaca(x, z0, z1) {
  const g = new THREE.Group();
  const L = z1 - z0, cz = (z0 + z1) / 2;
  const k = new THREE.Mesh(new THREE.PlaneGeometry(L, 2.62), MAT.kaca);
  k.rotation.y = Math.PI / 2;
  k.position.set(x, 1.37, cz);
  g.add(k);
  g.add(kotak(0.06, 0.08, L, MAT.logamGelap, x, 0.04, cz));
  g.add(kotak(0.06, 0.08, L, MAT.logamGelap, x, 2.7, cz));
  const n = Math.max(2, Math.round(L / 1.4));
  for (let i = 0; i <= n; i++) g.add(kotak(0.05, 2.66, 0.05, MAT.logamGelap, x, 1.37, z0 + (i / n) * L));
  g.add(kotak(0.03, 0.02, L, standar("stikerKaca", "#ffffff", 0.6, 0, { transparent: true, opacity: 0.5 }), x, 1.1, cz));
  return g;
}

function gabung(grup) {
  grup.updateMatrixWorld(true);
  const balik = new THREE.Matrix4().copy(grup.matrixWorld).invert();
  const kelompok = new Map();
  const buang = [];
  grup.traverse(function (o) {
    if (!o.isMesh) return;
    let p = o;
    while (p && p !== grup) {
      if (p.userData.hidup) return;
      p = p.parent;
    }
    const m = new THREE.Matrix4().multiplyMatrices(balik, o.matrixWorld);
    let gg = o.geometry.index ? o.geometry.toNonIndexed() : o.geometry.clone();
    gg.applyMatrix4(m);
    for (const nm of Object.keys(gg.attributes)) {
      if (nm !== "position" && nm !== "normal" && nm !== "uv") gg.deleteAttribute(nm);
    }
    if (!gg.attributes.uv) gg.setAttribute("uv", new THREE.BufferAttribute(new Float32Array(gg.attributes.position.count * 2), 2));
    if (!gg.attributes.normal) gg.computeVertexNormals();
    gg.morphAttributes = {};
    if (!kelompok.has(o.material)) kelompok.set(o.material, []);
    kelompok.get(o.material).push(gg);
    buang.push(o);
  });
  for (const o of buang) o.parent.remove(o);
  kelompok.forEach(function (daftar, bahan) {
    const g = mergeGeometries(daftar, false);
    daftar.forEach(function (d) { d.dispose(); });
    if (!g) return;
    const me = new THREE.Mesh(g, bahan);
    const tanpa = bahan.userData && bahan.userData.tanpaBayangan;
    me.castShadow = !tanpa && !bahan.transparent;
    me.receiveShadow = !bahan.transparent;
    grup.add(me);
  });
}

function bangunDunia() {
  const statis = new THREE.Group();
  scene.add(statis);
  grupB = new THREE.Group();
  grupB.visible = false;
  scene.add(grupB);

  const tanah = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.MeshStandardMaterial({ color: "#10131a", roughness: 1 }));
  tanah.rotation.x = -Math.PI / 2;
  tanah.position.y = -0.3;
  tanah.receiveShadow = true;
  scene.add(tanah);
  statis.add(kotak(26.0, 0.3, 14.6, standar("lempeng", "#2a2d35", 0.8, 0), 0, -0.151, 0));
  grupB.add(kotak(26.0, 0.3, 5.0, MAT.lempeng, 0, -0.152, 9.6));

  statis.add(lantai(RUANG.m, kanvas(512, 512, function (g, w, h) { gambarKayu(g, w, h, 28, 45, 45, 64, 21); }), 2.6, 0.55));
  statis.add(lantai(RUANG.t, kanvas(512, 512, function (g, w, h) { gambarUbin(g, w, h, 4); }), 3.2, 0.32));
  statis.add(lantai(RUANG.s, kanvas(512, 512, function (g, w, h) { gambarBintik(g, w, h, "#55695e", 26000, 0.12, 8); }), 2.5, 0.95));
  statis.add(lantai(RUANG.e, kanvas(512, 512, function (g, w, h) { gambarBeton(g, w, h, 9); }), 4.5, 0.38));
  grupB.add(lantai(RUANG.b, kanvas(512, 512, function (g, w, h) { gambarKayu(g, w, h, 36, 35, 62, 64, 33); }), 2.6, 0.5));
  statis.add(kotak(25.6, 0.012, 0.06, MAT.logamTerang, 0, 0.006, 2.1));

  const belakang = buatDinding(0, -7.2, 25.96, 0.2, 0, -1);
  const kiri = buatDinding(-12.9, 0, 0.2, 14.6, -1, 0);
  const kanan = buatDinding(12.9, 0, 0.2, 14.6, 1, 0);
  const depanA = buatDinding(0, 7.2, 25.96, 0.2, 0, 1, function () { return !urutanB.length; });
  const kiriB = buatDinding(-12.9, 9.65, 0.2, 4.7, -1, 0, function () { return !!urutanB.length; });
  const kananB = buatDinding(12.9, 9.65, 0.2, 4.7, 1, 0, function () { return !!urutanB.length; });
  const depanB = buatDinding(0, 12.2, 25.96, 0.2, 0, 1, function () { return !!urutanB.length; });

  [-10.6, -6.6, 6.6, 10.6].forEach(function (x) {
    const j = jendela(2.2, 1.4);
    j.position.set(x, 1.75, -7.09);
    belakang.g.add(j);
  });
  [-2.5, 3.5].forEach(function (z) {
    const j = jendela(2.0, 1.4);
    j.position.set(-12.79, 1.75, z === 3.5 ? 4.6 : -4.2);
    j.rotation.y = Math.PI / 2;
    kiri.g.add(j);
  });
  const jk = jendela(2.0, 1.4);
  jk.position.set(12.79, 1.75, 4.6);
  jk.rotation.y = -Math.PI / 2;
  kanan.g.add(jk);

  const pt = buatPapanTulis();
  pt.position.set(0, 1.55, -7.1);
  belakang.g.add(pt);
  const tl = tulisanDinding("RyHanC");
  tl.position.set(0, 2.72, -7.09);
  belakang.g.add(tl);
  const jm = jam();
  jm.position.set(3.1, 2.25, -7.1);
  belakang.g.add(jm);
  const lk1 = lukisan(41, 1.2, 0.9);
  lk1.position.set(-12.79, 1.75, -0.6);
  lk1.rotation.y = Math.PI / 2;
  kiri.g.add(lk1);
  const tv = monitor(buatLayar("grafik", 61), 1.9);
  tv.children.slice(0, 2).forEach(function (c) { tv.remove(c); });
  tv.position.set(12.78, 0.95, -2.2);
  tv.rotation.y = -Math.PI / 2;
  kanan.g.add(tv);
  const lk2 = lukisan(52, 0.9, 1.2);
  lk2.position.set(-12.79, 1.7, 9.6);
  lk2.rotation.y = Math.PI / 2;
  kiriB.g.add(lk2);
  [belakang, kiri, kanan, depanA].forEach(function (d) { statis.add(d.g); });
  [kiriB, kananB, depanB].forEach(function (d) { grupB.add(d.g); });

  statis.add(dindingKaca(-4.4, -7.1, -1.7));
  statis.add(dindingKaca(4.4, -7.1, -1.7));

  const layarKode = buatLayar("kode", 71);
  const layarKode2 = buatLayar("kode", 72);
  const layarGrafik = buatLayar("grafik", 73);
  const layarTerm = buatLayar("terminal", 74);

  statis.add(mejaKerja(RUMAH.m, { monitor: [layarGrafik, layarKode2] }));
  statis.add(mejaKerja(RUMAH.s, { monitor: [layarKode, layarKode2] }));
  statis.add(mejaKerja(RUMAH.e, { monitor: [layarTerm, layarKode, layarTerm] }));
  statis.add(mejaKerja({ x: 6.3, z: -0.1, arah: Math.PI }, { laptop: layarKode }));
  statis.add(mejaKerja({ x: 10.9, z: -0.1, arah: Math.PI }, { laptop: layarKode2 }));

  const sf = sofa();
  sf.position.set(-11.0, 0, -0.3);
  sf.rotation.y = Math.PI / 2;
  statis.add(sf);
  const kp1 = karpet(1.5, "#d8c4a8", "#c9b292");
  kp1.position.set(-9.8, 0.006, -0.3);
  statis.add(kp1);
  const mk = new THREE.Group();
  mk.add(silinder(0.45, 0.45, 0.04, MAT.kayuMeja, 0, 0.42, 0, 32));
  mk.add(silinder(0.04, 0.06, 0.4, MAT.logamGelap, 0, 0.2, 0, 12));
  mk.add(silinder(0.22, 0.22, 0.02, MAT.logamGelap, 0, 0.01, 0, 24));
  mk.add(silinder(0.05, 0.04, 0.1, MAT.keramik, 0.12, 0.49, 0.05, 16));
  mk.position.set(-9.7, 0, -0.3);
  statis.add(mk);
  const ll = lampuLantai(true);
  ll.position.set(-12.3, 0, 1.4);
  statis.add(ll);
  const rb1 = rakBuku(5);
  rb1.position.set(-12.6, 0, -5.6);
  rb1.rotation.y = Math.PI / 2;
  statis.add(rb1);
  const rb2 = rakBuku(9);
  rb2.position.set(12.6, 0, -5.6);
  rb2.rotation.y = -Math.PI / 2;
  statis.add(rb2);

  [[-12.2, -6.6, 1.2, 0], [-5.0, -6.5, 1.0, 2], [5.0, -6.5, 1.0, 2], [12.2, 0.8, 1.2, 1], [-3.8, -6.5, 1.1, 1], [3.8, -6.5, 1.1, 0], [-12.2, 6.5, 1.1, 2], [12.2, 6.5, 1.1, 0], [-4.1, 1.5, 0.9, 1], [4.1, 1.5, 0.9, 1]].forEach(function (p, i) {
    const tn = tanaman(p[2], p[3], 100 + i);
    tn.position.set(p[0], 0, p[1]);
    statis.add(tn);
  });

  const kp2 = karpet(3.2, "#6e5a4b", "#7d6857");
  kp2.position.set(PUSAT_MEJA.x, 0.006, PUSAT_MEJA.z);
  statis.add(kp2);
  const mr = new THREE.Group();
  mr.add(silinder(1.35, 1.35, 0.06, MAT.kayuMeja, 0, 0.74, 0, 64));
  mr.add(silinder(0.12, 0.18, 0.7, MAT.logamGelap, 0, 0.36, 0, 24));
  mr.add(silinder(0.6, 0.65, 0.04, MAT.logamGelap, 0, 0.02, 0, 32));
  const pusatMeja = tanaman(0.5, 2, 9);
  pusatMeja.position.y = 0.77;
  mr.add(pusatMeja);
  for (let i = 0; i < 4; i++) {
    const a = i * 1.6 + 0.3;
    const kertas = kotak(0.21, 0.004, 0.29, MAT.putih, Math.sin(a) * 0.95, 0.772, Math.cos(a) * 0.95);
    kertas.rotation.y = a;
    mr.add(kertas);
  }
  mr.position.set(PUSAT_MEJA.x, 0, PUSAT_MEJA.z);
  statis.add(mr);
  KURSI.forEach(function (k) {
    const c = kursiKantor(MAT.kainKursiRapat);
    c.position.set(k.x, 0, k.z);
    c.rotation.y = k.arah;
    statis.add(c);
  });

  [[-12.6, -10.2], [-6.9, -4.9], [4.9, 6.9], [10.2, 12.6]].forEach(function (r) {
    const w = r[1] - r[0], cx = (r[0] + r[1]) / 2;
    statis.add(kotak(w, 0.5, 0.4, MAT.kayuGelap, cx, 0.25, 2.1, 0.03));
    for (let x = r[0] + 0.3; x < r[1] - 0.1; x += 0.45) {
      const b = bola(0.2, MAT["daun" + (Math.round(x * 7) & 3)], x, 0.62, 2.1);
      b.scale.set(1, 0.7, 0.9);
      statis.add(b);
    }
  });

  [-11.8, -11.1, -10.4, 10.4, 11.1, 11.8].forEach(function (x, i) {
    const r = rakServer(i);
    r.position.set(x, 0, 3.0);
    statis.add(r);
  });
  const dis = new THREE.Group();
  dis.add(kotak(0.34, 1.0, 0.34, MAT.putih, 0, 0.5, 0, 0.03));
  dis.add(silinder(0.14, 0.14, 0.42, standar("galon", "#9fd3ff", 0.1, 0, { transparent: true, opacity: 0.55 }), 0, 1.21, 0, 20));
  dis.position.set(-8.2, 0, 6.6);
  statis.add(dis);
  const ll2 = lampuLantai(true);
  ll2.position.set(8.5, 0, 6.6);
  statis.add(ll2);
  const sf2 = sofa();
  sf2.position.set(5.6, 0, 6.5);
  sf2.rotation.y = Math.PI;
  statis.add(sf2);

  const mb = new THREE.Group();
  mb.add(kotak(12.6, 0.06, 1.2, MAT.kayuMeja, 0, 0.74, 0, 0.02));
  [-5.9, 5.9].forEach(function (x) {
    mb.add(kotak(0.08, 0.72, 1.0, MAT.logamGelap, x, 0.36, 0, 0.01));
  });
  for (let i = 0; i < 5; i++) {
    const tn = tanaman(0.35, 2, 200 + i);
    tn.position.set(-5 + i * 2.5, 0.77, 0);
    mb.add(tn);
  }
  mb.position.set(0, 0, 9.6);
  grupB.add(mb);
  KURSI_B.forEach(function (k) {
    const c = kursiKantor(MAT.kainKursi);
    c.position.set(k.x, 0, k.z);
    c.rotation.y = k.arah;
    grupB.add(c);
  });
  [[-12.2, 7.6], [12.2, 7.6], [-12.2, 11.6], [12.2, 11.6]].forEach(function (p, i) {
    const tn = tanaman(1.1, i % 3, 300 + i);
    tn.position.set(p[0], 0, p[1]);
    grupB.add(tn);
  });

  dinding.forEach(function (d) { gabung(d.g); });
  const sisaStatis = statis.children.filter(function (c) { return dinding.every(function (d) { return d.g !== c; }); });
  const inti = new THREE.Group();
  sisaStatis.forEach(function (c) { inti.add(c); });
  statis.add(inti);
  gabung(inti);
  const sisaB = grupB.children.filter(function (c) { return dinding.every(function (d) { return d.g !== c; }); });
  const intiB = new THREE.Group();
  sisaB.forEach(function (c) { intiB.add(c); });
  grupB.add(intiB);
  gabung(intiB);

  ["m", "t", "s"].forEach(function (k) {
    const R = RUANG[k];
    labelRuang.push(buatLabelRuang(R.nama, new THREE.Vector3((R.x0 + R.x1) / 2, 3.35, -7.2), null));
  });
  labelRuang.push(buatLabelRuang(RUANG.e.nama, new THREE.Vector3(-9.2, 0.05, 6.75), null));
  labelRuang.push(buatLabelRuang(RUANG.b.nama, new THREE.Vector3(-9.2, 0.05, 11.75), function () { return !!urutanB.length; }));
}

function buatLabelRuang(teks, pos, aktif) {
  const el = document.createElement("div");
  el.className = "ruang";
  el.textContent = teks;
  lapisan.appendChild(el);
  return { el: el, pos: pos, aktif: aktif };
}

function buatOrang(o) {
  const kulit = new THREE.MeshStandardMaterial({ color: o.kulit, roughness: 0.55 });
  const baju = new THREE.MeshPhysicalMaterial({ color: o.baju, roughness: 0.75, sheen: 0.8, sheenRoughness: 0.7, sheenColor: new THREE.Color("#ffffff") });
  const celana = new THREE.MeshStandardMaterial({ color: o.celana, roughness: 0.8 });
  const rambut = new THREE.MeshStandardMaterial({ color: o.rambut, roughness: 0.45 });
  const sepatu = standar("sepatu", "#1a1a1e", 0.35, 0.1);
  const gelap = standar("mata", "#141018", 0.2, 0);
  const root = new THREE.Group();
  const tubuh = new THREE.Group();
  root.add(tubuh);
  function m(g, b, x, y, z) {
    const me = new THREE.Mesh(g, b);
    me.position.set(x, y, z);
    me.castShadow = true;
    me.receiveShadow = true;
    return me;
  }
  tubuh.add(m(geo("panggul", function () { return new RoundedBoxGeometry(0.34, 0.18, 0.21, 3, 0.07); }), celana, 0, 0.95, 0));
  const ikat = m(geo("ikat", function () { return new RoundedBoxGeometry(0.35, 0.04, 0.22, 2, 0.015); }), standar("ikat", "#3a2a20", 0.5, 0.1), 0, 1.03, 0);
  tubuh.add(ikat);
  const dada = new THREE.Group();
  dada.position.y = 1.0;
  tubuh.add(dada);
  const badan = m(geo("badan", function () { return new THREE.CapsuleGeometry(0.17, 0.3, 6, 18); }), baju, 0, 0.24, 0);
  badan.scale.set(1.12, 1, 0.66);
  dada.add(badan);
  const kerah = m(geo("kerah", function () { return new THREE.TorusGeometry(0.07, 0.022, 8, 20); }), baju, 0, 0.55, 0.01);
  kerah.rotation.x = Math.PI / 2;
  dada.add(kerah);
  dada.add(m(geo("leher", function () { return new THREE.CylinderGeometry(0.05, 0.056, 0.13, 14); }), kulit, 0, 0.59, 0));
  const kepala = new THREE.Group();
  kepala.position.y = 0.71;
  dada.add(kepala);
  const muka = m(geo("kepala", function () { return new THREE.SphereGeometry(0.118, 28, 20); }), kulit, 0, 0, 0);
  muka.scale.set(0.94, 1.1, 1);
  kepala.add(muka);
  kepala.add(m(geo("dagu", function () { const s = new THREE.SphereGeometry(0.07, 16, 12); s.scale(1, 0.8, 0.9); return s; }), kulit, 0, -0.07, 0.035));
  const atap = m(geo("rambut" + o.gaya, function () { return new THREE.SphereGeometry(o.gaya === "rapi" ? 0.124 : 0.128, 28, 16, 0, Math.PI * 2, 0, Math.PI * 0.55); }), rambut, 0, 0.022, -0.008);
  atap.rotation.x = -0.32;
  atap.scale.set(0.98, 1.06, 1.04);
  kepala.add(atap);
  if (o.gaya === "panjang") {
    const ekor = m(geo("rambutPanjang", function () { return new THREE.CapsuleGeometry(0.105, 0.2, 6, 14); }), rambut, 0, -0.1, -0.055);
    ekor.scale.set(1.08, 1, 0.62);
    kepala.add(ekor);
  } else if (o.gaya === "pendek") {
    const jambul = m(geo("jambul", function () { const s = new THREE.SphereGeometry(0.06, 14, 10); s.scale(1.4, 0.6, 1); return s; }), rambut, 0.02, 0.105, 0.05);
    jambul.rotation.z = -0.3;
    kepala.add(jambul);
  }
  [-1, 1].forEach(function (sx) {
    kepala.add(m(geo("mata", function () { return new THREE.SphereGeometry(0.016, 12, 8); }), gelap, sx * 0.042, 0.012, 0.104));
    const alis = m(geo("alis", function () { return new RoundedBoxGeometry(0.045, 0.009, 0.012, 1, 0.004); }), rambut, sx * 0.043, 0.048, 0.108);
    alis.rotation.z = sx * -0.08;
    kepala.add(alis);
    const telinga = m(geo("telinga", function () { const s = new THREE.SphereGeometry(0.026, 12, 8); s.scale(0.5, 1, 0.8); return s; }), kulit, sx * 0.112, 0, 0);
    kepala.add(telinga);
  });
  const hidung = m(geo("hidung", function () { const s = new THREE.SphereGeometry(0.02, 12, 8); s.scale(0.8, 1, 1); return s; }), kulit, 0, -0.012, 0.118);
  kepala.add(hidung);
  const mulut = m(geo("mulut", function () { return new RoundedBoxGeometry(0.042, 0.008, 0.008, 1, 0.003); }), standar("bibir", "#8c3b33", 0.5, 0), 0, -0.055, 0.106);
  kepala.add(mulut);
  if (o.kacamata) {
    const lg = standar("lensa", "#202330", 0.2, 0.7);
    [-1, 1].forEach(function (sx) {
      kepala.add(m(geo("kacamata", function () { return new THREE.TorusGeometry(0.027, 0.004, 8, 22); }), lg, sx * 0.043, 0.012, 0.118));
    });
    kepala.add(m(geo("jembatan", function () { return new THREE.BoxGeometry(0.03, 0.005, 0.005); }), lg, 0, 0.016, 0.12));
  }
  const lengan = {};
  [-1, 1].forEach(function (sx) {
    const bahu = new THREE.Group();
    bahu.position.set(sx * 0.205, 0.47, 0);
    dada.add(bahu);
    bahu.add(m(geo("bahu", function () { return new THREE.SphereGeometry(0.07, 16, 12); }), baju, 0, 0, 0));
    bahu.add(m(geo("lenganAtas", function () { return new THREE.CapsuleGeometry(0.056, 0.2, 6, 14); }), baju, 0, -0.15, 0));
    const siku = new THREE.Group();
    siku.position.y = -0.29;
    bahu.add(siku);
    siku.add(m(geo("lenganBawah", function () { return new THREE.CapsuleGeometry(0.046, 0.19, 6, 12); }), kulit, 0, -0.12, 0));
    const tgn = m(geo("tangan", function () { const s = new THREE.SphereGeometry(0.048, 14, 10); s.scale(0.8, 1.15, 0.6); return s; }), kulit, 0, -0.27, 0);
    siku.add(tgn);
    lengan[sx] = { bahu: bahu, siku: siku };
  });
  const kaki = {};
  [-1, 1].forEach(function (sx) {
    const pinggul = new THREE.Group();
    pinggul.position.set(sx * 0.095, 0.92, 0);
    tubuh.add(pinggul);
    pinggul.add(m(geo("paha", function () { return new THREE.CapsuleGeometry(0.078, 0.3, 6, 14); }), celana, 0, -0.21, 0));
    const lutut = new THREE.Group();
    lutut.position.y = -0.44;
    pinggul.add(lutut);
    lutut.add(m(geo("betis", function () { return new THREE.CapsuleGeometry(0.064, 0.3, 6, 14); }), celana, 0, -0.2, 0));
    lutut.add(m(geo("sepatu", function () { return new RoundedBoxGeometry(0.115, 0.085, 0.26, 2, 0.035); }), sepatu, 0, -0.43, 0.045));
    kaki[sx] = { pinggul: pinggul, lutut: lutut };
  });
  return { root: root, tubuh: tubuh, dada: dada, badan: badan, kepala: kepala, mulut: mulut, lengan: lengan, kaki: kaki };
}

function campur(a, b, t) {
  return a + (b - a) * t;
}

function bedaSudut(a, b) {
  let d = (b - a) % (Math.PI * 2);
  if (d > Math.PI) d -= Math.PI * 2;
  if (d < -Math.PI) d += Math.PI * 2;
  return d;
}

function aturPose(O, s, t) {
  const w = s.bJalan, d = s.duduk, f = s.fase, sn = Math.sin(f);
  const ayun = sn * 0.55 * w;
  const ketik = s.diMeja ? d : 0;
  const bic = s.bBicara;
  O.kaki[-1].pinggul.rotation.x = campur(-ayun, -1.5, d);
  O.kaki[1].pinggul.rotation.x = campur(ayun, -1.5, d);
  O.kaki[-1].lutut.rotation.x = campur(w * 0.7 * Math.max(0, -sn), 1.5, d);
  O.kaki[1].lutut.rotation.x = campur(w * 0.7 * Math.max(0, sn), 1.5, d);
  const gerak = bic * (0.5 + 0.5 * Math.sin(t * 2.6 + s.benih));
  O.lengan[-1].bahu.rotation.x = campur(ayun * 0.9, -0.5 - 0.2 * ketik, d) + Math.sin(t * 1.3 + s.benih) * 0.02;
  O.lengan[1].bahu.rotation.x = campur(-ayun * 0.9, -0.5 - 0.2 * ketik, d) - gerak * 0.55;
  O.lengan[-1].bahu.rotation.z = campur(-0.07, -0.16, d);
  O.lengan[1].bahu.rotation.z = campur(0.07, 0.16, d) + gerak * 0.15;
  O.lengan[-1].siku.rotation.x = campur(-0.22, -0.95, d) + Math.sin(t * 17 + s.benih) * 0.05 * ketik;
  O.lengan[1].siku.rotation.x = campur(-0.22, -0.95, d) - gerak * 0.7 + Math.sin(t * 19 + s.benih * 2) * 0.05 * ketik;
  O.tubuh.position.y = -0.38 * d + Math.abs(sn) * 0.03 * w;
  O.tubuh.position.z = -0.06 * d;
  O.dada.rotation.x = 0.05 * w + 0.06 * ketik;
  O.badan.scale.y = 1 + Math.sin(t * 2.1 + s.benih) * 0.012;
  O.kepala.rotation.x = bic * Math.sin(t * 5.2) * 0.07 - 0.05 * ketik;
  O.kepala.rotation.y = (1 - w) * Math.sin(t * 0.45 + s.benih) * 0.32 * (1 - ketik * 0.7);
  O.mulut.scale.y = 1 + bic * Math.abs(Math.sin(t * 14)) * 3.5;
}

function rumah(k) {
  const a = AGEN[k];
  if (a.ruang === "b") return KURSI_B[urutanB.indexOf(k) % KURSI_B.length];
  return RUMAH[a.ruang];
}

function kursiRapat(k) {
  return KURSI[AGEN[k].kursi % KURSI.length];
}

function buatAgen(k, mulaiJauh) {
  const a = AGEN[k];
  const r = rumah(k);
  const s = {
    x: mulaiJauh ? -12.2 : r.x, z: mulaiJauh ? 9.6 : r.z, arah: r.arah, arahTuju: r.arah,
    lokasi: "rumah", pulang: null, sibuk: false, dx: 0, dz: 0,
    jalan: false, bJalan: 0, fase: 0, duduk: mulaiJauh ? 0 : 1, diMeja: true,
    bicara: false, bBicara: 0, benih: (hashWarna(k) % 100) / 10, model: null, nama: null, bub: null
  };
  ag[k] = s;
  if (!ada3D) return;
  const nomor = hashWarna(k);
  s.model = buatOrang({
    baju: a.warna,
    rambut: a.rambut || RAMBUT[nomor % RAMBUT.length],
    kulit: a.kulit || KULIT[nomor % KULIT.length],
    celana: a.celana || CELANA[nomor % CELANA.length],
    gaya: a.gaya || ["pendek", "rapi", "panjang"][nomor % 3],
    kacamata: a.kacamata || nomor % 4 === 1
  });
  s.model.root.position.set(s.x, 0, s.z);
  s.model.root.rotation.y = s.arah;
  scene.add(s.model.root);
  const nm = document.createElement("div");
  nm.className = "nama";
  nm.style.setProperty("--w", a.warna);
  const titik = document.createElement("i");
  const teks = document.createElement("span");
  teks.textContent = a.nama;
  const tanda = document.createElement("em");
  tanda.textContent = "!";
  const mikir = document.createElement("s");
  mikir.innerHTML = "<b>.</b><b>.</b><b>.</b>";
  nm.append(titik, teks, tanda, mikir);
  lapisan.appendChild(nm);
  s.nama = nm;
  const bub = document.createElement("div");
  bub.className = "bub";
  bub.style.setProperty("--w", a.warna);
  const judul = document.createElement("b");
  judul.textContent = a.nama;
  const isi = document.createElement("span");
  bub.append(judul, isi);
  lapisan.appendChild(bub);
  s.bub = bub;
  s.bubIsi = isi;
}

function pastikanAgen(k) {
  if (AGEN[k]) return;
  const n = urutanB.length;
  const nomor = hashWarna(k);
  AGEN[k] = {
    nama: k.charAt(0).toUpperCase() + k.slice(1),
    warna: warnaAgen(k),
    ruang: "b",
    kursi: 3 + (n % 4),
    rambut: RAMBUT[(n + 3) % RAMBUT.length],
    kulit: KULIT[nomor % KULIT.length],
    celana: CELANA[nomor % CELANA.length]
  };
  urutanB.push(k);
  if (grupB) grupB.visible = true;
  buatAgen(k, true);
  if (ada3D && !kameraDigeser) pasKamera();
}

function jalur(s, tujuan) {
  for (const px of [-4.4, 4.4]) {
    if ((s.x - px) * (tujuan.x - px) < 0) {
      const u = (px - s.x) / (tujuan.x - s.x);
      const zc = s.z + u * (tujuan.z - s.z);
      if (zc < -1.4) return { x: px, z: -0.4 };
    }
  }
  const sx = s.x < 0 ? -1 : 1;
  const tx = tujuan.x < 0 ? -1 : 1;
  if (s.z > 10.2 && tujuan.z < 10.2 && Math.abs(s.x) < 7.2) return { x: sx * 7.4, z: 10.75 };
  if (s.z > 8.7 && s.z < 10.95 && Math.abs(s.x) >= 7.2 && tujuan.z < 8.9) return { x: sx * 7.4, z: 8.3 };
  if (tujuan.z > 10.2 && s.z < 10.2 && Math.abs(tujuan.x) < 7.2) {
    if (Math.abs(s.x) < 7.2 && s.z < 8.95) return { x: tx * 7.4, z: 8.3 };
    if (Math.abs(s.x) >= 7.2) return { x: Math.sign(s.x) * 7.4, z: 10.75 };
  }
  return tujuan;
}

function perbaruiAgen(dt, t) {
  const kini = Date.now();
  const tunggu = menunggu && kini - menunggu < 330000;
  for (const k in AGEN) {
    const s = ag[k];
    if (!s) continue;
    let tujuan, duduki = null;
    if (s.lokasi === "rapat" || tunggu) duduki = kursiRapat(k);
    else {
      const r = rumah(k);
      if (s.sibuk) tujuan = { x: r.x + s.dx, z: r.z + s.dz };
      else duduki = r;
    }
    if (duduki) tujuan = duduki;
    s.diMeja = !!duduki && !(s.lokasi === "rapat" || tunggu);
    const lewat = jalur(s, tujuan);
    const jx = lewat.x - s.x, jz = lewat.z - s.z;
    const jarak = Math.hypot(jx, jz) + (lewat === tujuan ? 0 : 1);
    if (jarak > 0.04) {
      if (s.duduk > 0) {
        s.duduk = Math.max(0, s.duduk - dt * 2.4);
        s.jalan = false;
      } else {
        const nyata = Math.max(0.0001, Math.hypot(jx, jz));
        const l = Math.min(nyata, KECEPATAN * dt);
        s.x += (jx / nyata) * l;
        s.z += (jz / nyata) * l;
        s.jalan = true;
        s.arahTuju = Math.atan2(jx, jz);
      }
    } else {
      s.jalan = false;
      if (duduki) {
        s.arahTuju = duduki.arah;
        if (Math.abs(bedaSudut(s.arah, duduki.arah)) < 0.35) s.duduk = Math.min(1, s.duduk + dt * 2.2);
      }
    }
    s.arah += bedaSudut(s.arah, s.arahTuju) * Math.min(1, dt * 7);
    s.bJalan += ((s.jalan ? 1 : 0) - s.bJalan) * Math.min(1, dt * 8);
    if (s.jalan) s.fase += dt * 8.5;
    const data = terbaru[k];
    s.bicara = !!data && kini - data.waktu < BATAS_BICARA;
    s.bBicara += ((s.bicara ? 1 : 0) - s.bBicara) * Math.min(1, dt * 5);
    if (s.model) {
      s.model.root.position.set(s.x, 0, s.z);
      s.model.root.rotation.y = s.arah;
      aturPose(s.model, s, t);
    }
  }
}

function bicara(k) {
  const s = ag[k];
  if (!s) return;
  s.lokasi = "rapat";
  clearTimeout(s.pulang);
  s.pulang = setTimeout(function () { s.lokasi = "rumah"; }, LAMA_DI_RAPAT);
}

function iseng() {
  const nama = Object.keys(AGEN);
  const k = nama[Math.floor(Math.random() * nama.length)];
  const s = ag[k];
  if (!s || s.lokasi !== "rumah" || s.sibuk || Math.random() > 0.45) return;
  s.sibuk = true;
  const r = rumah(k);
  s.dx = (Math.random() - 0.5) * 3;
  s.dz = (r.arah === 0 ? -1 : 1) * (0.7 + Math.random() * 0.9);
  setTimeout(function () { s.sibuk = false; }, 5200);
}

const geoEfek = {};
function tambahEfek(jenis, x, z) {
  if (!ada3D) return;
  const g = new THREE.Group();
  g.position.set(x, 1.8, z);
  if (jenis === "surat") {
    g.add(kotak(0.36, 0.24, 0.015, MAT.putih, 0, 0, 0, 0.006));
    if (!geoEfek.lipat) {
      const sh = new THREE.Shape();
      sh.moveTo(-0.18, 0.12);
      sh.lineTo(0.18, 0.12);
      sh.lineTo(0, -0.02);
      sh.closePath();
      geoEfek.lipat = new THREE.ShapeGeometry(sh);
    }
    const lp = new THREE.Mesh(geoEfek.lipat, standar("lipat", "#e2ddd2", 0.6, 0, { side: THREE.DoubleSide }));
    lp.position.z = 0.009;
    g.add(lp);
    g.add(bola(0.022, standar("segel", "#c0392b", 0.4, 0), 0, 0.02, 0.012));
  } else if (jenis === "paket") {
    g.add(kotak(0.32, 0.28, 0.32, standar("kardus", "#c8955f", 0.85, 0), 0, 0, 0, 0.02));
    g.add(kotak(0.07, 0.285, 0.325, standar("lakban", "#e8c896", 0.5, 0), 0, 0, 0));
  } else {
    for (let i = 0; i < 7; i++) {
      const mm = new THREE.Mesh(geo("kilau", function () { return new THREE.OctahedronGeometry(0.06); }), standar("kilauBahan", "#ffd27a", 0.2, 0.3, { emissive: "#ffb347", emissiveIntensity: 2.2 }));
      mm.userData.a = (i / 7) * Math.PI * 2;
      g.add(mm);
    }
  }
  g.traverse(function (o) { if (o.isMesh) o.castShadow = true; });
  scene.add(g);
  efek3D.push({ g: g, jenis: jenis, x: x, z: z, t0: performance.now() });
}

function perbaruiEfek() {
  const kini = performance.now();
  for (let i = efek3D.length - 1; i >= 0; i--) {
    const e = efek3D[i];
    const u = (kini - e.t0) / 1000;
    if (u > 2.8) {
      scene.remove(e.g);
      efek3D.splice(i, 1);
      continue;
    }
    const sk = Math.min(1, u * 4) * Math.max(0, Math.min(1, (2.8 - u) * 2));
    e.g.scale.setScalar(Math.max(0.001, sk));
    if (e.jenis === "surat") {
      e.g.position.set(e.x + u * 1.6, 1.8 + u * 0.8 + Math.sin(u * 5) * 0.08, e.z + u * 0.6);
      e.g.rotation.set(Math.sin(u * 3) * 0.3, u * 1.5, Math.sin(u * 4) * 0.2);
    } else if (e.jenis === "paket") {
      e.g.position.y = 1.8 + u * 0.9;
      e.g.rotation.set(u * 0.6, u * 2.2, 0);
    } else {
      e.g.position.y = 1.9 + u * 0.4;
      e.g.children.forEach(function (c) {
        const a = c.userData.a + u * 2.5;
        c.position.set(Math.cos(a) * (0.3 + u * 0.15), Math.sin(u * 6 + c.userData.a) * 0.15, Math.sin(a) * (0.3 + u * 0.15));
        c.rotation.y = u * 6;
      });
    }
  }
}

function pasKamera() {
  if (!kamera) return;
  const potret = kamera.aspect < 1.05;
  const az = potret ? 0.82 : 0.2;
  const polar = potret ? 0.88 : 0.95;
  const zMax = urutanB.length ? 12.3 : 7.3;
  const pusat = new THREE.Vector3(0, 0.4, (-7.3 + zMax) / 2);
  const titik = [];
  for (const x of [-13, 13]) for (const z of [-7.3, zMax]) for (const y of [0, 2.2]) titik.push(new THREE.Vector3(x, y, z));
  const arah = new THREE.Vector3(Math.sin(polar) * Math.sin(az), Math.cos(polar), Math.sin(polar) * Math.cos(az));
  let lo = 4, hi = 160;
  for (let i = 0; i < 26; i++) {
    const mid = (lo + hi) / 2;
    kamera.position.copy(pusat).addScaledVector(arah, mid);
    kamera.lookAt(pusat);
    kamera.updateMatrixWorld();
    let muat = true;
    for (const p of titik) {
      vSementara.copy(p).project(kamera);
      if (vSementara.z > 1 || Math.abs(vSementara.x) > 0.97 || Math.abs(vSementara.y) > 0.9) {
        muat = false;
        break;
      }
    }
    if (muat) hi = mid;
    else lo = mid;
  }
  const jarak = hi * (potret ? 0.84 : 0.98);
  kamera.position.copy(pusat).addScaledVector(arah, jarak);
  kamera.lookAt(pusat);
  if (kontrol) {
    kontrol.target.copy(pusat);
    kontrol.update();
  }
}

function ukurUlang() {
  if (!renderer) return;
  const w = adegan.clientWidth, h = adegan.clientHeight;
  if (!w || !h) return;
  renderer.setSize(w, h, false);
  kamera.aspect = w / h;
  kamera.updateProjectionMatrix();
  if (!kameraDigeser) pasKamera();
}

function bangun3D() {
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  } catch (e) {
    return false;
  }
  if (!renderer.getContext()) return false;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  adegan.insertBefore(renderer.domElement, adegan.firstChild);

  scene = new THREE.Scene();
  scene.background = new THREE.Color("#0d0f15");
  scene.fog = new THREE.Fog("#0d0f15", 70, 170);
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;
  pmrem.dispose();

  kamera = new THREE.PerspectiveCamera(36, 1, 0.5, 400);
  scene.add(new THREE.HemisphereLight("#fff3e2", "#2b2838", 0.45));
  sunLight = new THREE.DirectionalLight("#ffe0bd", 2.6);
  sunLight.position.set(-9, 18, 13);
  sunLight.target.position.set(0, 0, 2.4);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.set(2048, 2048);
  const sc = sunLight.shadow.camera;
  sc.left = -19;
  sc.right = 19;
  sc.top = 17;
  sc.bottom = -17;
  sc.near = 1;
  sc.far = 60;
  sunLight.shadow.bias = -0.0004;
  sunLight.shadow.normalBias = 0.03;
  scene.add(sunLight);
  scene.add(sunLight.target);
  const isi = new THREE.DirectionalLight("#9fb6ff", 0.5);
  isi.position.set(12, 8, -6);
  scene.add(isi);

  bahanDasar();
  bangunDunia();

  kontrol = new OrbitControls(kamera, renderer.domElement);
  kontrol.enableDamping = true;
  kontrol.dampingFactor = 0.08;
  kontrol.minDistance = 5;
  kontrol.maxDistance = 95;
  kontrol.minPolarAngle = 0.2;
  kontrol.maxPolarAngle = 1.36;
  kontrol.screenSpacePanning = false;
  kontrol.addEventListener("start", function () {
    kameraDigeser = true;
    document.getElementById("aturKamera").hidden = false;
    document.getElementById("petunjuk").classList.add("hilang");
  });
  document.getElementById("aturKamera").addEventListener("click", function () {
    kameraDigeser = false;
    this.hidden = true;
    pasKamera();
  });
  new ResizeObserver(ukurUlang).observe(adegan);
  ukurUlang();
  setTimeout(function () { document.getElementById("petunjuk").classList.add("hilang"); }, 7000);
  return true;
}

let terlihat = true;
let terakhirLayar = 0;
const jamDunia = new THREE.Clock();

function posisiLayar(v, out) {
  vSementara.copy(v).project(kamera);
  out.x = (vSementara.x * 0.5 + 0.5) * adegan.clientWidth;
  out.y = (-vSementara.y * 0.5 + 0.5) * adegan.clientHeight;
  out.ok = vSementara.z < 1 && vSementara.z > -1;
  return out;
}

const titikLayar = { x: 0, y: 0, ok: true };
function perbaruiLapisan() {
  const W = adegan.clientWidth;
  for (const k in AGEN) {
    const s = ag[k];
    if (!s || !s.nama) continue;
    s.model.kepala.getWorldPosition(vKepala);
    vKepala.y += 0.26;
    posisiLayar(vKepala, titikLayar);
    s.nama.style.display = titikLayar.ok ? "flex" : "none";
    s.nama.style.transform = "translate(" + titikLayar.x.toFixed(1) + "px," + titikLayar.y.toFixed(1) + "px) translate(-50%,-100%)";
    s.layarX = titikLayar.x;
    s.layarY = titikLayar.y - s.nama.offsetHeight - 8;
    if (s.bub.style.display === "block") {
      const lebar = s.bub.offsetWidth, tinggi = s.bub.offsetHeight;
      const kiri = Math.min(Math.max(s.layarX - lebar / 2, 6), W - lebar - 6);
      s.bub.style.setProperty("--ekor", Math.min(Math.max(s.layarX - kiri, 16), lebar - 16) + "px");
      s.bub.style.transform = "translate(" + kiri.toFixed(1) + "px," + Math.max(4, s.layarY - tinggi).toFixed(1) + "px)";
    }
  }
  for (const l of labelRuang) {
    const aktif = !l.aktif || l.aktif();
    posisiLayar(l.pos, titikLayar);
    l.el.style.display = aktif && titikLayar.ok ? "block" : "none";
    l.el.style.transform = "translate(" + titikLayar.x.toFixed(1) + "px," + titikLayar.y.toFixed(1) + "px) translate(-50%,-100%)";
  }
}

function sembunyikanDinding() {
  for (const d of dinding) {
    vSementara.copy(kamera.position).sub(d.c);
    d.g.visible = d.aktif() && vSementara.dot(d.n) < 0;
  }
}

function perbaruiDetail(t) {
  if (t - terakhirLayar > 380) {
    terakhirLayar = t;
    for (const l of layar) l.gambar(t);
  }
  const cepat = kerja && Date.now() - kerja < 90000 ? 9 : 2.2;
  const detik = t / 1000;
  for (const b of lampuLed) {
    const v = Math.sin(detik * cepat + b.userData.fase * 1.7) + Math.sin(detik * cepat * 1.9 + b.userData.fase);
    b.emissiveIntensity = v > 0.4 ? 2.2 : 0.15;
  }
  if (jarumJam.j) {
    const d = new Date();
    const jamN = d.getHours() % 12 + d.getMinutes() / 60, men = d.getMinutes() + d.getSeconds() / 60;
    jarumJam.j.rotation.z = -(jamN / 12) * Math.PI * 2;
    jarumJam.m.rotation.z = -(men / 60) * Math.PI * 2;
    jarumJam.d.rotation.z = -(d.getSeconds() / 60) * Math.PI * 2;
  }
}

function putar() {
  requestAnimationFrame(putar);
  const dt = Math.min(0.1, jamDunia.getDelta());
  const t = jamDunia.elapsedTime;
  perbaruiAgen(dt, t);
  if (!terlihat) return;
  perbaruiEfek();
  perbaruiDetail(t * 1000);
  kontrol.update();
  sembunyikanDinding();
  renderer.render(scene, kamera);
  perbaruiLapisan();
}

function setStatus(kelas, teks) {
  document.getElementById("status").className = "status " + kelas;
  document.getElementById("statusTeks").textContent = teks;
}

function formatJam(iso) {
  return new Date(iso).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
}

function terapkan(baris, awal) {
  if (baris.agen === "rian") baris.agen = "pranowo";
  if (!AGEN[baris.agen] && baris.agen !== "sistem" && baris.agen !== "keputusan" && /^[a-z]{3,12}$/.test(baris.agen)) {
    pastikanAgen(baris.agen);
  }
  idTerakhir = Math.max(idTerakhir, baris.id);
  const waktu = Date.parse(baris.dibuat);
  const segar = !awal && Date.now() - waktu < BATAS_GELEMBUNG;
  if (baris.jenis === "tugas") {
    document.getElementById("tugasLabel").textContent = "Tugas";
    document.getElementById("tugasTeks").textContent = baris.teks.replace(/^Tugas dari bos:\s*/, "");
  } else if (baris.jenis === "rutin" && baris.agen === "sistem") {
    document.getElementById("tugasLabel").textContent = "Santai";
    document.getElementById("tugasTeks").textContent = baris.teks.replace(/^Obrolan santai di kantor tentang:\s*/, "");
  } else if (baris.jenis === "approval") {
    document.getElementById("tugasLabel").textContent = "Menunggu";
    document.getElementById("tugasTeks").textContent = "Tim menunggu persetujuanmu di Discord";
  } else if (baris.jenis === "keputusan") {
    document.getElementById("papanTeks").textContent = baris.teks;
    if (papanTulis) {
      papanTulis.teks = baris.teks;
      gambarPapan(baris.teks);
    }
  }
  if (baris.jenis === "approval") {
    menunggu = waktu;
  } else if (baris.jenis === "persetujuan") {
    menunggu = 0;
  } else if (baris.jenis === "kerja") {
    kerja = waktu;
  } else if (baris.jenis === "aksi" && baris.agen === "chatai") {
    kerja = 0;
    menunggu = 0;
    if (segar && ag.chatai) {
      const j = /email|surat|laporan/i.test(baris.teks) ? "surat" : (/repo|github/i.test(baris.teks) ? "paket" : "kilau");
      tambahEfek(j, ag.chatai.x, ag.chatai.z);
    }
  }
  if (AGEN[baris.agen]) {
    terbaru[baris.agen] = { teks: baris.teks, waktu: waktu, mulai: segar ? Date.now() : 0 };
    if (segar) bicara(baris.agen);
  }
  const log = document.getElementById("log");
  const kosong = document.getElementById("kosong");
  if (kosong) kosong.remove();
  const dekat = log.scrollHeight - log.scrollTop - log.clientHeight < 60;
  const el = document.createElement("div");
  el.className = "pesan";
  const info = AGEN[baris.agen];
  if (info) el.style.setProperty("--w", info.warna);
  const nama = document.createElement("b");
  nama.textContent = info ? info.nama : (baris.agen === "keputusan" ? "Keputusan" : "Sistem");
  const t = document.createElement("time");
  t.textContent = formatJam(baris.dibuat);
  const isi = document.createElement("span");
  isi.textContent = baris.teks;
  el.append(nama, t, document.createElement("br"), isi);
  log.appendChild(el);
  while (log.children.length > 80) log.removeChild(log.firstChild);
  if (dekat) log.scrollTop = log.scrollHeight;
}

function tampil() {
  if (!ada3D) return;
  const sekarang = Date.now();
  const tunggu = menunggu && sekarang - menunggu < 330000;
  const mikir = kerja && sekarang - kerja < 90000;
  let terkini = null;
  for (const k in AGEN) {
    if (terbaru[k] && (terkini === null || terbaru[k].waktu >= terbaru[terkini].waktu)) terkini = k;
  }
  for (const k in AGEN) {
    const s = ag[k];
    if (!s || !s.bub) continue;
    s.nama.classList.toggle("tunggu", !!tunggu);
    s.nama.classList.toggle("mikir", k === "chatai" && !!mikir);
    const data = terbaru[k];
    const umur = data ? sekarang - data.waktu : Infinity;
    if (data && k === terkini && umur < BATAS_GELEMBUNG) {
      let teks = data.teks.length > 170 ? data.teks.slice(0, 167) + "..." : data.teks;
      if (data.mulai) {
        const n = Math.max(1, Math.floor((sekarang - data.mulai) / 28));
        if (n < teks.length) teks = teks.slice(0, n);
      }
      if (s.bubIsi.textContent !== teks) s.bubIsi.textContent = teks;
      s.bub.style.display = "block";
    } else {
      s.bub.style.display = "none";
    }
  }
}

async function ambil(awal) {
  const q = awal ? "order=id.desc&limit=40" : "id=gt." + idTerakhir + "&order=id.asc&limit=100";
  const res = await fetch(KONFIG.url + "/rest/v1/kantor_pesan?select=*&" + q, {
    headers: { apikey: KONFIG.kunci, Authorization: "Bearer " + KONFIG.kunci }
  });
  if (!res.ok) throw new Error("kode " + res.status);
  const baris = await res.json();
  if (awal) baris.reverse();
  baris.forEach(function (b) { terapkan(b, awal); });
}

function buatPotret(daftar) {
  const hasil = {};
  let r2;
  try {
    r2 = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  } catch (e) {
    return hasil;
  }
  if (!r2.getContext()) return hasil;
  r2.setPixelRatio(1);
  r2.setSize(320, 400, false);
  r2.toneMapping = THREE.ACESFilmicToneMapping;
  r2.setClearColor(0x000000, 0);
  const sc = new THREE.Scene();
  const pm = new THREE.PMREMGenerator(r2);
  sc.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
  sc.environmentIntensity = 0.7;
  pm.dispose();
  const kunci = new THREE.DirectionalLight("#fff1dd", 2.4);
  kunci.position.set(-2, 3, 4);
  sc.add(kunci);
  const tepi = new THREE.DirectionalLight("#ffffff", 1.6);
  tepi.position.set(2, 2, -3);
  sc.add(tepi);
  const cam = new THREE.PerspectiveCamera(26, 320 / 400, 0.1, 30);
  cam.position.set(1.1, 1.25, 4.4);
  cam.lookAt(0, 0.95, 0);
  for (const p of daftar) {
    const a = AGEN[p.k] || {};
    const nomor = hashWarna(p.k);
    const O = buatOrang({
      baju: a.warna || warnaAgen(p.k),
      rambut: a.rambut || RAMBUT[nomor % RAMBUT.length],
      kulit: a.kulit || KULIT[nomor % KULIT.length],
      celana: a.celana || CELANA[nomor % CELANA.length],
      gaya: a.gaya || ["pendek", "rapi", "panjang"][nomor % 3],
      kacamata: a.kacamata || nomor % 4 === 1
    });
    O.root.rotation.y = 0.28;
    O.lengan[1].bahu.rotation.z = 2.55;
    O.lengan[1].bahu.rotation.x = -0.2;
    O.lengan[1].siku.rotation.z = 0.5;
    O.lengan[-1].bahu.rotation.z = -0.1;
    O.kepala.rotation.y = 0.15;
    O.kepala.rotation.z = -0.06;
    O.kaki[1].pinggul.rotation.x = -0.12;
    O.kaki[-1].pinggul.rotation.x = 0.08;
    sc.add(O.root);
    r2.render(sc, cam);
    try {
      hasil[p.k] = r2.domElement.toDataURL("image/png");
    } catch (e) {
    }
    sc.remove(O.root);
  }
  r2.dispose();
  if (r2.forceContextLoss) r2.forceContextLoss();
  return hasil;
}

function siapkanPembuka() {
  const pb = document.getElementById("pembuka");
  document.getElementById("ulangPembuka").addEventListener("click", function () {
    try {
      sessionStorage.removeItem("pembukaSelesai");
    } catch (e) {
    }
    location.reload();
  });
  let sudah = false;
  try {
    sudah = sessionStorage.getItem("pembukaSelesai") === "1";
  } catch (e) {
  }
  if (sudah || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    pb.remove();
    return;
  }
  const potret = buatPotret(PEKERJA);
  const daftar = [{ judul: "Kantor", peran: "kenalan dengan timnya", bg: "#0b0d12", fg: "#f4efe6", label: "RyHanC" }].concat(
    PEKERJA.map(function (p, i) {
      return { judul: p.nama, peran: p.peran, bg: p.bg, fg: p.fg, label: "anggota " + (i + 1) + " / " + PEKERJA.length, p: p };
    })
  );
  document.documentElement.style.overflow = "hidden";
  const adeganP = [];
  const batangP = [];
  const bar = document.createElement("div");
  bar.className = "pb-batang";
  daftar.forEach(function (d) {
    const s = document.createElement("section");
    s.className = "pb-scene";
    s.style.background = d.bg;
    s.style.color = d.fg;
    const lab = document.createElement("div");
    lab.className = "pb-label";
    lab.textContent = d.label;
    s.appendChild(lab);
    if (d.p && potret[d.p.k]) {
      const img = document.createElement("img");
      img.className = "pb-av";
      img.alt = "";
      img.src = potret[d.p.k];
      s.appendChild(img);
    }
    const nm = document.createElement("div");
    nm.className = "pb-nama";
    nm.style.fontSize = "min(" + Math.floor(88 / (d.judul.length * 0.66)) + "vw, 9rem)";
    Array.from(d.judul).forEach(function (ch, i) {
      const luar = document.createElement("span");
      luar.className = "pb-h";
      const dalam = document.createElement("span");
      dalam.style.setProperty("--i", i);
      dalam.textContent = ch === " " ? " " : ch;
      luar.appendChild(dalam);
      nm.appendChild(luar);
    });
    s.appendChild(nm);
    const per = document.createElement("div");
    per.className = "pb-peran";
    per.textContent = d.peran;
    s.appendChild(per);
    pb.appendChild(s);
    adeganP.push(s);
    const b = document.createElement("span");
    b.appendChild(document.createElement("i"));
    bar.appendChild(b);
    batangP.push(b);
  });
  const lewati = document.createElement("button");
  lewati.className = "pb-lewati";
  lewati.type = "button";
  lewati.textContent = "Lewati";
  pb.appendChild(lewati);
  pb.appendChild(bar);
  let n = 0;
  let pewaktu = null;
  function tampilkan(i) {
    const lama = adeganP[n];
    const baru = adeganP[i];
    if (lama !== baru) {
      lama.classList.remove("aktif");
      lama.classList.add("lama");
      setTimeout(function () { lama.classList.remove("lama"); }, 1000);
    }
    baru.classList.remove("lama");
    baru.classList.add("aktif");
    batangP.forEach(function (b, j) {
      b.className = j < i ? "lewat" : (j === i ? "on" : "");
    });
    n = i;
  }
  function selesai() {
    clearInterval(pewaktu);
    try {
      sessionStorage.setItem("pembukaSelesai", "1");
    } catch (e) {
    }
    pb.classList.add("keluar");
    document.documentElement.style.overflow = "";
    setTimeout(function () { pb.remove(); }, 1000);
  }
  lewati.addEventListener("click", selesai);
  tampilkan(0);
  pewaktu = setInterval(function () {
    if (n + 1 >= daftar.length) selesai();
    else tampilkan(n + 1);
  }, 2500);
}

function siapkanForm() {
  const form = document.getElementById("formPerintah");
  const info = document.getElementById("infoKirim");
  const tombol = document.getElementById("tombolKirim");
  try {
    document.getElementById("inKode").value = localStorage.getItem("kodeKantor") || "";
  } catch (e) {
  }
  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    if (typeof KONFIG === "undefined" || !KONFIG.url || !KONFIG.kunci) {
      info.textContent = "Halaman belum diatur, isi konfig.js dulu.";
      return;
    }
    const teks = document.getElementById("inTeks").value.trim();
    const kode = document.getElementById("inKode").value;
    if (teks.length < 3) return;
    try {
      localStorage.setItem("kodeKantor", kode);
    } catch (e) {
    }
    tombol.disabled = true;
    info.textContent = "Mengirim...";
    try {
      const res = await fetch(KONFIG.url + "/rest/v1/kantor_perintah", {
        method: "POST",
        headers: {
          apikey: KONFIG.kunci,
          Authorization: "Bearer " + KONFIG.kunci,
          "Content-Type": "application/json",
          Prefer: "return=minimal"
        },
        body: JSON.stringify({ teks: teks, kode: kode })
      });
      if (res.ok) {
        info.textContent = "Terkirim. Tim mulai bekerja dalam beberapa detik, lihat obrolannya di sini.";
        document.getElementById("inTeks").value = "";
      } else {
        info.textContent = "Gagal mengirim (kode " + res.status + ").";
      }
    } catch (e) {
      info.textContent = "Gagal mengirim, periksa koneksi.";
    }
    tombol.disabled = false;
  });
}

async function mulai() {
  siapkanPembuka();
  siapkanForm();
  const memuat = document.getElementById("memuat");
  try {
    ada3D = bangun3D();
  } catch (e) {
    ada3D = false;
    console.error(e);
  }
  for (const k in AGEN) buatAgen(k, false);
  if (ada3D) {
    new IntersectionObserver(function (isi) { terlihat = isi[0].isIntersecting; }).observe(adegan);
    requestAnimationFrame(putar);
    requestAnimationFrame(function () { memuat.classList.add("selesai"); });
  } else {
    document.getElementById("memuatTeks").textContent = "Perangkat ini belum mendukung WebGL, kantor 3D tidak bisa ditampilkan.";
    memuat.querySelector(".putar").remove();
  }
  setInterval(tampil, 120);
  setInterval(iseng, 6000);
  if (typeof KONFIG === "undefined" || !KONFIG.url || !KONFIG.kunci) {
    setStatus("putus", "Belum diatur");
    document.getElementById("tugasTeks").textContent = "Buat file konfig.js di folder web berisi alamat Supabase dan kunci anon.";
    return;
  }
  try {
    await ambil(true);
    setStatus("hidup", "Langsung");
  } catch (e) {
    setStatus("putus", "Terputus");
  }
  setInterval(async function () {
    try {
      await ambil(false);
      setStatus("hidup", "Langsung");
    } catch (e) {
      setStatus("putus", "Terputus");
    }
  }, 2500);
}

mulai();
