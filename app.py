"""Dashboard Monitoring Beban Trafo 20kV - ULP LABUAN"""
import pandas as pd
import numpy as np
from flask import Flask, request, jsonify
import os
import json

app = Flask(__name__)

# Load data sekali di startup
CSV_PATH = os.path.join(os.path.dirname(__file__), 'pengukuran_beban.csv')
df = pd.read_csv(CSV_PATH)
for col in ['KAPASITAS', 'beban_r', 'beban_s', 'beban_t', 'arus_rata2', 
            'unbalance_percent', 'persen_fasa_max', 'persen_daya_trafo']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Agregat per gardu (ambil nilai maksimum)
gardu_agg = df.groupby(['GARDU', 'UNIT_LAYANAN', 'PENYULANG', 'KAPASITAS']).agg(
    max_beban=('persen_daya_trafo', 'max'),
    avg_beban=('persen_daya_trafo', 'mean'),
    max_unbalance=('unbalance_percent', 'max'),
    max_r=('beban_r', 'max'),
    max_s=('beban_s', 'max'),
    max_t=('beban_t', 'max'),
    max_arus=('arus_rata2', 'max'),
    n_ukur=('persen_daya_trafo', 'count'),
    status=('status_beban_trafo', lambda x: x.mode().iloc[0] if not x.mode().empty else ''),
    kondisi=('kondisi_fasa_max', lambda x: x.mode().iloc[0] if not x.mode().empty else ''),
    overload_count=('status_beban_trafo', lambda x: (x == 'Overload').sum()),
).reset_index()

# Flag anomali
gardu_agg['is_anomali'] = False
for idx, row in gardu_agg.iterrows():
    gdf = df[df['GARDU'] == row['GARDU']]
    has_zero = (gdf['arus_rata2'] == 0).any()
    has_nonzero = (gdf['arus_rata2'] > 0).any()
    beban_spread = gdf['persen_daya_trafo'].max() - gdf['persen_daya_trafo'].min()
    if (has_zero and has_nonzero) or beban_spread > 50 or row['max_beban'] > 150:
        gardu_agg.at[idx, 'is_anomali'] = True

print(f"Loaded {len(df)} measurements, {len(gardu_agg)} unique gardu")

# ============================================================
# HTML DASHBOARD (single page, no Jinja2)
# ============================================================
HTML = r'''<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard Monitoring Beban Trafo 20kV - ULP LABUAN</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f1923; color: #e0e0e0; min-height: 100vh; }
.header { background: linear-gradient(135deg, #1a2a3a, #0d1b2a); padding: 16px 24px; border-bottom: 2px solid #1e88e5; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.header h1 { font-size: clamp(16px, 2.5vw, 22px); color: #64b5f6; }
.header .subtitle { font-size: 11px; color: #78909c; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; padding: 16px 24px; }
.card { background: #1a2a3a; border-radius: 10px; padding: 16px; border-left: 4px solid #1e88e5; }
.card.critical { border-left-color: #ef5350; }
.card.warning { border-left-color: #ff9800; }
.card.success { border-left-color: #4caf50; }
.card.info { border-left-color: #2196f3; }
.card .label { font-size: 11px; color: #78909c; text-transform: uppercase; letter-spacing: 1px; }
.card .value { font-size: clamp(22px, 3vw, 32px); font-weight: bold; color: #fff; margin-top: 4px; }
.card .pct { font-size: 11px; color: #78909c; margin-top: 2px; }
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 16px; padding: 0 24px 16px; }
.chart-box { background: #1a2a3a; border-radius: 10px; padding: 16px; }
.chart-box h3 { font-size: 13px; color: #64b5f6; margin-bottom: 12px; }
.chart-box canvas { max-height: 280px; }
.filters { padding: 8px 24px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.filters input, .filters select { background: #1a2a3a; border: 1px solid #37474f; color: #e0e0e0; padding: 8px 12px; border-radius: 6px; font-size: 12px; }
.filters input { width: 200px; }
.filters select { width: 150px; }
.table-wrap { padding: 0 24px 24px; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { background: #1e88e5; color: #fff; padding: 10px 8px; text-align: center; position: sticky; top: 0; cursor: pointer; user-select: none; }
th:hover { background: #1565c0; }
td { padding: 8px; text-align: center; border-bottom: 1px solid #263238; }
tr:hover { background: rgba(30,136,229,0.1); }
tr.overload { background: rgba(239,83,80,0.15); }
tr.overload:hover { background: rgba(239,83,80,0.25); }
tr.anomali { border-left: 3px solid #ff9800; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold; }
.badge-overload { background: #ef5350; color: #fff; }
.badge-underload { background: #78909c; color: #fff; }
.badge-normal { background: #4caf50; color: #fff; }
.badge-balance { background: #2196f3; color: #fff; }
.badge-unbalance { background: #ff9800; color: #fff; }
.clickable { cursor: pointer; color: #64b5f6; text-decoration: underline; }
.modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; overflow-y: auto; }
.modal-content { background: #1a2a3a; margin: 40px auto; padding: 24px; border-radius: 12px; max-width: 700px; border: 1px solid #37474f; }
.modal h3 { color: #64b5f6; margin-bottom: 16px; }
.modal table { font-size: 11px; }
.modal .close { float: right; color: #78909c; font-size: 24px; cursor: pointer; }
.modal .close:hover { color: #fff; }
.loading { text-align: center; padding: 40px; color: #78909c; }
.footer { text-align: center; padding: 8px; color: #546e7a; font-size: 10px; border-top: 1px solid #263238; margin: 0 24px; }
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>⚡ Dashboard Monitoring Beban Trafo 20kV</h1>
    <div class="subtitle">ULP LABUAN, UP3 Banten Selatan</div>
  </div>
  <div class="subtitle" id="lastUpdate">Memuat data...</div>
</div>

<div class="cards" id="cards"></div>

<div class="charts">
  <div class="chart-box"><h3>📊 Distribusi Status Beban</h3><canvas id="chartStatus"></canvas></div>
  <div class="chart-box"><h3>📊 Top 10 Penyulang - Gardu Overload</h3><canvas id="chartPenyulang"></canvas></div>
  <div class="chart-box"><h3>📊 Top 10 Gardu Overload Tertinggi</h3><canvas id="chartTop"></canvas></div>
</div>

<div class="filters">
  <input type="text" id="search" placeholder="🔍 Cari gardu..." oninput="renderTable()">
  <select id="filterStatus" onchange="renderTable()">
    <option value="">Semua Status</option>
    <option value="Overload">Overload</option>
    <option value="Normal">Normal</option>
    <option value="Underload">Underload</option>
  </select>
  <select id="filterBalance" onchange="renderTable()">
    <option value="">Semua Keseimbangan</option>
    <option value="Tidak Seimbang">Tidak Seimbang</option>
    <option value="Kurang Seimbang">Kurang Seimbang</option>
    <option value="Seimbang">Seimbang</option>
  </select>
  <select id="filterPenyulang" onchange="renderTable()">
    <option value="">Semua Penyulang</option>
  </select>
  <label style="font-size:12px;margin-left:8px;">
    <input type="checkbox" id="filterAnomali" onchange="renderTable()"> Hanya Anomali
  </label>
  <span style="margin-left:auto;font-size:12px;color:#78909c;" id="resultCount"></span>
</div>

<div class="table-wrap">
  <table id="dataTable">
    <thead>
      <tr>
        <th onclick="sortTable('GARDU')">GARDU ↕</th>
        <th onclick="sortTable('PENYULANG')">PENYULANG ↕</th>
        <th onclick="sortTable('KAPASITAS')">KAP ↕</th>
        <th onclick="sortTable('max_beban')">BEBAN MAX ↕</th>
        <th onclick="sortTable('avg_beban')">RATA2 ↕</th>
        <th onclick="sortTable('max_unbalance')">UNBALANCE ↕</th>
        <th>FASA R/S/T</th>
        <th>STATUS</th>
        <th>KESEIMBANGAN</th>
        <th>N UKUR</th>
        <th>DETAIL</th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>
</div>

<div class="footer">Dashboard Monitoring Beban Trafo &copy; 2026 ULP LABUAN | Data: pengukuran_beban.csv</div>

<!-- Detail Modal -->
<div class="modal" id="detailModal">
  <div class="modal-content">
    <span class="close" onclick="document.getElementById('detailModal').style.display='none'">&times;</span>
    <h3 id="modalTitle"></h3>
    <div id="modalBody"></div>
  </div>
</div>

<script>
let allData = [];
let filteredData = [];
let sortCol = 'max_beban';
let sortDir = -1; // descending

async function init() {
  const resp = await fetch('/api/summary');
  allData = await resp.json();
  filteredData = [...allData];
  
  renderCards();
  renderCharts();
  populateFilters();
  renderTable();
  document.getElementById('lastUpdate').textContent = 'Data: ' + allData.length + ' gardu | ' + new Date().toLocaleDateString('id-ID');
}

function renderCards() {
  const total = allData.length;
  const overload = allData.filter(d => d.status === 'Overload').length;
  const underload = allData.filter(d => d.status === 'Underload' && d.max_beban < 20).length;
  const unbalance = allData.filter(d => d.max_unbalance > 25).length;
  const anomali = allData.filter(d => d.is_anomali).length;
  
  document.getElementById('cards').innerHTML = `
    <div class="card info">
      <div class="label">Total Gardu</div>
      <div class="value">${total}</div>
      <div class="pct">10 Penyulang</div>
    </div>
    <div class="card critical">
      <div class="label">Overload</div>
      <div class="value">${overload}</div>
      <div class="pct">${(overload/total*100).toFixed(1)}%</div>
    </div>
    <div class="card warning">
      <div class="label">Underload &lt;20%</div>
      <div class="value">${underload}</div>
      <div class="pct">${(underload/total*100).toFixed(1)}%</div>
    </div>
    <div class="card warning">
      <div class="label">Tidak Seimbang</div>
      <div class="value">${unbalance}</div>
      <div class="pct">${(unbalance/total*100).toFixed(1)}%</div>
    </div>
    <div class="card critical">
      <div class="label">⚠ Anomali</div>
      <div class="value">${anomali}</div>
      <div class="pct">${(anomali/total*100).toFixed(1)}%</div>
    </div>
  `;
}

function renderCharts() {
  // Status pie
  const statusCounts = {Overload:0, Normal:0, Underload:0};
  allData.forEach(d => { if (statusCounts[d.status] !== undefined) statusCounts[d.status]++; });
  
  new Chart(document.getElementById('chartStatus'), {
    type: 'doughnut',
    data: {
      labels: ['Overload', 'Normal', 'Underload'],
      datasets: [{
        data: [statusCounts.Overload, statusCounts.Normal, statusCounts.Underload],
        backgroundColor: ['#ef5350', '#4caf50', '#78909c'],
        borderColor: '#0f1923',
        borderWidth: 2
      }]
    },
    options: { 
      responsive: true, 
      plugins: { legend: { position: 'bottom', labels: { color: '#b0bec5', font: { size: 11 } } } }
    }
  });

  // Per penyulang - overload count
  const penyulangMap = {};
  allData.forEach(d => { 
    if (!penyulangMap[d.PENYULANG]) penyulangMap[d.PENYULANG] = {total:0, overload:0};
    penyulangMap[d.PENYULANG].total++;
    if (d.status === 'Overload') penyulangMap[d.PENYULANG].overload++;
  });
  const sortedPen = Object.entries(penyulangMap)
    .sort((a,b) => b[1].overload - a[1].overload)
    .slice(0, 10);
  
  new Chart(document.getElementById('chartPenyulang'), {
    type: 'bar',
    data: {
      labels: sortedPen.map(p => p[0]),
      datasets: [{
        label: 'Overload',
        data: sortedPen.map(p => p[1].overload),
        backgroundColor: '#ef5350',
        borderRadius: 4
      }, {
        label: 'Total Gardu',
        data: sortedPen.map(p => p[1].total),
        backgroundColor: '#37474f',
        borderRadius: 4
      }]
    },
    options: { 
      indexAxis: 'y',
      responsive: true, 
      scales: { x: { ticks: { color: '#78909c' }, grid: { color: '#263238' } }, y: { ticks: { color: '#b0bec5', font: {size:10} }, grid: { display: false } } },
      plugins: { legend: { labels: { color: '#b0bec5', font: {size:10} } } }
    }
  });

  // Top 10 overload
  const top10 = allData.filter(d => d.status === 'Overload').sort((a,b) => b.max_beban - a.max_beban).slice(0, 10);
  new Chart(document.getElementById('chartTop'), {
    type: 'bar',
    data: {
      labels: top10.map(d => d.GARDU),
      datasets: [{
        label: 'Beban Max %',
        data: top10.map(d => d.max_beban),
        backgroundColor: top10.map(d => d.max_beban > 130 ? '#b71c1c' : d.max_beban > 100 ? '#ef5350' : '#ff9800'),
        borderRadius: 6
      }]
    },
    options: { 
      responsive: true,
      scales: { 
        y: { beginAtZero: true, ticks: { color: '#78909c', callback: v => v+'%' }, grid: { color: '#263238' } }, 
        x: { ticks: { color: '#b0bec5', font: {size:10} }, grid: { display: false } } 
      },
      plugins: { 
        legend: { display: false },
        annotation: { annotations: { line80: { type: 'line', yMin: 80, yMax: 80, borderColor: '#ff9800', borderWidth: 1, borderDash: [5,5], label: { display: true, content: '80%', position: 'end' } } } }
      }
    }
  });
}

function populateFilters() {
  const penyulangs = [...new Set(allData.map(d => d.PENYULANG))].sort();
  const sel = document.getElementById('filterPenyulang');
  penyulangs.forEach(p => { const opt = document.createElement('option'); opt.value = p; opt.textContent = p; sel.appendChild(opt); });
}

function applyFilters() {
  let data = [...allData];
  const search = document.getElementById('search').value.toLowerCase();
  const status = document.getElementById('filterStatus').value;
  const balance = document.getElementById('filterBalance').value;
  const penyulang = document.getElementById('filterPenyulang').value;
  const anomali = document.getElementById('filterAnomali').checked;
  
  if (search) data = data.filter(d => d.GARDU.toLowerCase().includes(search) || d.PENYULANG.toLowerCase().includes(search));
  if (status) data = data.filter(d => d.status === status);
  if (balance) data = data.filter(d => d.kondisi === balance);
  if (penyulang) data = data.filter(d => d.PENYULANG === penyulang);
  if (anomali) data = data.filter(d => d.is_anomali);
  
  data.sort((a,b) => {
    let va = a[sortCol], vb = b[sortCol];
    if (typeof va === 'string') { va = va.toLowerCase(); vb = vb.toLowerCase(); return sortDir * va.localeCompare(vb); }
    return sortDir * (va - vb);
  });
  
  return data;
}

function renderTable() {
  filteredData = applyFilters();
  document.getElementById('resultCount').textContent = filteredData.length + ' gardu';
  
  const tbody = document.querySelector('#dataTable tbody');
  tbody.innerHTML = filteredData.map(d => {
    const rowClass = (d.status === 'Overload' ? ' overload' : '') + (d.is_anomali ? ' anomali' : '');
    const statusBadge = d.status === 'Overload' ? 'badge-overload' : d.status === 'Underload' ? 'badge-underload' : 'badge-normal';
    const balBadge = d.kondisi.includes('Tidak') ? 'badge-unbalance' : d.kondisi.includes('Kurang') ? 'badge-balance' : 'badge-normal';
    const anomaliFlag = d.is_anomali ? ' ⚠' : '';
    return `<tr class="${rowClass}">
      <td>${d.GARDU}${anomaliFlag}</td>
      <td>${d.PENYULANG}</td>
      <td>${d.KAPASITAS} kVA</td>
      <td style="font-weight:bold;color:${d.max_beban > 100 ? '#ef5350' : d.max_beban > 80 ? '#ff9800' : '#e0e0e0'}">${d.max_beban.toFixed(0)}%</td>
      <td>${d.avg_beban.toFixed(0)}%</td>
      <td style="color:${d.max_unbalance > 25 ? '#ff9800' : '#e0e0e0'}">${d.max_unbalance.toFixed(0)}%</td>
      <td style="font-size:10px">R:${d.max_r.toFixed(0)} S:${d.max_s.toFixed(0)} T:${d.max_t.toFixed(0)}</td>
      <td><span class="badge ${statusBadge}">${d.status}</span></td>
      <td><span class="badge ${balBadge}">${d.kondisi}</span></td>
      <td>${d.n_ukur}x</td>
      <td><span class="clickable" onclick="showDetail('${d.GARDU}')">📋</span></td>
    </tr>`;
  }).join('');
}

function sortTable(col) {
  if (sortCol === col) sortDir *= -1; else { sortCol = col; sortDir = -1; }
  document.querySelectorAll('th').forEach(th => th.textContent = th.textContent.replace(' ↑','').replace(' ↓',''));
  renderTable();
}

async function showDetail(gardu) {
  const resp = await fetch('/api/detail?gardu=' + gardu);
  const data = await resp.json();
  document.getElementById('modalTitle').textContent = '📋 Riwayat Pengukuran: ' + gardu + ' (' + data.penyulang + ', ' + data.kapasitas + ' kVA)';
  let html = '<table><thead><tr><th>TANGGAL</th><th>WAKTU</th><th>R (A)</th><th>S (A)</th><th>T (A)</th><th>ARUS RATA</th><th>BEBAN %</th><th>UNBAL %</th><th>STATUS</th></tr></thead><tbody>';
  const lastIdx = data.measurements.length - 1;
  data.measurements.forEach((m, i) => {
    const isLatest = (i === lastIdx);
    const rowStyle = isLatest ? ' style="background:#2d1f00;border-left:3px solid #ff9800;font-weight:bold"' : '';
    const flag = m.arus_rata2 === 0 ? ' style="color:#ff9800" title="0A - anomali"' : '';
    html += `<tr${rowStyle}${flag}>
      <td>${m.tanggal}</td><td>${m.waktu}</td>
      <td>${m.beban_r}</td><td>${m.beban_s}</td><td>${m.beban_t}</td>
      <td>${m.arus_rata2}</td><td>${m.beban_pct}%</td><td>${m.unbalance}%</td>
      <td>${m.status}${isLatest ? ' <span style="background:#ff9800;color:#000;padding:1px 6px;border-radius:10px;font-size:9px;font-weight:bold">TERBARU</span>' : ''}</td>
    </tr>`;
  });
  html += '</tbody></table>';
  if (data.has_anomaly) html += '<p style="color:#ff9800;margin-top:12px;">⚠ Gardu ini terdeteksi anomali pengukuran. Verifikasi data!</p>';
  document.getElementById('modalBody').innerHTML = html;
  document.getElementById('detailModal').style.display = 'block';
}

window.onclick = function(e) { if (e.target.className === 'modal') e.target.style.display = 'none'; }

init();
</script>
</body>
</html>'''

@app.route('/')
def index():
    return HTML

@app.route('/api/summary')
def api_summary():
    """Return all gardu aggregated data as JSON"""
    records = []
    for _, row in gardu_agg.iterrows():
        records.append({
            'GARDU': row['GARDU'],
            'UNIT_LAYANAN': row['UNIT_LAYANAN'],
            'PENYULANG': row['PENYULANG'],
            'KAPASITAS': int(row['KAPASITAS']),
            'max_beban': round(row['max_beban'], 1),
            'avg_beban': round(row['avg_beban'], 1),
            'max_unbalance': round(row['max_unbalance'], 1),
            'max_r': round(row['max_r'], 1),
            'max_s': round(row['max_s'], 1),
            'max_t': round(row['max_t'], 1),
            'max_arus': round(row['max_arus'], 1),
            'n_ukur': int(row['n_ukur']),
            'status': str(row['status']).strip(),
            'kondisi': str(row['kondisi']).strip(),
            'is_anomali': bool(row['is_anomali']),
        })
    return jsonify(records)

@app.route('/api/detail')
def api_detail():
    """Return measurement history for a specific gardu"""
    gardu = request.args.get('gardu', '')
    gdf = df[df['GARDU'] == gardu].sort_values('tanggal_ukur')
    
    if len(gdf) == 0:
        return jsonify({'error': 'Gardu not found'}), 404
    
    row = gardu_agg[gardu_agg['GARDU'] == gardu].iloc[0]
    measurements = []
    for _, r in gdf.iterrows():
        tgl_str = str(r['tanggal_ukur'])[:16] if pd.notna(r['tanggal_ukur']) else '?'
        measurements.append({
            'tanggal': tgl_str,
            'waktu': str(r['waktu_ukur']),
            'beban_r': round(r['beban_r'], 1),
            'beban_s': round(r['beban_s'], 1),
            'beban_t': round(r['beban_t'], 1),
            'arus_rata2': round(r['arus_rata2'], 1),
            'beban_pct': round(r['persen_daya_trafo'], 1),
            'unbalance': round(r['unbalance_percent'], 1),
            'status': str(r['status_beban_trafo']).strip(),
        })
    
    return jsonify({
        'gardu': gardu,
        'penyulang': row['PENYULANG'],
        'kapasitas': int(row['KAPASITAS']),
        'has_anomaly': bool(row['is_anomali']),
        'measurements': measurements,
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)
