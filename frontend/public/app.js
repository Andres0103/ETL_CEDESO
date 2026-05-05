'use strict';

const state = { files: [], downloadFilename: null };

const $ = id => document.getElementById(id);
const fileInput    = $('file-input');
const dropzone     = $('dropzone');
const fileList     = $('file-list');
const btnPick      = $('btn-pick');
const btnProcess   = $('btn-process');
const btnDownload  = $('btn-download');
const progressWrap = $('progress-wrap');
const progFill     = $('prog-fill');
const progLabel    = $('prog-label');
const alertsEl     = $('alerts');
const resultCard   = $('result-card');
const selMes       = $('sel-mes');
const selAnio      = $('sel-anio');

(function init() {
  const now = new Date();
  selMes.value  = String(now.getMonth() + 1).padStart(2, '0');
  selAnio.value = now.getFullYear();
})();

// --- Drag & drop ---
dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('drag-over'); });
dropzone.addEventListener('dragleave', e => { if (!dropzone.contains(e.relatedTarget)) dropzone.classList.remove('drag-over'); });
dropzone.addEventListener('drop', e => { e.preventDefault(); dropzone.classList.remove('drag-over'); addFiles([...e.dataTransfer.files]); });
btnPick.addEventListener('click', () => { fileInput.value = ''; fileInput.click(); });
fileInput.addEventListener('change', () => { addFiles([...fileInput.files]); fileInput.value = ''; });

function addFiles(newFiles) {
  newFiles
    .filter(f => /\.xlsx?$/i.test(f.name) && !state.files.find(x => x.name === f.name))
    .forEach(f => state.files.push(f));
  renderFileList();
}

function removeFile(i) { state.files.splice(i, 1); renderFileList(); }
window.removeFile = removeFile;

function renderFileList() {
  fileList.innerHTML = state.files.map((f, i) => `
    <div class="file-card" id="fc-${i}">
      <span class="fc-icon">📄</span>
      <div class="fc-info">
        <div class="fc-name">${esc(f.name)}</div>
        <div class="fc-size">${(f.size / 1024).toFixed(0)} KB</div>
        <div class="fc-prog-wrap hidden" id="fp-wrap-${i}">
          <div class="fc-prog-track"><div class="fc-prog-fill" id="fp-fill-${i}"></div></div>
          <span class="fc-prog-label" id="fp-label-${i}">0%</span>
        </div>
      </div>
      <button class="fc-rm" id="fc-rm-${i}" type="button" onclick="removeFile(${i})">x</button>
    </div>`).join('');
  btnProcess.disabled = state.files.length === 0;
}

// --- Subida con progreso real via XMLHttpRequest ---
function uploadWithProgress(formData, onFileProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/procesar');

    xhr.upload.addEventListener('progress', e => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        onFileProgress(pct);
      }
    });

    xhr.addEventListener('load', () => {
      try {
        const data = JSON.parse(xhr.responseText);
        resolve({ ok: xhr.status < 400, status: xhr.status, data });
      } catch (_) {
        // Servidor devolvio HTML de error
        const match = xhr.responseText.match(/<pre[^>]*>([\s\S]{0,500})<\/pre>/i);
        const detail = match ? match[1].trim() : xhr.responseText.substring(0, 300);
        reject(new Error('Respuesta inesperada del servidor (HTTP ' + xhr.status + '): ' + detail));
      }
    });

    xhr.addEventListener('error', () => reject(new Error('Error de red. Verifica que el servidor este activo.')));
    xhr.addEventListener('abort', () => reject(new Error('Subida cancelada.')));

    xhr.send(formData);
  });
}

// --- Proceso principal ---
btnProcess.addEventListener('click', async () => {
  if (state.files.length === 0) return;

  clearAlerts();
  resultCard.classList.add('hidden');
  state.downloadFilename = null;
  btnProcess.disabled = true;

  // Mostrar barras de progreso en cada file-card
  state.files.forEach((_, i) => {
    const wrap = $(`fp-wrap-${i}`);
    if (wrap) wrap.classList.remove('hidden');
    setFileProgress(i, 0, 'Esperando...');
    const rmBtn = $(`fc-rm-${i}`);
    if (rmBtn) rmBtn.style.display = 'none';
  });

  progressWrap.classList.remove('hidden');
  setProgress(5, 'Preparando archivos...');

  const fd = new FormData();
  state.files.forEach(f => fd.append('files', f, f.name));
  fd.append('mes',  selMes.value);
  fd.append('anio', selAnio.value);

  setProgress(10, 'Subiendo archivos al servidor...');

  let result;
  try {
    result = await uploadWithProgress(fd, pct => {
      // El progreso de upload es global (todos los archivos juntos)
      // Lo distribuimos entre 10% y 70%
      const mapped = 10 + Math.round(pct * 0.6);
      setProgress(mapped, 'Subiendo archivos... ' + pct + '%');
      // Marcar cada archivo visualmente segun progreso global
      state.files.forEach((_, i) => {
        setFileProgress(i, pct, pct < 100 ? 'Subiendo...' : 'Subido');
      });
    });
  } catch (err) {
    addAlert('error', 'x', 'Error al subir archivos: <b>' + esc(err.message) + '</b>');
    done(); return;
  }

  setProgress(75, 'Python procesando y limpiando datos...');
  state.files.forEach((_, i) => setFileProgress(i, 100, 'Procesando...'));
  await sleep(200);

  if (!result.ok) {
    const msg = result.data.error || 'Error del servidor (HTTP ' + result.status + ')';
    const det = result.data.detalle || '';
    addAlert('error', 'x', '<b>' + esc(msg) + '</b>' +
      (det ? '<details><summary style="cursor:pointer;margin-top:4px">Ver detalle tecnico</summary>' +
              '<pre class="err-pre">' + esc(det) + '</pre></details>' : ''));
    done(); return;
  }

  setProgress(95, 'Generando Excel consolidado...');
  await sleep(300);
  setProgress(100, 'Listo.');
  await sleep(250);
  progressWrap.classList.add('hidden');

  const data = result.data;

  // Resultado por archivo
  (data.file_results || []).forEach((fr, i) => {
    if (fr.status === 'ok') {
      const badge = fr.errores > 0
        ? '<span class="badge badge-error">' + fr.errores + ' errores</span>'
        : fr.advertencias > 0
          ? '<span class="badge badge-warn">' + fr.advertencias + ' advertencias</span>'
          : '<span class="badge badge-ok">Sin problemas</span>';
      setFileProgress(i, 100, fr.errores > 0 ? 'Con errores' : fr.advertencias > 0 ? 'Con advertencias' : 'OK');
      addAlert('ok', 'v', '<b>' + esc(fr.filename) + '</b>: ' + fr.rows + ' registros. ' + badge);
    } else {
      setFileProgress(i, 100, 'Error');
      const msgs = (fr.alerts || []).map(a => esc(a.msg)).join(' - ');
      addAlert('error', 'x', '<b>' + esc(fr.filename) + '</b>: ' + msgs);
    }
  });

  // Tabla de errores
  const allAlerts = data.alerts || [];
  const errors = allAlerts.filter(a => a.type === 'error' && a.doc);
  const warns  = allAlerts.filter(a => a.type === 'warn'  && a.doc);

  if (errors.length > 0) {
    addAlert('error', 'x', buildAlertTable(
      errors.length + ' error(es) encontrado(s). Estos registros requieren correccion:', errors));
  }
  if (warns.length > 0) {
    addAlert('warn', '!', buildAlertTable(
      warns.length + ' advertencia(s). Revisa estos registros antes de subir a Power BI:', warns));
  }
  if (errors.length === 0 && warns.length === 0) {
    addAlert('ok', 'v', '<b>Todos los datos pasaron la validacion sin problemas.</b>');
  }

  // Stats
  const s = data.stats || {};
  $('s-total').textContent = s.total_beneficiarios ?? '-';
  $('s-paq').textContent   = s.total_paquetes      ?? '-';
  $('s-fem').textContent   = s.femenino             ?? '-';
  $('s-mas').textContent   = s.masculino            ?? '-';
  $('s-dias').textContent  = s.dias_unicos          ?? '-';
  $('s-err').textContent   = s.total_errores        ?? '-';
  $('s-warn').textContent  = s.total_advertencias   ?? '-';

  state.downloadFilename = data.filename;
  resultCard.classList.remove('hidden');
  resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  btnProcess.disabled = false;
});

btnDownload.addEventListener('click', () => {
  if (state.downloadFilename)
    window.location.href = '/descargar/' + encodeURIComponent(state.downloadFilename);
});

// --- Helpers ---
function setProgress(pct, label) {
  progFill.style.width  = pct + '%';
  progLabel.textContent = label;
}

function setFileProgress(i, pct, label) {
  const fill  = $('fp-fill-' + i);
  const lbl   = $('fp-label-' + i);
  if (fill)  fill.style.width  = pct + '%';
  if (lbl)   lbl.textContent   = pct === 100 ? label : pct + '%';
  // Color segun estado
  if (fill) {
    if (label === 'OK' || label === 'Subido' || pct === 100 && label === 'Procesando...')
      fill.style.background = '#2D5016';
    else if (label === 'Con errores' || label === 'Error')
      fill.style.background = '#991B1B';
    else if (label === 'Con advertencias')
      fill.style.background = '#92400E';
  }
}

function clearAlerts() { alertsEl.innerHTML = ''; }

function addAlert(type, icon, msg) {
  const el = document.createElement('div');
  el.className = 'alert ' + type;
  el.innerHTML = '<span class="alert-icon">' + icon + '</span><div class="alert-body">' + msg + '</div>';
  alertsEl.appendChild(el);
}

function done() {
  progressWrap.classList.add('hidden');
  btnProcess.disabled = false;
  // Restaurar botones de eliminar
  state.files.forEach((_, i) => {
    const rmBtn = $('fc-rm-' + i);
    if (rmBtn) rmBtn.style.display = '';
  });
}

function buildAlertTable(title, items) {
  const rows = items.slice(0, 30).map(a =>
    '<tr><td>' + esc(a.file || '') + '</td>' +
    '<td>' + esc(a.doc  || '') + '</td>' +
    '<td>' + esc(a.campo|| '') + '</td>' +
    '<td>' + esc(a.msg  || '') + '</td></tr>'
  ).join('');
  const more = items.length > 30
    ? '<tr><td colspan="4" style="font-style:italic">... y ' + (items.length - 30) + ' mas</td></tr>'
    : '';
  return title +
    '<div style="overflow-x:auto;margin-top:8px">' +
    '<table class="alert-table"><thead><tr>' +
    '<th>Archivo</th><th>Documento</th><th>Campo</th><th>Problema</th>' +
    '</tr></thead><tbody>' + rows + more + '</tbody></table></div>';
}

function esc(s) {
  return String(s ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
