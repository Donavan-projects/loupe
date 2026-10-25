// Loupe — génération du rapport HTML (v2)
// Utilisable tel quel dans un nœud Code n8n (mode "Run Once for Each Item") :
//   const html = renderRapport($json.analyse, $json.proof_of_work, { date: $now.toFormat('dd/MM/yyyy') });
//   return { json: { html } };
// Le HTML est autonome (CSS inline) et prévu pour l'impression A4 : Ctrl+P > Enregistrer en PDF,
// ou conversion directe par un service HTML → PDF (ex. Gotenberg) en v2.

function renderRapport(a, p, opts = {}) {
  // Les textes sont affichés sans les citations d'URL entre crochets ([http…]) que le modèle recopie parfois.
  const e = (s) => String(s ?? '').replace(/\s*\[\s*https?:\/\/[^\]]*\]/g, '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const page = (u) => { const m = String(u ?? '').match(/^https?:\/\/[^/]+(\/[^?#]*)?/); if (!m) return e(u); const segs = (m[1] || '/').split('/').filter(Boolean); return e(segs.length ? segs[segs.length - 1] : 'Accueil'); };
  // pages_analysees : liste d'objets { url, titre } depuis la v2.1, liste d'URL dans les anciennes analyses.
  const pages = (a.pages_analysees || []).map((x) => (x && typeof x === 'object' ? x : { url: x }));
  // Source d'un point fort ou d'une piste : la page analysée correspondante (crochets et texte autour ignorés), sinon null.
  const cle = (u) => String(u ?? '').replace(/\/+$/, '');
  const source = (s) => {
    const brut = String(s ?? '');
    const urls = [...(brut.match(/\[\s*https?:\/\/[^\]\s]+/g) || []).map((u) => u.replace(/^\[\s*/, '')), ...(brut.match(/https?:\/\/[^\s\[\],]+/g) || [])];
    for (const u of urls) { const p = pages.find((x) => cle(x.url) === cle(u)); if (p) return p; }
    return null;
  };
  // Titre de page affiché : « Accueil » pour la page d'accueil, sans le suffixe qui répète le nom de l'entreprise
  // (après « | », « – » ou « - »), et tronqué à 50 caractères.
  const simple = (s) => String(s ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const estAccueil = (u) => { const m = String(u ?? '').match(/^https?:\/\/[^/]+(\/[^?#]*)?/); return !!m && /^\/?([a-z]{2}([-_][a-z]{2})?\/?)?$/i.test(m[1] || '/'); };
  const nomPage = (x) => {
    if (estAccueil(x.url)) return 'Accueil';
    let t = String(x.titre ?? '').replace(/\s+/g, ' ').trim();
    if (!t) return page(x.url);
    const entreprise = simple(a.entreprise);
    const morceaux = t.split(/\s+[|–—-]\s+/);
    const dernier = simple(morceaux[morceaux.length - 1]);
    const premierMot = entreprise.split(' ')[0] || '';
    if (morceaux.length > 1 && dernier && entreprise && (dernier.includes(entreprise) || entreprise.includes(dernier) || (premierMot.length >= 3 && dernier.includes(premierMot)))) {
      t = t.slice(0, t.length - morceaux[morceaux.length - 1].length).replace(/\s+[|–—-]\s+$/, '').trim() || t;
    }
    return e(t.length > 50 ? t.slice(0, 49).trimEnd() + '…' : t);
  };
  const titre = (s) => { const p = source(s); if (p) return nomPage(p); return page(String(s ?? '').replace(/[\[\]]/g, '').split(',')[0].trim()); };
  // Les analyses enregistrées avant la v2.2 peuvent porter un préfixe « Contexte : » dans contexte_resume.
  const contexte = String(a.contexte_resume ?? '').replace(/^\s*contexte\s*:\s*/i, '').trim();
  // Étapes du proof-of-work : objets { etape, heures } depuis la v2.4, simples textes dans les anciennes analyses.
  const heures = (v) => e(String(v ?? '').replace('.', ','));
  const etape = (x) => (x && typeof x === 'object' ? e(x.etape) + (x.heures != null ? ' <span class="src">· ' + heures(x.heures) + ' h</span>' : '') : e(x));
  // Angles du contexte que les pages lues ne couvrent pas (depuis la v2.6).
  const nonCouvert = (Array.isArray(a.perimetre_non_couvert) ? a.perimetre_non_couvert : []).filter((x) => typeof x === 'string' && x.trim());
  const niveau = (v) => `<span class="niv niv-${e(v)}">${e(v)}</span>`;
  const m = a.marche || {};
  const date = e(opts.date || new Date().toLocaleDateString('fr-FR'));

  // Liste jointe par « · », sans ponctuation finale dans les éléments : la phrase ne se termine que par un seul point.
  const joindre = (elements) => elements.map((x) => String(x ?? '').trim().replace(/[\s.;,:·…]+$/, '')).filter(Boolean).join(' · ');
  const phrase = (s) => { const t = String(s ?? '').trim().replace(/[\s.;,:·]+$/, ''); return t ? e(t) + '.' : ''; };
  const noteContexte = phrase(a.note_contexte);
  // Encadré « Périmètre de l'analyse » : pages analysées, puis angles non couverts et note de contexte s'ils existent.
  const perimetre = `<div class="card perimetre"><div class="lbl">Périmètre de l'analyse</div>
  <p><strong>Pages analysées.</strong> ${joindre(pages.map(nomPage)) || '—'}.</p>
  ${nonCouvert.length ? `<p><strong>Angles non couverts.</strong> Angles du contexte que les pages lues ne permettent pas d'analyser : ${joindre(nonCouvert.map((x) => e(x)))}.</p>` : ''}
  ${noteContexte ? `<p>${noteContexte}</p>` : ''}
  <p class="note">Analyse générée automatiquement à partir du site public ; les pistes sont des propositions à discuter.</p>
</div>`;

  return `<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Loupe — ${e(a.entreprise)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><style>
@page { size: A4; margin: 14mm 0 16mm; @bottom-left { content: "Loupe · analyse produit et marché"; font: 8pt Inter, Arial, sans-serif; color: #8A8F98; padding-left: 16mm; } @bottom-right { content: counter(page) " / " counter(pages); font: 8pt Inter, Arial, sans-serif; color: #8A8F98; padding-right: 16mm; } }
@page :first { margin-top: 0; }
html, body, * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
:root { --ink:#16181D; --quiet:#5B616B; --line:#E4E6EA; --soft:#F5F6F8; --acc:#0F766E; --acc-soft:#E6F2F1; --warm:#B45309; }
* { box-sizing: border-box; }
body { font-family: Inter, "Segoe UI", "Helvetica Neue", Arial, sans-serif; color: var(--ink); font-size: 9.6pt; line-height: 1.5; margin: 0; background: #fff; }
.sheet { padding: 0 16mm 10mm; background: #fff; }
.cover { background: var(--ink); color: #fff; margin: 0 -16mm; padding: 22mm 16mm 12mm; }
.actions { display: none; }
@media screen {
  html { background: #E7E9EC; }
  body { background: #E7E9EC; padding: 12mm 4mm 20mm; }
  .sheet { max-width: 210mm; margin: 0 auto; box-shadow: 0 2px 18px rgba(0,0,0,.12); border-radius: 2mm; overflow: hidden; }
  .actions { display: flex; justify-content: center; gap: 3mm; max-width: 210mm; margin: 0 auto 6mm; }
  .actions button { font: 600 10pt Inter, "Segoe UI", Arial, sans-serif; background: var(--acc); color: #fff; border: 0; border-radius: 2mm; padding: 3mm 6mm; cursor: pointer; }
  .actions span { align-self: center; font-size: 8.5pt; color: var(--quiet); }
  .pow { margin-top: 10mm; border-top: 1px solid var(--line); padding-top: 2mm; }
}
@media print {
  /* Impression dense : texte et espacements réduits d'environ 10 % par rapport à l'écran, bandeau de couverture inchangé. */
  body { background: #fff; font-size: 8.1pt; line-height: 1.34; }
  h2 { margin: 5.2mm 0 2.2mm; font-size: 7.7pt; }
  h3 { font-size: 9.9pt; }
  p { margin-bottom: 1.7mm; }
  .cover { padding: 18mm 16mm 9mm; }
  .cover h1 { font-size: 24pt; margin-top: 4mm; }
  .synthese { margin-top: 4.75mm; font-size: 9pt; }
  .pv { font-size: 9.9pt; }
  .card { padding: 2.7mm 3.6mm; }
  .grid { gap: 2.7mm; }
  .forts li { padding-top: 2.2mm; padding-bottom: 2.2mm; }
  .piste { padding: 3.1mm 4.1mm; margin-bottom: 2.2mm; }
  .pow-tete { padding: 4mm 4.5mm; }
  .pow-tete h3 { font-size: 11.7pt; }
  .cols, .kpis { margin-top: 3.6mm; }
  .kpi .v { font-size: 8.1pt; }
  .big { font-size: 16.2pt; }
  ul.l li, ol.l li { margin-bottom: 1.1mm; }
}
.brand { font-size: 8.5pt; letter-spacing: .18em; text-transform: uppercase; color: #7DD3C8; font-weight: 600; }
.cover h1 { font-size: 28pt; line-height: 1.1; margin: 6mm 0 2mm; font-weight: 700; letter-spacing: -.01em; }
.cover .meta { color: #A9B0BA; font-size: 9pt; }
.synthese { margin: 7mm 0 0; font-size: 11pt; line-height: 1.55; color: #E8EAED; max-width: 150mm; }
h2 { break-after: avoid; font-size: 8.5pt; letter-spacing: .14em; text-transform: uppercase; color: var(--acc); margin: 9mm 0 3mm; font-weight: 700; }
h3 { font-size: 11pt; margin: 0 0 1.5mm; }
p { margin: 0 0 2mm; }
.pv { font-size: 12pt; line-height: 1.5; border-left: 3px solid var(--acc); padding-left: 4mm; margin-top: 2mm; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; }
.card { background: var(--soft); border-radius: 3mm; padding: 4mm 4.5mm; break-inside: avoid; }
.card .lbl { font-size: 7.5pt; letter-spacing: .1em; text-transform: uppercase; color: var(--quiet); font-weight: 600; margin-bottom: 1mm; }
.ctx { background: var(--acc-soft); }
.perimetre { background: none; border: 1px dashed var(--line); color: var(--quiet); font-size: 8.5pt; margin-bottom: 3mm; }
.perimetre p { margin: 0 0 1.2mm; }
.perimetre p:last-child { margin-bottom: 0; }
.perimetre strong { color: var(--ink); font-weight: 600; }
.note { font-size: 7.5pt; color: var(--quiet); font-style: italic; margin-top: 1.5mm; }
.forts { list-style: none; padding: 0; margin: 0; }
.forts li { padding: 2.5mm 0 2.5mm 7mm; border-bottom: 1px solid var(--line); position: relative; break-inside: avoid; }
.forts li::before { content: "✓"; position: absolute; left: 0; top: 2.3mm; color: var(--acc); font-weight: 700; }
.src { color: var(--quiet); font-size: 8pt; }
.piste { border: 1px solid var(--line); border-radius: 3mm; padding: 4.5mm 5mm; margin-bottom: 3mm; break-inside: avoid; }
.piste.retenue { border: 1.5px solid var(--acc); background: linear-gradient(0deg, #fff, var(--acc-soft)); }
.piste-tete { display: flex; justify-content: space-between; align-items: baseline; gap: 4mm; }
.num { color: var(--acc); font-weight: 700; margin-right: 2mm; }
.badges { white-space: nowrap; font-size: 7.5pt; color: var(--quiet); }
.niv { display: inline-block; padding: .4mm 2.2mm; border-radius: 9mm; font-weight: 600; margin-left: 1mm; text-transform: capitalize; }
.niv-fort { background: #D1FAE5; color: #065F46; } .niv-moyen { background: #FEF3C7; color: #92400E; } .niv-faible { background: #E5E7EB; color: #374151; }
.tag { display: inline-block; font-size: 7pt; letter-spacing: .08em; text-transform: uppercase; color: #fff; background: var(--acc); border-radius: 9mm; padding: .5mm 2.5mm; margin-bottom: 2mm; font-weight: 700; }
.pow { margin-top: 2mm; }
.pow-tete, .kpis { break-inside: avoid; }
.pow-intro { break-inside: avoid; break-after: avoid; }
.pow-tete { background: var(--soft); border-radius: 3mm; padding: 6mm; }
.pow-tete h3 { font-size: 15pt; line-height: 1.25; margin-bottom: 2mm; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; margin-top: 5mm; }
ul.l, ol.l { margin: 0; padding-left: 4.5mm; } ul.l li, ol.l li { margin-bottom: 1.3mm; }
.hors li { color: var(--quiet); }
.kpis { display: grid; grid-template-columns: 1.3fr .7fr 2fr; gap: 3mm; margin-top: 5mm; }
.kpi { border-top: 2px solid var(--acc); padding-top: 2mm; }
.kpi .v { font-size: 10pt; font-weight: 600; }
.big { font-size: 18pt; font-weight: 700; color: var(--acc); }
</style></head><body>
<div class="actions"><button onclick="window.print()">Enregistrer en PDF</button><span>Choisir « Enregistrer au format PDF » comme destination.</span></div>
<main class="sheet">
<section class="cover">
  <div class="brand">Loupe · analyse produit &amp; marché</div>
  <h1>${e(a.entreprise)}</h1>
  <div class="meta">${date} · ${pages.length} pages analysées${opts.url ? ' · ' + e(opts.url) : ''}</div>
  ${contexte ? `<div class="meta">Contexte : ${e(contexte)}</div>` : ''}
  <p class="synthese">${e(a.synthese)}</p>
</section>

<h2>Proposition de valeur</h2>
<p class="pv">${e(a.proposition_de_valeur)}</p>

<h2>Le marché</h2>
<div class="grid">
  <div class="card"><div class="lbl">Segment</div>${e(m.segment)}</div>
  <div class="card"><div class="lbl">Cible</div>${e(m.cible)}</div>
  <div class="card"><div class="lbl">Positionnement</div>${e(m.positionnement)}</div>
  <div class="card"><div class="lbl">Différenciation</div>${e(m.differenciation)}</div>
  <div class="card"><div class="lbl">Modèle économique</div>${e(m.modele_economique)}</div>
  <div class="card ctx"><div class="lbl">Contexte du secteur</div>${e(m.contexte_marche)}<div class="note">Tendances générales, hors site analysé.</div></div>
</div>

<div style="break-inside: avoid"><h2>Points forts</h2>
<ul class="forts">${(a.points_forts || []).map((f) => `<li>${e(f.constat)} <span class="src">— ${titre(f.source)}</span></li>`).join('')}</ul></div>

<h2>Pistes de développement</h2>
${(a.pistes || []).map((x, i) => `<div class="piste${x.titre === p?.piste_retenue ? ' retenue' : ''}">
  ${x.titre === p?.piste_retenue ? '<span class="tag">Piste prototypée</span>' : ''}
  <div class="piste-tete"><h3><span class="num">${i + 1}</span>${e(x.titre)}</h3><div class="badges">Impact ${niveau(x.impact)} Effort ${niveau(x.effort)}</div></div>
  <p><strong>Opportunité.</strong> ${e(x.opportunite)}</p>
  ${x.existant ? `<p><strong>Existant.</strong> ${e(x.existant)}</p>` : ''}
  <p><strong>Piste.</strong> ${e(x.proposition)}</p>
  ${x.apport ? `<p><strong>Apport.</strong> ${e(x.apport)}</p>` : ''}
  ${source(x.source) ? `<div class="src">Inspirée de : ${titre(x.source)}</div>` : ''}
</div>`).join('')}
${perimetre}

${p ? `<section class="pow">
<div class="pow-intro">
<h2>Proof-of-work</h2>
<div class="pow-tete">
  <h3>${e(p.titre)}</h3>
  <p>${e(p.objectif)}</p>
  <p class="src" style="font-size:9pt;margin:0"><strong style="color:var(--ink)">Valeur pour l'entreprise.</strong> ${e(p.valeur_pour_l_entreprise)}</p>
</div>
<p style="margin-top:4mm"><strong>Pourquoi cette piste.</strong> ${e(p.justification_choix)}</p>
</div>
<div class="kpis">
  <div class="kpi"><div class="lbl" style="font-size:7.5pt;color:var(--quiet);text-transform:uppercase;letter-spacing:.1em;font-weight:600">Stack suggérée</div><div class="v">${e(p.stack_suggeree)}</div></div>
  <div class="kpi"><div class="lbl" style="font-size:7.5pt;color:var(--quiet);text-transform:uppercase;letter-spacing:.1em;font-weight:600">Durée</div><div class="big">${heures(p.duree_calculee_heures ?? p.duree_estimee_heures)} h</div></div>
  <div class="kpi"><div class="lbl" style="font-size:7.5pt;color:var(--quiet);text-transform:uppercase;letter-spacing:.1em;font-weight:600">Critère de succès</div><div class="v" style="font-weight:400">${e(p.critere_de_succes)}</div></div>
</div>
<div class="cols">
  <div><div class="card" style="background:none;padding:0"><div class="lbl">Périmètre</div></div><ul class="l">${(p.perimetre || []).map((x) => `<li>${e(x)}</li>`).join('')}</ul>
       <div class="lbl" style="font-size:7.5pt;letter-spacing:.1em;text-transform:uppercase;color:var(--quiet);font-weight:600;margin:4mm 0 1mm">Hors périmètre</div><ul class="l hors">${(p.hors_perimetre || []).map((x) => `<li>${e(x)}</li>`).join('')}</ul></div>
  <div><div class="card" style="background:none;padding:0"><div class="lbl">Étapes</div></div><ol class="l">${(p.etapes || []).map((x) => `<li>${etape(x)}</li>`).join('')}</ol></div>
</div>
</section>` : ''}

</main>
</body></html>`;
}

if (typeof module !== 'undefined') module.exports = { renderRapport };
