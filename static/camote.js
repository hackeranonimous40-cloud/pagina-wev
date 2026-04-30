const API_URL = 'https://apiparagit-3yxs.onrender.com/precios';
const GITHUB_URL = 'https://raw.githubusercontent.com/yeifer125/iadatos/main/historial2025.json';
const PROXY_URL = 'https://api.allorigins.win/raw?url=';
let allData = { api: [], github: [] };
let priceChart;

function log(msg) { console.log('[Camote]', msg); }

function parseDate(dateStr) {
  if (!dateStr) return null;
  if (dateStr.includes('/')) {
    const parts = dateStr.split('/');
    if (parts.length === 3) {
      const d = new Date(parseInt(parts[2]), parseInt(parts[1]) - 1, parseInt(parts[0]));
      return isNaN(d.getTime()) ? null : d;
    }
  }
  const d = new Date(dateStr);
  return isNaN(d.getTime()) ? null : d;
}

function getMonthName(num) {
  const m = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"};
  return m[num] || '';
}

async function loadAllData() {
  try {
    log('Cargando...');
    document.getElementById('plantingTableBody').innerHTML = '<tr><td colspan="4" class="loading"><div class="spinner"></div>Cargando...</td></tr>';
    
    let apiData = [], githubData = [];
    
    // API
    try {
      const r = await fetch(API_URL);
      if (r.ok) apiData = await r.json();
    } catch(e) { log('API falló: '+e.message); }
    
    // GitHub
    try {
      const r = await fetch(GITHUB_URL);
      if (r.ok) githubData = await r.json();
    } catch(e) { log('GitHub falló: '+e.message); }
    
    allData = { api: apiData, github: githubData };
    log(`Datos: API=${apiData.length}, GitHub=${githubData.length}`);
    
    if (apiData.length + githubData.length === 0) {
      document.getElementById('plantingTableBody').innerHTML = '<tr><td colspan="4" style="color:#ef4444">Sin datos</td></tr>';
      return;
    }
    
    processData();
  } catch(e) {
    log('ERROR: '+e.message);
    document.getElementById('plantingTableBody').innerHTML = '<tr><td colspan="4" style="color:#ef4444">Error</td></tr>';
  }
}

function processData() {
  const apiCamote = allData.api.filter(i => i.producto?.toLowerCase().includes('camote'));
  const githubCamote = allData.github.filter(i => i.producto?.toLowerCase().includes('camote'));
  
  log(`Camote: API=${apiCamote.length}, GitHub=${githubCamote.length}`);
  
  // Fecha más reciente
  let latest = null;
  for (const i of apiCamote) {
    const d = parseDate(i.fecha);
    if (d && (!latest || d > latest)) latest = d;
  }
  
  // Precios de hoy
  const today = latest ? apiCamote.filter(i => {
    const d = parseDate(i.fecha);
    return d && d.getTime() === latest.getTime();
  }) : [];
  
  // Tabla histórica
  const monthly = {};
  for (const i of [...apiCamote, ...githubCamote]) {
    if (!i.fecha || !i.promedio) continue;
    const d = parseDate(i.fecha);
    if (!d) continue;
    const k = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
    const p = parseFloat(i.promedio);
    if (!isNaN(p)) {
      if (!monthly[k]) monthly[k] = [];
      monthly[k].push(p);
    }
  }
  
  const avg = {};
  for (const [k, v] of Object.entries(monthly)) {
    avg[k] = v.reduce((a,b)=>a+b,0) / v.length;
  }
  
  const allAvg = Object.values(avg);
  const overall = allAvg.length ? allAvg.reduce((a,b)=>a+b,0)/allAvg.length : 0;
  
  const table = Object.entries(avg).sort((a,b)=>new Date(a[0])-new Date(b[0])).map(([k, p]) => {
    const [y, m] = k.split('-').map(Number);
    const plant = new Date(y, m-4, 1);
    return {
      mes_cosecha: getMonthName(m),
      mes_plantar: getMonthName(plant.getMonth()+1),
      year: y,
      plantar_year: plant.getFullYear(),
      precio: Math.round(p),
      recomendacion: p > overall*1.1 ? 'OPTIMO' : p > overall ? 'BUENO' : 'MENOR'
    };
  });
  
  updateUI(avg, table, today);
}

function updateUI(monthly, table, today) {
  document.getElementById('lastUpdate').textContent = new Date().toLocaleString('es-CR');
  document.getElementById('dataCount').textContent = `${Object.keys(monthly).length} meses`;
  document.getElementById('statMonths').textContent = Object.keys(monthly).length;
  
  const prices = Object.values(monthly);
  const a = prices.length ? Math.round(prices.reduce((x,y)=>x+y,0)/prices.length) : 0;
  const b = prices.length ? Math.round(Math.max(...prices)) : 0;
  document.getElementById('statAvg').textContent = '₡'+a;
  document.getElementById('statBest').textContent = '₡'+b;
  document.getElementById('statRecords').textContent = table.length;
  
  // Tabla
  const tbody = document.getElementById('plantingTableBody');
  if (table.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4">Sin datos</td></tr>';
  } else {
    tbody.innerHTML = table.map(r => {
      const cls = r.recomendacion==='OPTIMO' ? 'optimo' : r.recomendacion==='BUENO' ? 'bueno' : '';
      const badge = r.recomendacion==='OPTIMO' ? 'badge-optimo' : r.recomendacion==='BUENO' ? 'badge-bueno' : 'badge-normal';
      return `<tr class="${cls}"><td>${r.mes_cosecha} ${r.year}</td><td>${r.mes_plantar} ${r.plantar_year}</td><td class="precio">₡${r.precio.toLocaleString()}</td><td><span class="badge ${badge}">${r.recomendacion}</span></td></tr>`;
    }).join('');
  }
  
  // Precio hoy
  updateTodayPrices(today);
  
  // Chart
  updateChart(Object.entries(monthly).sort((a,b)=>new Date(a[0])-new Date(b[0])));
}

function updateTodayPrices(today) {
  const c = document.getElementById('todayPrices');
  if (today.length > 0) {
    const i = today[0];
    document.getElementById('todayBadge').textContent = i.fecha || 'Reciente';
    c.innerHTML = `<div style="margin-bottom:15px;font-weight:600">${i.producto}</div><div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;"><div style="background:#0f172a;padding:12px;border-radius:10px;"><div style="font-size:0.7rem;color:#94a3b8">MÍNIMO</div><div style="font-size:1.3rem;font-weight:700;color:#0ea5e9">₡${parseInt(i.minimo).toLocaleString()}</div></div><div style="background:#0f172a;padding:12px;border-radius:10px;"><div style="font-size:0.7rem;color:#94a3b8">MÁXIMO</div><div style="font-size:1.3rem;font-weight:700;color:#f59e0b">₡${parseInt(i.maximo).toLocaleString()}</div></div><div style="background:#0f172a;padding:12px;border-radius:10px;"><div style="font-size:0.7rem;color:#94a3b8">PROMEDIO</div><div style="font-size:1.3rem;font-weight:700;color:#22c55e">₡${parseInt(i.promedio).toLocaleString()}</div></div><div style="background:#0f172a;padding:12px;border-radius:10px;"><div style="font-size:0.7rem;color:#94a3b8">MODA</div><div style="font-size:1.3rem;font-weight:700;color:#a855f7">₡${parseInt(i.moda).toLocaleString()}</div></div></div>`;
  } else {
    c.innerHTML = '<p style="color:#94a3b8">Sin datos</p>';
  }
}

function updateChart(data) {
  const ctx = document.getElementById('priceChart').getContext('2d');
  if (priceChart) priceChart.destroy();
  const months = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'};
  priceChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => { const [y,m] = d[0].split('-'); return `${months[parseInt(m)]} ${y.slice(2)}`; }),
      datasets: [{ data: data.map(d=>d[1]), backgroundColor: 'rgba(34,197,94,0.7)', borderColor: '#22c55e', borderWidth: 2, borderRadius: 6 }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(148,163,184,0.1)' }, ticks: { color: '#94a3b8' } },
        y: { grid: { color: 'rgba(148,163,184,0.1)' }, ticks: { color: '#94a3b8', callback: v=>'₡'+v } }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  log('Iniciando...');
  loadAllData();
});
