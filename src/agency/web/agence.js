"use strict";
/* Page "L'agence" — construit la galerie d'équipe depuis /roster.json. */

const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function agentCard(a, color) {
  const exp = (a.expertise || []).slice(0, 3)
    .map(e => `<li>${esc(e)}</li>`).join("");
  const pin = a.pipeline ? '<span class="agent-card__pin">★ cœur de mission</span>' : "";
  return `<article class="agent-card reveal" style="--c:${color}">
    <div class="agent-card__media">
      <img src="/avatars/${a.key}.png" alt="Avatar de ${esc(a.name)}" loading="lazy"
           onerror="this.style.display='none'">
      <span class="agent-card__role">${esc(a.role)}</span>${pin}
    </div>
    <div class="agent-card__body">
      <h4 class="agent-card__name">${esc(a.name)}</h4>
      <p class="agent-card__mission">${esc(a.mission)}</p>
      <ul class="agent-card__exp">${exp}</ul>
      <p class="agent-card__perso">« ${esc(a.personality)} »</p>
    </div>
  </article>`;
}

function department(d) {
  const cards = d.agents.map(a => agentCard(a, d.color)).join("");
  return `<section class="dept" style="--c:${d.color}">
    <div class="dept__head">
      <span class="dept__emoji">${d.emoji}</span>
      <div><h3>${esc(d.label)}</h3><p>${esc(d.blurb || "")}</p></div>
    </div>
    <div class="dept__grid">${cards}</div>
  </section>`;
}

function chip(c) {
  return `<span class="chip"><b>${esc(c.name)}</b> · <span>${esc(c.mission)}</span></span>`;
}

function observeReveal() {
  const items = [].slice.call(document.querySelectorAll(".reveal"));
  if (!("IntersectionObserver" in window)) {
    items.forEach(el => el.classList.add("in")); return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach(en => {
      if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
    });
  }, { threshold: 0.1 });
  items.forEach(el => io.observe(el));
}

async function init() {
  try {
    const data = await fetch("/roster.json").then(r => r.json());
    document.getElementById("team").innerHTML =
      (data.departments || []).map(department).join("");
    document.getElementById("catalog").innerHTML =
      (data.catalog || []).map(chip).join("");
  } catch (e) {
    document.getElementById("team").innerHTML =
      '<p style="color:var(--muted)">Impossible de charger l\'équipe. Lancez le serveur via <code>python agency.py dashboard</code>.</p>';
  }
  observeReveal();
}

init();
