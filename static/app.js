let knownIds = new Set();
let lastData = "";

function colorClass(score) {
  if (score >= 8) return "green";
  if (score >= 5) return "yellow";
  return "red";
}

function esc(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderCard(email, rank) {
  const cls = colorClass(email.puntaje_total);
  const fillPct = ((email.puntaje_total / 10) * 100).toFixed(1);
  const isNew = !knownIds.has(email.id);
  return `
    <div class="card ${cls}${isNew ? " new" : ""}" id="card-${esc(email.id)}"
         onclick="toggleCard('${esc(email.id)}')">
      <div class="card-header">
        <div class="rank">#${rank}</div>
        <div class="sender">
          <div class="sender-name">${esc(email.remitente_nombre || email.remitente_email)}</div>
        </div>
        <div class="score-area">
          <div class="score-number">${Number(email.puntaje_total).toFixed(1)}</div>
          <div class="score-bar">
            <div class="score-fill" style="width:${fillPct}%"></div>
          </div>
        </div>
      </div>
      <div class="card-body">
        <div class="subject">Asunto: <span>${esc(email.asunto)}</span></div>
        <div class="dim-group-label">Base</div>
        <div class="dimensions">
          <div class="dim"><span class="dim-label">Asunto</span>
            <span class="dim-score">${email.puntaje_asunto ?? "—"}/10</span></div>
          <div class="dim"><span class="dim-label">Persuasión</span>
            <span class="dim-score">${email.puntaje_persuasion ?? "—"}/10</span></div>
          <div class="dim"><span class="dim-label">Contexto</span>
            <span class="dim-score">${email.puntaje_contexto ?? "—"}/10</span></div>
          <div class="dim"><span class="dim-label">Propuesta</span>
            <span class="dim-score">${email.puntaje_propuesta ?? "—"}/10</span></div>
        </div>
        <div class="dim-group-label">Avanzado</div>
        <div class="dimensions">
          <div class="dim"><span class="dim-label">Gancho</span>
            <span class="dim-score">${email.puntaje_gancho ?? "—"}/10</span></div>
          <div class="dim"><span class="dim-label">Personalización</span>
            <span class="dim-score">${email.puntaje_personalizacion ?? "—"}/10</span></div>
          <div class="dim"><span class="dim-label">Unicidad</span>
            <span class="dim-score">${email.puntaje_unicidad ?? "—"}/10</span></div>
          <div class="dim"><span class="dim-label">CTA</span>
            <span class="dim-score">${email.puntaje_cta ?? "—"}/10</span></div>
        </div>
        <div class="resumen">"${esc(email.resumen_gemini)}"</div>
        <div class="cuerpo">${esc(email.cuerpo)}</div>
      </div>
    </div>`;
}

function toggleCard(id) {
  const card = document.getElementById("card-" + id);
  if (card) card.classList.toggle("expanded");
}

async function fetchAndRender() {
  try {
    const res = await fetch("/api/emails");
    const emails = await res.json();
    const serialized = JSON.stringify(emails);
    if (serialized === lastData) return;
    lastData = serialized;

    const board = document.getElementById("board");
    if (emails.length === 0) {
      board.innerHTML = '<div class="empty-state">Esperando correos...</div>';
      return;
    }
    board.innerHTML = emails.map((e, i) => renderCard(e, i + 1)).join("");
    emails.forEach(e => knownIds.add(e.id));
  } catch (err) {
    console.error("fetch error:", err);
  }
}

async function limpiarDB() {
  if (!confirm("Limpiar todos los correos del board?")) return;
  await fetch("/api/clear", { method: "POST" });
  knownIds = new Set();
  lastData = "";
  fetchAndRender();
}

fetchAndRender();
setInterval(fetchAndRender, 3000);
