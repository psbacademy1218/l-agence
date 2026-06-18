"use strict";
/* Mission Control — pilote l'affichage en interrogeant l'API toutes les 800 ms.
   Aucune dépendance : DOM natif. */

const $ = (s, r = document) => r.querySelector(s);
const api = (p, opts) => fetch(p, opts).then(r => r.json());
const PIPE_LABELS = {
  scout: "Détecte & qualifie", closer: "Rédige l'approche",
  strategist: "Cadre la mission", designer: "Direction artistique",
  copywriter: "Contenu sur-mesure", builder: "Code le site",
  inspector: "Contrôle qualité", optimizer: "SEO technique",
  launcher: "Déploie & vérifie",
};
const STATE_FR = { pending: "en attente", running: "en action…", passed: "terminé",
  failed: "échec", skipped: "ignoré" };
const DOT = { passed: "✓", running: "▸", failed: "✕", pending: "·", skipped: "–" };

let TEAM = [];               // [{key,emoji,name,...}]
let TEAM_BY = {};            // key -> persona
let PIPE_KEYS = [];          // agents du pipeline (hors manager)
let busy = false;

function timeOf(ts) { return (ts || "").split("T")[1] || ""; }

/* ---------- squelette : équipe + pipeline ---------- */
function renderTeam() {
  const wrap = $("#agents");
  wrap.innerHTML = "";
  PIPE_KEYS.forEach(k => {
    const p = TEAM_BY[k];
    const d = document.createElement("div");
    d.className = "agent"; d.id = "agent-" + k; d.dataset.st = "pending";
    d.innerHTML = `<span class="agent__avatar"><img src="/avatars/${k}.png" alt=""
        onerror="this.style.display='none'"><i>${p.emoji}</i></span>
      <div><div class="agent__name">${p.name}</div>
      <div class="agent__role">${PIPE_LABELS[k] || ""}</div>
      <div class="agent__state">en attente</div></div>`;
    wrap.appendChild(d);
  });
}
function renderPipelineSkeleton() {
  const ol = $("#pipeline"); ol.innerHTML = "";
  PIPE_KEYS.forEach((k, i) => {
    const p = TEAM_BY[k];
    const li = document.createElement("li");
    li.className = "step"; li.id = "step-" + k; li.dataset.st = "pending";
    li.innerHTML = `<span class="step__dot">·</span>
      <span class="step__name">${p.emoji} ${p.name} <small>· ${PIPE_LABELS[k] || ""}</small></span>
      <span class="step__score"></span>`;
    ol.appendChild(li);
  });
}

/* ---------- prospects ---------- */
function renderProspects(list) {
  const wrap = $("#prospects"); wrap.innerHTML = "";
  list.forEach(p => {
    const d = document.createElement("div");
    d.className = "prospect";
    d.innerHTML = `<div class="prospect__top">
        <span class="prospect__name">${p.name}</span>
        <span class="prospect__score">${p.score}/100</span></div>
      <div class="prospect__pb">${p.problem}</div>`;
    const b = document.createElement("button");
    b.className = "btn"; b.textContent = "▶ Lancer la mission";
    b.disabled = !p.qualified || busy;
    b.onclick = () => launch("accept", String(p.index));
    d.appendChild(b);
    wrap.appendChild(d);
  });
}

/* ---------- mise à jour live ---------- */
function setPill(run, ctrl) {
  const pill = $("#status-pill"), dot = $("#live-dot");
  let cls = "pill--idle", txt = "● au repos";
  const running = run && run.stages && run.stages.find(s => s.status === "running");
  if (ctrl.active && running) {
    const p = TEAM_BY[running.name] || { emoji: "", name: running.name };
    cls = "pill--run"; txt = `${p.emoji} ${p.name} en action…`;
  } else if (ctrl.active) { cls = "pill--run"; txt = "● mission en cours…"; }
  else if (run && run.status === "delivered") { cls = "pill--done"; txt = "✓ site livré"; }
  else if (run && run.status === "aborted") { cls = "pill--abort"; txt = "✕ interrompu"; }
  else if (run && run.status === "awaiting_reply") { cls = "pill--done"; txt = "✉ brouillon prêt"; }
  pill.className = "pill " + cls; pill.textContent = txt;
  dot.classList.toggle("on", ctrl.active);
}

function updateAgents(run) {
  const byKey = {};
  (run && run.stages || []).forEach(s => byKey[s.name] = s);
  PIPE_KEYS.forEach(k => {
    const card = $("#agent-" + k); if (!card) return;
    const s = byKey[k] || { status: "pending" };
    card.dataset.st = s.status;
    card.classList.toggle("active", s.status === "running");
    const st = card.querySelector(".agent__state");
    st.textContent = STATE_FR[s.status] || s.status;
    if (s.status === "passed" && s.score != null)
      st.textContent = `terminé · ${Math.round(s.score)}/100`;
  });
}

function updatePipeline(run) {
  const byKey = {};
  (run && run.stages || []).forEach(s => byKey[s.name] = s);
  PIPE_KEYS.forEach(k => {
    const li = $("#step-" + k); if (!li) return;
    const s = byKey[k] || { status: "pending", attempts: 0, score: null };
    li.dataset.st = s.status;
    li.querySelector(".step__dot").textContent = DOT[s.status] || "·";
    const sc = li.querySelector(".step__score");
    let txt = s.score != null ? `${Math.round(s.score)}/100` : "";
    li.querySelector(".step__name small").innerHTML =
      `· ${PIPE_LABELS[k] || ""}` +
      (s.attempts > 1 ? ` <span class="step__retry">↻ ${s.attempts} essais</span>` : "");
    sc.textContent = txt;
  });
}

function updateHub(run, ctrl) {
  const line = $("#hub-line"), meta = $("#hub-meta");
  const stages = (run && run.stages) || [];
  const done = stages.filter(s => s.status === "passed").length;
  meta.textContent = `${done}/${stages.length || 9} étapes validées`;
  const running = stages.find(s => s.status === "running");
  if (running) {
    const p = TEAM_BY[running.name] || { emoji: "", name: running.name };
    line.textContent = `▸ j'ai la main à ${p.emoji} ${p.name} — ${PIPE_LABELS[running.name] || ""}`;
  } else if (run && run.status === "delivered") {
    line.textContent = "Mission livrée. Le site a passé tous les contrôles. ✅";
  } else if (run && run.status === "aborted") {
    line.textContent = "Mission interrompue après échec du contrôle qualité.";
  } else {
    line.textContent = "assigne chaque étape · contrôle la qualité · relance · tranche quand c'est prêt";
  }
}

function updateFeed(run) {
  const box = $("#feed");
  const log = (run && run.log) || [];
  if (!log.length) { box.innerHTML = '<div class="feed__empty">En attente du premier agent…</div>'; return; }
  const near = box.scrollHeight - box.scrollTop - box.clientHeight < 60;
  box.innerHTML = log.slice(-200).map(e => {
    const p = TEAM_BY[e.agent] || { emoji: "•", name: e.agent };
    return `<div class="feed__row"><span class="feed__t">${timeOf(e.ts)}</span>` +
      `<span class="feed__who who-${e.agent}">${p.emoji} ${p.name}</span>` +
      `<span class="feed__msg">${escapeHtml(e.message)}</span></div>`;
  }).join("");
  if (near) box.scrollTop = box.scrollHeight;
}

function updateDeliverable(data) {
  const run = data.run, box = $("#deliverable");
  if (!run || run.status !== "delivered") { box.hidden = true; return; }
  const bb = run.blackboard || {};
  const dep = bb.deploy || {}, des = bb.design || {}, seo = bb.seo || {};
  const insp = (run.stages || []).find(s => s.name === "inspector") || {};
  const slug = run.slug || data.slug;
  const url = `/site/${slug}/index.html`;
  box.hidden = false;
  box.innerHTML =
    `<div class="deliverable__bar"><span>🎉 Site livré — aperçu</span>
       <a href="${url}" target="_blank" rel="noopener">Ouvrir en grand ↗</a></div>
     <iframe title="Aperçu du site livré" src="${url}"></iframe>
     <div class="deliverable__meta">
       <span>DA : ${des.archetype || "?"} / ${des.palette_key || "?"}</span>
       <span>QA : <b>${insp.score != null ? Math.round(insp.score) : "?"}/100</b></span>
       <span>Type : ${(bb.build || {}).site_type || "?"}</span>
       <span>Déploiement : <b>${dep.verified ? "vérifié ✓" : "?"}</b></span>
     </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

/* ---------- boucle ---------- */
async function tick() {
  try {
    const data = await api("/api/state");
    const run = data.run, ctrl = data.controller || {};
    busy = !!ctrl.active;
    document.querySelectorAll(".controls .btn, .prospect button, .nm button")
      .forEach(b => { b.disabled = busy; });
    setPill(run, ctrl);
    updateAgents(run); updatePipeline(run); updateHub(run, ctrl);
    updateFeed(run); updateDeliverable(data);
    $("#mission-sub").textContent = run
      ? `Mission : ${run.client?.name || "?"} — ${run.status}`
      : "Aucune mission. Lance-en une pour voir l'équipe travailler.";
  } catch (e) { /* serveur occupé : on réessaiera */ }
}

async function launch(command, arg) {
  if (busy) return;
  const pace = $("#pace").value;
  busy = true;
  document.querySelectorAll(".controls .btn, .prospect button, .nm button").forEach(b => b.disabled = true);
  await api("/api/launch", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ command, arg, pace }),
  }).catch(() => {});
  setTimeout(tick, 150);
}

async function init() {
  TEAM = await api("/api/team");
  TEAM_BY = {}; TEAM.forEach(p => TEAM_BY[p.key] = p);
  PIPE_KEYS = TEAM.filter(p => p.key !== "manager").map(p => p.key);
  renderTeam(); renderPipelineSkeleton();
  try { renderProspects(await api("/api/prospects")); } catch (e) {}
  document.querySelectorAll(".controls .btn").forEach(b =>
    b.addEventListener("click", () => launch(b.dataset.cmd)));
  const pf = document.getElementById("nm-prospect");
  if (pf) pf.addEventListener("submit", (e) => {
    e.preventDefault();
    const city = document.getElementById("nm-city").value.trim();
    const sector = document.getElementById("nm-sector").value.trim();
    if (city && sector) launch("prospect", { city, sector });
  });
  const uf = document.getElementById("nm-url");
  if (uf) uf.addEventListener("submit", (e) => {
    e.preventDefault();
    const url = document.getElementById("nm-urlinput").value.trim();
    if (url) launch("mission_url", { url });
  });
  tick();
  setInterval(tick, 800);
  setInterval(async () => {  // rafraîchit la liste des prospects après une prospection
    if (!busy) { try { renderProspects(await api("/api/prospects")); } catch (e) {} }
  }, 4000);
}

init();
