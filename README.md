# Dashboard Monitoring Beban Trafo 20kV — ULP LABUAN

Monitoring beban trafo distribusi 20kV: overload, underload, keseimbangan fasa, dan deteksi anomali pengukuran.

## 2 Cara Pakai

### A. Statis (cPanel / shared hosting / GitHub Pages) — PALING GAMPANG
Cukup upload **`index.html`** + **`pengukuran_beban.csv`** ke `public_html`. Tidak perlu Python/server.
Buka `https://domainmu.com/index.html`. Baca CSV langsung di browser (PapaParse + Chart.js via CDN).

### B. Flask (PythonAnywhere / Railway) — kalau butuh backend
```bash
pip install -r requirements.txt
python app.py   # buka http://localhost:5002
```

## Update Data
Ganti isi `pengukuran_beban.csv` (format kolom sama). Statis: refresh browser. Flask: reload app.

## Kolom CSV
`UNIT_LAYANAN, PENYULANG, GARDU, KAPASITAS, tanggal_ukur, waktu_ukur, beban_r, beban_s, beban_t, arus_rata2, unbalance_percent, persen_fasa_max, kondisi_fasa_max, persen_daya_trafo, status_beban_trafo`
