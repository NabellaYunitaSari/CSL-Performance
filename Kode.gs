/**
 * ============================================================
 * Kode.gs — Dashboard Customer Satisfaction (CSL)
 * Backend Google Apps Script (satu file, siap tempel ke editor
 * Apps Script bawaan yang membuat file default bernama "Kode.gs").
 *
 * File ini adalah gabungan dari 8 modul asal (urutan dipertahankan
 * agar dependensi antar fungsi/konstanta tetap benar):
 *   00_Config.gs        -> konstanta & warna
 *   01_Sheets.gs        -> pembacaan worksheet
 *   02_Columns.gs       -> deteksi kolom & normalisasi wilayah
 *   03_Calc.gs          -> filter & perhitungan satisfaction/NPS
 *   04_Charts.gs        -> data Section 1 & 2 (KPI, peta, matriks, heatmap)
 *   05_Demographics.gs  -> data Section 3 (demografi, SES, NPS, insight)
 *   06_Region.gs        -> data Section 4 (Profil Wilayah & Budaya)
 *   07_Api.gs           -> routing Web API (doGet/doPost) + Framework
 *
 * Tidak ada satu pun rumus, urutan kategori, warna, atau teks yang
 * diubah dari versi Python (app_backend.py) maupun versi delapan-file
 * sebelumnya. Hanya digabung menjadi satu file agar sesuai kebiasaan
 * proyek Apps Script yang memakai satu file "Kode.gs".
 *
 * CARA PASANG
 * 1. Buka spreadsheet CSL -> Extensions > Apps Script.
 * 2. Ganti isi file default (Code.gs / Kode.gs) dengan seluruh isi file ini.
 * 3. Project Settings > Script Properties, tambahkan:
 *      key   : SPREADSHEET_ID
 *      value : ID spreadsheet (bagian /d/<ID>/ pada URL)
 * 4. Jalankan fungsi testUnitPage sekali untuk memberi izin akses.
 * 5. Deploy > New deployment > Web app
 *      Execute as     : Me
 *      Who has access : Anyone
 *    Simpan URL /exec untuk dipakai frontend.
 * ============================================================
 */


// ============================================================
// BERKAS ASAL: 00_Config.gs
// ============================================================

/**
 * ============================================================
 * 00_Config.gs
 * Seluruh konstanta hasil porting dari app_backend.py.
 * Nilai warna, nama profil, mapping karesidenan, alias kolom,
 * indikator yang dikecualikan, dan mapping motor TIDAK diubah.
 * ============================================================
 */

// URL spreadsheet disimpan di Script Properties agar tidak hardcode.
// Set sekali lewat menu: Project Settings > Script Properties
//   key   : SPREADSHEET_ID
//   value : id spreadsheet (bagian /d/<ID>/ pada URL)
function getSpreadsheetId_() {
  var id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!id) {
    throw new Error(
      "Script Property 'SPREADSHEET_ID' belum diisi. " +
      "Isi dengan ID spreadsheet CSL pada Project Settings > Script Properties."
    );
  }
  return id;
}

var RED_OUTLINE = '#E60012';
var ORANGE_OUTLINE = '#FF6B00';
var BLUE_OUTLINE = '#1665D8';

var GREEN = '#35A853';
var RED = '#E60012';
var YELLOW = '#FFB000';
var ORANGE = '#FF6B00';

var SEMESTER_ORDER = { 1: 0, 2: 1 };

var TARGET_PROVINCES = [
  'dki jakarta', 'jakarta', 'jawa barat', 'jawa tengah',
  'daerah istimewa yogyakarta', 'di yogyakarta', 'yogyakarta',
  'jawa timur', 'banten', 'bali', 'nusa tenggara barat', 'ntb',
  'nusa tenggara timur', 'ntt'
];

var SHP_KAB_CANDIDATES = [
  'WADMKK', 'ADM2_EN', 'NAME_2', 'KABKOT', 'kabupaten', 'name',
  'ADM2_REF', 'ADM2ALT1EN', 'ADM2ALT2EN'
];

var SHP_PROV_CANDIDATES = [
  'WADMPR', 'ADM1_EN', 'NAME_1', 'PROVINSI', 'PROVINCE', 'adm1_en'
];

var PROFILE_NAMES = {
  P1: 'Detractor', P2: 'Below Average', P3: 'Middle',
  P4: 'Above Average', P5: 'Promoter'
};

var PROFILE_COLORS = {
  P1: RED, P2: ORANGE, P3: YELLOW, P4: '#9CCC65', P5: GREEN
};

// Mapping nama wilayah baku dashboard -> Keresidenan.
var KARESIDENAN_MAP = {
  'Surabaya': 'Karesidenan Surabaya',
  'Gresik': 'Karesidenan Eks Surabaya',
  'Sidoarjo': 'Karesidenan Eks Surabaya',
  'Mojokerto': 'Karesidenan Eks Surabaya',
  'Jombang': 'Karesidenan Eks Surabaya',
  'Malang': 'Karesidenan Malang',
  'Kota Malang': 'Karesidenan Malang',
  'Pasuruan': 'Karesidenan Eks Malang',
  'Probolinggo': 'Karesidenan Eks Malang',
  'Lumajang': 'Karesidenan Eks Malang',
  'Banyuwangi': 'Karesidenan Besuki',
  'Jember': 'Karesidenan Besuki',
  'Bondowoso': 'Karesidenan Besuki',
  'Situbondo': 'Karesidenan Besuki',
  'Kediri': 'Karesidenan Kediri',
  'Kab-Kodya Blitar': 'Karesidenan Kediri',
  'Tulungagung': 'Karesidenan Kediri',
  'Trenggalek': 'Karesidenan Kediri',
  'Nganjuk': 'Karesidenan Kediri',
  'Madiun': 'Karesidenan Madiun',
  'Ngawi': 'Karesidenan Madiun',
  'Magetan': 'Karesidenan Madiun',
  'Ponorogo': 'Karesidenan Madiun',
  'Pacitan': 'Karesidenan Madiun',
  'Bojonegoro': 'Karesidenan Bojonegoro',
  'Tuban': 'Karesidenan Bojonegoro',
  'Lamongan': 'Karesidenan Bojonegoro',
  'Bangkalan': 'Karesidenan Madura',
  'Sampang': 'Karesidenan Madura',
  'Pamekasan': 'Karesidenan Madura',
  'Sumenep': 'Karesidenan Madura',
  'Kupang': 'Karesidenan Kupang'
};

var KAB_TO_PROVINSI = {
  'surabaya': 'Jawa Timur', 'sidoarjo': 'Jawa Timur', 'gresik': 'Jawa Timur',
  'malang': 'Jawa Timur', 'batu': 'Jawa Timur', 'pasuruan': 'Jawa Timur',
  'probolinggo': 'Jawa Timur', 'lumajang': 'Jawa Timur', 'kediri': 'Jawa Timur',
  'nganjuk': 'Jawa Timur', 'tulungagung': 'Jawa Timur', 'trenggalek': 'Jawa Timur',
  'blitar': 'Jawa Timur', 'madiun': 'Jawa Timur', 'ngawi': 'Jawa Timur',
  'magetan': 'Jawa Timur', 'ponorogo': 'Jawa Timur', 'pacitan': 'Jawa Timur',
  'bojonegoro': 'Jawa Timur', 'tuban': 'Jawa Timur', 'lamongan': 'Jawa Timur',
  'jombang': 'Jawa Timur', 'mojokerto': 'Jawa Timur', 'jember': 'Jawa Timur',
  'banyuwangi': 'Jawa Timur', 'bondowoso': 'Jawa Timur', 'situbondo': 'Jawa Timur',
  'pamekasan': 'Jawa Timur', 'sampang': 'Jawa Timur', 'sumenep': 'Jawa Timur',
  'bangkalan': 'Jawa Timur',
  'jakarta': 'DKI Jakarta',
  'bandung': 'Jawa Barat', 'bogor': 'Jawa Barat', 'bekasi': 'Jawa Barat',
  'depok': 'Jawa Barat', 'cirebon': 'Jawa Barat', 'tasikmalaya': 'Jawa Barat',
  'sukabumi': 'Jawa Barat', 'karawang': 'Jawa Barat',
  'semarang': 'Jawa Tengah', 'solo': 'Jawa Tengah', 'surakarta': 'Jawa Tengah',
  'tegal': 'Jawa Tengah', 'pekalongan': 'Jawa Tengah', 'magelang': 'Jawa Tengah',
  'yogyakarta': 'DI Yogyakarta', 'sleman': 'DI Yogyakarta', 'bantul': 'DI Yogyakarta',
  'denpasar': 'Bali', 'badung': 'Bali', 'gianyar': 'Bali',
  'mataram': 'Nusa Tenggara Barat', 'lombok': 'Nusa Tenggara Barat',
  'kupang': 'Nusa Tenggara Timur'
};

// Urutan key dipertahankan sama seperti dict ALIASES pada Python.
var ALIASES_ORDER = [
  'year', 'semester', 'main_dealer', 'layer', 'karesidenan', 'kab_kota',
  'dealer_code', 'profile', 'gender', 'age', 'motor_type', 'ses',
  'payment', 'retention', 'nps', 'nps_unit', 'nps_dealer', 'importance'
];

var ALIASES = {
  year: ['year', 'tahun'],
  semester: ['semester', 'periode'],
  main_dealer: ['main dealer', 'md code', 'maindealer', 'kode main dealer'],
  layer: ['layer'],
  karesidenan: ['karesidenan', 'keresidenan', 'residency'],
  kab_kota: [
    'kab/kota', 'kabupaten/kota', 'kab kota', 'city of dealer',
    'city of ahass', 'city of parts shop', 'city', 'kota', 'kabupaten'
  ],
  dealer_code: [
    'dealer code', 'kode dealer', 'ahass code', 'kode ahass',
    'parts shop code', 'kode part shop', 'dealer', 'ahass', 'part shop'
  ],
  profile: ['profile', 'profil'],
  gender: ['gender', 'jenis kelamin'],
  age: ['age group', 'age', 'usia', 'kelompok usia'],
  motor_type: [
    'type of motorcycle', 'variant of motorcycle', 'type of parts',
    'type motor', 'tipe motor', 'jenis motor', 'merk', 'segment'
  ],
  ses: ['ses'],
  payment: [
    'd15', 'd12', 'd6', 'd7', 'payment', 'tipe pembayaran', 'metode pembayaran',
    'method of payment', 'method of purchasing', 'cara pembayaran'
  ],
  retention: [
    'retention unit', 'retention service', 'retention part', 'retention level',
    'retention', 'retensi pelanggan', 'retensi'
  ],
  nps: ['nps'],
  nps_unit: ['nps_unit', 'nps unit'],
  nps_dealer: ['nps_dealer', 'nps dealer', 'nps ahass', 'nps part shop', 'nps part'],
  importance: ['importance']
};

// Indikator hanya untuk metadata matriks, tidak masuk perhitungan CSL.
var EXCLUDED_CALCULATION_INDICATORS = {
  sales: ['E16', 'E17', 'F19', 'F20', 'B8', 'C13'],
  service: ['D14', 'C11', 'A4'],
  parts: ['G21', 'D10', 'D12', 'D14', 'D13']
};

// ============================================================
// MOTOR MAPPING & CANONICALIZATION
// ============================================================

var MOTOR_MASTER = [
  'Beat', 'Beat Street', 'Genio', 'Scoopy', 'Vario 125',
  'Vario 125 Street', 'Vario Evo 160', 'Stylo 160', 'PCX 160',
  'ADV 160', 'Forza', 'CB150 Verza', 'Sonic 150R',
  'CB150R StreetFire', 'SB150X', 'CRF150L', 'CBR150R',
  'CBR250RR', 'CRF250L', 'ST125 Dax', 'Monkey',
  'CRF250 Rally', 'Revo', 'Supra X 125 FI', 'GTR 150',
  'Super Cub C125', 'CT125', 'ICON e:', 'EM1 e:', 'CUV e:'
];

var MOTOR_RANK = (function () {
  var r = {};
  for (var i = 0; i < MOTOR_MASTER.length; i++) r[MOTOR_MASTER[i]] = i;
  return r;
})();

var MOTOR_ALIAS = {
  // Beat
  beat: 'Beat',
  beatfi: 'Beat',
  beatesp: 'Beat',
  beatespcbsiss: 'Beat',
  beatespcbsseries: 'Beat',
  beatpopesp: 'Beat',
  beatdeluxe: 'Beat',
  beatdeluxesmartkey: 'Beat',
  beatcbs: 'Beat',
  beatfics: 'Beat',
  beatficw: 'Beat',
  beatsw: 'Beat',

  // Beat Street
  beatstreet: 'Beat Street',
  beatstreetfi: 'Beat Street',
  newbeatstreetesp: 'Beat Street',
  allnewbeatstreet: 'Beat Street',

  // Genio
  genio: 'Genio',
  geniocbs: 'Genio',
  geniocbsiss: 'Genio',

  // Scoopy
  scoopy: 'Scoopy',
  scoopyfisporty: 'Scoopy',
  scoopyfistylish: 'Scoopy',
  allnewscoopy: 'Scoopy',
  allnewscoopy2025: 'Scoopy',
  allnewscoopy2025smartkeytype: 'Scoopy',
  allnewscoopy2025cbstype: 'Scoopy',
  allnewscoopynewgenerationengine: 'Scoopy',
  allnewscoopynewgenerationenginesmartkeytype: 'Scoopy',
  allnewhondascoopyespsporty: 'Scoopy',
  allnewhondascoopyespstylish: 'Scoopy',

  // Vario 125
  vario125: 'Vario 125',
  vario125cbs: 'Vario 125',
  variotechno125pgmfi: 'Vario 125',
  variotechno125pgmficbs: 'Vario 125',
  vario125cbsidlingstopsystem: 'Vario 125',

  // Vario 125 Street
  vario125street: 'Vario 125 Street',

  // Vario 160
  vario160: 'Vario Evo 160',
  varioevo160: 'Vario Evo 160',
  vario160cbs: 'Vario Evo 160',
  vario160abs: 'Vario Evo 160',

  // Stylo
  stylo160: 'Stylo 160',
  stylo160abs: 'Stylo 160',
  stylo160cbs: 'Stylo 160',

  // PCX
  pcx: 'PCX 160',
  pcx160: 'PCX 160',
  allnewpcx160: 'PCX 160',
  allnewpcx160cbs: 'PCX 160',
  allnewpcx160abs: 'PCX 160',
  allnewpcx1602025cbstype: 'PCX 160',
  allnewpcx1602025roadsynctype: 'PCX 160',
  pcxhybrid: 'PCX 160',
  pcx150: 'PCX 160',
  allnewpcx150: 'PCX 160',

  // ADV
  adv: 'ADV 160',
  adv160: 'ADV 160',
  adv160abs: 'ADV 160',
  adv160cbs: 'ADV 160',
  adv160roadsync: 'ADV 160',

  // Forza
  forza: 'Forza',

  // Verza
  verza: 'CB150 Verza',
  verza150cw: 'CB150 Verza',
  cb150verza: 'CB150 Verza',
  cb150verzasw: 'CB150 Verza',

  // Sonic
  sonic: 'Sonic 150R',
  sonic150r: 'Sonic 150R',

  // CB150R StreetFire
  streetfire: 'CB150R StreetFire',
  cb150rstreetfire: 'CB150R StreetFire',

  // CB150X
  cb150x: 'SB150X',
  sb150x: 'SB150X',

  // CRF150L
  crf150: 'CRF150L',
  crf150l: 'CRF150L',

  // CBR150R
  cbr150: 'CBR150R',
  cbr150r: 'CBR150R',

  // CBR250RR
  cbr250rr: 'CBR250RR',

  // CRF250L
  crf250: 'CRF250L',
  crf250l: 'CRF250L',

  // ST125 Dax
  st125dax: 'ST125 Dax',
  dax: 'ST125 Dax',

  // Monkey
  monkey: 'Monkey',

  // CRF250 Rally
  crf250rally: 'CRF250 Rally',

  // Revo
  revo: 'Revo',
  revofit: 'Revo',
  revofi: 'Revo',
  revofisw: 'Revo',
  revox: 'Revo',

  // Supra X 125
  suprax125: 'Supra X 125 FI',
  suprax125fi: 'Supra X 125 FI',
  newsuprax125fi: 'Supra X 125 FI',
  newsuprax125fisw: 'Supra X 125 FI',
  newsuprax125rcw: 'Supra X 125 FI',
  newsuprax125ficw: 'Supra X 125 FI',

  // GTR
  gtr150: 'GTR 150',

  // Super Cub
  supercub: 'Super Cub C125',
  supercubc125: 'Super Cub C125',

  // CT125
  ct125: 'CT125',

  // Electric
  icone: 'ICON e:',
  em1e: 'EM1 e:',
  cuve: 'CUV e:'
};

var MOTOR_KEYWORD_RULES = [
  // Harus yang lebih spesifik diletakkan lebih dahulu
  ['beatstreet', 'Beat Street'],
  ['beat', 'Beat'],

  ['vario125street', 'Vario 125 Street'],
  ['vario125', 'Vario 125'],

  ['vario160', 'Vario Evo 160'],
  ['varioevo160', 'Vario Evo 160'],

  ['stylo160', 'Stylo 160'],
  ['stylo', 'Stylo 160'],

  ['scoopy', 'Scoopy'],
  ['genio', 'Genio'],
  ['forza', 'Forza'],

  ['pcx', 'PCX 160'],

  ['adv160', 'ADV 160'],
  ['adv', 'ADV 160'],

  ['cb150verza', 'CB150 Verza'],
  ['verza', 'CB150 Verza'],

  ['sonic150r', 'Sonic 150R'],
  ['sonic', 'Sonic 150R'],

  ['cb150rstreetfire', 'CB150R StreetFire'],
  ['streetfire', 'CB150R StreetFire'],

  ['cb150x', 'SB150X'],
  ['sb150x', 'SB150X'],

  ['crf150l', 'CRF150L'],
  ['crf150', 'CRF150L'],

  ['cbr150r', 'CBR150R'],
  ['cbr150', 'CBR150R'],

  ['cbr250rr', 'CBR250RR'],

  // CRF250 Rally harus sebelum CRF250L
  ['crf250rally', 'CRF250 Rally'],
  ['crf250l', 'CRF250L'],
  ['crf250', 'CRF250L'],

  ['st125dax', 'ST125 Dax'],
  ['dax', 'ST125 Dax'],

  ['monkey', 'Monkey'],

  ['revo', 'Revo'],

  ['suprax125', 'Supra X 125 FI'],

  ['gtr150', 'GTR 150'],

  ['supercubc125', 'Super Cub C125'],
  ['supercub', 'Super Cub C125'],

  ['ct125', 'CT125'],

  ['icone', 'ICON e:'],
  ['em1e', 'EM1 e:'],
  ['cuve', 'CUV e:']
];

// ============================================================
// SES / RETENTION / PERIODE — label, urutan, dan warna
// (dipindahkan dari _stacked_pct agar isi legend tetap identik)
// ============================================================

var SES_ORDER = ['A', 'A2', 'B', 'C1', 'C2', 'D', 'E'];

var SES_RANGES = {
  'A': '> Rp6 juta',
  'A2': 'Rp4–6 juta',
  'B': 'Rp2,5–4 juta',
  'C1': 'Rp1,75–2,5 juta',
  'C2': 'Rp1,25–1,75 juta',
  'D': 'Rp0,9–1,25 juta',
  'E': '≤ Rp0,9 juta'
};

var SES_COLORS = (function () {
  var palette = ['#1E88E5', GREEN, '#8BC34A', '#C0CA33', YELLOW, ORANGE, RED];
  var out = {};
  for (var i = 0; i < SES_ORDER.length; i++) out[SES_ORDER[i]] = palette[i];
  return out;
})();

var RETENTION_LABELS = {
  1: 'Sangat tidak mungkin membeli kembali',
  2: 'Kurang mungkin membeli kembali',
  3: 'Cukup mungkin membeli kembali',
  4: 'Mungkin membeli kembali',
  5: 'Sangat mungkin membeli kembali'
};

var RETENTION_COLORS = {
  1: RED,
  2: '#F4511E',
  3: YELLOW,
  4: '#9CCC65',
  5: GREEN
};

var PERIOD_ORDER = [
  'Kurang dari 6 bulan',
  '7–12 bulan lagi',
  '1–2 tahun',
  '2–3 tahun',
  '3–4 tahun',
  'Lebih dari 4 tahun'
];

var CATEGORY_GRADIENT = [GREEN, '#7CB342', YELLOW, ORANGE, '#F4511E', RED, '#C8102E'];
var GENERIC_PALETTE = [RED, ORANGE, YELLOW, GREEN, '#1E88E5', '#8E24AA', '#D81B60'];

// Rentang SES pada ringkasan profil (memuat A1 juga, sesuai Python).
var SES_RANGES_INSIGHT = {
  'A': '> Rp6 juta',
  'A1': '> Rp6 juta',
  'A2': 'Rp4–6 juta',
  'B': 'Rp2,5–4 juta',
  'C1': 'Rp1,75–2,5 juta',
  'C2': 'Rp1,25–1,75 juta',
  'D': 'Rp0,9–1,25 juta',
  'E': '≤ Rp0,9 juta'
};

// ============================================================
// UNIT PAGE CONFIG
// ============================================================

var UNIT_CONFIG = {
  sales: { unitLabel: 'Sales', sheet: 'sales_respondent', dealerLabel: 'Dealer', hLabel: 'H1' },
  service: { unitLabel: 'Service', sheet: 'service_respondent', dealerLabel: 'AHASS', hLabel: 'H2' },
  parts: { unitLabel: 'Spare Part', sheet: 'parts_respondent', dealerLabel: 'Part Shop', hLabel: 'H3' }
};

var PAGE_OPTIONS = ['H1 SALES', 'H2 SERVICE', 'H3 SPARE PART', 'PROFIL WILAYAH', 'FRAMEWORK'];

// ============================================================
// REGION / PROFIL WILAYAH (CLUSTER BPS & KELOMPOK BUDAYA)
// ============================================================

var RW_CLUSTER_SHEET = 'Hasil_Cluster';
var RW_CULTURE_SHEET_CANDIDATES = ['Pengelompokkan_budaya', 'pengelompokkan_budaya', 'pengelompokan_budaya'];
var RW_CLUSTER_COLUMN = 'Cluster_k3';
var RW_CLUSTER_PROFILE_COLUMN = 'Profil_k3';
var RW_CLUSTER_REGION_COLUMN = 'Kabupaten/Kota';

var RW_H_CONFIG = {
  H1: { sheet: 'sales_respondent', region_column: 'City of Dealer', profile_column: 'Profile', metadata_sheet: 'profile_metadata_H1', title: 'Sales' },
  H2: { sheet: 'service_respondent', region_column: 'City of AHASS', profile_column: 'Profile', metadata_sheet: 'profile_metadata_H2', title: 'Service' },
  H3: { sheet: 'parts_respondent', region_column: 'City of Parts Shop', profile_column: 'Profile', metadata_sheet: 'profile_metadata_H3', title: 'Spare Part' }
};

var RW_PROFILE_ORDER = [1, 2, 3, 4, 5];

var RW_PROFILE_COLORS = { 1: RED, 2: ORANGE, 3: YELLOW, 4: '#9CCC65', 5: GREEN };

var RW_CLUSTER_PROFILE_COLORS = (function () {
  var out = {};
  for (var i = 0; i < RW_PROFILE_ORDER.length; i++) {
    var p = RW_PROFILE_ORDER[i];
    out['Profile ' + p] = RW_PROFILE_COLORS[p];
  }
  return out;
})();

var RW_MINIMUM_RESPONDENTS = 30;

var RW_CLUSTERING_VARIABLES = [
  ['Kepadatan penduduk', 'Jumlah penduduk dibagi luas wilayah.'],
  ['Proporsi usia produktif', 'Penduduk usia produktif dibanding total penduduk.'],
  ['Motor per 1.000 penduduk', 'Populasi sepeda motor per 1.000 penduduk.'],
  ['Mobil per 1.000 penduduk', 'Populasi mobil per 1.000 penduduk.'],
  ['PDRB per kapita', 'Total PDRB sembilan sektor dibanding jumlah penduduk.'],
  ['Proporsi sektor primer', 'PDRB pertanian + pertambangan dibanding total PDRB.'],
  ['Proporsi sektor sekunder', 'PDRB manufaktur + listrik + konstruksi dibanding total PDRB.'],
  ['UMK', 'Upah Minimum Kabupaten/Kota.'],
  ['Persentase penduduk miskin', 'Persentase penduduk miskin BPS.'],
  ['TPT', 'Tingkat Pengangguran Terbuka.']
];

var RW_CLUSTER_EXPLANATIONS = {
  'Metropolitan Ekonomi Tinggi': {
    description: 'Wilayah pada cluster ini memiliki karakteristik perkotaan yang kuat, ' +
      'ditandai dengan kepadatan penduduk, PDRB per kapita, tingkat upah, ' +
      'serta jumlah kendaraan yang relatif tinggi. Di sisi lain, persentase ' +
      'penduduk miskinnya relatif lebih rendah dibandingkan wilayah lain.',
    character: 'Kepadatan penduduk tinggi · PDRB per kapita tinggi · ' +
      'Upah tinggi · Jumlah kendaraan tinggi · Kemiskinan relatif rendah'
  },

  'Industri Berupah Tinggi': {
    description: 'Wilayah pada cluster ini memiliki aktivitas ekonomi yang banyak didukung ' +
      'oleh sektor sekunder seperti industri, manufaktur, listrik, dan konstruksi. ' +
      'Tingkat upahnya relatif tinggi, sedangkan peran sektor primer seperti ' +
      'pertanian dan pertambangan relatif lebih rendah.',
    character: 'Sektor industri kuat · Upah relatif tinggi · ' +
      'Sektor primer relatif lebih rendah'
  },

  'Nonmetropolitan Berbasis Primer': {
    description: 'Wilayah pada cluster ini memiliki karakteristik yang relatif lebih ' +
      'nonmetropolitan dibandingkan dua cluster lainnya dan kegiatan ekonominya ' +
      'cenderung lebih bertumpu pada sektor primer.',
    character: 'Karakter nonmetropolitan · Peran sektor primer relatif lebih kuat'
  }
};

var RW_CULTURE_INFO = {
  arek: {
    description: 'Budaya urban-pesisir, egaliter, dan lugas.',
    character: 'Terbuka, berani, spontan, egaliter, dan guyub.'
  },
  mataraman: {
    description: 'Dipengaruhi budaya Jawa pedalaman/Mataram.',
    character: 'Halus, santun, menghormati tata krama, dan menjaga harmoni.'
  },
  pendalungan: {
    description: 'Percampuran budaya Jawa dan Madura.',
    character: 'Adaptif, terbuka, pekerja keras, dan multikultural.'
  },
  madura: {
    description: 'Budaya Madura dengan bahasa, tradisi, dan ikatan kekerabatan yang kuat.',
    character: 'Tegas, berani, pekerja keras, menjunjung harga diri dan solidaritas.'
  },
  using: {
    description: 'Budaya asli Banyuwangi dengan bahasa dan kesenian khas.',
    character: 'Memegang tradisi, ekspresif, kuat dalam seni dan identitas lokal.'
  },
  tengger: {
    description: 'Masyarakat Tengger dengan tradisi dan adat khas pegunungan.',
    character: 'Komunal, menjaga adat, gotong royong, dan kuat pada tradisi.'
  },
  ntt: {
    description: 'Sangat beragam, termasuk Timor, Flores, Sumba, Rote, Alor, Sabu, dan lainnya.',
    character: 'Komunal, kekeluargaan, kuat pada adat, solidaritas, dan penghormatan terhadap leluhur.'
  }
};

// Alias disesuaikan dengan bentuk nama wilayah pada file cluster BPS.
var RW_REGION_ALIASES = {
  'surabaya': 'Kota Surabaya',
  'kota surabaya': 'Kota Surabaya',
  'kota malang': 'Kota Malang',
  'kabupaten malang': 'Kabupaten Malang',
  'kab malang': 'Kabupaten Malang',
  'blitar': 'Kab-Kodya Blitar',
  'kab kodya blitar': 'Kab-Kodya Blitar',
  'kab-kodya blitar': 'Kab-Kodya Blitar',
  'kabupaten blitar': 'Kab-Kodya Blitar',
  'kota blitar': 'Kab-Kodya Blitar',
  'kediri': 'Kediri',
  'kabupaten kediri': 'Kediri',
  'kota kediri': 'Kediri',
  'kab kodya kediri': 'Kediri',
  'probolinggo': 'Probolinggo',
  'kabupaten probolinggo': 'Probolinggo',
  'kota probolinggo': 'Probolinggo',
  'kab kodya probolinggo': 'Probolinggo',
  'mojokerto': 'Mojokerto',
  'kabupaten mojokerto': 'Mojokerto',
  'kota mojokerto': 'Mojokerto',
  'kab kodya mojokerto': 'Mojokerto',
  'pasuruan': 'Pasuruan',
  'kabupaten pasuruan': 'Pasuruan',
  'kota pasuruan': 'Pasuruan',
  'kab kodya pasuruan': 'Pasuruan',
  'madiun': 'Madiun',
  'kabupaten madiun': 'Madiun',
  'kota madiun': 'Madiun',
  'kab kodya madiun': 'Madiun',
  'sidoarjo': 'Sidoarjo',
  'kabupaten sidoarjo': 'Sidoarjo',
  'pamekasan': 'Pamekasan',
  'kabupaten pamekasan': 'Pamekasan',
  'trenggalek': 'Trenggalek',
  'kabupaten trenggalek': 'Trenggalek',
  'nganjuk': 'Nganjuk',
  'kabupaten nganjuk': 'Nganjuk',
  'lamongan': 'Lamongan',
  'kabupaten lamongan': 'Lamongan',
  'jember': 'Jember',
  'kabupaten jember': 'Jember',
  'lumajang': 'Lumajang',
  'kabupaten lumajang': 'Lumajang',
  'bojonegoro': 'Bojonegoro',
  'kabupaten bojonegoro': 'Bojonegoro',
  'bangkalan': 'Bangkalan',
  'kabupaten bangkalan': 'Bangkalan',
  'jombang': 'Jombang',
  'kabupaten jombang': 'Jombang',
  'banyuwangi': 'Banyuwangi',
  'kabupaten banyuwangi': 'Banyuwangi',
  'gresik': 'Gresik',
  'kabupaten gresik': 'Gresik',
  'situbondo': 'Situbondo',
  'kabupaten situbondo': 'Situbondo',
  'tulungagung': 'Tulungagung',
  'kabupaten tulungagung': 'Tulungagung',
  'sumenep': 'Sumenep',
  'kabupaten sumenep': 'Sumenep',
  'magetan': 'Magetan',
  'kabupaten magetan': 'Magetan',
  'pacitan': 'Pacitan',
  'kabupaten pacitan': 'Pacitan',
  'ngawi': 'Ngawi',
  'kabupaten ngawi': 'Ngawi',
  'ponorogo': 'Ponorogo',
  'kabupaten ponorogo': 'Ponorogo',
  'tuban': 'Tuban',
  'kabupaten tuban': 'Tuban',
  'bondowoso': 'Bondowoso',
  'kabupaten bondowoso': 'Bondowoso',
  'sampang': 'Sampang',
  'kabupaten sampang': 'Sampang',
  'kupang': 'Kupang',
  'kabupaten kupang': 'Kupang',
  'kota kupang': 'Kupang'
};

// ============================================================
// BERKAS ASAL: 01_Sheets.gs
// ============================================================

/**
 * ============================================================
 * 01_Sheets.gs
 * Pengganti read_sheet() / try_read_sheet() versi Python.
 *
 * Python membaca worksheet lewat gviz CSV lalu pandas.read_csv.
 * Di Apps Script worksheet dibaca langsung dengan SpreadsheetApp,
 * tetapi perilakunya dibuat sama persis:
 *   - header di-strip spasinya
 *   - nama kolom duplikat diberi suffix .1, .2, ... seperti pandas
 *     (penting untuk "Reasons NPS.1" pada H2 dan H3)
 *   - sel kosong dianggap missing value (padanan NaN)
 * ============================================================
 */

// Memo per-eksekusi supaya satu request tidak membaca sheet berulang kali.
var SHEET_MEMO_ = {};

/**
 * Membaca satu worksheet menjadi bentuk "dataframe" sederhana:
 *   { columns: [nama kolom...], rows: [ {kolom: nilai}, ... ] }
 */
function readSheet_(sheetName) {
  if (Object.prototype.hasOwnProperty.call(SHEET_MEMO_, sheetName)) {
    return SHEET_MEMO_[sheetName];
  }

  var ss = SpreadsheetApp.openById(getSpreadsheetId_());
  var sheet = ss.getSheetByName(sheetName);

  if (!sheet) {
    throw new Error("Worksheet '" + sheetName + "' tidak ditemukan.");
  }

  var lastRow = sheet.getLastRow();
  var lastCol = sheet.getLastColumn();

  if (lastRow < 1 || lastCol < 1) {
    var kosong = { columns: [], rows: [] };
    SHEET_MEMO_[sheetName] = kosong;
    return kosong;
  }

  var values = sheet.getRange(1, 1, lastRow, lastCol).getValues();
  var header = values[0];

  // Nama kolom: strip spasi + mangle duplikat seperti pandas.
  var seen = {};
  var columns = [];
  for (var c = 0; c < header.length; c++) {
    var name = String(header[c] === null || header[c] === undefined ? '' : header[c]).trim();
    if (name === '') {
      // pandas memberi nama "Unnamed: n" untuk header kosong.
      name = 'Unnamed: ' + c;
    }
    if (Object.prototype.hasOwnProperty.call(seen, name)) {
      seen[name] += 1;
      columns.push(name + '.' + seen[name]);
    } else {
      seen[name] = 0;
      columns.push(name);
    }
  }

  var rows = [];
  for (var r = 1; r < values.length; r++) {
    var raw = values[r];
    var isEmptyRow = true;
    var obj = {};

    for (var i = 0; i < columns.length; i++) {
      var v = raw[i];
      if (v === '' || v === null || v === undefined) {
        obj[columns[i]] = null; // padanan NaN
      } else {
        obj[columns[i]] = v;
        isEmptyRow = false;
      }
    }

    // pandas melewati baris yang benar-benar kosong.
    if (!isEmptyRow) rows.push(obj);
  }

  var df = { columns: columns, rows: rows };
  SHEET_MEMO_[sheetName] = df;
  return df;
}

/**
 * Padanan try_read_sheet(): mengembalikan dataframe kosong bila gagal.
 * Pesan error dicatat pada log, tidak menghentikan proses.
 */
function tryReadSheet_(sheetName) {
  try {
    return readSheet_(sheetName);
  } catch (e) {
    Logger.log("Gagal membaca sheet '" + sheetName + "': " + e.message);
    return { columns: [], rows: [] };
  }
}

/** Padanan try_read_sheet_silent(). */
function tryReadSheetSilent_(sheetName) {
  try {
    return readSheet_(sheetName);
  } catch (e) {
    return { columns: [], rows: [] };
  }
}

/** Mencoba beberapa alternatif nama worksheet secara berurutan. */
function readFirstAvailableSheet_(sheetNames) {
  for (var i = 0; i < sheetNames.length; i++) {
    var df = tryReadSheetSilent_(sheetNames[i]);
    if (!isEmptyDf_(df)) return df;
  }
  return { columns: [], rows: [] };
}

function isEmptyDf_(df) {
  return !df || !df.rows || df.rows.length === 0;
}

function hasColumn_(df, column) {
  if (!df || !column) return false;
  for (var i = 0; i < df.columns.length; i++) {
    if (df.columns[i] === column) return true;
  }
  return false;
}

/** Membuat dataframe baru dari subset baris, kolom tetap sama. */
function subsetDf_(df, rows) {
  return { columns: df.columns, rows: rows };
}

/** Nilai dianggap ada (bukan NaN/None/kosong). */
function notNull_(v) {
  return v !== null && v !== undefined && v !== '';
}

/**
 * Padanan pd.to_numeric(errors="coerce").
 * Mengembalikan null bila tidak dapat dikonversi.
 */
function toNum_(v) {
  if (v === null || v === undefined || v === '') return null;
  if (typeof v === 'number') return isNaN(v) ? null : v;
  if (typeof v === 'boolean') return v ? 1 : 0;
  if (v instanceof Date) return v.getTime();
  var s = String(v).trim();
  if (s === '') return null;
  var n = Number(s);
  return isNaN(n) ? null : n;
}

/** String bersih untuk perbandingan/label. */
function toStr_(v) {
  if (v === null || v === undefined) return '';
  if (v instanceof Date) {
    return Utilities.formatDate(v, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  }
  return String(v);
}

/** Padanan round(x, n) Python untuk kebutuhan tampilan angka. */
function roundTo_(value, digits) {
  if (value === null || value === undefined || isNaN(value)) return null;
  var f = Math.pow(10, digits);
  return Math.round(value * f) / f;
}

/** Rata-rata dengan melewati nilai kosong (skipna seperti pandas). */
function meanSkipNa_(values) {
  var sum = 0;
  var n = 0;
  for (var i = 0; i < values.length; i++) {
    var v = values[i];
    if (v !== null && v !== undefined && !isNaN(v)) {
      sum += v;
      n += 1;
    }
  }
  return n === 0 ? null : sum / n;
}

/** Median seperti numpy.median. */
function median_(values) {
  var arr = [];
  for (var i = 0; i < values.length; i++) {
    if (values[i] !== null && !isNaN(values[i])) arr.push(values[i]);
  }
  if (!arr.length) return null;
  arr.sort(function (a, b) { return a - b; });
  var mid = Math.floor(arr.length / 2);
  return arr.length % 2 ? arr[mid] : (arr[mid - 1] + arr[mid]) / 2;
}

/**
 * Padanan Series.value_counts(): urut dari frekuensi terbesar.
 * Untuk frekuensi sama, urutan kemunculan pertama dipertahankan
 * (pandas juga stabil pada implementasi saat ini).
 */
function valueCounts_(values) {
  var counts = {};
  var order = [];
  for (var i = 0; i < values.length; i++) {
    var key = values[i];
    if (!Object.prototype.hasOwnProperty.call(counts, key)) {
      counts[key] = 0;
      order.push(key);
    }
    counts[key] += 1;
  }
  var items = order.map(function (k, idx) {
    return { label: k, count: counts[k], seq: idx };
  });
  items.sort(function (a, b) {
    if (b.count !== a.count) return b.count - a.count;
    return a.seq - b.seq;
  });
  return items;
}

// ============================================================
// BERKAS ASAL: 02_Columns.gs
// ============================================================

/**
 * ============================================================
 * 02_Columns.gs
 * Porting dari bagian "COLUMN AUTO-DETECTION & HELPERS",
 * "INDICATOR METADATA", dan "PERIOD HELPERS" pada app_backend.py.
 * Logika pencarian kolom dan normalisasi nama wilayah dibuat sama
 * persis, termasuk urutan prioritas exact match lalu substring.
 * ============================================================
 */

/** Padanan find_col(): exact match dulu, baru substring, mengikuti urutan kandidat. */
function findCol_(df, candidates) {
  if (!df || !df.columns || df.rows.length === 0) return null;

  var lowerMap = {};
  for (var i = 0; i < df.columns.length; i++) {
    var key = String(df.columns[i]).trim().toLowerCase();
    if (!Object.prototype.hasOwnProperty.call(lowerMap, key)) {
      lowerMap[key] = df.columns[i];
    }
  }

  for (var a = 0; a < candidates.length; a++) {
    var candA = String(candidates[a]).trim().toLowerCase();
    if (Object.prototype.hasOwnProperty.call(lowerMap, candA)) return lowerMap[candA];
  }

  for (var b = 0; b < candidates.length; b++) {
    var candB = String(candidates[b]).trim().toLowerCase();
    for (var c = 0; c < df.columns.length; c++) {
      var colLower = String(df.columns[c]).trim().toLowerCase();
      if (colLower.indexOf(candB) !== -1) return df.columns[c];
    }
  }

  return null;
}

/** Padanan build_indicator_name_map(): KODE -> nama indikator. */
function buildIndicatorNameMap_(metaDf) {
  if (isEmptyDf_(metaDf)) return {};

  var codeCol = findCol_(metaDf, [
    'Kode_Indikator', 'kode indikator', 'Kode Indicator',
    'kode_indicator', 'indicator code', 'kode', 'code'
  ]);
  var nameCol = findCol_(metaDf, [
    'Nama_Indikator', 'nama indikator', 'Indicator Name',
    'nama_indicator', 'indicator', 'atribut', 'attribute',
    'description', 'keterangan'
  ]);

  if (!codeCol || !nameCol) return {};

  var result = {};
  for (var i = 0; i < metaDf.rows.length; i++) {
    var row = metaDf.rows[i];
    if (!notNull_(row[codeCol])) continue;
    var code = toStr_(row[codeCol]).trim().toUpperCase();
    var name = toStr_(row[nameCol]).trim();
    if (code && name && name.toLowerCase() !== 'nan') result[code] = name;
  }
  return result;
}

/** Padanan detect_columns(). */
function detectColumns_(df, unitKey) {
  var cols = {};

  for (var i = 0; i < ALIASES_ORDER.length; i++) {
    var logical = ALIASES_ORDER[i];
    var cand = ALIASES[logical].slice();

    if (logical === 'dealer_code') {
      if (unitKey === 'sales') cand = ['dealer code', 'kode dealer', 'dealer'].concat(cand);
      else if (unitKey === 'service') cand = ['ahass code', 'kode ahass', 'ahass'].concat(cand);
      else if (unitKey === 'parts') cand = ['parts shop code', 'kode part shop', 'part shop'].concat(cand);
    }

    if (logical === 'nps_dealer') {
      if (unitKey === 'sales') cand = ['nps dealer'].concat(cand);
      else if (unitKey === 'service') cand = ['nps ahass'].concat(cand);
      else if (unitKey === 'parts') cand = ['nps part shop'].concat(cand);
    }

    if (logical === 'nps') {
      // NPS umum dicari exact agar tidak tertukar dengan NPS Unit/Part Shop.
      var exactNps = null;
      for (var c = 0; c < df.columns.length; c++) {
        if (String(df.columns[c]).trim().toLowerCase() === 'nps') {
          exactNps = df.columns[c];
          break;
        }
      }
      cols[logical] = exactNps;
      continue;
    }

    cols[logical] = findCol_(df, cand);
  }

  return cols;
}

/** Padanan _norm(). */
function norm_(s) {
  if (!notNull_(s)) return '';
  return toStr_(s).trim().toLowerCase().replace(/^(kota|kabupaten|kab\.?)\s+/, '').trim();
}

/** Padanan _normalize_location_name(). */
function normalizeLocationName_(s) {
  if (!notNull_(s)) return '';
  var name = toStr_(s).trim().toLowerCase();
  name = name.replace(/\bkab-kodya\b/g, '');
  name = name.replace(/\b(kabupaten|kab|kodya|kota)\b\.?/g, '');
  name = name.replace(/\s+/g, ' ').trim();
  return name;
}

/** Padanan _normalize_exact_location(). */
function normalizeExactLocation_(s) {
  if (!notNull_(s)) return '';
  var name = toStr_(s).trim().toLowerCase();
  name = name.replace(/\bkab-kodya\b/g, '');
  name = name.replace(/\b(kabupaten|kab)\b\.?/g, '');
  name = name.replace(/\s+/g, ' ').trim();
  return name;
}

/** Padanan str.title() Python. */
function titleCase_(s) {
  return String(s).replace(/[A-Za-z]+/g, function (word) {
    return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
  });
}

/** Padanan _dashboard_region_name(): nama wilayah baku dashboard. */
function dashboardRegionName_(value) {
  if (!notNull_(value) || toStr_(value).trim() === '') return '';

  var raw = toStr_(value).trim().toLowerCase().replace(/[_\/]+/g, ' ');
  raw = raw.replace(/\s+/g, ' ').trim();
  var simple = normalizeLocationName_(raw);

  // Inset ditampilkan sebagai NTT, tetapi filter Kab/Kota mengikuti Kupang.
  if (simple === 'ntt' || simple === 'nusa tenggara timur' || simple.indexOf('kupang') !== -1) {
    return 'Kupang';
  }
  if (raw.indexOf('kota malang') !== -1 || raw.indexOf('kodya malang') !== -1) {
    return 'Kota Malang';
  }
  if (simple === 'malang' || simple === 'batu') return 'Malang';

  var mergedNames = {
    'mojokerto': 'Mojokerto', 'kediri': 'Kediri',
    'probolinggo': 'Probolinggo', 'pasuruan': 'Pasuruan',
    'madiun': 'Madiun', 'blitar': 'Kab-Kodya Blitar'
  };
  if (Object.prototype.hasOwnProperty.call(mergedNames, simple)) return mergedNames[simple];

  return titleCase_(simple);
}

/** Padanan add_karesidenan(): menambah kolom Karesidenan bila belum ada. */
function addKaresidenan_(df, cols) {
  if (isEmptyDf_(df)) return df;
  if (cols.karesidenan && hasColumn_(df, cols.karesidenan)) return df;

  var kabCol = cols.kab_kota;
  if (!kabCol || !hasColumn_(df, kabCol)) return df;

  var columns = df.columns.slice();
  if (columns.indexOf('Karesidenan') === -1) columns.push('Karesidenan');

  var rows = [];
  for (var i = 0; i < df.rows.length; i++) {
    var row = df.rows[i];
    var copy = {};
    for (var k in row) if (Object.prototype.hasOwnProperty.call(row, k)) copy[k] = row[k];
    var regionName = dashboardRegionName_(row[kabCol]);
    copy['Karesidenan'] = Object.prototype.hasOwnProperty.call(KARESIDENAN_MAP, regionName)
      ? KARESIDENAN_MAP[regionName]
      : 'Lainnya';
    rows.push(copy);
  }

  cols.karesidenan = 'Karesidenan';
  return { columns: columns, rows: rows };
}

/** Padanan kab_to_provinsi(). */
function kabToProvinsi_(kabValue) {
  var key = norm_(kabValue);
  return Object.prototype.hasOwnProperty.call(KAB_TO_PROVINSI, key) ? KAB_TO_PROVINSI[key] : null;
}

// ============================================================
// INDICATOR METADATA
// ============================================================

/** Padanan _canonical_unit_key(). */
function canonicalUnitKey_(unitKey) {
  var unit = String(unitKey || '').trim().toLowerCase();
  if (unit === 'h1') return 'sales';
  if (unit === 'h2') return 'service';
  if (unit === 'h3') return 'parts';
  return unit;
}

/** Padanan excluded_calculation_indicators(). */
function excludedCalculationIndicators_(unitKey) {
  var unit = canonicalUnitKey_(unitKey);
  return Object.prototype.hasOwnProperty.call(EXCLUDED_CALCULATION_INDICATORS, unit)
    ? EXCLUDED_CALCULATION_INDICATORS[unit]
    : [];
}

/** Padanan indicator_columns(). */
function indicatorColumns_(df, metaDf, unitKey) {
  if (isEmptyDf_(df)) return [];

  var excluded = excludedCalculationIndicators_(unitKey);
  var excludedSet = {};
  for (var e = 0; e < excluded.length; e++) excludedSet[excluded[e]] = true;

  if (!isEmptyDf_(metaDf)) {
    var codeCol = findCol_(metaDf, ['kode_indicator', 'code', 'kode', 'atribut', 'attribute']);
    if (codeCol) {
      var seen = {};
      var codes = [];
      for (var i = 0; i < metaDf.rows.length; i++) {
        var raw = metaDf.rows[i][codeCol];
        if (!notNull_(raw)) continue;
        var code = toStr_(raw).trim();
        if (Object.prototype.hasOwnProperty.call(seen, code)) continue;
        seen[code] = true;
        codes.push(code);
      }
      var out = [];
      for (var c = 0; c < codes.length; c++) {
        if (hasColumn_(df, codes[c]) && !excludedSet[codes[c].toUpperCase()]) out.push(codes[c]);
      }
      return out;
    }
  }

  var pattern = /^[A-Za-z]\d{1,2}$/;
  var fallback = [];
  for (var j = 0; j < df.columns.length; j++) {
    var name = String(df.columns[j]).trim();
    if (pattern.test(name) && !excludedSet[name.toUpperCase()]) fallback.push(df.columns[j]);
  }
  return fallback;
}

/** Padanan _canonical_main_dealer(). */
function canonicalMainDealer_(value) {
  var normalized = String(value === null || value === undefined ? '' : value)
    .toUpperCase().replace(/[^A-Z0-9]/g, '');
  if (normalized === 'M2Z' || normalized === 'M3Z') return normalized;
  return 'Semua';
}

/** Padanan _canonical_target_layer(). */
function canonicalTargetLayer_(value) {
  var normalized = String(value === null || value === undefined ? '' : value)
    .toUpperCase().replace(/[^A-Z0-9]/g, '');
  var aliases = {
    'BIGWING': 'BigWing',
    'WING': 'Wing',
    'REGULERH123': 'RegulerH123',
    'REGULARH123': 'RegulerH123',
    'REGULER123': 'RegulerH123',
    'REGULERH23': 'RegulerH23',
    'REGULARH23': 'RegulerH23',
    'REGULER23': 'RegulerH23'
  };
  return Object.prototype.hasOwnProperty.call(aliases, normalized) ? aliases[normalized] : '';
}

/** Padanan _find_target_col(): exact match toleran spasi/underscore. */
function findTargetCol_(metaDf, candidates) {
  if (isEmptyDf_(metaDf)) return null;

  var normalizedColumns = {};
  for (var i = 0; i < metaDf.columns.length; i++) {
    var key = String(metaDf.columns[i]).toLowerCase().replace(/[^a-z0-9]/g, '');
    if (!Object.prototype.hasOwnProperty.call(normalizedColumns, key)) {
      normalizedColumns[key] = metaDf.columns[i];
    }
  }

  for (var c = 0; c < candidates.length; c++) {
    var nc = String(candidates[c]).toLowerCase().replace(/[^a-z0-9]/g, '');
    if (Object.prototype.hasOwnProperty.call(normalizedColumns, nc)) return normalizedColumns[nc];
  }
  return null;
}

/** Padanan get_target_col(). */
function getTargetCol_(metaDf, mainDealer, layer) {
  var md = canonicalMainDealer_(mainDealer);
  var layerSuffix = canonicalTargetLayer_(layer);

  var candidates = [];
  if (layerSuffix) candidates.push('Target_' + md + '_' + layerSuffix);
  candidates.push('Target_' + md);
  candidates.push('Target');

  return findTargetCol_(metaDf, candidates);
}

// ============================================================
// PERIOD HELPERS
// ============================================================

/** Padanan _parse_semester(). */
function parseSemester_(val) {
  if (!notNull_(val)) return null;
  var s = toStr_(val).trim().toLowerCase();
  if (s.indexOf('2') !== -1) return 2;
  if (s.indexOf('1') !== -1) return 1;
  var n = toNum_(s);
  return n === null ? null : Math.trunc(n);
}

/** Padanan get_available_periods(). */
function getAvailablePeriods_(df, cols) {
  var yearCol = cols.year;
  var semCol = cols.semester;
  if (!yearCol || !semCol || isEmptyDf_(df)) return [];

  var seen = {};
  var periods = [];
  for (var i = 0; i < df.rows.length; i++) {
    var row = df.rows[i];
    if (!notNull_(row[yearCol]) || !notNull_(row[semCol])) continue;
    var year = toNum_(row[yearCol]);
    var sem = parseSemester_(row[semCol]);
    if (year === null || sem === null) continue;
    var key = Math.trunc(year) + '|' + sem;
    if (!seen[key]) {
      seen[key] = true;
      periods.push([Math.trunc(year), sem]);
    }
  }

  periods.sort(function (a, b) {
    if (a[0] !== b[0]) return a[0] - b[0];
    return a[1] - b[1];
  });
  return periods;
}

/** Padanan get_previous_period(). */
function getPreviousPeriod_(selectedYear, selectedSemester, availablePeriods) {
  if (selectedYear === null || selectedYear === undefined) return null;
  if (selectedSemester === null || selectedSemester === undefined) return null;

  var year = parseInt(selectedYear, 10);
  var sem = parseInt(selectedSemester, 10);
  if (isNaN(year) || isNaN(sem)) return null;
  if (!availablePeriods || !availablePeriods.length) return null;

  var idx = -1;
  for (var i = 0; i < availablePeriods.length; i++) {
    if (availablePeriods[i][0] === year && availablePeriods[i][1] === sem) {
      idx = i;
      break;
    }
  }
  if (idx <= 0) return null;
  return availablePeriods[idx - 1];
}

/** Padanan period_label(). */
function periodLabel_(year, sem) {
  return 'Semester ' + sem + ' ' + year;
}

// ============================================================
// FILTER HELPERS
// ============================================================

/** Padanan _options(): nilai unik terurut sebagai string. */
function options_(df, col) {
  if (!col || !hasColumn_(df, col)) return [];
  var seen = {};
  var vals = [];
  for (var i = 0; i < df.rows.length; i++) {
    var v = df.rows[i][col];
    if (!notNull_(v)) continue;
    var s = toStr_(v);
    if (!seen[s]) {
      seen[s] = true;
      vals.push(s);
    }
  }
  vals.sort();
  return vals;
}

/** Padanan _fmt_pct(): 42.0 -> "42%", 42.3 -> "42.3%". */
function fmtPct_(value) {
  if (value === null || value === undefined || isNaN(value)) return '';
  var v = roundTo_(Number(value), 1);
  if (Math.abs(v - Math.round(v)) < 1e-9) return String(Math.round(v)) + '%';
  return v.toFixed(1) + '%';
}

/** Padanan _entity_name_column(). */
function entityNameColumn_(df, keyPrefix, dealerLabel) {
  if (isEmptyDf_(df)) return null;

  var unit = String(keyPrefix || '').trim().toLowerCase();
  var label = String(dealerLabel || '').trim().toLowerCase();
  var candidates;

  if (unit === 'sales' || label.indexOf('dealer') !== -1) {
    candidates = ['Dealer Name', 'Name of Dealer', 'Nama Dealer', 'Dealer_Name', 'dealer name'];
  } else if (unit === 'service' || label.indexOf('ahass') !== -1) {
    candidates = ['AHASS Name', 'Name of AHASS', 'Nama AHASS', 'AHASS_Name', 'ahass name'];
  } else {
    candidates = [
      'Parts Shop Name', 'Part Shop Name', 'Name of Parts Shop',
      'Nama Parts Shop', 'Nama Part Shop', 'Parts_Shop_Name',
      'parts shop name', 'part shop name'
    ];
  }

  // Exact match diprioritaskan agar kolom kode tidak salah terdeteksi.
  var exact = {};
  for (var i = 0; i < df.columns.length; i++) {
    var key = String(df.columns[i]).trim().toLowerCase().replace(/\s+/g, ' ');
    if (!Object.prototype.hasOwnProperty.call(exact, key)) exact[key] = df.columns[i];
  }
  for (var c = 0; c < candidates.length; c++) {
    var ck = candidates[c].trim().toLowerCase().replace(/\s+/g, ' ');
    if (Object.prototype.hasOwnProperty.call(exact, ck)) return exact[ck];
  }

  return findCol_(df, candidates);
}

/** Padanan _find_exact_data_col(). */
function findExactDataCol_(df, columnName) {
  if (!df || !columnName) return null;
  var target = String(columnName).trim().toLowerCase().replace(/\s+/g, ' ');
  for (var i = 0; i < df.columns.length; i++) {
    var key = String(df.columns[i]).trim().toLowerCase().replace(/\s+/g, ' ');
    if (key === target) return df.columns[i];
  }
  return null;
}

// ============================================================
// BERKAS ASAL: 03_Calc.gs
// ============================================================

/**
 * ============================================================
 * 03_Calc.gs
 * Porting dari bagian "FILTERS" dan "CALCULATIONS" app_backend.py.
 * Rumus satisfaction, target gap, selisih semester, dan NPS
 * dipertahankan sama persis, termasuk pembulatannya.
 * ============================================================
 */

/**
 * Padanan apply_filters().
 * filters: {year, semester, main_dealer, layer, karesidenan, kab_kota, dealer}
 */
function applyFilters_(df, cols, filters, overrideYear, overrideSemester, ignorePeriod) {
  if (isEmptyDf_(df)) return df;

  var rows = df.rows;
  var yearCol = cols.year;
  var semCol = cols.semester;

  if (!ignorePeriod) {
    var yr = (overrideYear !== null && overrideYear !== undefined) ? overrideYear : filters.year;
    var sm = (overrideSemester !== null && overrideSemester !== undefined) ? overrideSemester : filters.semester;

    if (yr !== null && yr !== undefined && yearCol) {
      rows = rows.filter(function (r) { return toStr_(r[yearCol]) === String(yr); });
    }
    if (sm !== null && sm !== undefined && semCol) {
      rows = rows.filter(function (r) { return parseSemester_(r[semCol]) === sm; });
    }
  } else {
    if (overrideYear !== null && overrideYear !== undefined && yearCol) {
      rows = rows.filter(function (r) { return toStr_(r[yearCol]) === String(overrideYear); });
    }
    if (overrideSemester !== null && overrideSemester !== undefined && semCol) {
      rows = rows.filter(function (r) { return parseSemester_(r[semCol]) === overrideSemester; });
    }
  }

  var mapping = [
    ['main_dealer', cols.main_dealer],
    ['layer', cols.layer],
    ['karesidenan', cols.karesidenan],
    ['dealer', cols.dealer_code]
  ];

  for (var m = 0; m < mapping.length; m++) {
    var key = mapping[m][0];
    var col = mapping[m][1];
    var val = filters[key];
    if (val !== null && val !== undefined && val !== 'Semua' && col && hasColumn_(df, col)) {
      (function (c, v) {
        rows = rows.filter(function (r) { return toStr_(r[c]) === String(v); });
      })(col, val);
    }
  }

  var kabVal = filters.kab_kota;
  var kabCol = cols.kab_kota;
  if (kabVal !== null && kabVal !== undefined && kabCol && hasColumn_(df, kabCol)) {
    var target = dashboardRegionName_(kabVal);
    rows = rows.filter(function (r) { return dashboardRegionName_(r[kabCol]) === target; });
  }

  return subsetDf_(df, rows);
}

/** Padanan calculate_satisfaction(): rata-rata per responden, lalu dirata-rata. */
function calculateSatisfaction_(df, indicatorCols) {
  if (isEmptyDf_(df) || !indicatorCols || !indicatorCols.length) return null;

  var perRow = [];
  for (var i = 0; i < df.rows.length; i++) {
    var row = df.rows[i];
    var vals = [];
    for (var c = 0; c < indicatorCols.length; c++) {
      vals.push(toNum_(row[indicatorCols[c]]));
    }
    var rowMean = meanSkipNa_(vals);
    if (rowMean !== null) perRow.push(rowMean);
  }

  var meanScore = meanSkipNa_(perRow);
  if (meanScore === null) return null;
  return roundTo_(meanScore / 5 * 100, 1);
}

/** Padanan calculate_attribute_satisfaction(). */
function calculateAttributeSatisfaction_(df, indicatorCols) {
  var result = {};
  var order = [];
  if (isEmptyDf_(df) || !indicatorCols || !indicatorCols.length) {
    return { values: result, order: order };
  }

  for (var c = 0; c < indicatorCols.length; c++) {
    var col = indicatorCols[c];
    var vals = [];
    for (var i = 0; i < df.rows.length; i++) vals.push(toNum_(df.rows[i][col]));
    var m = meanSkipNa_(vals);
    if (m === null) continue;
    result[col] = roundTo_(m / 5 * 100, 1);
    order.push(col);
  }

  return { values: result, order: order };
}

/** Padanan calculate_target_gap(). */
function calculateTargetGap_(attrSat, metaDf, mainDealer, layer) {
  var gaps = { values: {}, order: [] };
  if (!attrSat || !attrSat.order.length || isEmptyDf_(metaDf)) return gaps;

  var codeCol = findCol_(metaDf, ['kode_indicator', 'code', 'kode', 'atribut', 'attribute']);
  var targetCol = getTargetCol_(metaDf, mainDealer, layer);
  if (!codeCol || !targetCol) return gaps;

  // Index metadata berdasarkan kode (ambil kemunculan pertama, seperti .loc).
  var metaIndexed = {};
  for (var i = 0; i < metaDf.rows.length; i++) {
    var code = toStr_(metaDf.rows[i][codeCol]).trim();
    if (code && !Object.prototype.hasOwnProperty.call(metaIndexed, code)) {
      metaIndexed[code] = metaDf.rows[i][targetCol];
    }
  }

  for (var o = 0; o < attrSat.order.length; o++) {
    var key = attrSat.order[o];
    var cCode = String(key).trim();
    if (!Object.prototype.hasOwnProperty.call(metaIndexed, cCode)) continue;

    var rawTarget = metaIndexed[cCode];
    var tVal;
    if (typeof rawTarget === 'number') {
      tVal = (rawTarget > 0 && rawTarget <= 1.5) ? rawTarget * 100 : rawTarget;
    } else {
      var tStr = toStr_(rawTarget).replace(/%/g, '').replace(/,/g, '.').trim();
      tVal = tStr === '' ? NaN : Number(tStr);
      if (!isNaN(tVal) && tVal > 0 && tVal <= 1.5 && toStr_(rawTarget).indexOf('%') === -1) {
        tVal = tVal * 100;
      }
    }
    if (isNaN(tVal)) continue;

    gaps.values[cCode] = roundTo_(attrSat.values[key] - tVal, 1);
    gaps.order.push(cCode);
  }

  return gaps;
}

/** Padanan calculate_semester_difference(). */
function calculateSemesterDifference_(dfCur, dfPrev, indicatorCols) {
  if (isEmptyDf_(dfPrev)) return null;

  var cur = calculateAttributeSatisfaction_(dfCur, indicatorCols);
  var prev = calculateAttributeSatisfaction_(dfPrev, indicatorCols);
  if (!prev.order.length) return null;

  var diffs = { values: {}, order: [] };
  for (var i = 0; i < cur.order.length; i++) {
    var code = cur.order[i];
    if (Object.prototype.hasOwnProperty.call(prev.values, code)) {
      diffs.values[code] = roundTo_(cur.values[code] - prev.values[code], 1);
      diffs.order.push(code);
    }
  }
  return diffs;
}

/** Padanan compute_nps(). */
function computeNps_(df, column) {
  if (!column || isEmptyDf_(df) || !hasColumn_(df, column)) return null;

  var promoters = 0;
  var detractors = 0;
  var total = 0;

  for (var i = 0; i < df.rows.length; i++) {
    var v = toNum_(df.rows[i][column]);
    if (v === null) continue;
    total += 1;
    if (v >= 9) promoters += 1;
    if (v <= 6) detractors += 1;
  }

  if (total === 0) return null;
  return roundTo_((promoters - detractors) / total * 100, 1);
}

/** Padanan compact_motor_key(). */
function compactMotorKey_(value) {
  return toStr_(value).toLowerCase().replace(/[^a-z0-9]+/g, '');
}

/** Padanan canonical_motor(). */
function canonicalMotor_(value) {
  var raw = toStr_(value).replace(/\s+/g, ' ').trim();
  if (!raw) return null;
  var low = raw.toLowerCase();
  if (low === 'nan' || low === 'none' || low === '-') return null;

  var keyNorm = compactMotorKey_(raw);
  if (Object.prototype.hasOwnProperty.call(MOTOR_ALIAS, keyNorm)) return MOTOR_ALIAS[keyNorm];

  for (var i = 0; i < MOTOR_KEYWORD_RULES.length; i++) {
    if (keyNorm.indexOf(MOTOR_KEYWORD_RULES[i][0]) !== -1) return MOTOR_KEYWORD_RULES[i][1];
  }

  return raw;
}

/** Padanan retention_score() pada _stacked_pct. */
function retentionScore_(value) {
  var textValue = toStr_(value).trim().toLowerCase();
  var numeric = toNum_(textValue.replace(/,/g, '.'));
  if (numeric !== null) {
    var score = Math.round(numeric);
    if (score >= 1 && score <= 5) return score;
  }
  if (textValue.indexOf('sangat tidak') !== -1 || textValue.indexOf('tidak mungkin') !== -1) return 1;
  if (textValue.indexOf('kurang') !== -1) return 2;
  if (textValue.indexOf('cukup') !== -1) return 3;
  if (textValue.indexOf('sangat mungkin') !== -1) return 5;
  if (textValue.indexOf('mungkin') !== -1) return 4;
  return null;
}

/** Padanan canonical_period() pada _stacked_pct. */
function canonicalPeriod_(value) {
  var raw = toStr_(value).replace(/\s+/g, ' ').trim();
  var low = raw.toLowerCase().replace(/–/g, '-').replace(/—/g, '-');

  if (/(<\s*6|kurang.*6|less.*6|0\s*[-\/]\s*6|1\s*[-\/]\s*6|sampai.*6)/.test(low)) {
    return 'Kurang dari 6 bulan';
  }
  if (/(7\s*[-\/]\s*12|6\s*[-\/]\s*12|7.*12)/.test(low) ||
      ((low.indexOf('bulan') !== -1 || low.indexOf('month') !== -1) && low.indexOf('12') !== -1)) {
    return '7–12 bulan lagi';
  }
  if (/1\s*[-\/]\s*2\s*(tahun|year)/.test(low) ||
      (low.indexOf('1') !== -1 && low.indexOf('2') !== -1 && (low.indexOf('tahun') !== -1 || low.indexOf('year') !== -1))) {
    return '1–2 tahun';
  }
  if (/2\s*[-\/]\s*3\s*(tahun|year)/.test(low) ||
      (low.indexOf('2') !== -1 && low.indexOf('3') !== -1 && (low.indexOf('tahun') !== -1 || low.indexOf('year') !== -1))) {
    return '2–3 tahun';
  }
  if (/3\s*[-\/]\s*4\s*(tahun|year)/.test(low) ||
      (low.indexOf('3') !== -1 && low.indexOf('4') !== -1 && (low.indexOf('tahun') !== -1 || low.indexOf('year') !== -1))) {
    return '3–4 tahun';
  }
  if ((low.indexOf('lebih') !== -1 || low.indexOf('more') !== -1 || low.indexOf('>') !== -1) &&
      (low.indexOf('tahun') !== -1 || low.indexOf('year') !== -1)) {
    return 'Lebih dari 4 tahun';
  }
  return raw;
}

/** Padanan purchase_location_key(): kunci pengurutan lokasi pembelian. */
function purchaseLocationKey_(value) {
  var low = toStr_(value).replace(/\s+/g, ' ').trim().toLowerCase();

  // 1. Showroom/dealer yang SAMA → paling kiri
  if (low.indexOf('yang sama') !== -1 || low.indexOf('dealer sama') !== -1 ||
      low.indexOf('showroom sama') !== -1 || low.indexOf('same dealer') !== -1 ||
      low.indexOf('same showroom') !== -1) {
    return [0, low];
  }

  // 2. Showroom/dealer yang BERBEDA → setelah yang sama
  if (low.indexOf('yang berbeda') !== -1 || low.indexOf('dealer berbeda') !== -1 ||
      low.indexOf('showroom berbeda') !== -1 || low.indexOf('different dealer') !== -1 ||
      low.indexOf('different showroom') !== -1) {
    return [1, low];
  }

  // 3. Belum tahu → paling kanan
  if (low.indexOf('belum tahu') !== -1 || low.indexOf('tidak tahu') !== -1 ||
      low.indexOf('tidak menentukan') !== -1) {
    return [2, low];
  }

  if (low.indexOf('online') !== -1 || low.indexOf('marketplace') !== -1) return [3, low];
  if (low.indexOf('pameran') !== -1 || low.indexOf('event') !== -1) return [4, low];
  if (low.indexOf('lain') !== -1) return [5, low];

  return [6, low];
}

/** Padanan age_sort_key() pada _age_group_hbar. */
function ageSortKey_(label) {
  var s = toStr_(label);
  var m = s.match(/(\d+)/);
  if (m) return parseInt(m[1], 10);
  if (s.indexOf('<') !== -1) return 0;
  if (s.indexOf('>') !== -1) return 999;
  return 500;
}

/** Nilai kolom sebagai daftar string bersih (dropna + astype(str)). */
function columnStrings_(df, col) {
  var out = [];
  if (!col || !hasColumn_(df, col)) return out;
  for (var i = 0; i < df.rows.length; i++) {
    var v = df.rows[i][col];
    if (!notNull_(v)) continue;
    out.push(toStr_(v));
  }
  return out;
}

/** Nilai kolom untuk _stacked_pct: strip + buang nan/none/"-". */
function stackedRawSeries_(df, col) {
  var out = [];
  if (!col || !hasColumn_(df, col)) return out;
  for (var i = 0; i < df.rows.length; i++) {
    var v = df.rows[i][col];
    if (!notNull_(v)) continue;
    var s = toStr_(v).trim();
    var low = s.toLowerCase();
    if (s === '' || low === 'nan' || low === 'none' || low === '-') continue;
    out.push(s);
  }
  return out;
}

/** Padanan dominant() pada render_overall_profile_insight. */
function dominant_(df, column, transform) {
  if (!column || !hasColumn_(df, column)) return null;

  var values = [];
  for (var i = 0; i < df.rows.length; i++) {
    var v = df.rows[i][column];
    if (!notNull_(v)) continue;
    var t = transform ? transform(v) : v;
    if (t === null || t === undefined) continue;
    var s = toStr_(t).trim();
    var low = s.toLowerCase();
    if (s === '' || low === 'nan' || low === 'none' || low === '-') continue;
    values.push(s);
  }

  if (!values.length) return null;

  var counts = valueCounts_(values);
  var label = String(counts[0].label);
  var count = counts[0].count;
  var pct = count / values.length * 100;
  return { label: label, count: count, pct: pct };
}

/** Padanan short_label(). */
function shortLabel_(value, maxLength) {
  maxLength = maxLength || 58;
  var v = toStr_(value).replace(/\s+/g, ' ').trim();
  if (v.length <= maxLength) return v;
  return v.slice(0, maxLength - 1).replace(/\s+$/, '') + '…';
}

/** Padanan retention_text() pada ringkasan profil. */
function retentionText_(value) {
  var text = toStr_(value).trim();
  var numeric = toNum_(text.replace(/,/g, '.'));

  var labels = {
    5: 'sangat mungkin membeli kembali',
    4: 'mungkin membeli kembali',
    3: 'cukup mungkin membeli kembali',
    2: 'kurang mungkin membeli kembali',
    1: 'sangat tidak mungkin membeli kembali'
  };

  if (numeric !== null) {
    var score = Math.round(numeric);
    if (Object.prototype.hasOwnProperty.call(labels, score)) return labels[score];
  }

  return text ? text.toLowerCase() : text;
}

/** Escape HTML, padanan html.escape() Python. */
function escapeHtml_(text) {
  return toStr_(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
}

// ============================================================
// BERKAS ASAL: 04_Charts.gs
// ============================================================

/**
 * ============================================================
 * 04_Charts.gs
 * Menyiapkan DATA untuk setiap chart persis seperti yang dihitung
 * di dalam fungsi render_* pada versi Streamlit.
 *
 * Yang dipindahkan ke sini hanya bagian penyiapan data:
 * urutan kategori, nilai persentase, jumlah responden, warna,
 * dan teks hover/legend. Penggambaran Plotly tetap di frontend,
 * sehingga bentuk chart tidak berubah sama sekali.
 * ============================================================
 */

// ============================================================
// SECTION 1 : KPI, SATISFACTION, TARGET GAP, SELISIH SEMESTER
// ============================================================

/** Padanan render_kpi_cards(): label dan warna KPI. */
function buildKpiCards_(satS1, satS2, nResponden) {
  function statusLabel(v) {
    var x = v === null || v === undefined ? 0 : v;
    return x >= 70 ? 'Baik' : (x >= 50 ? 'Cukup' : 'Kurang');
  }

  var cards = [];

  cards.push({
    label: 'Satisfaction Semester 1',
    value: satS1 !== null ? satS1.toFixed(1) + '%' : 'N/A',
    sub: satS1 !== null ? statusLabel(satS1) : '-',
    subColor: '#2E7D32'
  });

  cards.push({
    label: 'Satisfaction Semester 2',
    value: satS2 !== null ? satS2.toFixed(1) + '%' : 'N/A',
    sub: satS2 !== null ? statusLabel(satS2) : '-',
    subColor: '#2E7D32'
  });

  if (satS1 !== null && satS2 !== null) {
    var diff = roundTo_(satS2 - satS1, 1);
    var sign = diff >= 0 ? '+' : '';
    cards.push({
      label: 'Improvement',
      value: sign + diff.toFixed(1) + '%',
      sub: diff >= 0 ? 'Meningkat' : 'Menurun',
      subColor: diff >= 0 ? '#2E7D32' : '#C62828'
    });
  } else {
    cards.push({ label: 'Improvement', value: 'N/A', sub: '-', subColor: '#888888' });
  }

  cards.push({
    label: 'Jumlah Responden',
    value: nResponden !== null && nResponden !== undefined
      ? String(nResponden).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
      : 'N/A',
    sub: 'Responden',
    subColor: '#555555'
  });

  return cards;
}

/** Padanan render_satisfaction_chart(): data batang satisfaction per atribut. */
function buildSatisfactionChart_(attrSat, indicatorNames) {
  var items = [];
  for (var i = 0; i < attrSat.order.length; i++) {
    var code = attrSat.order[i];
    var value = attrSat.values[code];
    items.push({
      code: code,
      name: indicatorNames[String(code).trim().toUpperCase()] || 'Nama indikator belum tersedia',
      value: value,
      text: fmtPct_(value)
    });
  }
  var maxVal = items.length ? Math.max.apply(null, items.map(function (x) { return x.value; })) : 100;
  return {
    title: 'Satisfaction Score by Attribute',
    subtitle: 'Data ditampilkan berdasarkan filter yang dipilih',
    color: RED,
    items: items,
    xRangeMax: Math.max(112, maxVal + 12),
    height: Math.max(280, 26 * items.length)
  };
}

/** Padanan render_target_gap_chart(). */
function buildTargetGapChart_(gaps, attrSat, indicatorNames) {
  var items = [];
  for (var i = 0; i < gaps.order.length; i++) {
    var code = gaps.order[i];
    var gap = gaps.values[code];
    items.push({
      code: code,
      name: indicatorNames[String(code).trim().toUpperCase()] || 'Nama indikator belum tersedia',
      gap: gap,
      satisfaction: Object.prototype.hasOwnProperty.call(attrSat.values, code) ? attrSat.values[code] : null,
      color: gap >= 0 ? GREEN : RED,
      text: (gap >= 0 ? '+' : '') + gap.toFixed(1) + '%'
    });
  }

  var vals = items.map(function (x) { return x.gap; });
  var maxVal = vals.length ? Math.max.apply(null, vals) : 0;
  var minVal = vals.length ? Math.min.apply(null, vals) : 0;

  return {
    title: 'Performance vs Attribute Target',
    subtitle: 'Data ditampilkan berdasarkan filter yang dipilih',
    items: items,
    xMax: Math.max(0.1, maxVal + Math.max(0.12, Math.abs(maxVal) * 0.25)),
    xMin: Math.min(0, minVal - Math.max(0.05, Math.abs(minVal) * 0.25)),
    height: Math.max(280, 26 * items.length)
  };
}

/** Padanan render_semester_difference_chart(). */
function buildSemesterDifferenceChart_(diffs, subtitle, attrSat, indicatorNames) {
  if (diffs === null) {
    return {
      title: 'Satisfaction Semester Ini vs Semester Sebelumnya',
      subtitle: subtitle,
      available: false,
      message: 'Data periode sebelumnya tidak tersedia untuk filter ini.',
      items: []
    };
  }

  var items = [];
  for (var i = 0; i < diffs.order.length; i++) {
    var code = diffs.order[i];
    var value = diffs.values[code];
    items.push({
      code: code,
      name: indicatorNames[String(code).trim().toUpperCase()] || 'Nama indikator belum tersedia',
      diff: value,
      satisfaction: Object.prototype.hasOwnProperty.call(attrSat.values, code) ? attrSat.values[code] : null,
      color: value >= 0 ? GREEN : RED,
      text: (value >= 0 ? '+' : '') + value.toFixed(1) + '%'
    });
  }

  var vals = items.map(function (x) { return x.diff; });
  var maxVal = vals.length ? Math.max.apply(null, vals) : 0;
  var minVal = vals.length ? Math.min.apply(null, vals) : 0;

  return {
    title: 'Satisfaction Semester Ini vs Semester Sebelumnya',
    subtitle: subtitle,
    available: true,
    items: items,
    xMax: Math.max(0.1, maxVal + Math.max(0.12, Math.abs(maxVal) * 0.25)),
    xMin: Math.min(0, minVal - Math.max(0.05, Math.abs(minVal) * 0.25)),
    height: Math.max(280, 26 * items.length)
  };
}

// ============================================================
// SECTION 1 : PETA SATISFACTION
// ============================================================

/** Padanan _load_h123_by_location(): rata-rata satisfaction H1+H2+H3 per wilayah. */
function loadH123ByLocation_() {
  var result = {};
  var unitSources = [
    ['sales', 'sales_respondent', ['Indicator_metadata_H1', 'Indikator_metadata_H1']],
    ['service', 'service_respondent', ['Indicator_metadata_H2', 'Indikator_metadata_H2']],
    ['parts', 'parts_respondent', ['Indicator_metadata_H3', 'Indikator_metadata_H3']]
  ];

  for (var u = 0; u < unitSources.length; u++) {
    var sourceUnit = unitSources[u][0];
    var sourceSheet = unitSources[u][1];
    var metadataSheets = unitSources[u][2];

    var sourceDf = tryReadSheet_(sourceSheet);
    if (isEmptyDf_(sourceDf)) continue;

    var sourceCols = detectColumns_(sourceDf, sourceUnit);
    var sourceLocation = sourceCols.kab_kota;
    if (!sourceLocation || !hasColumn_(sourceDf, sourceLocation)) continue;

    var sourceMeta = readFirstAvailableSheet_(metadataSheets);
    var sourceIndicators = indicatorColumns_(sourceDf, sourceMeta, sourceUnit);

    var groups = {};
    for (var i = 0; i < sourceDf.rows.length; i++) {
      var row = sourceDf.rows[i];
      if (!notNull_(row[sourceLocation])) continue;
      var region = dashboardRegionName_(row[sourceLocation]);
      if (!groups[region]) groups[region] = [];
      groups[region].push(row);
    }

    for (var key in groups) {
      if (!Object.prototype.hasOwnProperty.call(groups, key)) continue;
      var sat = calculateSatisfaction_(subsetDf_(sourceDf, groups[key]), sourceIndicators);
      if (sat !== null) {
        if (!result[key]) result[key] = [];
        result[key].push(sat);
      }
    }
  }

  return result;
}

/** Padanan satisfaction_color() pada create_map(). */
function satisfactionColor_(value, scaleMin, scaleMax) {
  if (value === null || value === undefined || isNaN(value)) return '#D9DEE5';

  var ratio = (Number(value) - scaleMin) / (scaleMax - scaleMin);
  ratio = Math.max(0, Math.min(1, ratio));

  var stops = [[230, 0, 18], [255, 176, 0], [53, 168, 83]];
  var local, start, end;
  if (ratio <= 0.5) {
    local = ratio * 2; start = stops[0]; end = stops[1];
  } else {
    local = (ratio - 0.5) * 2; start = stops[1]; end = stops[2];
  }

  var hex = '#';
  for (var i = 0; i < 3; i++) {
    var v = Math.round(start[i] + (end[i] - start[i]) * local);
    var h = v.toString(16).toUpperCase();
    hex += h.length === 1 ? '0' + h : h;
  }
  return hex;
}

/**
 * Padanan create_map() bagian perhitungan.
 * Geometri tidak dihitung di sini: Apps Script tidak bisa membaca
 * shapefile, sehingga polygon diambil dari GeoJSON statis di frontend.
 * Yang dikirim adalah nilai per wilayah + warna + skala legenda,
 * sehingga tampilan peta tetap sama.
 */
function buildMapData_(unitKey, df, cols, indicatorCols) {
  var locationCol = cols.kab_kota;
  var profileCol = cols.profile;

  if (!locationCol || !hasColumn_(df, locationCol)) {
    return {
      available: false,
      message: 'Kolom kabupaten/kota pada data responden tidak ditemukan.',
      regions: []
    };
  }

  var hLabel = UNIT_CONFIG[unitKey] ? UNIT_CONFIG[unitKey].hLabel : '';

  // Satisfaction dan profil dominan per wilayah dari scope hasil filter.
  var groups = {};
  for (var i = 0; i < df.rows.length; i++) {
    var row = df.rows[i];
    if (!notNull_(row[locationCol])) continue;
    var region = dashboardRegionName_(row[locationCol]);
    if (!groups[region]) groups[region] = [];
    groups[region].push(row);
  }

  var h123 = loadH123ByLocation_();
  var regions = [];
  var satValues = [];

  for (var key in groups) {
    if (!Object.prototype.hasOwnProperty.call(groups, key)) continue;

    var groupDf = subsetDf_(df, groups[key]);
    var sat = calculateSatisfaction_(groupDf, indicatorCols);
    if (sat === null) continue;

    var dominantProfile = '-';
    if (profileCol && hasColumn_(groupDf, profileCol)) {
      var profileValues = [];
      for (var p = 0; p < groupDf.rows.length; p++) {
        var pv = groupDf.rows[p][profileCol];
        if (notNull_(pv)) profileValues.push(toStr_(pv).trim());
      }
      if (profileValues.length) dominantProfile = String(valueCounts_(profileValues)[0].label);
    }

    var h123Values = Object.prototype.hasOwnProperty.call(h123, key) ? h123[key] : [];
    var h123Mean = h123Values.length ? meanSkipNa_(h123Values) : null;

    satValues.push(sat);
    regions.push({
      region: key,
      satisfaction: sat,
      satisfactionText: sat.toFixed(1) + '%',
      cslH123: h123Mean,
      cslH123Text: h123Mean !== null ? h123Mean.toFixed(1) + '%' : 'Tidak ada data',
      dominantProfile: dominantProfile
    });
  }

  if (!satValues.length) {
    return {
      available: false,
      message: 'Nilai satisfaction per wilayah belum tersedia untuk filter yang dipilih.',
      regions: []
    };
  }

  var scaleMin = Math.min.apply(null, satValues);
  var scaleMax = Math.max.apply(null, satValues);
  if (Math.abs(scaleMin - scaleMax) < 1e-9) {
    scaleMin = Math.max(0, scaleMin - 1);
    scaleMax = Math.min(100, scaleMax + 1);
  }

  for (var r = 0; r < regions.length; r++) {
    regions[r].color = satisfactionColor_(regions[r].satisfaction, scaleMin, scaleMax);
  }

  return {
    available: true,
    hLabel: hLabel,
    tooltipAliases: ['Kabupaten/Kota:', 'Satisfaction ' + hLabel + ':', '%CSL H123:', 'Profile Dominan:'],
    regions: regions,
    scaleMin: scaleMin,
    scaleMax: scaleMax,
    legendTitle: 'Nilai Satisfaction',
    legendLowText: 'Rendah · ' + scaleMin.toFixed(1) + '%',
    legendHighText: 'Tinggi · ' + scaleMax.toFixed(1) + '%',
    // Bounds awal Jawa Timur, sama seperti JATIM_BOUNDS pada Python.
    jatimBounds: [[-8.95, 110.75], [-6.70, 114.65]],
    noDataColor: '#D9DEE5'
  };
}

/**
 * Padanan _set_map_region_filter(): menentukan nilai filter hasil klik peta.
 * Mengembalikan selection baru yang dipakai frontend untuk memperbarui dropdown.
 */
function resolveMapRegionFilter_(df, cols, region, currentSelection) {
  var kabCol = cols.kab_kota;
  var mdCol = cols.main_dealer;
  var karCol = cols.karesidenan;

  var canonicalRegion = dashboardRegionName_(region);
  if (!canonicalRegion || !kabCol || !hasColumn_(df, kabCol)) return null;

  var regionRows = df.rows.filter(function (r) {
    return dashboardRegionName_(r[kabCol]) === canonicalRegion;
  });
  if (!regionRows.length) return null;

  var result = { kab_kota: canonicalRegion, layer: 'Semua', dealer: 'Semua' };

  // Scope mengikuti Tahun dan Semester yang sedang aktif.
  var scoped = regionRows;
  var yearCol = cols.year;
  var semCol = cols.semester;
  var selectedYear = currentSelection ? currentSelection.year : null;
  var selectedSem = currentSelection ? currentSelection.semesterLabel : null;

  if (selectedYear && selectedYear !== 'Semua' && yearCol && hasColumn_(df, yearCol)) {
    scoped = scoped.filter(function (r) { return toStr_(r[yearCol]) === String(selectedYear); });
  }
  if ((selectedSem === 'Semester 1' || selectedSem === 'Semester 2') && semCol && hasColumn_(df, semCol)) {
    var semNumber = selectedSem.indexOf('1') !== -1 ? 1 : 2;
    scoped = scoped.filter(function (r) { return parseSemester_(r[semCol]) === semNumber; });
  }
  if (!scoped.length) scoped = regionRows;

  if (mdCol && hasColumn_(df, mdCol)) {
    var mds = [];
    var seenMd = {};
    for (var i = 0; i < scoped.length; i++) {
      var mv = scoped[i][mdCol];
      if (!notNull_(mv)) continue;
      var ms = toStr_(mv);
      if (!seenMd[ms]) { seenMd[ms] = true; mds.push(ms); }
    }
    mds.sort();
    if (mds.length) result.main_dealer = mds[0];
  }

  if (karCol && hasColumn_(df, karCol)) {
    var kars = [];
    var seenKar = {};
    for (var j = 0; j < scoped.length; j++) {
      var kv = scoped[j][karCol];
      if (!notNull_(kv)) continue;
      var ks = toStr_(kv);
      if (!seenKar[ks]) { seenKar[ks] = true; kars.push(ks); }
    }
    kars.sort();
    result.karesidenan = kars.length ? kars[0] : 'Semua';
  } else {
    result.karesidenan = 'Semua';
  }

  return result;
}

// ============================================================
// SECTION 1 : TOP & BOTTOM 5 DEALER
// ============================================================

/** Padanan render_top_bottom_dealer_satisfaction(). */
function buildDealerRanking_(dfProfile, cols, indicatorCols, unitKey, filters) {
  // Ranking sampai level Kabupaten/Kota, tidak tampil jika Dealer spesifik dipilih.
  if (filters) {
    var dealerSelected = filters.dealer !== null && filters.dealer !== undefined &&
      filters.dealer !== 'Semua' && filters.dealer !== '';
    if (dealerSelected) return { show: false };
  }

  if (isEmptyDf_(dfProfile)) {
    return { show: true, empty: true, message: 'Data dealer tidak tersedia untuk filter yang dipilih.' };
  }

  var dealerCodeCol = cols.dealer_code;
  if (!dealerCodeCol || !hasColumn_(dfProfile, dealerCodeCol)) {
    return { show: true, empty: true, message: 'Kolom kode dealer tidak ditemukan.' };
  }

  var unit = String(unitKey).trim().toLowerCase();
  var dealerNameCol, entityLabel;

  if (unit === 'sales') {
    dealerNameCol = findCol_(dfProfile, ['Dealer Name', 'Name of Dealer', 'Nama Dealer', 'Dealer']);
    entityLabel = 'Dealer';
  } else if (unit === 'service') {
    dealerNameCol = findCol_(dfProfile, ['AHASS Name', 'Name of AHASS', 'Nama AHASS', 'AHASS']);
    entityLabel = 'AHASS';
  } else {
    dealerNameCol = findCol_(dfProfile, [
      'Parts Shop Name', 'Part Shop Name', 'Name of Parts Shop',
      'Nama Parts Shop', 'Parts Shop', 'Part Shop'
    ]);
    entityLabel = 'Part Shop';
  }

  var validIndicators = indicatorCols.filter(function (c) { return hasColumn_(dfProfile, c); });
  if (!validIndicators.length) {
    return { show: true, empty: true, message: 'Indikator satisfaction tidak tersedia.' };
  }

  var summaryMap = {};
  var order = [];

  for (var i = 0; i < dfProfile.rows.length; i++) {
    var row = dfProfile.rows[i];

    var vals = [];
    for (var c = 0; c < validIndicators.length; c++) vals.push(toNum_(row[validIndicators[c]]));
    var rowMean = meanSkipNa_(vals);
    var satPct = rowMean === null ? null : rowMean / 5 * 100;

    var code = notNull_(row[dealerCodeCol]) ? toStr_(row[dealerCodeCol]).trim() : '';
    var name = code;
    if (dealerNameCol && hasColumn_(dfProfile, dealerNameCol)) {
      name = notNull_(row[dealerNameCol]) ? toStr_(row[dealerNameCol]).trim() : '';
    }
    if (code === '') continue;

    var key = code + '||' + name;
    if (!summaryMap[key]) {
      summaryMap[key] = { code: code, name: name, sum: 0, n: 0 };
      order.push(key);
    }
    if (satPct !== null) {
      summaryMap[key].sum += satPct;
      summaryMap[key].n += 1;
    }
  }

  var summary = [];
  for (var o = 0; o < order.length; o++) {
    var item = summaryMap[order[o]];
    if (item.n === 0) continue; // Satisfaction NaN dibuang seperti .notna()
    var name2 = item.name;
    var label;
    if (!name2 || name2.toLowerCase() === 'nan' || name2.toLowerCase() === 'none') label = item.code;
    else if (name2 === item.code) label = name2;
    else label = name2 + ' (' + item.code + ')';

    summary.push({
      code: item.code,
      label: label,
      satisfaction: item.sum / item.n,
      responden: item.n,
      seq: o
    });
  }

  if (!summary.length) {
    return { show: true, empty: true, message: 'Nilai satisfaction dealer tidak tersedia.' };
  }

  var sortedHigh = summary.slice().sort(function (a, b) {
    if (b.satisfaction !== a.satisfaction) return b.satisfaction - a.satisfaction;
    if (b.responden !== a.responden) return b.responden - a.responden;
    return a.seq - b.seq;
  });
  var top = sortedHigh.slice(0, 5);

  var sortedLow = summary.slice().sort(function (a, b) {
    if (a.satisfaction !== b.satisfaction) return a.satisfaction - b.satisfaction;
    if (b.responden !== a.responden) return b.responden - a.responden;
    return a.seq - b.seq;
  });
  var bottom = sortedLow.slice(0, 5);

  function fmtList(list) {
    return list.map(function (x, idx) {
      return {
        rank: idx + 1,
        code: x.code,
        label: x.label,
        value: x.satisfaction.toFixed(1) + '%',
        responden: x.responden
      };
    });
  }

  return {
    show: true,
    empty: false,
    entityLabel: entityLabel,
    totalCount: summary.length,
    highTitle: '5 ' + entityLabel + ' dengan Satisfaction Tertinggi',
    lowTitle: '5 ' + entityLabel + ' dengan Satisfaction Terendah',
    allHighTitle: 'Urutan Seluruh ' + entityLabel + ' (Satisfaction Tertinggi)',
    allLowTitle: 'Urutan Seluruh ' + entityLabel + ' (Satisfaction Terendah)',
    top: fmtList(top),
    bottom: fmtList(bottom),
    allHigh: fmtList(sortedHigh),
    allLow: fmtList(sortedLow)
  };
}

// ============================================================
// SECTION 2 : MATRIX SATISFACTION x IMPORTANCE
// ============================================================

/** Padanan render_importance_matrix() bagian pengolahan data. */
function buildImportanceMatrix_(unitKey, filters) {
  var uStr = String(unitKey).trim().toLowerCase();
  var sheetCandidates;

  if (uStr === 'sales' || uStr === 'h1') {
    sheetCandidates = ['matriks_h1', 'matriks_H1', 'matrix_h1', 'matriks', 'matrix'];
  } else if (uStr === 'service' || uStr === 'h2') {
    sheetCandidates = ['matriks_h2', 'matriks_H2', 'matrix_h2', 'matriks', 'matrix'];
  } else if (uStr === 'parts' || uStr === 'h3') {
    sheetCandidates = ['matriks_h3', 'matriks_H3', 'matrix_h3', 'matriks', 'matrix'];
  } else {
    sheetCandidates = ['matriks_h1', 'matriks_h2', 'matriks_h3', 'matriks', 'matrix'];
  }

  var matDf = readFirstAvailableSheet_(sheetCandidates);
  if (isEmptyDf_(matDf)) {
    return { available: false, message: 'Worksheet matriks tidak ditemukan.' };
  }

  var codeCol = findCol_(matDf, ['Attribute', 'attribute', 'Kode_Indicator', 'kode_indicator', 'kode', 'kode atribut', 'code']);
  var satCol = findCol_(matDf, ['Performance', 'performance', 'satisfaction', 'nilai satisfaction']);
  var impCol = findCol_(matDf, ['Relative_Importance', 'relative_importance', 'Weighting', 'weighting', 'importance', 'nilai importance']);
  var avgSatCol = findCol_(matDf, [
    'AVG Satisfaction', 'avg_satisfaction', 'average satisfaction',
    'mean satisfaction', 'rata-rata satisfaction', 'avg performance'
  ]);
  var rankSatCol = findCol_(matDf, [
    'Satisfaction_Rank', 'satisfaction_rank', 'Rank Satisfaction', 'rank_satisfaction', 'satisfaction rank',
    'peringkat satisfaction', 'rank performance'
  ]);
  var rankImpCol = findCol_(matDf, [
    'Importance_Rank', 'importance_rank', 'Rank Importance', 'rank_importance', 'importance rank',
    'peringkat importance', 'rank weighting'
  ]);

  if (!codeCol || !satCol || !impCol) {
    return { available: false, message: 'Kolom Kode, Satisfaction, atau Importance tidak ditemukan pada worksheet matriks.' };
  }

  // Nama indikator sesuai unit agar kode yang sama tidak tertukar.
  var metaCandidates = {
    sales: ['Indicator_metadata_H1', 'indicator_metadata_H1'],
    h1: ['Indicator_metadata_H1', 'indicator_metadata_H1'],
    service: ['Indicator_metadata_H2', 'indicator_metadata_H2'],
    h2: ['Indicator_metadata_H2', 'indicator_metadata_H2'],
    parts: ['Indicator_metadata_H3', 'indicator_metadata_H3'],
    h3: ['Indicator_metadata_H3', 'indicator_metadata_H3']
  };
  var metaList = (metaCandidates[uStr] || []).concat(['indicator_metadata']);

  var indicatorNameMap = {};
  for (var mi = 0; mi < metaList.length; mi++) {
    var metaLookup = tryReadSheet_(metaList[mi]);
    if (isEmptyDf_(metaLookup)) continue;
    var metaCodeCol = findCol_(metaLookup, [
      'Kode_Indikator', 'kode indikator', 'Kode Indicator',
      'kode_indicator', 'indicator code', 'kode', 'code'
    ]);
    var metaNameCol = findCol_(metaLookup, [
      'Nama_Indikator', 'nama indikator', 'Indicator Name',
      'nama_indicator', 'indicator', 'atribut', 'attribute',
      'description', 'keterangan'
    ]);
    if (metaCodeCol && metaNameCol) {
      for (var mr = 0; mr < metaLookup.rows.length; mr++) {
        var mrow = metaLookup.rows[mr];
        if (!notNull_(mrow[metaCodeCol])) continue;
        var ck = toStr_(mrow[metaCodeCol]).trim().toUpperCase();
        var nv = toStr_(mrow[metaNameCol]).trim();
        if (ck && nv && nv.toLowerCase() !== 'nan') indicatorNameMap[ck] = nv;
      }
      break;
    }
  }

  var rows = matDf.rows.slice();
  var mdSelectorNeeded = false;

  if (filters) {
    if (hasColumn_(matDf, 'Tahun') && filters.year) {
      rows = rows.filter(function (r) { return toStr_(r['Tahun']) === String(filters.year); });
    }

    if (hasColumn_(matDf, 'Semester') && filters.semester) {
      var semVal = String(filters.semester);
      if (semVal.toLowerCase().indexOf('semester') !== 0) semVal = 'Semester ' + semVal;
      var matchedSem = rows.filter(function (r) {
        return toStr_(r['Semester']).toLowerCase() === semVal.toLowerCase();
      });
      if (matchedSem.length) rows = matchedSem;
    }

    var subDf = subsetDf_(matDf, rows);
    var catTypeCol = findCol_(subDf, ['Category_Type', 'category_type']);
    var catCol = findCol_(subDf, ['Category', 'category']);

    if (catTypeCol && catCol) {
      var targetType = null;
      var targetCat = null;

      if (filters.dealer) {
        targetType = 'DEALER'; targetCat = String(filters.dealer);
      } else if (filters.kab_kota) {
        targetType = 'KOTA'; targetCat = String(filters.kab_kota);
      } else if (filters.karesidenan) {
        targetType = 'KARES'; targetCat = String(filters.karesidenan);
      } else if (filters.layer) {
        targetType = 'LAYER'; targetCat = String(filters.layer);
      } else if (filters.main_dealer &&
                 ['M2Z', 'M3Z', 'SEMUA'].indexOf(String(filters.main_dealer).trim().toUpperCase()) !== -1) {
        targetType = 'MAIN DEALER'; targetCat = String(filters.main_dealer).trim().toUpperCase();
      } else {
        // Python menampilkan selectbox "Pilih Main Dealer (Matriks)".
        mdSelectorNeeded = true;
        targetType = 'MAIN DEALER';
        targetCat = filters.matrixMainDealer ? String(filters.matrixMainDealer) : 'M2Z';
      }

      if (targetType && targetCat) {
        var matched;
        if (targetType === 'MAIN DEALER' && targetCat === 'SEMUA') {
          matched = rows.filter(function (r) {
            return toStr_(r[catTypeCol]).trim().toUpperCase() === targetType &&
                   toStr_(r[catCol]).trim().toUpperCase() === 'SEMUA';
          });
          if (!matched.length) {
            matched = rows.filter(function (r) {
              var cat = toStr_(r[catCol]).trim().toUpperCase();
              return toStr_(r[catTypeCol]).trim().toUpperCase() === targetType &&
                     (cat === 'M2Z' || cat === 'M3Z');
            });
          }
        } else {
          var upperCat = targetCat.toUpperCase();
          matched = rows.filter(function (r) {
            return toStr_(r[catTypeCol]).trim().toUpperCase() === targetType &&
                   toStr_(r[catCol]).trim().toUpperCase() === upperCat;
          });
        }
        if (matched.length) rows = matched;
      }
    }
  }

  if (!rows.length) {
    return { available: false, message: 'Data matriks tidak tersedia untuk filter yang dipilih.', mdSelectorNeeded: mdSelectorNeeded };
  }

  // Groupby kode indikator.
  var grouped = {};
  var groupOrder = [];
  for (var g = 0; g < rows.length; g++) {
    var gc = toStr_(rows[g][codeCol]);
    if (!Object.prototype.hasOwnProperty.call(grouped, gc)) {
      grouped[gc] = [];
      groupOrder.push(gc);
    }
    grouped[gc].push(rows[g]);
  }
  groupOrder.sort(); // pandas groupby mengurutkan key

  function numericSeries(list, col) {
    var out = [];
    for (var i = 0; i < list.length; i++) {
      var raw = toStr_(list[i][col]).replace(/%/g, '').replace(/,/g, '.');
      var n = raw.trim() === '' ? null : Number(raw);
      out.push(isNaN(n) ? null : n);
    }
    return out;
  }

  var points = [];
  for (var go = 0; go < groupOrder.length; go++) {
    var cCode = groupOrder[go];
    var group = grouped[cCode];

    var perfSeries = numericSeries(group, satCol);
    var impSeries = numericSeries(group, impCol);
    var avgPerf = meanSkipNa_(perfSeries);
    var avgImp = meanSkipNa_(impSeries);
    if (avgPerf === null || avgImp === null) continue;

    var xVal = avgPerf <= 10 ? roundTo_(avgPerf / 5 * 100, 1) : roundTo_(avgPerf, 1);
    var yVal = roundTo_(avgImp, 2);

    var avgSatSeries = avgSatCol ? numericSeries(group, avgSatCol) : perfSeries;
    var avgSatValue = meanSkipNa_(avgSatSeries);
    if (avgSatValue !== null && avgSatValue <= 10) avgSatValue = avgSatValue / 5 * 100;

    function firstNumeric(col) {
      if (!col) return null;
      for (var i = 0; i < group.length; i++) {
        var n = toNum_(group[i][col]);
        if (n !== null) return n;
      }
      return null;
    }

    points.push({
      code: String(cCode).trim(),
      name: indicatorNameMap[String(cCode).trim().toUpperCase()] || 'Nama indikator belum tersedia',
      x: xVal,
      y: yVal,
      avgSat: avgSatValue !== null ? avgSatValue : xVal,
      rawSat: avgPerf,
      rankSat: firstNumeric(rankSatCol),
      rankImp: firstNumeric(rankImpCol)
    });
  }

  if (!points.length) {
    return { available: false, message: 'Data matriks tidak tersedia.', mdSelectorNeeded: mdSelectorNeeded };
  }

  var xs = points.map(function (p) { return p.x; });
  var ys = points.map(function (p) { return p.y; });
  var xMid = roundTo_(median_(xs), 2);
  var yMid = roundTo_(median_(ys), 2);

  // Warna kuadran: I hijau, II merah, III orange, IV kuning.
  var quadrants = {
    keep: { label: 'Pertahankan', roman: 'Kuadran I', color: GREEN },
    priority: { label: 'Prioritas Utama', roman: 'Kuadran II', color: RED },
    gradual: { label: 'Perbaikan Bertahap', roman: 'Kuadran III', color: ORANGE },
    low: { label: 'Prioritas Rendah', roman: 'Kuadran IV', color: YELLOW }
  };

  function classify(x, y) {
    if (x >= xMid && y >= yMid) return 'keep';
    if (x < xMid && y >= yMid) return 'priority';
    if (x < xMid && y < yMid) return 'gradual';
    if (x >= xMid && y < yMid) return 'low';
    return 'gradual';
  }

  var pointsByQuadrant = { keep: [], priority: [], gradual: [], low: [] };
  for (var pi = 0; pi < points.length; pi++) {
    var qk = classify(points[pi].x, points[pi].y);
    points[pi].quadrant = qk;
    points[pi].color = quadrants[qk].color;
    pointsByQuadrant[qk].push(points[pi]);
  }

  // Default: kuadran dengan indikator terbanyak.
  var defaultQuadrant = 'keep';
  var maxCount = -1;
  var qOrder = ['keep', 'priority', 'gradual', 'low'];
  for (var q = 0; q < qOrder.length; q++) {
    if (pointsByQuadrant[qOrder[q]].length > maxCount) {
      maxCount = pointsByQuadrant[qOrder[q]].length;
      defaultQuadrant = qOrder[q];
    }
  }

  var xMin = Math.min.apply(null, xs);
  var xMax = Math.max.apply(null, xs);
  var yMin = Math.min.apply(null, ys);
  var yMax = Math.max.apply(null, ys);
  var xPad = Math.max(0.50, (xMax - xMin) * 0.08);
  var yPad = Math.max(0.80, (yMax - yMin) * 0.10);

  // Daftar indikator per kuadran diurutkan berdasarkan kode.
  for (var qq = 0; qq < qOrder.length; qq++) {
    pointsByQuadrant[qOrder[qq]].sort(function (a, b) {
      return a.code < b.code ? -1 : (a.code > b.code ? 1 : 0);
    });
  }

  return {
    available: true,
    mdSelectorNeeded: mdSelectorNeeded,
    description: 'Matriks ini menunjukkan posisi setiap atribut berdasarkan tingkat Satisfaction (X) dan Importance (Y).',
    points: points,
    quadrants: quadrants,
    quadrantOrder: qOrder,
    pointsByQuadrant: pointsByQuadrant,
    xMid: xMid,
    yMid: yMid,
    xLo: Math.max(0, xMin - xPad),
    xHi: xMax + xPad,
    yLo: Math.max(0, yMin - yPad),
    yHi: Math.min(105, yMax + yPad),
    defaultQuadrant: defaultQuadrant,
    caption: 'Klik titik pada matriks, atau klik salah satu tombol kuadran di atas, untuk melihat detail indikator di panel kanan.'
  };
}

// ============================================================
// SECTION 3 : HEATMAP PROFIL
// ============================================================

/** Padanan render_profile_heatmap(). */
function buildProfileHeatmap_(unitKey) {
  var uStr = String(unitKey).trim().toLowerCase();
  var sheetCandidates, metadataCandidates;

  if (uStr === 'sales' || uStr === 'h1') {
    sheetCandidates = ['heatmap_h1', 'heatmap_H1', 'heatmap'];
    metadataCandidates = ['Indicator_metadata_H1', 'Indikator_metadata_H1'];
  } else if (uStr === 'service' || uStr === 'h2') {
    sheetCandidates = ['heatmap_h2', 'heatmap_H2', 'heatmap'];
    metadataCandidates = ['Indicator_metadata_H2', 'Indikator_metadata_H2'];
  } else if (uStr === 'parts' || uStr === 'h3') {
    sheetCandidates = ['heatmap_h3', 'heatmap_H3', 'heatmap'];
    metadataCandidates = ['Indicator_metadata_H3', 'Indikator_metadata_H3'];
  } else {
    sheetCandidates = ['heatmap_h1', 'heatmap_h2', 'heatmap_h3', 'heatmap'];
    metadataCandidates = ['indicator_metadata'];
  }

  var heatmapMeta = readFirstAvailableSheet_(metadataCandidates);
  var heatmapIndicatorNames = buildIndicatorNameMap_(heatmapMeta);

  var hmDf = { columns: [], rows: [] };
  for (var s = 0; s < sheetCandidates.length; s++) {
    var candidate = tryReadSheet_(sheetCandidates[s]);
    if (!isEmptyDf_(candidate) &&
        (hasColumn_(candidate, 'Profile') || hasColumn_(candidate, 'profile') || hasColumn_(candidate, 'Kode_Indikator'))) {
      hmDf = candidate;
      break;
    }
  }

  if (isEmptyDf_(hmDf)) {
    return { available: false, message: 'Worksheet heatmap tidak ditemukan.' };
  }

  var pCol = findCol_(hmDf, ['Profile', 'profile', 'p', 'profil']);
  var kCol = findCol_(hmDf, ['Kode_Indikator', 'kode_indicator', 'kode', 'code', 'attribute', 'indikator']);
  var vCol = findCol_(hmDf, ['Nilai', 'nilai', 'value', 'val', 'selisih', 'gap']);

  // Indikator metadata-only tidak boleh muncul pada heatmap.
  var excluded = excludedCalculationIndicators_(unitKey);
  var excludedSet = {};
  for (var e = 0; e < excluded.length; e++) excludedSet[excluded[e]] = true;

  var rows = hmDf.rows;
  if (kCol && excluded.length) {
    rows = rows.filter(function (r) {
      return !excludedSet[toStr_(r[kCol]).trim().toUpperCase()];
    });
  }

  var attrCodes = [];
  var profilesLabel = [];
  var matrix = [];

  if (pCol && kCol && vCol) {
    var cleanRows = rows.filter(function (r) {
      return notNull_(r[pCol]) && notNull_(r[kCol]) && notNull_(r[vCol]);
    });

    var pivot = {};
    var codeOrder = [];
    var profileSet = {};

    for (var i = 0; i < cleanRows.length; i++) {
      var row = cleanRows[i];
      var profileKey = toStr_(row[pCol]).replace(/P/gi, '').replace(/Profile/gi, '').trim();
      var value = Number(toStr_(row[vCol]).replace(/,/g, '.'));
      if (isNaN(value)) continue;

      var code = toStr_(row[kCol]);
      if (!Object.prototype.hasOwnProperty.call(pivot, code)) {
        pivot[code] = {};
        codeOrder.push(code);
      }
      pivot[code][profileKey] = value;
      profileSet[profileKey] = true;
    }

    // Kolom profile: 1..5 bila tersedia.
    var existing = ['1', '2', '3', '4', '5'].filter(function (p) { return profileSet[p]; });
    if (!existing.length) {
      existing = Object.keys(profileSet).sort();
    }

    codeOrder.sort(); // pivot pandas mengurutkan index
    attrCodes = codeOrder;
    profilesLabel = existing;

    for (var c = 0; c < attrCodes.length; c++) {
      var rowVals = [];
      for (var p2 = 0; p2 < profilesLabel.length; p2++) {
        var raw = pivot[attrCodes[c]][profilesLabel[p2]];
        // Gap Likert → Persentase, skala maksimum satisfaction = 5
        rowVals.push(raw === undefined ? null : (raw / 5) * 100);
      }
      matrix.push(rowVals);
    }
  } else {
    var profCols = [];
    var wanted = ['P1', 'P2', 'P3', 'P4', 'P5', 'PROFILE 1', 'PROFILE 2', 'PROFILE 3', 'PROFILE 4', 'PROFILE 5'];
    for (var pc = 0; pc < hmDf.columns.length; pc++) {
      if (wanted.indexOf(String(hmDf.columns[pc]).trim().toUpperCase()) !== -1) profCols.push(hmDf.columns[pc]);
    }
    if (!kCol || !profCols.length) {
      return { available: false, message: 'Struktur kolom heatmap tidak ditemukan pada worksheet heatmap.' };
    }

    profilesLabel = profCols.map(function (pcName) {
      var digits = String(pcName).replace(/[^0-9]/g, '');
      return digits || String(pcName);
    });

    for (var r2 = 0; r2 < rows.length; r2++) {
      var vals = [];
      for (var pc2 = 0; pc2 < profCols.length; pc2++) {
        var n = Number(toStr_(rows[r2][profCols[pc2]]).replace(/,/g, '.').trim());
        vals.push(isNaN(n) ? 0.0 : n);
      }
      attrCodes.push(toStr_(rows[r2][kCol]).trim());
      matrix.push(vals);
    }
  }

  if (!matrix.length || !attrCodes.length) {
    return { available: false, message: 'Data heatmap tidak tersedia.' };
  }

  // Teks pada tiap sel, format sama seperti Python.
  var textMatrix = [];
  for (var m = 0; m < matrix.length; m++) {
    var lineText = [];
    for (var n2 = 0; n2 < matrix[m].length; n2++) {
      var v2 = matrix[m][n2];
      if (v2 === null || v2 === undefined || isNaN(v2)) {
        lineText.push('');
      } else if (roundTo_(v2, 2) === 0) {
        lineText.push('0%');
      } else {
        var valueText = v2.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
        lineText.push(valueText + '%');
      }
    }
    textMatrix.push(lineText);
  }

  var names = attrCodes.map(function (code) {
    return heatmapIndicatorNames[String(code).trim().toUpperCase()] || 'Nama indikator belum tersedia';
  });

  return {
    available: true,
    title: 'Customer Profile Heatmap vs Overall Average',
    subtitle: 'Kesenjangan Karakteristik Tiap Customer Profile Terhadap Rata-rata Keseluruhan',
    z: matrix,
    text: textMatrix,
    x: profilesLabel.map(function (p) { return 'P' + p; }),
    y: attrCodes,
    names: names,
    colorscale: [
      [0.0, '#B71C1C'],
      [0.35, '#EF5350'],
      [0.5, '#FFFFFF'],
      [0.65, '#81C784'],
      [1.0, '#2E7D32']
    ],
    height: Math.max(340, 34 * attrCodes.length + 90)
  };
}

// ============================================================
// SECTION 3 : DAFTAR PROFIL & PENJELASAN
// ============================================================

/** Padanan render_profile_list(). */
function buildProfileList_(dfFiltered, cols, profileMetaDf, selectedProfile) {
  var profileCol = cols.profile;
  var selected = selectedProfile || 'P1';

  var metaNames = {};
  if (!isEmptyDf_(profileMetaDf)) {
    var codeCol = findCol_(profileMetaDf, ['profile', 'profil', 'code', 'no']);
    var nameCol = findCol_(profileMetaDf, ['profile name', 'nama profil', 'nama', 'name']);
    if (codeCol && nameCol) {
      for (var i = 0; i < profileMetaDf.rows.length; i++) {
        var row = profileMetaDf.rows[i];
        var pRaw = toStr_(row[codeCol]).replace('.0', '').trim();
        var pMatch = pRaw.match(/(\d+)/);
        if (!pMatch) continue;
        var pKey = 'P' + pMatch[1];
        var nVal = toStr_(row[nameCol]).trim();
        if (nVal && nVal.toLowerCase() !== 'nan') metaNames[pKey] = nVal;
      }
    }
  }

  var total = isEmptyDf_(dfFiltered) ? 0 : dfFiltered.rows.length;
  var profileCodes = ['P1', 'P2', 'P3', 'P4', 'P5'];
  var profileCounts = {};

  for (var p = 0; p < profileCodes.length; p++) {
    var code = profileCodes[p];
    var count = 0;

    if (profileCol && !isEmptyDf_(dfFiltered) && hasColumn_(dfFiltered, profileCol)) {
      var reCode = new RegExp(code, 'i');
      for (var r = 0; r < dfFiltered.rows.length; r++) {
        var v = dfFiltered.rows[r][profileCol];
        if (notNull_(v) && reCode.test(toStr_(v))) count += 1;
      }
      if (count === 0) {
        var pNum = code.replace('P', '');
        var reNum = new RegExp('\\b' + pNum + '\\b', 'i');
        for (var r2 = 0; r2 < dfFiltered.rows.length; r2++) {
          var v2 = dfFiltered.rows[r2][profileCol];
          if (notNull_(v2) && reNum.test(toStr_(v2))) count += 1;
        }
      }
    }

    profileCounts[code] = count;
  }

  var availableProfiles = profileCodes.filter(function (c) { return profileCounts[c] > 0; });
  if (availableProfiles.length && availableProfiles.indexOf(selected) === -1) {
    selected = availableProfiles[0];
  }

  var items = [];
  for (var q = 0; q < profileCodes.length; q++) {
    var pc = profileCodes[q];
    var cnt = profileCounts[pc];
    var pct = total > 0 ? Math.round(cnt / total * 100) : 0;
    var isDisabled = cnt === 0;
    var isActive = (pc === selected) && !isDisabled;
    var num = pc.replace('P', '');
    var name = metaNames[pc] || PROFILE_NAMES[pc] || ('Profil ' + num);

    items.push({
      code: pc,
      num: num,
      name: name,
      count: cnt,
      pct: pct,
      color: PROFILE_COLORS[pc],
      disabled: isDisabled,
      active: isActive,
      title: 'Profil ' + num + ' – ' + name,
      help: isDisabled
        ? 'Profil ' + num + ' – ' + name + ': tidak tersedia pada filter ini'
        : 'Profil ' + num + ' – ' + name + ': ' + cnt + ' orang (' + pct + '%)'
    });
  }

  return {
    title: 'Profile List',
    subtitle: 'Klik kartu profil untuk memilih',
    items: items,
    selected: selected
  };
}

/** Padanan render_profile_explanation(). */
function buildProfileExplanation_(profileMetaDf, selectedProfile) {
  var pNum = String(selectedProfile).replace('P', '').trim();
  var pKey = 'P' + pNum;

  var name = PROFILE_NAMES[pKey] || ('Profil ' + pNum);
  var insight = null;
  var reco = null;

  if (!isEmptyDf_(profileMetaDf)) {
    var codeCol = findCol_(profileMetaDf, ['profile', 'profil', 'code', 'no']);
    var nameCol = findCol_(profileMetaDf, ['profile name', 'nama profil', 'nama', 'name']);
    var insightCol = findCol_(profileMetaDf, ['business insight', 'insight']);
    var recoCol = findCol_(profileMetaDf, ['recommendation', 'rekomendasi']);

    if (codeCol) {
      var re = new RegExp('\\b' + pNum + '\\b', 'i');
      for (var i = 0; i < profileMetaDf.rows.length; i++) {
        var row = profileMetaDf.rows[i];
        if (!notNull_(row[codeCol]) || !re.test(toStr_(row[codeCol]))) continue;

        if (nameCol && notNull_(row[nameCol])) {
          var nVal = toStr_(row[nameCol]).trim();
          if (nVal && nVal.toLowerCase() !== 'nan') name = nVal;
        }
        if (insightCol && notNull_(row[insightCol])) insight = toStr_(row[insightCol]).trim();
        if (recoCol && notNull_(row[recoCol])) reco = toStr_(row[recoCol]).trim();
        break;
      }
    }
  }

  return {
    title: 'Profile Description: Profile ' + pNum + ' – ' + name,
    insightHeader: 'Business Insight',
    insightText: (insight && insight.toLowerCase() !== 'nan')
      ? insight : 'Business insight tidak tersedia untuk profil ini.',
    recoHeader: 'Rekomendasi Strategis',
    recoText: (reco && reco.toLowerCase() !== 'nan')
      ? reco : 'Rekomendasi tidak tersedia untuk profil ini.'
  };
}

// ============================================================
// BERKAS ASAL: 05_Demographics.gs
// ============================================================

/**
 * ============================================================
 * 05_Demographics.gs
 * Porting dari _simple_pie, _age_group_hbar, _motor_type_hbar,
 * _stacked_pct, _top_reasons_hbar, render_nps_gauge, dan
 * render_overall_profile_insight.
 *
 * Urutan kategori, warna, teks legend, dan isi kalimat ringkasan
 * dipertahankan sama persis dengan versi Streamlit.
 * ============================================================
 */

/** Padanan _simple_pie(). */
function buildPieChart_(df, col, title, colors) {
  if (!col || isEmptyDf_(df) || !hasColumn_(df, col)) {
    return { title: title, available: false, message: 'Data tidak tersedia.' };
  }

  var counts = valueCounts_(columnStrings_(df, col));
  if (!counts.length) {
    return { title: title, available: false, message: 'Data tidak tersedia.' };
  }

  return {
    title: title,
    available: true,
    labels: counts.map(function (c) { return c.label; }),
    values: counts.map(function (c) { return c.count; }),
    colors: colors || null,
    hole: 0.35,
    height: 315
  };
}

/** Padanan _age_group_hbar(). */
function buildAgeChart_(df, col, title) {
  if (!col || isEmptyDf_(df) || !hasColumn_(df, col)) {
    return { title: title, available: false, message: 'Data tidak tersedia.' };
  }

  var counts = valueCounts_(columnStrings_(df, col));
  if (!counts.length) {
    return { title: title, available: false, message: 'Data tidak tersedia.' };
  }

  var total = 0;
  for (var i = 0; i < counts.length; i++) total += counts[i].count;

  // Urut berdasarkan angka usia, reverse=True seperti Python.
  var sorted = counts.slice().sort(function (a, b) {
    return ageSortKey_(b.label) - ageSortKey_(a.label);
  });

  var items = sorted.map(function (c) {
    var pct = roundTo_(c.count / total * 100, 1);
    return { label: c.label, pct: pct, count: c.count, text: pct.toFixed(1) + '%' };
  });

  var maxVal = items.length ? Math.max.apply(null, items.map(function (x) { return x.pct; })) : 100;

  return {
    title: title,
    available: true,
    color: RED,
    items: items,
    xRangeMax: Math.max(112, maxVal + 12),
    height: Math.max(330, 32 * items.length + 60)
  };
}

/** Padanan _motor_type_hbar(). */
function buildMotorChart_(df, col, title) {
  if (!col || isEmptyDf_(df) || !hasColumn_(df, col)) {
    return { title: title, available: false, message: 'Data tidak tersedia.' };
  }

  var normalized = [];
  for (var i = 0; i < df.rows.length; i++) {
    var v = df.rows[i][col];
    if (!notNull_(v)) continue;
    var canon = canonicalMotor_(v);
    if (canon !== null) normalized.push(canon);
  }

  if (!normalized.length) {
    return { title: title, available: false, message: 'Data tidak tersedia.' };
  }

  var counts = valueCounts_(normalized);
  var total = 0;
  for (var c = 0; c < counts.length; c++) total += counts[c].count;

  var countMap = {};
  for (var d = 0; d < counts.length; d++) countMap[counts[d].label] = counts[d].count;

  // Urut: jumlah terbesar dulu, tie-breaker MOTOR_RANK lalu nama.
  var labels = counts.map(function (x) { return String(x.label); });
  labels.sort(function (a, b) {
    if (countMap[b] !== countMap[a]) return countMap[b] - countMap[a];
    var ra = Object.prototype.hasOwnProperty.call(MOTOR_RANK, a) ? MOTOR_RANK[a] : 10000;
    var rb = Object.prototype.hasOwnProperty.call(MOTOR_RANK, b) ? MOTOR_RANK[b] : 10000;
    if (ra !== rb) return ra - rb;
    var la = a.toLowerCase(), lb = b.toLowerCase();
    return la < lb ? -1 : (la > lb ? 1 : 0);
  });

  // Plotly menaruh item pertama paling bawah, jadi dibalik.
  var labelsPlot = labels.slice().reverse();
  var items = labelsPlot.map(function (label) {
    var cnt = countMap[label];
    var pct = roundTo_(cnt / total * 100, 1);
    return { label: label, pct: pct, count: cnt, text: fmtPct_(pct) };
  });

  var maxVal = items.length ? Math.max.apply(null, items.map(function (x) { return x.pct; })) : 100;

  return {
    title: title,
    available: true,
    color: RED,
    items: items,
    xRangeMax: Math.max(112, maxVal + 15),
    height: Math.max(330, 32 * items.length + 60)
  };
}

/**
 * Padanan _stacked_pct().
 * Hanya menyiapkan data: urutan label, persentase, jumlah responden,
 * warna, teks hover, dan legend. Pemenggalan teks di dalam bar tetap
 * dilakukan di frontend supaya hasil visualnya identik.
 */
function buildStackedPct_(df, col, title, opts) {
  opts = opts || {};

  if (!col || isEmptyDf_(df) || !hasColumn_(df, col)) {
    return { title: title, available: false, message: 'Data tidak tersedia.' };
  }

  var rawSeries = stackedRawSeries_(df, col);
  if (!rawSeries.length) {
    return { title: title, available: false, message: 'Data tidak tersedia.' };
  }

  var normalized = [];
  var labels = [];
  var counts, countMap = {};

  function buildCountMap(list) {
    var vc = valueCounts_(list);
    var map = {};
    for (var i = 0; i < vc.length; i++) map[String(vc[i].label)] = vc[i].count;
    return { vc: vc, map: map };
  }

  if (opts.isSes) {
    for (var i = 0; i < rawSeries.length; i++) {
      var s = rawSeries[i].toUpperCase().split(' ').join('');
      if (s === 'A1') s = 'A'; // A1 disatukan sebagai SES A
      normalized.push(s);
    }
    var ses = buildCountMap(normalized);
    countMap = ses.map;
    labels = SES_ORDER.filter(function (level) {
      return Object.prototype.hasOwnProperty.call(countMap, level);
    });
    var extraSes = Object.keys(countMap).filter(function (x) { return SES_ORDER.indexOf(x) === -1; });
    extraSes.sort();
    labels = labels.concat(extraSes);

  } else if (opts.isRetention) {
    for (var j = 0; j < rawSeries.length; j++) {
      var score = retentionScore_(rawSeries[j]);
      if (score !== null) normalized.push(String(score));
    }
    if (!normalized.length) {
      return { title: title, available: false, message: 'Data tidak tersedia.' };
    }
    var ret = buildCountMap(normalized);
    countMap = ret.map;
    labels = [];
    for (var sc = 1; sc <= 5; sc++) {
      if (Object.prototype.hasOwnProperty.call(countMap, String(sc))) labels.push(String(sc));
    }

  } else if (opts.isPurchasePeriod) {
    for (var k = 0; k < rawSeries.length; k++) normalized.push(canonicalPeriod_(rawSeries[k]));
    var per = buildCountMap(normalized);
    countMap = per.map;
    labels = PERIOD_ORDER.filter(function (l) {
      return Object.prototype.hasOwnProperty.call(countMap, l);
    });
    var extraPeriod = Object.keys(countMap).filter(function (x) { return PERIOD_ORDER.indexOf(x) === -1; });
    extraPeriod.sort(function (a, b) {
      var la = a.toLowerCase(), lb = b.toLowerCase();
      return la < lb ? -1 : (la > lb ? 1 : 0);
    });
    labels = labels.concat(extraPeriod);

  } else if (opts.isPurchaseLocation) {
    for (var m = 0; m < rawSeries.length; m++) {
      normalized.push(rawSeries[m].replace(/\s+/g, ' ').trim());
    }
    var loc = buildCountMap(normalized);
    countMap = loc.map;
    labels = Object.keys(countMap);
    labels.sort(function (a, b) {
      var ka = purchaseLocationKey_(a);
      var kb = purchaseLocationKey_(b);
      if (ka[0] !== kb[0]) return ka[0] - kb[0];
      return ka[1] < kb[1] ? -1 : (ka[1] > kb[1] ? 1 : 0);
    });
    if (opts.reverseOrder) labels = labels.reverse();

  } else {
    normalized = rawSeries.slice();
    var gen = buildCountMap(normalized);
    countMap = gen.map;
    labels = gen.vc.map(function (x) { return String(x.label); });
  }

  if (!labels.length) {
    return { title: title, available: false, message: 'Data tidak tersedia.' };
  }

  var total = 0;
  for (var t = 0; t < labels.length; t++) total += (countMap[labels[t]] || 0);

  var categoryColors = {};
  if (opts.isPurchasePeriod || opts.isPurchaseLocation) {
    var gradient = CATEGORY_GRADIENT.slice();
    if (opts.reverseLocationColors) gradient = gradient.reverse();
    for (var g = 0; g < labels.length; g++) {
      categoryColors[labels[g]] = gradient[Math.min(g, gradient.length - 1)];
    }
  }

  var segments = [];
  for (var i2 = 0; i2 < labels.length; i2++) {
    var label = labels[i2];
    var respondents = countMap[label] || 0;
    var value = roundTo_(respondents / total * 100, 1);
    var barColor, hoverTitle;

    if (opts.isSes) {
      barColor = Object.prototype.hasOwnProperty.call(SES_COLORS, label)
        ? SES_COLORS[label] : GENERIC_PALETTE[i2 % GENERIC_PALETTE.length];
      var rangeText = Object.prototype.hasOwnProperty.call(SES_RANGES, label)
        ? SES_RANGES[label] : 'Rentang tidak tersedia';
      hoverTitle = 'SES ' + label + ': ' + rangeText;
    } else if (opts.isRetention) {
      var scoreNum = parseInt(label, 10);
      barColor = RETENTION_COLORS[scoreNum];
      hoverTitle = 'Retention ' + scoreNum + ': ' + RETENTION_LABELS[scoreNum];
    } else if (opts.isPurchasePeriod || opts.isPurchaseLocation) {
      barColor = categoryColors[label];
      hoverTitle = label;
    } else {
      barColor = GENERIC_PALETTE[i2 % GENERIC_PALETTE.length];
      hoverTitle = label;
    }

    segments.push({
      label: String(label),
      value: value,
      respondents: respondents,
      color: barColor,
      hoverTitle: hoverTitle,
      pctText: fmtPct_(value)
    });
  }

  // Legend: isi dan urutannya sama persis dengan Python.
  var legend = [];
  if (opts.isSes) {
    for (var ls = 0; ls < SES_ORDER.length; ls++) {
      var lvl = SES_ORDER[ls];
      legend.push({ color: SES_COLORS[lvl], bold: lvl, text: SES_RANGES[lvl] });
    }
  } else if (opts.isRetention) {
    for (var lr = 1; lr <= 5; lr++) {
      legend.push({ color: RETENTION_COLORS[lr], bold: String(lr), text: RETENTION_LABELS[lr] });
    }
  } else if (opts.isPurchasePeriod || opts.isPurchaseLocation) {
    for (var lp = 0; lp < labels.length; lp++) {
      legend.push({ color: categoryColors[labels[lp]], bold: null, text: String(labels[lp]) });
    }
  } else if (opts.showCategoryLegend) {
    for (var lg = 0; lg < labels.length; lg++) {
      legend.push({
        color: GENERIC_PALETTE[lg % GENERIC_PALETTE.length],
        bold: null,
        text: String(labels[lg])
      });
    }
  }

  return {
    title: title,
    available: true,
    segments: segments,
    legend: legend,
    height: 108
  };
}

/** Padanan _top_reasons_hbar(). */
function buildTopReasons_(df, col, title, topN, separator) {
  topN = topN || 5;
  separator = separator || ';';

  if (!col || isEmptyDf_(df) || !hasColumn_(df, col)) {
    return { title: title, available: false, message: 'Data tidak tersedia.' };
  }

  var reasonLabels = {};
  var normalizedReasons = [];
  var totalNotNa = 0;

  for (var i = 0; i < df.rows.length; i++) {
    var rawValue = df.rows[i][col];
    if (!notNull_(rawValue)) continue;
    totalNotNa += 1;

    var parts = toStr_(rawValue).split(separator);
    for (var p = 0; p < parts.length; p++) {
      // Python: re.sub(r"\s+", " ", raw).strip(" ;,.-")
      var cleanReason = parts[p].replace(/\s+/g, ' ').replace(/^[\s;,.\-]+|[\s;,.\-]+$/g, '');
      if (!cleanReason) continue;
      var low = cleanReason.toLowerCase();
      if (low === 'nan' || low === 'none' || low === '-') continue;

      if (!Object.prototype.hasOwnProperty.call(reasonLabels, low)) reasonLabels[low] = cleanReason;
      normalizedReasons.push(low);
    }
  }

  if (!normalizedReasons.length) {
    return { title: title, available: false, message: 'Data tidak tersedia.' };
  }

  var counts = valueCounts_(normalizedReasons).slice(0, topN);
  var totalRespondents = Math.max(totalNotNa, 1);

  var items = counts.map(function (c) {
    return {
      label: reasonLabels[c.label],
      count: c.count,
      pct: roundTo_(c.count / totalRespondents * 100, 1)
    };
  });

  // Dibalik agar item terbesar berada paling atas pada bar horizontal.
  items.reverse();

  var maxCount = items.length ? Math.max.apply(null, items.map(function (x) { return x.count; })) : 1;

  return {
    title: title,
    available: true,
    color: ORANGE,
    items: items.map(function (x) {
      return { label: x.label, count: x.count, pct: x.pct, pctText: fmtPct_(x.pct) };
    }),
    maxCount: maxCount,
    xLimit: Math.max(1.6, maxCount * 1.34),
    labelX: maxCount * 1.03,
    xAxisTitle: 'Frekuensi Dipilih',
    height: Math.max(315, 54 * items.length + 65)
  };
}

/** Padanan render_nps_gauge(). */
function buildNpsGauge_(value, title) {
  if (value === null || value === undefined) {
    return { title: title, available: false, message: 'Data tidak tersedia.' };
  }

  var valClamped = Math.max(0, Math.min(100, Number(value)));
  var label = valClamped >= 85 ? 'Sangat Baik'
    : (valClamped >= 70 ? 'Baik' : (valClamped >= 50 ? 'Cukup' : 'Kurang'));

  return {
    title: title,
    available: true,
    value: valClamped,
    steps: [
      { range: [0, 50], color: RED },
      { range: [50, 70], color: ORANGE },
      { range: [70, 85], color: YELLOW },
      { range: [85, 100], color: GREEN }
    ],
    barColor: '#212121',
    caption: 'Status NPS: ' + label + ' (' + valClamped.toFixed(1) + ')',
    height: 250
  };
}

/**
 * Padanan render_overall_profile_insight().
 * Kalimat dan susunan HTML dipertahankan sama persis.
 */
function buildOverallProfileInsight_(dfFiltered, dfProf, cols, selectedProfile, unit, profileMetaDf) {
  if (isEmptyDf_(dfProf)) {
    return {
      available: false,
      message: 'Ringkasan profil belum tersedia karena tidak ada responden pada filter ini.'
    };
  }

  function npsValue(column) {
    if (!column || !hasColumn_(dfProf, column)) return null;
    return computeNps_(dfProf, column);
  }

  var totalFiltered = isEmptyDf_(dfFiltered) ? 0 : dfFiltered.rows.length;
  var profileCount = dfProf.rows.length;
  var profilePct = totalFiltered ? (profileCount / totalFiltered * 100) : 0;

  var profileNumber = String(selectedProfile || '').replace('P', '').trim();
  var profileName = 'Profil ' + profileNumber;

  if (!isEmptyDf_(profileMetaDf)) {
    var metaProfileCol = findCol_(profileMetaDf, ['Profile', 'Profil', 'Code', 'No']);
    var metaNameCol = findCol_(profileMetaDf, ['Profile Name', 'Nama Profil', 'Profile_Name', 'nama', 'name']);

    if (metaProfileCol && metaNameCol) {
      for (var i = 0; i < profileMetaDf.rows.length; i++) {
        var metaRow = profileMetaDf.rows[i];
        var rawCode = toStr_(metaRow[metaProfileCol]).trim();
        var codeMatch = rawCode.match(/(\d+)/);
        if (!codeMatch || codeMatch[1] !== profileNumber) continue;

        var rawName = toStr_(metaRow[metaNameCol]).trim();
        var lowName = rawName.toLowerCase();
        if (rawName && lowName !== 'nan' && lowName !== 'none' && lowName !== '-') {
          profileName = rawName;
          break;
        }
      }
    }
  }

  var gender = dominant_(dfProf, cols.gender, null);
  var age = dominant_(dfProf, cols.age, null);
  var motor = dominant_(dfProf, cols.motor_type, canonicalMotor_);
  var ses = dominant_(dfProf, cols.ses, null);

  var sentence1 = '<b>Profil ' + profileNumber + ' – ' + escapeHtml_(profileName) + '</b> ' +
    'mencakup <b>' + profilePct.toFixed(1) + '%</b> dari total pelanggan ' +
    'pada filter yang dipilih.';

  var demographicParts = [];
  if (gender) demographicParts.push(shortLabel_(gender.label).toLowerCase() + ' (' + gender.pct.toFixed(1) + '%)');
  if (age) demographicParts.push('kelompok usia ' + shortLabel_(age.label) + ' (' + age.pct.toFixed(1) + '%)');
  if (motor) demographicParts.push('pengguna ' + shortLabel_(motor.label) + ' (' + motor.pct.toFixed(1) + '%)');

  var sentence2 = '';
  if (demographicParts.length) {
    var demoText;
    if (demographicParts.length === 1) demoText = demographicParts[0];
    else if (demographicParts.length === 2) demoText = demographicParts.join(' dan ');
    else demoText = demographicParts.slice(0, -1).join(', ') + ', dan ' + demographicParts[demographicParts.length - 1];
    sentence2 = 'Profil ini didominasi oleh ' + escapeHtml_(demoText) + '.';
  }

  var behaviorParts = [];
  if (ses) {
    var sesCode = shortLabel_(ses.label).toUpperCase().trim();
    var sesRange = SES_RANGES_INSIGHT[sesCode];
    if (sesRange) behaviorParts.push('SES ' + sesCode + ' (' + sesRange + ') sebesar ' + ses.pct.toFixed(1) + '%');
    else behaviorParts.push('SES ' + sesCode + ' sebesar ' + ses.pct.toFixed(1) + '%');
  }

  if (unit === 'sales') {
    var payment = dominant_(dfProf, cols.payment, null);
    var showroom = dominant_(dfProf, findExactDataCol_(dfProf, 'Showroom'), null);

    if (payment) {
      behaviorParts.push('menggunakan pembayaran ' + shortLabel_(payment.label).toLowerCase() +
        ' (' + payment.pct.toFixed(1) + '%)');
    }
    if (showroom) {
      behaviorParts.push('memilih ' + shortLabel_(showroom.label) + ' sebagai lokasi ' +
        'pembelian berikutnya (' + showroom.pct.toFixed(1) + '%)');
    }
  } else if (unit === 'service') {
    var frequency = dominant_(dfProf, findExactDataCol_(dfProf, 'Frequency Visit to AHASS'), null);
    if (frequency) {
      behaviorParts.push('memiliki pola kunjungan AHASS ' + shortLabel_(frequency.label).toLowerCase() +
        ' (' + frequency.pct.toFixed(1) + '%)');
    }
  } else {
    var futurePart = dominant_(dfProf, findExactDataCol_(dfProf, 'Future Purchase Part'), null);
    if (futurePart) {
      behaviorParts.push('memilih ' + shortLabel_(futurePart.label) +
        ' untuk pembelian part berikutnya (' + futurePart.pct.toFixed(1) + '%)');
    }
  }

  var sentence3 = '';
  if (behaviorParts.length) {
    var behaviorText;
    if (behaviorParts.length === 1) behaviorText = behaviorParts[0];
    else if (behaviorParts.length === 2) behaviorText = behaviorParts.join(' dan ');
    else behaviorText = behaviorParts.slice(0, -1).join(', ') + ', dan ' + behaviorParts[behaviorParts.length - 1];
    sentence3 = 'Dari sisi ekonomi dan perilaku, mayoritas pelanggan berada pada ' +
      escapeHtml_(behaviorText) + '.';
  }

  // Retensi menjadi kalimat tersendiri.
  var retentionParts = [];

  if (unit === 'sales') {
    var retention = dominant_(dfProf, cols.retention, retentionText_);
    if (retention) {
      retentionParts.push('<b>' + escapeHtml_(shortLabel_(retention.label)) + '</b> ' +
        'sebesar <b>' + retention.pct.toFixed(1) + '%</b>');
    }
  } else if (unit === 'service') {
    var retUnitSvc = dominant_(dfProf, findExactDataCol_(dfProf, 'Retention Unit'), retentionText_);
    var retService = dominant_(dfProf, findExactDataCol_(dfProf, 'Retention Service'), retentionText_);

    if (retUnitSvc) {
      retentionParts.push('untuk pembelian unit, <b>' + escapeHtml_(shortLabel_(retUnitSvc.label)) + '</b> ' +
        'sebesar <b>' + retUnitSvc.pct.toFixed(1) + '%</b>');
    }
    if (retService) {
      retentionParts.push('untuk layanan AHASS, <b>' + escapeHtml_(shortLabel_(retService.label)) + '</b> ' +
        'sebesar <b>' + retService.pct.toFixed(1) + '%</b>');
    }
  } else {
    var retUnitPart = dominant_(dfProf, findExactDataCol_(dfProf, 'Retention Unit'), retentionText_);
    var retPart = dominant_(dfProf, findExactDataCol_(dfProf, 'Retention Part'), retentionText_);

    if (retUnitPart) {
      retentionParts.push('untuk pembelian unit, <b>' + escapeHtml_(shortLabel_(retUnitPart.label)) + '</b> ' +
        'sebesar <b>' + retUnitPart.pct.toFixed(1) + '%</b>');
    }
    if (retPart) {
      retentionParts.push('untuk pembelian part, <b>' + escapeHtml_(shortLabel_(retPart.label)) + '</b> ' +
        'sebesar <b>' + retPart.pct.toFixed(1) + '%</b>');
    }
  }

  var sentence4 = '';
  if (retentionParts.length) {
    var retentionTextSummary = retentionParts.length === 1
      ? retentionParts[0] : retentionParts.join(' dan ');
    sentence4 = 'Dari sisi retensi, mayoritas pelanggan menunjukkan kecenderungan ' +
      'untuk kembali menggunakan produk atau layanan Honda; ' + retentionTextSummary + '.';
  }

  var npsUnitScore = npsValue(cols.nps_unit);
  var npsDealerScore = npsValue(cols.nps_dealer);
  var npsParts = [];

  if (npsUnitScore !== null) npsParts.push('NPS Unit <b>' + npsUnitScore.toFixed(1) + '</b>');

  if (npsDealerScore !== null) {
    var npsLabel = unit === 'sales' ? 'NPS Dealer' : (unit === 'service' ? 'NPS AHASS' : 'NPS Part');
    npsParts.push(npsLabel + ' <b>' + npsDealerScore.toFixed(1) + '</b>');
  }

  var sentence5 = '';
  if (npsParts.length) {
    var validScores = [];
    if (npsUnitScore !== null) validScores.push(npsUnitScore);
    if (npsDealerScore !== null) validScores.push(npsDealerScore);
    var avgNps = validScores.length ? meanSkipNa_(validScores) : null;

    if (avgNps !== null) {
      var loyaltyLabel;
      if (avgNps >= 85) loyaltyLabel = 'sangat baik';
      else if (avgNps >= 70) loyaltyLabel = 'baik';
      else if (avgNps >= 50) loyaltyLabel = 'cukup baik';
      else loyaltyLabel = 'masih perlu diperkuat';

      sentence5 = 'Nilai ' + npsParts.join(' dan ') +
        ' menunjukkan tingkat loyalitas pelanggan yang <b>' + loyaltyLabel + '</b>.';
    }
  }

  var narrative = [sentence1, sentence2, sentence3, sentence4, sentence5]
    .filter(function (s) { return s; })
    .join(' ');

  return {
    available: true,
    header: 'Ringkasan Profil',
    narrative: narrative
  };
}

/**
 * Padanan render_demographic_charts(): menyusun seluruh chart Section 3
 * mengikuti susunan baris/kolom yang sama seperti versi Streamlit.
 */
function buildDemographicCharts_(dfFiltered, cols, selectedProfile, unitKey) {
  var dfProf = dfFiltered;
  var profileCol = cols.profile;

  if (selectedProfile && profileCol && !isEmptyDf_(dfFiltered) && hasColumn_(dfFiltered, profileCol)) {
    var pNum = String(selectedProfile).replace('P', '').trim();
    var reNum = new RegExp('\\b' + pNum + '\\b', 'i');
    var reCode = new RegExp(selectedProfile, 'i');

    var matched = dfFiltered.rows.filter(function (r) {
      var v = r[profileCol];
      if (!notNull_(v)) return false;
      var s = toStr_(v);
      return reNum.test(s) || reCode.test(s);
    });

    if (matched.length) dfProf = subsetDf_(dfFiltered, matched);
  }

  var unit = String(unitKey || '').trim().toLowerCase();
  var out = { unit: unit, rows: {} };

  // Baris 1: demografi. H1 empat kolom (ada Payment), H2/H3 tiga kolom.
  out.rows.demographic = {
    columns: unit === 'sales' ? 4 : 3,
    gender: buildPieChart_(dfProf, cols.gender, 'Number of Respondents by Gender', [RED, ORANGE]),
    age: buildAgeChart_(dfProf, cols.age, 'Number of Respondents by Age'),
    motor: buildMotorChart_(dfProf, cols.motor_type, 'Motor Type')
  };

  if (unit === 'sales') {
    out.rows.demographic.payment = buildPieChart_(
      dfProf, cols.payment, 'Payment Type Distribution',
      [RED, ORANGE, YELLOW, GREEN, '#1E88E5']
    );
  }

  var npsUnitCol = cols.nps_unit;
  var npsDealerCol = cols.nps_dealer;

  if (unit === 'sales') {
    out.rows.second = {
      ses: buildStackedPct_(dfProf, cols.ses, 'SES', { isSes: true }),
      retention: buildStackedPct_(dfProf, cols.retention, 'Retention', { isRetention: true })
    };

    out.rows.third = {
      purchasePeriod: buildStackedPct_(
        dfProf, findExactDataCol_(dfProf, 'Period'), 'Next Purchase Period',
        { isPurchasePeriod: true }
      ),
      showroom: buildStackedPct_(
        dfProf, findExactDataCol_(dfProf, 'Showroom'), 'Next Purchase Location',
        { isPurchaseLocation: true }
      )
    };

    out.rows.fourth = {
      npsUnit: buildNpsGauge_(computeNps_(dfProf, npsUnitCol), 'NPS Unit'),
      reasonUnit: buildTopReasons_(dfProf, findExactDataCol_(dfProf, 'Reasons_Unit'), 'Top 5 Reason NPS Unit'),
      npsDealer: buildNpsGauge_(computeNps_(dfProf, npsDealerCol), 'NPS Dealer'),
      reasonDealer: buildTopReasons_(dfProf, findExactDataCol_(dfProf, 'Reasons_Dealer'), 'Top 5 Reason NPS Dealer')
    };

  } else if (unit === 'service') {
    out.rows.second = {
      ses: buildStackedPct_(dfProf, cols.ses, 'SES', { isSes: true }),
      frequencyAhass: buildStackedPct_(
        dfProf, findExactDataCol_(dfProf, 'Frequency Visit to AHASS'), 'Frequency Visit to AHASS',
        { showCategoryLegend: true }
      )
    };

    out.rows.third = {
      retentionUnit: buildStackedPct_(
        dfProf, findExactDataCol_(dfProf, 'Retention Unit'), 'Retention Unit', { isRetention: true }
      ),
      retentionService: buildStackedPct_(
        dfProf, findExactDataCol_(dfProf, 'Retention Service'), 'Retention Service', { isRetention: true }
      )
    };

    out.rows.fourth = {
      npsUnit: buildNpsGauge_(computeNps_(dfProf, npsUnitCol), 'NPS Unit'),
      reasonUnit: buildTopReasons_(dfProf, findExactDataCol_(dfProf, 'Reasons NPS.1'), 'Top 5 Reason NPS Unit'),
      npsDealer: buildNpsGauge_(computeNps_(dfProf, npsDealerCol), 'NPS AHASS'),
      reasonAhass: buildTopReasons_(dfProf, findExactDataCol_(dfProf, 'Reasons NPS'), 'Top 5 Reason NPS AHASS')
    };

  } else {
    out.rows.second = {
      ses: buildStackedPct_(dfProf, cols.ses, 'SES', { isSes: true }),
      futurePurchasePart: buildStackedPct_(
        dfProf, findExactDataCol_(dfProf, 'Future Purchase Part'), 'Future Purchase Part Location',
        { isPurchaseLocation: true, reverseOrder: true, reverseLocationColors: true, fullInsideLabel: true }
      )
    };

    out.rows.third = {
      retentionUnit: buildStackedPct_(
        dfProf, findExactDataCol_(dfProf, 'Retention Unit'), 'Retention Unit', { isRetention: true }
      ),
      retentionParts: buildStackedPct_(
        dfProf, findExactDataCol_(dfProf, 'Retention Part'), 'Retention Parts', { isRetention: true }
      )
    };

    out.rows.fourth = {
      npsUnit: buildNpsGauge_(computeNps_(dfProf, npsUnitCol), 'NPS Unit'),
      reasonUnit: buildTopReasons_(dfProf, findExactDataCol_(dfProf, 'Reasons NPS.1'), 'Top 5 Reason NPS Unit'),
      npsDealer: buildNpsGauge_(computeNps_(dfProf, npsDealerCol), 'NPS Part'),
      reasonParts: buildTopReasons_(dfProf, findExactDataCol_(dfProf, 'Reasons NPS'), 'Top 5 Reason NPS Parts')
    };
  }

  return { charts: out, dfProf: dfProf };
}

// ============================================================
// BERKAS ASAL: 06_Region.gs
// ============================================================

/**
 * ============================================================
 * 06_Region.gs
 * Porting dari seluruh fungsi rw_* pada app_backend.py
 * (Section 4: Profil Wilayah & Cluster Budaya).
 *
 * Rumus Jensen–Shannon Similarity, ambang kategori kemiripan,
 * dan teks penjelasan cluster/budaya tidak diubah.
 * ============================================================
 */

/** Padanan rw_culture_info(). */
function rwCultureInfo_(cultureName) {
  var key = String(cultureName || '').toLowerCase().replace(/[^a-z]/g, '');

  if (key.indexOf('arek') !== -1) return RW_CULTURE_INFO.arek;
  if (key.indexOf('mataram') !== -1) return RW_CULTURE_INFO.mataraman;
  if (key.indexOf('pendalungan') !== -1 || key.indexOf('pendhalungan') !== -1 || key.indexOf('pendaulungan') !== -1) {
    return RW_CULTURE_INFO.pendalungan;
  }
  if (key.indexOf('madura') !== -1) return RW_CULTURE_INFO.madura;
  if (key.indexOf('using') !== -1 || key.indexOf('osing') !== -1) return RW_CULTURE_INFO.using;
  if (key.indexOf('tengger') !== -1) return RW_CULTURE_INFO.tengger;
  if (key === 'ntt' || key.indexOf('nusatenggaratimur') !== -1) return RW_CULTURE_INFO.ntt;

  return {
    description: 'Penjelasan budaya belum tersedia.',
    character: 'Karakter umum belum tersedia.'
  };
}

/** Padanan rw_normalize_text(). */
function rwNormalizeText_(value) {
  if (!notNull_(value)) return null;
  var text = toStr_(value).trim().toLowerCase();
  if (!text || text === 'nan' || text === 'none' || text === '-') return null;
  text = text.replace(/[\/_.]+/g, ' ');
  text = text.replace(/\s+/g, ' ').trim();
  return text;
}

/** Padanan rw_normalize_region(). */
function rwNormalizeRegion_(value) {
  var text = rwNormalizeText_(value);
  if (text === null) return null;

  text = text.split('kab.').join('kabupaten ');
  text = text.split('kab ').join('kabupaten ');
  text = text.split('kodya').join('kota');
  text = text.replace(/\s+/g, ' ').trim();

  if (Object.prototype.hasOwnProperty.call(RW_REGION_ALIASES, text)) return RW_REGION_ALIASES[text];

  var withoutKab = text.replace(/^kabupaten\s+/, '').trim();
  if (Object.prototype.hasOwnProperty.call(RW_REGION_ALIASES, withoutKab)) return RW_REGION_ALIASES[withoutKab];

  // Padanan " ".join(word.capitalize() ...)
  return text.split(' ').map(function (w) {
    return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
  }).join(' ');
}

/** Padanan rw_normalize_profile(). */
function rwNormalizeProfile_(value) {
  if (!notNull_(value)) return null;

  if (typeof value === 'number') {
    if (isNaN(value)) return null;
    var p = Math.trunc(value);
    return RW_PROFILE_ORDER.indexOf(p) !== -1 ? p : null;
  }

  var match = toStr_(value).match(/([1-5])/);
  if (!match) return null;
  var pv = parseInt(match[1], 10);
  return RW_PROFILE_ORDER.indexOf(pv) !== -1 ? pv : null;
}

/** Padanan rw_validate_columns(). */
function rwValidateColumns_(df, requiredColumns, sourceName) {
  var missing = [];
  for (var i = 0; i < requiredColumns.length; i++) {
    if (!hasColumn_(df, requiredColumns[i])) missing.push(requiredColumns[i]);
  }
  if (missing.length) {
    throw new Error('Kolom berikut tidak ditemukan pada ' + sourceName + ': ' + missing.join(', '));
  }
}

/** Padanan rw_load_cluster_data(). */
function rwLoadClusterData_() {
  var clusterDf = tryReadSheetSilent_(RW_CLUSTER_SHEET);
  if (isEmptyDf_(clusterDf)) {
    throw new Error("Worksheet '" + RW_CLUSTER_SHEET + "' tidak ditemukan atau kosong.");
  }

  rwValidateColumns_(
    clusterDf,
    [RW_CLUSTER_REGION_COLUMN, RW_CLUSTER_COLUMN, RW_CLUSTER_PROFILE_COLUMN],
    'worksheet ' + RW_CLUSTER_SHEET
  );

  var seen = {};
  var rows = [];

  for (var i = 0; i < clusterDf.rows.length; i++) {
    var row = clusterDf.rows[i];
    var regionKey = rwNormalizeRegion_(row[RW_CLUSTER_REGION_COLUMN]);
    var clusterNum = toNum_(row[RW_CLUSTER_COLUMN]);
    var clusterProfile = row[RW_CLUSTER_PROFILE_COLUMN];

    if (regionKey === null || clusterNum === null || !notNull_(clusterProfile)) continue;
    if (Object.prototype.hasOwnProperty.call(seen, regionKey)) continue;
    seen[regionKey] = true;

    var out = {};
    out[RW_CLUSTER_REGION_COLUMN] = toStr_(row[RW_CLUSTER_REGION_COLUMN]);
    out[RW_CLUSTER_COLUMN] = Math.trunc(clusterNum);
    out[RW_CLUSTER_PROFILE_COLUMN] = toStr_(clusterProfile);
    out['Region_Key'] = regionKey;
    rows.push(out);
  }

  return {
    columns: [RW_CLUSTER_REGION_COLUMN, RW_CLUSTER_COLUMN, RW_CLUSTER_PROFILE_COLUMN, 'Region_Key'],
    rows: rows
  };
}

/** Padanan rw_load_culture_data(). */
function rwLoadCultureData_() {
  var cultureDf = readFirstAvailableSheet_(RW_CULTURE_SHEET_CANDIDATES);
  if (isEmptyDf_(cultureDf)) {
    throw new Error("Worksheet 'Pengelompokkan_budaya' tidak ditemukan atau kosong.");
  }

  var kabCol = findCol_(cultureDf, ['kabupaten/kota', 'kab/kota', 'kabupaten', 'kota', 'wilayah']);
  var zonaCol = findCol_(cultureDf, ['budaya_utama', 'zona budaya', 'budaya', 'cluster budaya', 'kelompok budaya']);
  var clusterCol = findCol_(cultureDf, ['cluster_budaya', 'cluster budaya']);

  if (!kabCol || !zonaCol) {
    throw new Error('Kolom Kabupaten/Kota atau Budaya_Utama tidak ditemukan pada worksheet budaya.');
  }

  var seen = {};
  var rows = [];

  for (var i = 0; i < cultureDf.rows.length; i++) {
    var row = cultureDf.rows[i];
    var regionKey = rwNormalizeRegion_(row[kabCol]);
    var kelompok = toStr_(row[zonaCol]).trim();

    if (regionKey === null || !kelompok) continue;
    if (Object.prototype.hasOwnProperty.call(seen, regionKey)) continue;
    seen[regionKey] = true;

    var clusterBudaya = clusterCol ? toNum_(row[clusterCol]) : null;

    rows.push({
      'Kabupaten/Kota_Budaya': toStr_(row[kabCol]),
      'Kelompok_Budaya': kelompok,
      'Cluster_Budaya': clusterBudaya === null ? null : Math.trunc(clusterBudaya),
      'Region_Key': regionKey
    });
  }

  return {
    columns: ['Kabupaten/Kota_Budaya', 'Kelompok_Budaya', 'Cluster_Budaya', 'Region_Key'],
    rows: rows
  };
}

/** Padanan rw_load_profile_metadata(). */
function rwLoadProfileMetadata_(hCode) {
  var config = RW_H_CONFIG[hCode];
  var metadataDf = tryReadSheetSilent_(config.metadata_sheet);
  if (isEmptyDf_(metadataDf)) {
    throw new Error("Worksheet '" + config.metadata_sheet + "' tidak ditemukan atau kosong.");
  }

  var profileCol = findCol_(metadataDf, ['profile', 'profil', 'no', 'code']);
  var nameCol = findCol_(metadataDf, ['profile name', 'nama profil', 'nama', 'name']);
  if (!profileCol || !nameCol) {
    throw new Error("Kolom Profile / Profile Name tidak ditemukan pada '" + config.metadata_sheet + "'.");
  }

  var rows = [];
  for (var i = 0; i < metadataDf.rows.length; i++) {
    var profile = rwNormalizeProfile_(metadataDf.rows[i][profileCol]);
    if (profile === null) continue;
    rows.push({
      'Profile': profile,
      'Profile Name': toStr_(metadataDf.rows[i][nameCol])
    });
  }

  return { columns: ['Profile', 'Profile Name'], rows: rows };
}

/** Padanan rw_load_csl_profile_data(). */
function rwLoadCslProfileData_(hCode) {
  var config = RW_H_CONFIG[hCode];
  var respondentDf = tryReadSheetSilent_(config.sheet);
  if (isEmptyDf_(respondentDf)) {
    throw new Error("Worksheet '" + config.sheet + "' tidak ditemukan atau kosong.");
  }

  var regionCol = findCol_(respondentDf, [config.region_column.toLowerCase()]);
  if (!regionCol && hasColumn_(respondentDf, config.region_column)) regionCol = config.region_column;

  var profileCol = findCol_(respondentDf, [config.profile_column.toLowerCase()]);
  if (!profileCol && hasColumn_(respondentDf, config.profile_column)) profileCol = config.profile_column;

  if (!regionCol || !profileCol) {
    throw new Error("Kolom wilayah/profile tidak ditemukan pada '" + config.sheet + "'.");
  }

  var regionNonNull = 0;
  var profileNonNull = 0;
  var rows = [];
  var regionSet = {};

  for (var i = 0; i < respondentDf.rows.length; i++) {
    var row = respondentDf.rows[i];
    if (notNull_(row[regionCol])) regionNonNull += 1;
    if (notNull_(row[profileCol])) profileNonNull += 1;

    var regionKey = rwNormalizeRegion_(row[regionCol]);
    var profileClean = rwNormalizeProfile_(row[profileCol]);
    if (regionKey === null || profileClean === null) continue;

    regionSet[regionKey] = true;
    rows.push({ 'Region_Key': regionKey, 'Profile_Clean': profileClean });
  }

  var diagnostic = {
    total_rows: respondentDf.rows.length,
    region_non_null: regionNonNull,
    profile_non_null: profileNonNull,
    valid_rows: rows.length,
    valid_regions: Object.keys(regionSet).length
  };

  return {
    df: { columns: ['Region_Key', 'Profile_Clean'], rows: rows },
    diagnostic: diagnostic
  };
}

/** Padanan rw_calculate_region_profile_distribution(). */
function rwCalculateRegionProfileDistribution_(respondentDf, metadataDf, clusterDf, minimumRespondents) {
  // Merge respondent ke cluster berdasarkan Region_Key.
  var clusterByRegion = {};
  for (var c = 0; c < clusterDf.rows.length; c++) {
    clusterByRegion[clusterDf.rows[c]['Region_Key']] = clusterDf.rows[c];
  }

  var unmatchedSet = {};
  var groups = {};
  var groupOrder = [];

  for (var i = 0; i < respondentDf.rows.length; i++) {
    var row = respondentDf.rows[i];
    var regionKey = row['Region_Key'];
    var clusterRow = clusterByRegion[regionKey];

    if (!clusterRow) {
      unmatchedSet[regionKey] = true;
      continue;
    }

    if (!Object.prototype.hasOwnProperty.call(groups, regionKey)) {
      groups[regionKey] = {
        regionKey: regionKey,
        cluster: clusterRow[RW_CLUSTER_COLUMN],
        clusterProfile: clusterRow[RW_CLUSTER_PROFILE_COLUMN],
        display: clusterRow[RW_CLUSTER_REGION_COLUMN],
        counts: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 }
      };
      groupOrder.push(regionKey);
    }
    groups[regionKey].counts[row['Profile_Clean']] += 1;
  }

  var unmatchedRegions = Object.keys(unmatchedSet).sort();

  if (!groupOrder.length) {
    return { summary: [], unmatchedRegions: unmatchedRegions };
  }

  var profileNameMap = {};
  for (var m = 0; m < metadataDf.rows.length; m++) {
    profileNameMap[metadataDf.rows[m]['Profile']] = metadataDf.rows[m]['Profile Name'];
  }

  var summary = [];
  for (var g = 0; g < groupOrder.length; g++) {
    var grp = groups[groupOrder[g]];

    var totalResponden = 0;
    for (var p = 0; p < RW_PROFILE_ORDER.length; p++) {
      totalResponden += grp.counts[RW_PROFILE_ORDER[p]];
    }

    var item = {
      'Kabupaten/Kota': grp.display,
      'Region_Key': grp.regionKey,
      'Cluster': grp.cluster,
      'Profil_Wilayah': grp.clusterProfile,
      'Jumlah_Responden': totalResponden
    };

    var percents = [];
    for (var q = 0; q < RW_PROFILE_ORDER.length; q++) {
      var prof = RW_PROFILE_ORDER[q];
      var cnt = grp.counts[prof];
      item['Jumlah_Profile_' + prof] = cnt;
      var pct = totalResponden > 0 ? (cnt / totalResponden * 100) : null;
      item['Persen_Profile_' + prof] = pct;
      percents.push({ profile: prof, pct: pct === null ? -Infinity : pct });
    }

    // argsort menurun: profil dominan dan profil kedua.
    var sortedPercents = percents.slice().sort(function (a, b) {
      if (b.pct !== a.pct) return b.pct - a.pct;
      return a.profile - b.profile;
    });

    item['Profile_Dominan'] = sortedPercents[0].profile;
    item['Profile_Kedua'] = sortedPercents[1].profile;
    item['Persen_Dominan'] = item['Persen_Profile_' + sortedPercents[0].profile];
    item['Persen_Kedua'] = item['Persen_Profile_' + sortedPercents[1].profile];
    item['Margin_Dominasi'] = (item['Persen_Dominan'] === null || item['Persen_Kedua'] === null)
      ? null : item['Persen_Dominan'] - item['Persen_Kedua'];

    item['Status_Sampel'] = totalResponden >= minimumRespondents ? 'Memadai' : 'Di Bawah Minimum';
    item['Nama_Profile_Dominan'] = profileNameMap[item['Profile_Dominan']] || null;
    item['Nama_Profile_Kedua'] = profileNameMap[item['Profile_Kedua']] || null;

    summary.push(item);
  }

  // sort_values([Cluster, Kabupaten/Kota])
  summary.sort(function (a, b) {
    if (a['Cluster'] !== b['Cluster']) return a['Cluster'] - b['Cluster'];
    var ka = toStr_(a['Kabupaten/Kota']);
    var kb = toStr_(b['Kabupaten/Kota']);
    return ka < kb ? -1 : (ka > kb ? 1 : 0);
  });

  return { summary: summary, unmatchedRegions: unmatchedRegions };
}

/** Padanan rw_jensen_shannon_similarity(). */
function rwJensenShannonSimilarity_(firstDistribution, secondDistribution) {
  var first = firstDistribution.slice();
  var second = secondDistribution.slice();

  var sumFirst = 0, sumSecond = 0;
  for (var i = 0; i < first.length; i++) {
    first[i] = (first[i] === null || isNaN(first[i])) ? 0 : first[i];
    second[i] = (second[i] === null || isNaN(second[i])) ? 0 : second[i];
    sumFirst += first[i];
    sumSecond += second[i];
  }
  if (sumFirst <= 0 || sumSecond <= 0) return null;

  for (var j = 0; j < first.length; j++) {
    first[j] = first[j] / sumFirst;
    second[j] = second[j] / sumSecond;
  }

  var midpoint = [];
  for (var k = 0; k < first.length; k++) midpoint.push(0.5 * (first[k] + second[k]));

  function klDivergence(distribution, reference) {
    var sum = 0;
    for (var n = 0; n < distribution.length; n++) {
      if (distribution[n] > 0) {
        sum += distribution[n] * (Math.log(distribution[n] / reference[n]) / Math.LN2);
      }
    }
    return sum;
  }

  var jsDivergence = 0.5 * klDivergence(first, midpoint) + 0.5 * klDivergence(second, midpoint);
  var jsDistance = Math.sqrt(Math.max(jsDivergence, 0));
  return 1 - jsDistance;
}

/** Padanan rw_classify_similarity(). */
function rwClassifySimilarity_(value) {
  if (value === null || value === undefined || isNaN(value)) return 'Belum Dapat Dinilai';
  if (value >= 0.85) return 'Sangat Mirip';
  if (value >= 0.70) return 'Cukup Mirip';
  return 'Beragam';
}

/** Menghitung rata-rata kemiripan pasangan wilayah dalam satu grup. */
function rwGroupSimilarity_(group) {
  var matrix = group.map(function (row) {
    var dist = [];
    for (var p = 0; p < RW_PROFILE_ORDER.length; p++) {
      var v = row['Persen_Profile_' + RW_PROFILE_ORDER[p]];
      dist.push(v === null ? 0 : v / 100);
    }
    return dist;
  });

  var sims = [];
  for (var i = 0; i < matrix.length; i++) {
    for (var j = i + 1; j < matrix.length; j++) {
      var sim = rwJensenShannonSimilarity_(matrix[i], matrix[j]);
      if (sim !== null && !isNaN(sim)) sims.push(sim);
    }
  }
  return sims.length ? meanSkipNa_(sims) : null;
}

/** Menghitung profil mayoritas dan konsistensinya dalam satu grup. */
function rwGroupMajority_(group) {
  var dominants = group.map(function (r) { return String(r['Profile_Dominan']); });
  if (!dominants.length) return { profile: null, regions: 0, consistency: null };

  var counts = valueCounts_(dominants);
  var majorityProfile = parseInt(counts[0].label, 10);
  var majorityRegions = counts[0].count;
  return {
    profile: majorityProfile,
    regions: majorityRegions,
    consistency: majorityRegions / group.length * 100
  };
}

/** Padanan rw_calculate_cluster_similarity(). */
function rwCalculateClusterSimilarity_(regionSummary, minimumRespondents) {
  if (!regionSummary.length) return [];

  var eligible = regionSummary.filter(function (r) {
    return r['Jumlah_Responden'] >= minimumRespondents;
  });

  var groups = {};
  var order = [];
  for (var i = 0; i < eligible.length; i++) {
    var key = eligible[i]['Cluster'] + '||' + eligible[i]['Profil_Wilayah'];
    if (!groups[key]) {
      groups[key] = [];
      order.push(key);
    }
    groups[key].push(eligible[i]);
  }

  var results = [];
  for (var o = 0; o < order.length; o++) {
    var group = groups[order[o]];
    var parts = order[o].split('||');
    var majority = rwGroupMajority_(group);
    var averageSimilarity = rwGroupSimilarity_(group);

    results.push({
      Cluster: parseInt(parts[0], 10),
      Profil_Wilayah: parts[1],
      Jumlah_Wilayah_Valid: group.length,
      Profile_Mayoritas: majority.profile,
      Jumlah_Wilayah_Sesuai: majority.regions,
      Konsistensi_Profile_Dominan: majority.consistency,
      Kemiripan_Distribusi: averageSimilarity,
      Kategori_Kemiripan: rwClassifySimilarity_(averageSimilarity)
    });
  }

  results.sort(function (a, b) { return a.Cluster - b.Cluster; });
  return results;
}

/** Padanan rw_calculate_culture_similarity(). */
function rwCalculateCultureSimilarity_(regionSummaryCulture, minimumRespondents) {
  if (!regionSummaryCulture.length) return [];

  var eligible = regionSummaryCulture.filter(function (r) {
    return r['Jumlah_Responden'] >= minimumRespondents && notNull_(r['Kelompok_Budaya']);
  });

  var groups = {};
  var order = [];
  for (var i = 0; i < eligible.length; i++) {
    var key = eligible[i]['Kelompok_Budaya'];
    if (!groups[key]) {
      groups[key] = [];
      order.push(key);
    }
    groups[key].push(eligible[i]);
  }

  var results = [];
  for (var o = 0; o < order.length; o++) {
    var group = groups[order[o]];
    var majority = rwGroupMajority_(group);
    var averageSimilarity = rwGroupSimilarity_(group);

    results.push({
      Kelompok_Budaya: order[o],
      Jumlah_Wilayah_Valid: group.length,
      Profile_Mayoritas: majority.profile,
      Jumlah_Wilayah_Sesuai: majority.regions,
      Konsistensi_Profile_Dominan: majority.consistency,
      Kemiripan_Distribusi: averageSimilarity,
      Kategori_Kemiripan: rwClassifySimilarity_(averageSimilarity)
    });
  }

  results.sort(function (a, b) {
    return a.Kelompok_Budaya < b.Kelompok_Budaya ? -1 : (a.Kelompok_Budaya > b.Kelompok_Budaya ? 1 : 0);
  });
  return results;
}

/** Padanan rw_create_cluster_dominant_chart() bagian data. */
function rwBuildClusterDominantChart_(regionSummary) {
  var counts = {};
  var clusterOrder = [];

  for (var i = 0; i < regionSummary.length; i++) {
    var cluster = regionSummary[i]['Profil_Wilayah'];
    var profile = regionSummary[i]['Profile_Dominan'];
    if (!counts[cluster]) {
      counts[cluster] = {};
      clusterOrder.push(cluster);
    }
    counts[cluster][profile] = (counts[cluster][profile] || 0) + 1;
  }

  clusterOrder.sort();

  var series = [];
  for (var p = 0; p < RW_PROFILE_ORDER.length; p++) {
    var prof = RW_PROFILE_ORDER[p];
    var values = [];
    var hasData = false;

    for (var c = 0; c < clusterOrder.length; c++) {
      var clusterCounts = counts[clusterOrder[c]];
      var total = 0;
      for (var k in clusterCounts) if (Object.prototype.hasOwnProperty.call(clusterCounts, k)) total += clusterCounts[k];
      var cnt = clusterCounts[prof] || 0;
      if (cnt > 0) hasData = true;
      values.push(total > 0 ? cnt / total * 100 : 0);
    }

    if (hasData) {
      series.push({
        name: 'Profile ' + prof,
        color: RW_CLUSTER_PROFILE_COLORS['Profile ' + prof],
        values: values
      });
    }
  }

  return {
    title: 'Dominasi Profile berdasarkan Cluster Wilayah',
    subtitle: 'Proporsi kabupaten/kota berdasarkan customer profile dominan pada cluster karakteristik wilayah (BPS)',
    xLabels: clusterOrder,
    xAxisTitle: 'Cluster Wilayah',
    yAxisTitle: 'Persentase Wilayah',
    series: series,
    barWidth: 0.45,
    height: 300,
    legendTitle: 'Profile Dominan'
  };
}

/** Padanan rw_create_culture_dominant_chart() bagian data. */
function rwBuildCultureDominantChart_(regionSummary, cultureDf) {
  var cultureByRegion = {};
  for (var c = 0; c < cultureDf.rows.length; c++) {
    cultureByRegion[cultureDf.rows[c]['Region_Key']] = cultureDf.rows[c]['Kelompok_Budaya'];
  }

  var counts = {};
  var cultureOrder = [];

  for (var i = 0; i < regionSummary.length; i++) {
    var culture = cultureByRegion[regionSummary[i]['Region_Key']];
    if (!notNull_(culture)) continue;

    var profile = regionSummary[i]['Profile_Dominan'];
    if (!counts[culture]) {
      counts[culture] = {};
      cultureOrder.push(culture);
    }
    counts[culture][profile] = (counts[culture][profile] || 0) + 1;
  }

  cultureOrder.sort();

  var series = [];
  for (var p = 0; p < RW_PROFILE_ORDER.length; p++) {
    var prof = RW_PROFILE_ORDER[p];
    var values = [];
    var hasData = false;

    for (var k = 0; k < cultureOrder.length; k++) {
      var cultureCounts = counts[cultureOrder[k]];
      var total = 0;
      for (var key in cultureCounts) if (Object.prototype.hasOwnProperty.call(cultureCounts, key)) total += cultureCounts[key];
      var cnt = cultureCounts[prof] || 0;
      if (cnt > 0) hasData = true;
      values.push(total > 0 ? cnt / total * 100 : 0);
    }

    if (hasData) {
      series.push({
        name: 'Profile ' + prof,
        color: RW_CLUSTER_PROFILE_COLORS['Profile ' + prof],
        values: values
      });
    }
  }

  return {
    title: 'Dominasi Profile berdasarkan Kelompok Budaya',
    subtitle: 'Proporsi kabupaten/kota berdasarkan customer profile dominan pada masing-masing kelompok budaya',
    xLabels: cultureOrder,
    xAxisTitle: 'Kelompok Budaya',
    yAxisTitle: 'Persentase Wilayah',
    series: series,
    barWidth: 0.50,
    height: 300,
    legendTitle: 'Profile Dominan'
  };
}

/** Padanan rw_render_cluster_region_details(). */
function rwBuildClusterRegionDetails_(clusterDf) {
  var groups = {};
  var order = [];

  for (var i = 0; i < clusterDf.rows.length; i++) {
    var row = clusterDf.rows[i];
    var key = row[RW_CLUSTER_COLUMN] + '||' + row[RW_CLUSTER_PROFILE_COLUMN];
    if (!groups[key]) {
      groups[key] = { cluster: row[RW_CLUSTER_COLUMN], name: row[RW_CLUSTER_PROFILE_COLUMN], regions: [] };
      order.push(key);
    }
    if (notNull_(row[RW_CLUSTER_REGION_COLUMN])) {
      groups[key].regions.push(toStr_(row[RW_CLUSTER_REGION_COLUMN]));
    }
  }

  var items = order.map(function (k) { return groups[k]; });
  items.sort(function (a, b) { return a.cluster - b.cluster; });

  return items.map(function (g) {
    var uniqueRegions = [];
    var seen = {};
    for (var r = 0; r < g.regions.length; r++) {
      if (!seen[g.regions[r]]) { seen[g.regions[r]] = true; uniqueRegions.push(g.regions[r]); }
    }
    uniqueRegions.sort();

    var info = RW_CLUSTER_EXPLANATIONS[String(g.name).trim()] || {};
    return {
      title: 'Cluster ' + g.cluster + ' – ' + g.name,
      regionCount: uniqueRegions.length,
      countText: '(' + uniqueRegions.length + ' Wilayah)',
      description: info.description || 'Penjelasan penamaan cluster belum tersedia untuk profile ini.',
      regions: uniqueRegions.join(', ')
    };
  });
}

/** Padanan rw_render_culture_region_details(). */
function rwBuildCultureRegionDetails_(cultureDf) {
  var groups = {};
  var order = [];

  for (var i = 0; i < cultureDf.rows.length; i++) {
    var row = cultureDf.rows[i];
    var key = row['Kelompok_Budaya'];
    if (!notNull_(key)) continue;
    if (!groups[key]) {
      groups[key] = { name: key, cluster: row['Cluster_Budaya'], regions: [] };
      order.push(key);
    }
    if (notNull_(row['Kabupaten/Kota_Budaya'])) groups[key].regions.push(toStr_(row['Kabupaten/Kota_Budaya']));
  }

  // Urutan mengikuti Cluster_Budaya bila ada, jika tidak berdasarkan nama.
  var hasClusterBudaya = false;
  for (var o = 0; o < order.length; o++) {
    if (groups[order[o]].cluster !== null && groups[order[o]].cluster !== undefined) hasClusterBudaya = true;
  }

  if (hasClusterBudaya) {
    order.sort(function (a, b) {
      var ca = groups[a].cluster, cb = groups[b].cluster;
      if (ca === null || ca === undefined) return 1;
      if (cb === null || cb === undefined) return -1;
      return ca - cb;
    });
  } else {
    order.sort();
  }

  return order.map(function (k) {
    var g = groups[k];
    var uniqueRegions = [];
    var seen = {};
    for (var r = 0; r < g.regions.length; r++) {
      if (!seen[g.regions[r]]) { seen[g.regions[r]] = true; uniqueRegions.push(g.regions[r]); }
    }
    uniqueRegions.sort();

    var info = rwCultureInfo_(g.name);
    var clusterPrefix = (g.cluster !== null && g.cluster !== undefined)
      ? 'Cluster Budaya ' + g.cluster + ' – ' : '';

    return {
      title: clusterPrefix + g.name,
      regionCount: uniqueRegions.length,
      countText: '(' + uniqueRegions.length + ' Wilayah)',
      description: info.description,
      character: info.character,
      regions: uniqueRegions.join(', ')
    };
  });
}

/**
 * Payload lengkap Section 4, padanan rw_render_region_profile_page().
 * selectedH: 'H1' | 'H2' | 'H3'
 * selectedCluster: 'Semua' atau nama Profil Wilayah
 * sortProfile: 'Profile Wilayah' atau 'Profile 1'..'Profile 5'
 */
function buildRegionProfilePage_(selectedH, selectedCluster, sortProfile) {
  selectedH = RW_H_CONFIG[selectedH] ? selectedH : 'H1';
  selectedCluster = selectedCluster || 'Semua';
  sortProfile = sortProfile || 'Profile Wilayah';

  var minimumRespondents = RW_MINIMUM_RESPONDENTS;

  var clusterDf, cultureDf, metadataDf, respondentPack;
  try {
    clusterDf = rwLoadClusterData_();
    cultureDf = rwLoadCultureData_();
    metadataDf = rwLoadProfileMetadata_(selectedH);
    respondentPack = rwLoadCslProfileData_(selectedH);
  } catch (e) {
    return {
      available: false,
      error: e.message,
      hint: "Periksa nama worksheet 'Hasil_Cluster', 'Pengelompokkan_budaya', dan " +
            "'profile_metadata_H1/H2/H3' pada Google Sheets."
    };
  }

  var respondentDf = respondentPack.df;
  if (isEmptyDf_(respondentDf)) {
    return {
      available: false,
      error: 'Tidak ada baris yang memiliki wilayah dan Profile secara bersamaan untuk bagian ini.'
    };
  }

  var dist = rwCalculateRegionProfileDistribution_(
    respondentDf, metadataDf, clusterDf, minimumRespondents
  );
  var regionSummary = dist.summary;

  if (!regionSummary.length) {
    return {
      available: false,
      error: 'Tidak ada wilayah CSL yang berhasil dipasangkan dengan data cluster BPS.',
      unmatchedRegions: dist.unmatchedRegions
    };
  }

  // Opsi filter cluster.
  var clusterSet = {};
  for (var i = 0; i < regionSummary.length; i++) {
    if (notNull_(regionSummary[i]['Profil_Wilayah'])) clusterSet[regionSummary[i]['Profil_Wilayah']] = true;
  }
  var clusterOptions = ['Semua'].concat(Object.keys(clusterSet).sort());
  if (clusterOptions.indexOf(selectedCluster) === -1) selectedCluster = 'Semua';

  var filteredSummary = regionSummary.slice();
  if (selectedCluster !== 'Semua') {
    filteredSummary = filteredSummary.filter(function (r) {
      return r['Profil_Wilayah'] === selectedCluster;
    });
  }

  // Pengurutan stacked bar.
  var sortedSummary = filteredSummary.slice();
  if (sortProfile === 'Profile Wilayah') {
    sortedSummary.sort(function (a, b) {
      if (a['Profil_Wilayah'] !== b['Profil_Wilayah']) {
        return a['Profil_Wilayah'] < b['Profil_Wilayah'] ? -1 : 1;
      }
      if (a['Cluster'] !== b['Cluster']) return a['Cluster'] - b['Cluster'];
      var ka = toStr_(a['Kabupaten/Kota']), kb = toStr_(b['Kabupaten/Kota']);
      return ka < kb ? -1 : (ka > kb ? 1 : 0);
    });
  } else {
    var numMatch = String(sortProfile).match(/(\d+)/);
    var selectedProfileNumber = numMatch ? parseInt(numMatch[1], 10) : 1;
    var sortColumn = 'Persen_Profile_' + selectedProfileNumber;
    sortedSummary.sort(function (a, b) {
      var va = a[sortColumn] === null ? -Infinity : a[sortColumn];
      var vb = b[sortColumn] === null ? -Infinity : b[sortColumn];
      if (va !== vb) return vb - va;
      if (a['Profil_Wilayah'] !== b['Profil_Wilayah']) {
        return a['Profil_Wilayah'] < b['Profil_Wilayah'] ? -1 : 1;
      }
      var ka = toStr_(a['Kabupaten/Kota']), kb = toStr_(b['Kabupaten/Kota']);
      return ka < kb ? -1 : (ka > kb ? 1 : 0);
    });
  }

  // KPI.
  var eligibleSummary = filteredSummary.filter(function (r) {
    return r['Jumlah_Responden'] >= minimumRespondents;
  });

  var clusterSimilarityAll = rwCalculateClusterSimilarity_(regionSummary, minimumRespondents);

  var cultureByRegion = {};
  for (var cc = 0; cc < cultureDf.rows.length; cc++) {
    cultureByRegion[cultureDf.rows[cc]['Region_Key']] = cultureDf.rows[cc]['Kelompok_Budaya'];
  }
  var regionSummaryCulture = regionSummary.map(function (r) {
    var copy = {};
    for (var k in r) if (Object.prototype.hasOwnProperty.call(r, k)) copy[k] = r[k];
    copy['Kelompok_Budaya'] = cultureByRegion[r['Region_Key']] || null;
    return copy;
  });
  var cultureSimilarityAll = rwCalculateCultureSimilarity_(regionSummaryCulture, minimumRespondents);

  var dominantOverall = null;
  if (eligibleSummary.length) {
    var dominants = eligibleSummary.map(function (r) { return String(r['Profile_Dominan']); });
    // mode(): nilai terkecil bila seri, sesuai perilaku pandas.
    var vc = valueCounts_(dominants);
    var topCount = vc[0].count;
    var tied = vc.filter(function (x) { return x.count === topCount; })
      .map(function (x) { return parseInt(x.label, 10); });
    tied.sort(function (a, b) { return a - b; });
    dominantOverall = tied[0];
  }

  var profileNameMap = {};
  for (var mm = 0; mm < metadataDf.rows.length; mm++) {
    profileNameMap[metadataDf.rows[mm]['Profile']] = metadataDf.rows[mm]['Profile Name'];
  }
  var dominantOverallName = dominantOverall !== null
    ? (profileNameMap[dominantOverall] || '-') : '-';

  var relevantSimilarity = selectedCluster === 'Semua'
    ? clusterSimilarityAll
    : clusterSimilarityAll.filter(function (r) { return r.Profil_Wilayah === selectedCluster; });

  var simValues = relevantSimilarity
    .map(function (r) { return r.Kemiripan_Distribusi; })
    .filter(function (v) { return v !== null && !isNaN(v); });
  var averageDistributionSimilarity = simValues.length ? meanSkipNa_(simValues) : null;

  var jumlahWilayahSet = {};
  var jumlahResponden = 0;
  for (var f = 0; f < filteredSummary.length; f++) {
    jumlahWilayahSet[filteredSummary[f]['Kabupaten/Kota']] = true;
    jumlahResponden += filteredSummary[f]['Jumlah_Responden'];
  }
  var jumlahWilayah = Object.keys(jumlahWilayahSet).length;

  var similarityPct = averageDistributionSimilarity !== null ? averageDistributionSimilarity * 100 : null;
  var similarityCategory = rwClassifySimilarity_(averageDistributionSimilarity);
  var similarityColor = similarityCategory === 'Sangat Mirip' ? GREEN
    : (similarityCategory === 'Cukup Mirip' ? ORANGE
      : (similarityCategory === 'Beragam' ? RED : '#888888'));

  var dominantColor = dominantOverall !== null
    ? (RW_PROFILE_COLORS[dominantOverall] || '#555555') : '#888888';

  var kpi = [
    {
      label: 'Jumlah Wilayah',
      value: String(jumlahWilayah).replace(/\B(?=(\d{3})+(?!\d))/g, '.'),
      sub: 'Wilayah Tercakup', subColor: '#555555'
    },
    {
      label: 'Jumlah Responden',
      value: String(jumlahResponden).replace(/\B(?=(\d{3})+(?!\d))/g, '.'),
      sub: 'Responden Tervalidasi', subColor: '#555555'
    },
    {
      label: 'Profile Dominan Umum',
      value: dominantOverall !== null ? 'Profile ' + dominantOverall : '-',
      sub: dominantOverallName, subColor: dominantColor
    },
    {
      label: 'Kemiripan Distribusi',
      value: similarityPct !== null ? similarityPct.toFixed(1) + '%' : 'N/A',
      sub: similarityCategory, subColor: similarityColor
    }
  ];

  // Stacked bar per wilayah.
  var stackedSeries = [];
  for (var sp = 0; sp < RW_PROFILE_ORDER.length; sp++) {
    var prof = RW_PROFILE_ORDER[sp];
    stackedSeries.push({
      name: 'Profile ' + prof,
      profileLabel: profileNameMap[prof] || ('Profile ' + prof),
      color: RW_PROFILE_COLORS[prof],
      values: sortedSummary.map(function (r) { return r['Persen_Profile_' + prof]; }),
      counts: sortedSummary.map(function (r) { return r['Jumlah_Profile_' + prof]; })
    });
  }

  var eligibleAll = regionSummary.filter(function (r) {
    return r['Jumlah_Responden'] >= minimumRespondents;
  });

  function similarityInsight(list, isCluster) {
    return list.map(function (row) {
      var majProf = row.Profile_Mayoritas !== null ? 'Profile ' + row.Profile_Mayoritas : '-';
      var simPct = (row.Kemiripan_Distribusi !== null && !isNaN(row.Kemiripan_Distribusi))
        ? (row.Kemiripan_Distribusi * 100).toFixed(1) + '%' : '-';
      var consPct = (row.Konsistensi_Profile_Dominan !== null && !isNaN(row.Konsistensi_Profile_Dominan))
        ? row.Konsistensi_Profile_Dominan.toFixed(1) + '%' : '-';

      return {
        header: isCluster
          ? 'Cluster ' + row.Cluster + ' – ' + row.Profil_Wilayah
          : row.Kelompok_Budaya,
        majorityProfile: majProf,
        regionsMatched: row.Jumlah_Wilayah_Sesuai,
        regionsValid: row.Jumlah_Wilayah_Valid,
        consistency: consPct,
        similarity: simPct,
        category: row.Kategori_Kemiripan
      };
    });
  }

  return {
    available: true,
    sectionBadge: 'SECTION 4',
    sectionTitle: 'PROFIL WILAYAH & CLUSTER BUDAYA',
    description: 'Menunjukkan pengelompokan kabupaten/kota berdasarkan karakteristik wilayah ' +
      '(Cluster BPS) dan kelompok budaya, serta kesesuaiannya dengan distribusi ' +
      'Customer Profile hasil survei.',
    selection: { h: selectedH, cluster: selectedCluster, sortProfile: sortProfile },
    options: {
      h: Object.keys(RW_H_CONFIG).map(function (k) {
        return { value: k, label: k + ' — ' + RW_H_CONFIG[k].title };
      }),
      cluster: clusterOptions,
      sortProfile: ['Profile Wilayah'].concat(RW_PROFILE_ORDER.map(function (p) { return 'Profile ' + p; }))
    },
    unmatchedRegions: dist.unmatchedRegions,
    kpi: kpi,
    stackedChart: {
      title: 'Distribusi Customer Profile per Kabupaten/Kota',
      subtitle: 'Komposisi Profile 1–5 pada masing-masing kabupaten/kota berdasarkan persentase responden',
      regions: sortedSummary.map(function (r) { return r['Kabupaten/Kota']; }),
      totals: sortedSummary.map(function (r) { return r['Jumlah_Responden']; }),
      series: stackedSeries,
      height: Math.max(420, sortedSummary.length * 32)
    },
    clusterDominantChart: rwBuildClusterDominantChart_(eligibleAll),
    cultureDominantChart: rwBuildCultureDominantChart_(eligibleAll, cultureDf),
    clusteringMethodology: {
      title: 'Dasar Pembentukan Cluster Wilayah',
      intro: 'Cluster wilayah dibentuk menggunakan **K-Means (k=3)** setelah seluruh ' +
        'variabel distandardisasi menggunakan **Z-Score**.',
      variablesTitle: 'Variabel pembentuk cluster',
      variables: RW_CLUSTERING_VARIABLES.map(function (v) { return { name: v[0], desc: v[1] }; })
    },
    clusterDetails: {
      title: 'Keterangan Profile/Cluster Wilayah (BPS)',
      items: rwBuildClusterRegionDetails_(clusterDf)
    },
    cultureDetails: {
      title: 'Keterangan Kelompok Budaya',
      caption: 'Kelompok budaya digunakan sebagai konteks interpretasi wilayah dan tidak menjadi ' +
        'variabel pembentuk K-Means pada clustering BPS.',
      items: rwBuildCultureRegionDetails_(cultureDf)
    },
    clusterInsight: {
      title: 'Insight Cluster Wilayah',
      emptyMessage: 'Kemiripan belum dapat dinilai.',
      items: similarityInsight(clusterSimilarityAll, true)
    },
    cultureInsight: {
      title: 'Insight Kelompok Budaya',
      emptyMessage: 'Belum ada insight.',
      items: similarityInsight(cultureSimilarityAll, false)
    }
  };
}

// ============================================================
// BERKAS ASAL: 07_Api.gs
// ============================================================

/**
 * ============================================================
 * 07_Api.gs
 * Web API yang dikonsumsi frontend HTML (Cloudflare).
 *
 * Endpoint (semua lewat GET):
 *   ?action=config
 *   ?action=filterOptions&unit=sales&year=&semester=&md=&layer=&kar=&kab=&dealer=
 *   ?action=unitPage&unit=sales&...&profile=P1
 *   ?action=matrix&unit=sales&...&matrixMd=M2Z
 *   ?action=heatmap&unit=sales
 *   ?action=mapClick&unit=sales&region=NTT&year=&semester=
 *   ?action=regionPage&h=H1&cluster=Semua&sort=Profile%20Wilayah
 *   ?action=framework
 *
 * Tambahkan &callback=fn untuk JSONP bila diperlukan.
 * ============================================================
 */

function doGet(e) {
  var params = (e && e.parameter) ? e.parameter : {};
  var action = params.action || 'config';
  var payload;

  try {
    payload = routeAction_(action, params);
    payload.ok = true;
  } catch (err) {
    payload = { ok: false, error: String(err && err.message ? err.message : err) };
  }

  var json = JSON.stringify(payload);

  if (params.callback) {
    return ContentService
      .createTextOutput(params.callback + '(' + json + ');')
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }

  return ContentService
    .createTextOutput(json)
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  return doGet(e);
}

function routeAction_(action, params) {
  switch (action) {
    case 'config': return apiConfig_();
    case 'filterOptions': return apiFilterOptions_(params);
    case 'unitPage': return apiUnitPage_(params);
    case 'matrix': return apiMatrix_(params);
    case 'heatmap': return apiHeatmap_(params);
    case 'mapClick': return apiMapClick_(params);
    case 'regionPage': return apiRegionPage_(params);
    case 'framework': return apiFramework_();
    default:
      throw new Error("Action '" + action + "' tidak dikenal.");
  }
}

// ============================================================
// KONFIGURASI UMUM
// ============================================================

function apiConfig_() {
  return {
    pageOptions: PAGE_OPTIONS,
    units: {
      sales: { key: 'sales', unitLabel: 'Sales', dealerLabel: 'Dealer', hLabel: 'H1', page: 'H1 SALES' },
      service: { key: 'service', unitLabel: 'Service', dealerLabel: 'AHASS', hLabel: 'H2', page: 'H2 SERVICE' },
      parts: { key: 'parts', unitLabel: 'Spare Part', dealerLabel: 'Part Shop', hLabel: 'H3', page: 'H3 SPARE PART' }
    },
    colors: {
      red: RED, orange: ORANGE, yellow: YELLOW, green: GREEN,
      redOutline: RED_OUTLINE, orangeOutline: ORANGE_OUTLINE, blueOutline: BLUE_OUTLINE
    },
    profileNames: PROFILE_NAMES,
    profileColors: PROFILE_COLORS,
    sections: {
      one: { badge: 'SECTION 1', title: 'CSL PERFORMANCE INDEX' },
      two: { badge: 'SECTION 2', title: 'MATRIX SATISFACTION x IMPORTANCE' },
      three: { badge: 'SECTION 3', title: 'PROFILE CUSTOMER' },
      four: { badge: 'SECTION 4', title: 'PROFIL WILAYAH & CLUSTER BUDAYA' }
    },
    mapHeader: { title: 'Satisfaction Map', badge: 'CLICK MAP TO FILTER' },
    lastUpdate: formatUpdateTime_(new Date())
  };
}

/** Padanan _format_update_time(): "15 Sep 2026, 09:30 WIB". */
function formatUpdateTime_(date) {
  var monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
  var wib = 'GMT+7';
  var day = Utilities.formatDate(date, wib, 'dd');
  var month = parseInt(Utilities.formatDate(date, wib, 'MM'), 10);
  var year = Utilities.formatDate(date, wib, 'yyyy');
  var time = Utilities.formatDate(date, wib, 'HH:mm');
  return day + ' ' + monthNames[month - 1] + ' ' + year + ', ' + time + ' WIB';
}

// ============================================================
// LOADER DATA UNIT
// ============================================================

/** Memuat data responden + metadata untuk satu unit (H1/H2/H3). */
function loadUnitContext_(unitKey) {
  var config = UNIT_CONFIG[unitKey];

  if (!config) {
    throw new Error("Unit '" + unitKey + "' tidak dikenal.");
  }

  // =========================
  // 1. DATA RESPONDEN
  // =========================
  var dfRaw = tryReadSheet_(config.sheet);

  if (isEmptyDf_(dfRaw)) {
    throw new Error(
      "Data '" + config.sheet +
      "' tidak ditemukan atau gagal dimuat dari Google Sheets."
    );
  }

  // =========================
  // 2. METADATA INDIKATOR
  // =========================
  var indicatorMetadataSheet;

  if (unitKey === 'sales' || unitKey === 'h1') {
    indicatorMetadataSheet = 'Indicator_metadata_H1';
  } else if (unitKey === 'service' || unitKey === 'h2') {
    indicatorMetadataSheet = 'Indicator_metadata_H2';
  } else if (unitKey === 'parts' || unitKey === 'h3') {
    indicatorMetadataSheet = 'Indicator_metadata_H3';
  } else {
    throw new Error(
      "Unit '" + unitKey +
      "' tidak memiliki konfigurasi metadata indikator."
    );
  }

  var metaDf = tryReadSheet_(indicatorMetadataSheet);

  if (isEmptyDf_(metaDf)) {
    throw new Error(
      "Metadata indikator '" + indicatorMetadataSheet +
      "' tidak ditemukan atau kosong."
    );
  }

  // =========================
  // 3. METADATA PROFILE
  // =========================
  var profileMetadataSheet;

  if (unitKey === 'sales' || unitKey === 'h1') {
    profileMetadataSheet = 'profile_metadata_H1';
  } else if (unitKey === 'service' || unitKey === 'h2') {
    profileMetadataSheet = 'profile_metadata_H2';
  } else if (unitKey === 'parts' || unitKey === 'h3') {
    profileMetadataSheet = 'profile_metadata_H3';
  } else {
    throw new Error(
      "Unit '" + unitKey +
      "' tidak memiliki konfigurasi profile metadata."
    );
  }

  var profileMetaDf = tryReadSheet_(profileMetadataSheet);

  if (isEmptyDf_(profileMetaDf)) {
    throw new Error(
      "Metadata profil '" + profileMetadataSheet +
      "' tidak ditemukan atau kosong."
    );
  }

  // =========================
  // 4. PROSES DATA
  // =========================
  var cols = detectColumns_(dfRaw, unitKey);

  dfRaw = addKaresidenan_(dfRaw, cols);

  var indicatorCols = indicatorColumns_(
    dfRaw,
    metaDf,
    unitKey
  );

  // =========================
  // 5. RETURN CONTEXT
  // =========================
  return {
    unitKey: unitKey,
    config: config,
    df: dfRaw,
    cols: cols,
    metaDf: metaDf,
    profileMetaDf: profileMetaDf,
    indicatorCols: indicatorCols,
    indicatorNames: buildIndicatorNameMap_(metaDf)
  };
}

/**
 * Padanan render_filters(): membangun opsi bertingkat dan
 * memvalidasi pilihan (fallback ke "Semua" bila tidak tersedia).
 */
function buildFilterState_(ctx, params) {
  var df = ctx.df;
  var cols = ctx.cols;

  var yearCol = cols.year;
  var semCol = cols.semester;
  var mdCol = cols.main_dealer;
  var layerCol = cols.layer;
  var karCol = cols.karesidenan;
  var kabCol = cols.kab_kota;
  var dealerCol = cols.dealer_code;

  // Tahun
  var years = [];
  if (yearCol && hasColumn_(df, yearCol)) {
    var seenYear = {};
    for (var i = 0; i < df.rows.length; i++) {
      var yv = toNum_(df.rows[i][yearCol]);
      if (yv === null) continue;
      var ys = String(Math.trunc(yv));
      if (!seenYear[ys]) { seenYear[ys] = true; years.push(ys); }
    }
    years.sort();
  }
  var selYear = params.year && params.year !== '' ? String(params.year) : 'Semua';
  if (selYear !== 'Semua' && years.indexOf(selYear) === -1) selYear = 'Semua';

  // Periode
  var sems = ['Semester 1', 'Semester 2'];
  var selSem = params.semester && sems.indexOf(params.semester) !== -1 ? params.semester : sems[0];

  // Scope awal
  var scopeRows = df.rows;
  if (selYear !== 'Semua' && yearCol) {
    scopeRows = scopeRows.filter(function (r) { return toStr_(r[yearCol]) === selYear; });
  }
  if (semCol) {
    var targetSem = selSem.indexOf('1') !== -1 ? 1 : 2;
    scopeRows = scopeRows.filter(function (r) { return parseSemester_(r[semCol]) === targetSem; });
  }
  var dfScope = subsetDf_(df, scopeRows);

  // Main Dealer
  var mds = options_(dfScope, mdCol).filter(function (v) {
    return v.trim().toLowerCase() !== 'semua';
  });
  var mdOptions = ['Semua'].concat(mds);
  var selMd = params.md && mdOptions.indexOf(params.md) !== -1 ? params.md : 'Semua';
  if (selMd !== 'Semua' && mdCol) {
    dfScope = subsetDf_(dfScope, dfScope.rows.filter(function (r) { return toStr_(r[mdCol]) === selMd; }));
  }

  // Layer
  var layers = options_(dfScope, layerCol);
  var layerOptions = ['Semua'].concat(layers);
  var selLayer = params.layer && layerOptions.indexOf(params.layer) !== -1 ? params.layer : 'Semua';
  if (selLayer !== 'Semua' && layerCol) {
    dfScope = subsetDf_(dfScope, dfScope.rows.filter(function (r) { return toStr_(r[layerCol]) === selLayer; }));
  }

  // Karesidenan
  var kars = options_(dfScope, karCol);
  var karOptions = ['Semua'].concat(kars);
  var selKar = params.kar && karOptions.indexOf(params.kar) !== -1 ? params.kar : 'Semua';
  if (selKar !== 'Semua' && karCol) {
    dfScope = subsetDf_(dfScope, dfScope.rows.filter(function (r) { return toStr_(r[karCol]) === selKar; }));
  }

  // Kab / Kota
  var kabs = [];
  if (kabCol && hasColumn_(dfScope, kabCol)) {
    var seenKab = {};
    for (var k = 0; k < dfScope.rows.length; k++) {
      var kv = dfScope.rows[k][kabCol];
      if (!notNull_(kv)) continue;
      var name = dashboardRegionName_(kv);
      if (name && !seenKab[name]) { seenKab[name] = true; kabs.push(name); }
    }
    kabs.sort();
  }
  var kabOptions = ['Semua'].concat(kabs);
  var selKab = params.kab && kabOptions.indexOf(params.kab) !== -1 ? params.kab : 'Semua';
  if (selKab !== 'Semua' && kabCol) {
    dfScope = subsetDf_(dfScope, dfScope.rows.filter(function (r) {
      return dashboardRegionName_(r[kabCol]) === selKab;
    }));
  }

  // Dealer/AHASS/Part Shop: value = kode, label = Nama (Kode)
  var deals = options_(dfScope, dealerCol);
  var dealerNameCol = entityNameColumn_(dfScope, ctx.unitKey, ctx.config.dealerLabel);
  var dealerDisplay = {};

  if (dealerCol && hasColumn_(dfScope, dealerCol)) {
    for (var d = 0; d < dfScope.rows.length; d++) {
      var row = dfScope.rows[d];
      if (!notNull_(row[dealerCol])) continue;
      var codeText = toStr_(row[dealerCol]).trim();
      if (!codeText) continue;
      if (Object.prototype.hasOwnProperty.call(dealerDisplay, codeText)) continue;

      var nameText = '';
      if (dealerNameCol && notNull_(row[dealerNameCol])) {
        var candidate = toStr_(row[dealerNameCol]).trim();
        var low = candidate.toLowerCase();
        if (candidate !== '' && low !== 'nan' && low !== 'none' && low !== '-') nameText = candidate;
      }

      dealerDisplay[codeText] = (nameText && nameText !== codeText)
        ? nameText + ' (' + codeText + ')'
        : codeText;
    }
  }

  var dealerOptions = ['Semua'].concat(deals);
  var selDealer = params.dealer && dealerOptions.indexOf(params.dealer) !== -1 ? params.dealer : 'Semua';

  var filters = {
    year: selYear === 'Semua' ? null : selYear,
    semester: selSem.indexOf('1') !== -1 ? 1 : 2,
    main_dealer: selMd,
    layer: selLayer === 'Semua' ? null : selLayer,
    karesidenan: selKar === 'Semua' ? null : selKar,
    kab_kota: selKab === 'Semua' ? null : selKab,
    dealer: selDealer === 'Semua' ? null : selDealer
  };

  var optionsPayload = {
    year: { label: 'Tahun', options: ['Semua'].concat(years), selected: selYear },
    semester: { label: 'Periode', options: sems, selected: selSem },
    mainDealer: { label: 'Main Dealer', options: mdOptions, selected: selMd },
    layer: { label: 'Layer', options: layerOptions, selected: selLayer },
    karesidenan: { label: 'Karesidenan', options: karOptions, selected: selKar },
    kabKota: { label: 'Kab / Kota', options: kabOptions, selected: selKab },
    dealer: {
      label: ctx.config.dealerLabel,
      options: dealerOptions.map(function (code) {
        return {
          value: code,
          label: code === 'Semua' ? 'Semua' : (dealerDisplay[code] || code)
        };
      }),
      selected: selDealer
    }
  };

  return { filters: filters, options: optionsPayload, semesterLabel: selSem };
}

function apiFilterOptions_(params) {
  var unitKey = params.unit || 'sales';
  var ctx = loadUnitContext_(unitKey);
  var state = buildFilterState_(ctx, params);
  return { unit: unitKey, filterOptions: state.options, filters: state.filters };
}

// ============================================================
// UNIT PAGE (SECTION 1 + SECTION 3)
// ============================================================

function apiUnitPage_(params) {
  var unitKey = params.unit || 'sales';
  var ctx = loadUnitContext_(unitKey);

  var state = buildFilterState_(ctx, params);
  var filters = state.filters;
  var cols = ctx.cols;
  var dfAll = ctx.df;
  var indicatorCols = ctx.indicatorCols;

  var dfFiltered = applyFilters_(dfAll, cols, filters, null, null, false);

  // KPI: satisfaction semester 1 dan 2 pada tahun terpilih.
  var dfS1 = applyFilters_(dfAll, cols, filters, null, 1, true);
  var dfS2 = applyFilters_(dfAll, cols, filters, null, 2, true);

  var yearCol = cols.year;
  if (filters.year && yearCol) {
    dfS1 = subsetDf_(dfS1, dfS1.rows.filter(function (r) { return toStr_(r[yearCol]) === String(filters.year); }));
    dfS2 = subsetDf_(dfS2, dfS2.rows.filter(function (r) { return toStr_(r[yearCol]) === String(filters.year); }));
  }

  var satS1 = calculateSatisfaction_(dfS1, indicatorCols);
  var satS2 = calculateSatisfaction_(dfS2, indicatorCols);
  var nResponden = isEmptyDf_(dfFiltered) ? 0 : dfFiltered.rows.length;

  // Satisfaction per atribut dan gap terhadap target.
  var attrSat = calculateAttributeSatisfaction_(dfFiltered, indicatorCols);
  var targetMd = filters.main_dealer;
  var targetLayer = filters.layer;
  if (!isEmptyDf_(dfFiltered)) {
    if ((!targetMd || targetMd === 'Semua') && cols.main_dealer) {
      var uniqMds = options_(dfFiltered, cols.main_dealer);
      if (uniqMds.length === 1) targetMd = uniqMds[0];
    }
    if ((!targetLayer || targetLayer === 'Semua') && cols.layer) {
      var uniqLayers = options_(dfFiltered, cols.layer);
      if (uniqLayers.length === 1) targetLayer = uniqLayers[0];
    }
  }
  var gaps = calculateTargetGap_(attrSat, ctx.metaDf, targetMd, targetLayer);

  // Periode sebelumnya.
  var availablePeriods = getAvailablePeriods_(dfAll, cols);
  var prevPeriod = null;
  if (filters.year && filters.semester) {
    prevPeriod = getPreviousPeriod_(filters.year, filters.semester, availablePeriods);
  }

  var diffChart = null;
  var chartLayout = 2;

  if (prevPeriod) {
    var prevYear = prevPeriod[0];
    var prevSem = prevPeriod[1];
    var dfPrev = applyFilters_(dfAll, cols, filters, prevYear, prevSem, true);
    var diffs = calculateSemesterDifference_(dfFiltered, dfPrev, indicatorCols);

    var curLabel = periodLabel_(filters.year, filters.semester);
    var prevLabel = periodLabel_(prevYear, prevSem);
    var subtitle = curLabel + ' − ' + prevLabel;

    diffChart = buildSemesterDifferenceChart_(diffs, subtitle, attrSat, ctx.indicatorNames);
    chartLayout = 3;
  }

  // Ranking dealer: mengikuti filter Kabupaten/Kota, tidak muncul jika Dealer tertentu dipilih.
  var dealerSelected = filters.dealer;
  var showDealerRanking = (dealerSelected === null || dealerSelected === '' || dealerSelected === 'Semua');

  var ranking = { show: false };
  if (showDealerRanking) {
    var dealerRankFilters = {};
    for (var fk in filters) if (Object.prototype.hasOwnProperty.call(filters, fk)) dealerRankFilters[fk] = filters[fk];
    dealerRankFilters.dealer = null;

    var dfDealerRank = applyFilters_(dfAll, cols, dealerRankFilters, null, null, false);
    ranking = buildDealerRanking_(dfDealerRank, cols, indicatorCols, unitKey, dealerRankFilters);
  }

  // Section 3: profil, penjelasan, demografi.
  var profileList = buildProfileList_(dfFiltered, cols, ctx.profileMetaDf, params.profile || 'P1');
  var selectedProfile = profileList.selected;
  var profileExplanation = buildProfileExplanation_(ctx.profileMetaDf, selectedProfile);
  var demographics = buildDemographicCharts_(dfFiltered, cols, selectedProfile, unitKey);
  var insight = buildOverallProfileInsight_(
    dfFiltered, demographics.dfProf, cols, selectedProfile, unitKey, ctx.profileMetaDf
  );

  return {
    unit: unitKey,
    unitLabel: ctx.config.unitLabel,
    dealerLabel: ctx.config.dealerLabel,
    filters: filters,
    filterOptions: state.options,
    section1: {
      map: buildMapData_(unitKey, dfAll, cols, indicatorCols),
      kpi: buildKpiCards_(satS1, satS2, nResponden),
      chartLayout: chartLayout,
      satisfactionChart: buildSatisfactionChart_(attrSat, ctx.indicatorNames),
      targetGapChart: buildTargetGapChart_(gaps, attrSat, ctx.indicatorNames),
      semesterDifferenceChart: diffChart,
      ranking: ranking
    },
    section3: {
      profileList: profileList,
      profileExplanation: profileExplanation,
      insight: insight,
      demographics: demographics.charts
    }
  };
}

function apiMatrix_(params) {
  var unitKey = params.unit || 'sales';
  var ctx = loadUnitContext_(unitKey);
  var state = buildFilterState_(ctx, params);

  var filters = state.filters;
  if (params.matrixMd) filters.matrixMainDealer = params.matrixMd;

  return {
    unit: unitKey,
    matrix: buildImportanceMatrix_(unitKey, filters)
  };
}

function apiHeatmap_(params) {
  var unitKey = params.unit || 'sales';
  return { unit: unitKey, heatmap: buildProfileHeatmap_(unitKey) };
}

function apiMapClick_(params) {
  var unitKey = params.unit || 'sales';
  var region = params.region || '';
  var ctx = loadUnitContext_(unitKey);

  var selection = resolveMapRegionFilter_(ctx.df, ctx.cols, region, {
    year: params.year || null,
    semesterLabel: params.semester || null
  });

  return { unit: unitKey, region: region, selection: selection };
}

function apiRegionPage_(params) {
  return {
    regionPage: buildRegionProfilePage_(
      params.h || 'H1',
      params.cluster || 'Semua',
      params.sort || 'Profile Wilayah'
    )
  };
}

// ============================================================
// FRAMEWORK (SECTION STATIS)
// ============================================================

/**
 * Isi halaman Framework dipindahkan apa adanya dari
 * render_framework_placeholder(): teks, ikon, dan urutannya sama.
 */
function apiFramework_() {
  var matrixSteps = [
    {
      no: '01', icon: 'fa-solid fa-chart-column', title: 'STEP 1<br>SATISFACTION SCORE<br>CALCULATION',
      items: [
        ['fa-solid fa-chart-column', '1. Hitung rata-rata score setiap atribut', 'A1–Axx, B1–Bxx, dan seterusnya.'],
        ['fa-solid fa-sitemap', '2. Kelompokkan atribut berdasarkan Moment of Truth (MOT)', 'Setiap atribut dikelompokkan ke dalam MOT yang sesuai.'],
        ['fa-solid fa-chart-line', '3. Hitung rata-rata score masing-masing MOT', 'Rata-rata atribut membentuk score setiap MOT.'],
        ['fa-solid fa-chart-pie', '4. Hitung Total Score', 'Total Score merupakan rata-rata seluruh MOT.']
      ],
      output: ['Score Total', 'Score MOT', 'Score Atribut']
    },
    {
      no: '02', icon: 'fa-solid fa-bullseye', title: 'STEP 2<br>CUSTOMER SATISFACTION<br>DRIVER MODELLING',
      items: [
        ['fa-solid fa-bullseye', 'Target', 'Total CSL Score.'],
        ['fa-solid fa-table-cells', 'Predictor', 'Seluruh atribut CSL.'],
        ['fa-solid fa-tree', 'Random Forest Regression', 'Model hubungan atribut dengan Total CSL Score.'],
        ['fa-solid fa-braille', 'SHAP Analysis', 'Mengukur kontribusi masing-masing atribut.'],
        ['fa-solid fa-magnifying-glass-chart', 'Hitung Mean Absolute SHAP Value', 'Besarnya pengaruh rata-rata setiap atribut.'],
        ['fa-solid fa-trophy', 'Ranking Satisfaction Driver', 'Urutan atribut berdasarkan pengaruhnya.']
      ],
      output: ['SHAP Importance', 'Satisfaction Rank']
    },
    {
      no: '03', icon: 'fa-solid fa-users', title: 'STEP 3<br>CUSTOMER IMPORTANCE<br>ANALYSIS',
      items: [
        ['fa-solid fa-users', 'Data', 'Transformasi rank dari Top 5 Importance Attributes: 5 = paling penting, 4 = rank kedua, 3 = rank ketiga, 2 = rank keempat, 1 = rank kelima, dan 0 = tidak dipilih.'],
        ['fa-solid fa-scale-balanced', 'Weighted Ranking Method', 'Memberikan bobot berdasarkan posisi atribut.'],
        ['fa-solid fa-chart-column', 'Weighting Score', 'Menghitung score hasil pembobotan.'],
        ['fa-solid fa-list-ol', 'Importance Rank', 'Mengurutkan atribut berdasarkan weighting score.']
      ],
      output: ['Importance Score', 'Importance Rank']
    },
    {
      no: '04', icon: 'fa-solid fa-sliders', title: 'STEP 4<br>PRIORITY IMPROVEMENT<br>MATRIX',
      items: [
        ['fa-solid fa-xmarks-lines', 'Input', 'X Axis = Importance Rank; Y Axis = Satisfaction Driver Rank.'],
        ['fa-solid fa-sliders', 'Hitung Median Importance Rank', 'Median menjadi garis pembagi vertikal.'],
        ['fa-solid fa-sliders', 'Hitung Median Satisfaction Rank', 'Median menjadi garis pembagi horizontal.'],
        ['fa-solid fa-table-cells-large', 'Pemetaan 4 Kuadran Matrix', 'Kuadran I Pertahankan, II Prioritas Utama, III Perbaikan Bertahap, dan IV Prioritas Rendah.']
      ],
      output: ['Matriks 4 Kuadran', 'Daftar Prioritas']
    },
    {
      no: '05', icon: 'fa-solid fa-cart-shopping', title: 'STEP 5<br>INTERACTIVE<br>DASHBOARD',
      items: [
        ['fa-solid fa-cart-shopping', 'Sales [H1]', 'Analisis kepuasan pembelian unit.'],
        ['fa-solid fa-screwdriver-wrench', 'Service [H2]', 'Analisis kepuasan layanan AHASS.'],
        ['fa-solid fa-gears', 'Spare Part [H3]', 'Analisis kepuasan suku cadang.'],
        ['fa-solid fa-users', 'TOTAL (ALL)', 'Ringkasan performa keseluruhan.'],
        ['fa-solid fa-store', 'MAIN DEALER', 'M2Z dan M3Z.'],
        ['fa-solid fa-layer-group', 'LAYER', 'Reguler H123, Reguler H23, Wing, dan Big Wing.'],
        ['fa-solid fa-location-dot', 'KARESIDENAN', 'Surabaya, Kediri, Madiun, dan wilayah lainnya.']
      ],
      output_label: 'OUTPUT DASHBOARD',
      output: ['Quadrant Matrix', 'Focus Item Table', 'Analysis Summary']
    },
    {
      no: '06', icon: 'fa-solid fa-bullseye', title: 'STEP 6<br>FOCUS ITEM<br>IDENTIFICATION',
      items: [
        ['fa-solid fa-bullseye', 'Ambil atribut pada Kuadran II', 'Priority Improvement.'],
        ['fa-solid fa-chart-line', 'Importance Tinggi × Satisfaction Rendah', 'Menentukan atribut yang paling perlu diperbaiki.'],
        ['fa-solid fa-clipboard-check', 'Generate Focus Item List', 'Menyusun daftar akhir fokus perbaikan.']
      ],
      output: ['Top Priority Attributes', 'Focus Improvement Area']
    }
  ];

  var profilingSteps = [
    {
      no: '01', icon: '☰', title: 'STEP 1<br>PERSIAPAN<br>DATA',
      items: [
        ['Kumpulkan indikator kepuasan', 'Seluruh atribut satisfaction (A1–H23, dst) dijadikan variabel input clustering.'],
        ['Bersihkan data kosong', 'Nilai kosong/spasi diubah menjadi missing value agar tidak mengganggu model.'],
        ['Cek kelengkapan data', 'Menghitung jumlah & persentase data hilang tiap indikator sebagai kontrol kualitas.']
      ],
      output: ['Dataset indikator siap dianalisis']
    },
    {
      no: '02', icon: '⌕', title: 'STEP 2<br>EKSPLORASI<br>DATA (EDA)',
      items: [
        ['Lihat sebaran jawaban', 'Distribusi tiap indikator diperiksa untuk memahami pola respon pelanggan.'],
        ['Cek hubungan antar indikator', 'Correlation matrix dipakai agar tidak ada indikator yang terlalu tumpang tindih.']
      ],
      output: ['Pola distribusi & korelasi indikator']
    },
    {
      no: '03', icon: '⚖', title: 'STEP 3<br>PENENTUAN JUMLAH<br>PROFIL (MODEL SELECTION)',
      items: [
        ['Coba beberapa jumlah kelompok', 'Gaussian Mixture Model (GMM) dijalankan untuk k = 2 sampai 8 kelompok pelanggan.'],
        ['Bandingkan 3 ukuran kualitas', 'AIC & BIC (semakin rendah semakin baik) serta Silhouette Score (semakin tinggi semakin baik).'],
        ['Pilih jumlah terbaik', 'Kombinasi ketiga ukuran menunjukkan 5 kelompok sebagai jumlah Customer Profile paling optimal.']
      ],
      output: ['Jumlah profil optimal (k = 5)']
    },
    {
      no: '04', icon: '◈', title: 'STEP 4<br>PEMBENTUKAN PROFIL<br>(GMM / LATENT PROFILE)',
      items: [
        ['Latih model final', 'GMM dilatih dengan 5 kelompok dan covariance type "full" agar tiap kelompok punya pola sebarannya sendiri.'],
        ['Beri label profil', 'Setiap pelanggan diberi label Profile 1–5 sesuai kelompok yang paling mungkin ia miliki.'],
        ['Hitung tingkat keyakinan', 'Posterior probability & Confidence Score menunjukkan seberapa yakin model menempatkan pelanggan pada profil tersebut.']
      ],
      output: ['Label Customer Profile 1–5', 'Confidence score']
    },
    {
      no: '05', icon: '▦', title: 'STEP 5<br>INTERPRETASI<br>KARAKTERISTIK PROFIL',
      items: [
        ['Hitung profile gap', 'Rata-rata tiap indikator per profil dibandingkan dengan rata-rata seluruh pelanggan.'],
        ['Visualisasi heatmap', 'Merah menunjukkan indikator di bawah rata-rata, hijau menunjukkan di atas rata-rata.'],
        ['Lengkapi dengan demografi', 'Gender, usia, SES, tipe motor, NPS, dan retention dianalisis untuk melengkapi karakter tiap profil.']
      ],
      output: ['Heatmap profile gap', 'Insight karakteristik tiap profil']
    },
    {
      no: '06', icon: '⌖', title: 'STEP 6<br>PEMETAAN WILAYAH<br>& VALIDASI',
      items: [
        ['Hitung proporsi profil per wilayah', 'Persentase Profile 1–5 dihitung untuk tiap kabupaten/kota.'],
        ['Bandingkan dengan cluster wilayah', 'Dicocokkan dengan Cluster Karakteristik Wilayah (BPS) dan Kelompok Budaya.'],
        ['Ukur kemiripan distribusi', 'Jensen–Shannon Similarity dipakai untuk melihat seberapa konsisten profil dalam satu cluster/budaya.']
      ],
      output: ['Distribusi profil per wilayah', 'Tingkat kemiripan cluster/budaya']
    }
  ];

  var insights = [
    {
      icon: '↗', color: RED,
      title: 'Bandingkan Performa Antar Semester',
      desc: 'Chart "Selisih Satisfaction Antar Semester" dan KPI Improvement pada Section 1 menunjukkan atribut mana yang naik/turun dibanding semester sebelumnya, sehingga tren performa terlihat jelas.'
    },
    {
      icon: '⚑', color: ORANGE,
      title: 'Temukan Wilayah / Dealer yang Butuh Perhatian',
      desc: 'Peta Satisfaction diwarnai merah–kuning–hijau berdasarkan nilai kepuasan tiap kabupaten/kota. Klik wilayahnya (termasuk inset NTT) atau pakai filter Dealer/AHASS/Part Shop untuk fokus ke titik terlemah.'
    },
    {
      icon: '◉', color: YELLOW,
      title: 'Prioritaskan Atribut yang Perlu Diperbaiki',
      desc: 'Kuadran II "Prioritas Utama" pada Matrix Satisfaction x Importance (Section 2) menunjukkan atribut dengan importance tinggi tapi satisfaction rendah.'
    },
    {
      icon: '⌦', color: GREEN,
      title: 'Pantau Capaian terhadap Target',
      desc: 'Chart "Capaian terhadap Target Atribut" membandingkan nilai satisfaction aktual dengan target Main Dealer/Layer, sehingga atribut yang belum mencapai standar langsung terlihat.'
    },
    {
      icon: '◐', color: BLUE_OUTLINE,
      title: 'Kenali Karakteristik Dominan Tiap Wilayah',
      desc: 'Heatmap Customer Profile (Section 3) dan halaman Profil Wilayah menunjukkan tipe pelanggan dominan pada tiap kabupaten/kota, dealer, dan karesidenan.'
    },
    {
      icon: '◔', color: '#00897B',
      title: 'Ukur Loyalitas Pelanggan (NPS & Retention)',
      desc: 'Gauge NPS Unit/Dealer/AHASS/Part Shop serta chart Retention menunjukkan seberapa besar pelanggan yang loyal dan berpotensi merekomendasikan dealer ke orang lain.'
    },
    {
      icon: '❖', color: '#8E24AA',
      title: 'Sesuaikan Strategi dengan Budaya & Karakter Wilayah',
      desc: 'Halaman Profil Wilayah membandingkan distribusi Customer Profile dengan Cluster Karakteristik Wilayah (BPS) dan Kelompok Budaya, lengkap dengan tingkat kemiripan antar wilayah dalam satu cluster.'
    },
    {
      icon: '◆', color: '#C9A400',
      title: 'Pahami Profil Demografis Pelanggan',
      desc: 'Chart gender, usia, SES, tipe motor, dan metode pembayaran pada Section 3 membantu memetakan segmen pasar tiap dealer, wilayah, maupun customer profile.'
    }
  ];

  return {
    framework: {
      matrixSection: {
        title: 'ALUR PERHITUNGAN MATRIX SATISFACTION x IMPORTANCE',
        subtitle: 'Enam tahap pengolahan data survei kepuasan menjadi Priority Improvement Matrix, ' +
          'mulai dari perhitungan skor sampai pemetaan atribut ke dalam empat kuadran prioritas.',
        steps: matrixSteps
      },
      profilingSection: {
        title: 'ALUR CUSTOMER PROFILING (CLUSTERING GMM)',
        subtitleHtml: 'Pengelompokan pelanggan menjadi 5 Customer Profile menggunakan ' +
          '<b>Gaussian Mixture Model (GMM)</b>, yaitu metode clustering yang mengelompokkan pelanggan ' +
          'berdasarkan kemiripan pola jawaban survei. Selanjutnya, setiap pelanggan ditempatkan pada ' +
          'profil yang paling sesuai dengan karakteristiknya beserta tingkat keyakinan hasil ' +
          'pengelompokannya.',
        steps: profilingSteps
      },
      insightSection: {
        title: 'APA YANG BISA DIDAPATKAN DARI DASHBOARD INI?',
        items: insights
      }
    }
  };
}

// ============================================================
// UTILITAS PENGUJIAN (jalankan manual dari editor Apps Script)
// ============================================================

function testUnitPage() {
  var result = apiUnitPage_({ unit: 'sales', semester: 'Semester 1', profile: 'P1' });
  Logger.log('KPI: ' + JSON.stringify(result.section1.kpi));
  Logger.log('Jumlah atribut: ' + result.section1.satisfactionChart.items.length);
  Logger.log('Wilayah pada peta: ' + result.section1.map.regions.length);
}

function testRegionPage() {
  var result = apiRegionPage_({ h: 'H1' });
  Logger.log(JSON.stringify(result.regionPage.kpi));
}

function testMatrix() {
  var result = apiMatrix_({ unit: 'sales', semester: 'Semester 1' });
  Logger.log('Titik matriks: ' + (result.matrix.points ? result.matrix.points.length : 0));
}
