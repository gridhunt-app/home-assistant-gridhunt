/*
 * Gridhunt Lovelace card (served by the Gridhunt integration at /gridhunt_static/gridhunt-card.js).
 *
 *   type: custom:gridhunt-card
 *   entry_id: optional (first Gridhunt entry by default)
 *   map: svg | live-page        (svg = lightweight map drawn in the card; live-page = embedded Gridhunt live page)
 *   title: optional
 *
 * Data: hass.callWS({type: "gridhunt/card"}) every 20 s (riding) / 60 s (idle); route map: gridhunt/route.
 * Extensions: window.gridhuntCardExtensions = [{ id, title(data, ctx), mapLayers(data, proj, ctx), sections(data, ctx) }]
 * may add map layers and sections (loaded as separate scripts when the account has extra features).
 */
(() => {
  const VERSION = "0.1.0";
  const I18N = {
    en: {
      live: "LIVE", nobody: "Nobody is riding right now", lastRide: "Last ride", done: "ridden", left: "to go", tiles: "new tiles",
      square: "square", total: "tiles", year: "this year", rides: "rides", routes: "Planned routes", moments: "Moments", updated: "updated {s} s ago",
      noSignal: "no signal for {m} min", offRoute: "off route", distance: "distance", progress: "progress", noRoutes: "No saved routes yet.", open: "Open full screen",
      mStarted: "Start", mFinished: "Ride finished", mTiles: "+{n} new tiles", mSquare: "New square {from}×{from} → {to}×{to}", mOff: "Left the route", mBack: "Back on route",
      loading: "Loading…", error: "Gridhunt is not available.", km: "km",
      allYears: "All", play: "Play", pause: "Pause",
    },
    pl: {
      live: "NA ŻYWO", nobody: "Teraz nikt nie jedzie", lastRide: "Ostatnia jazda", done: "przejechane", left: "do mety", tiles: "nowe kafle",
      square: "kwadrat", total: "kafle", year: "w tym roku", rides: "jazdy", routes: "Zaplanowane trasy", moments: "Momenty", updated: "aktualizacja {s} s temu",
      noSignal: "brak sygnału od {m} min", offRoute: "poza trasą", distance: "dystans", progress: "postęp", noRoutes: "Nie masz jeszcze zapisanych tras.", open: "Pełny ekran",
      mStarted: "Start", mFinished: "Koniec jazdy", mTiles: "+{n} nowych kafli", mSquare: "Nowy kwadrat {from}×{from} → {to}×{to}", mOff: "Zjazd z trasy", mBack: "Z powrotem na trasie",
      loading: "Wczytywanie…", error: "Gridhunt jest niedostępny.", km: "km",
      allYears: "Wszystko", play: "Odtwórz", pause: "Pauza",
    },
  };
  const fmt = (s, o) => String(s).replace(/\{(\w+)\}/g, (_, k) => String(o[k] ?? ""));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const Z = 2 ** 14;
  /** Gridhunt mark (variant C, geometry from apps/web/src/lib/brand/mark.tsx, tight frame): tile, current square, target. */
  const LOGO = '<svg class="logo" viewBox="17 16 67 67" aria-hidden="true"><rect x="18" y="55" width="27" height="27" rx="2" style="fill:var(--gh-mark-tile)"/><path d="M18 41H59V82" style="fill:none;stroke:var(--gh-square);stroke-width:14"/><path d="M18 22.5H77.5V82" style="fill:none;stroke:var(--gh-target);stroke-width:11;stroke-dasharray:22.31 14.88 44.62 14.88 22.31 1000"/></svg>';

  /** Web Mercator (0..1) and a fit-to-box projection. */
  const merc = (lat, lon) => [(lon + 180) / 360, (1 - Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360)) / Math.PI) / 2];
  function projection(points, w, h, pad = 16) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const [la, lo] of points) { const [x, y] = merc(la, lo); x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
    if (!isFinite(x0)) return null;
    const span = Math.max(x1 - x0, y1 - y0, 4 / Z);
    const s = Math.min((w - 2 * pad) / Math.max(x1 - x0, span * 0.2, 1e-9), (h - 2 * pad) / Math.max(y1 - y0, span * 0.2, 1e-9));
    const ox = (w - (x1 - x0) * s) / 2 - x0 * s, oy = (h - (y1 - y0) * s) / 2 - y0 * s;
    const p = { scale: s, ox, oy, w, h, xy: (la, lo) => { const [x, y] = merc(la, lo); return [x * s + ox, y * s + oy]; }, tile: (tx, ty) => [(tx / Z) * s + ox, (ty / Z) * s + oy, s / Z] };
    return p;
  }
  const path = (proj, pts) => pts.length < 2 ? "" : "M" + pts.map(([la, lo]) => proj.xy(la, lo).map((v) => v.toFixed(1)).join(" ")).join("L");
  function tilesSvg(proj, xy, cls, color) {
    let out = "";
    for (let i = 0; i + 1 < xy.length; i += 2) {
      const [x, y, s] = proj.tile(xy[i], xy[i + 1]);
      out += `<rect class="${cls}" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${s.toFixed(1)}" height="${s.toFixed(1)}"${color ? ` style="fill:${esc(color)};stroke:${esc(color)}"` : ""}/>`;
    }
    return out;
  }
  /** z14 grid lines in view (only when tiles are big enough to read). */
  function gridSvg(proj) {
    const px = proj.scale / Z;
    if (px < 9) return "";
    const tx0 = Math.floor(((0 - proj.ox) / proj.scale) * Z), tx1 = Math.ceil(((proj.w - proj.ox) / proj.scale) * Z);
    const ty0 = Math.floor(((0 - proj.oy) / proj.scale) * Z), ty1 = Math.ceil(((proj.h - proj.oy) / proj.scale) * Z);
    if ((tx1 - tx0) * (ty1 - ty0) > 2500) return "";
    let d = "";
    for (let x = tx0; x <= tx1; x++) { const X = ((x / Z) * proj.scale + proj.ox).toFixed(1); d += `M${X} 0V${proj.h}`; }
    for (let y = ty0; y <= ty1; y++) { const Y = ((y / Z) * proj.scale + proj.oy).toFixed(1); d += `M0 ${Y}H${proj.w}`; }
    return `<path class="grid" d="${d}"/>`;
  }

  class GridhuntCard extends HTMLElement {
    setConfig(config) {
      this._config = { map: "svg", ...(config || {}) };
      this._timer = null;
    }
    static getStubConfig() { return { map: "svg" }; }
    getCardSize() { return 7; }
    set hass(hass) {
      const first = !this._hass;
      this._hass = hass;
      if (first) { this._render(); this._load(); }
    }
    connectedCallback() { if (this._hass && !this._timer) this._load(); }
    disconnectedCallback() { clearTimeout(this._timer); this._timer = null; }
    get t() {
      const l = String(this._hass?.locale?.language || this._hass?.language || "en").slice(0, 2);
      return I18N[l] || I18N.en;
    }
    async _load() {
      clearTimeout(this._timer);
      try {
        const msg = { type: "gridhunt/card" };
        if (this._config.entry_id) msg.entry_id = this._config.entry_id;
        this._data = await this._hass.callWS(msg);
        this._error = null;
      } catch (e) {
        this._error = e;
      }
      this._render();
      const poll = this._data?.state?.riding ? (this._data.state.pollSec || 20) : 60;
      if (this.isConnected) this._timer = setTimeout(() => this._load(), poll * 1000);
    }
    async _pickRoute(id) {
      this._routeId = id;
      this._route = null;
      this._render();
      try {
        const msg = { type: "gridhunt/route", route_id: id };
        if (this._config.entry_id) msg.entry_id = this._config.entry_id;
        this._route = await this._hass.callWS(msg);
      } catch { this._route = { error: true }; }
      this._render();
    }
    _ext() { return (window.gridhuntCardExtensions || []).filter((e) => e && typeof e === "object"); }
    _ctx() { return { hass: this._hass, config: this._config, card: this, t: this.t, esc, fmt, refresh: () => this._load() }; }

    _mapSvg(d, w = 640, h = 360) {
      const live = d.live || {};
      const pts = [...(live.line || []).flat(), ...((live.me && live.me.trail) || [])];
      if (d.state.position) pts.push([d.state.position.lat, d.state.position.lon]);
      for (const ext of this._ext()) if (ext.points) pts.push(...(ext.points(d) || []));
      const proj = projection(pts, w, h);
      if (!proj) return "";
      let extra = "";
      for (const ext of this._ext()) if (ext.mapLayers) extra += ext.mapLayers(d, proj, this._ctx()) || "";
      const me = d.state.position ? proj.xy(d.state.position.lat, d.state.position.lon) : null;
      return `<svg class="map" viewBox="0 0 ${w} ${h}" role="img">
        ${gridSvg(proj)}
        ${tilesSvg(proj, live.myTiles || [], "mine")}
        ${(live.line || []).map((p) => `<path class="route" d="${path(proj, p)}"/>`).join("")}
        ${live.me && live.me.trail ? `<path class="trail" d="${path(proj, live.me.trail)}"/>` : ""}
        ${extra}
        ${me ? `<circle class="me-halo" cx="${me[0].toFixed(1)}" cy="${me[1].toFixed(1)}" r="16"/><circle class="me" cx="${me[0].toFixed(1)}" cy="${me[1].toFixed(1)}" r="8"/>` : ""}
      </svg>`;
    }
    /** Tile model for the idle map (cached per payload): order of first visits, per-year lists. */
    _tileModel(tm) {
      if (this._tmSrc === tm && this._tm) return this._tm;
      const n = (tm.tiles || []).length / 2, first = new Float64Array(n).fill(Infinity), years = {};
      for (const [y, flat] of Object.entries(tm.visits || {})) {
        const list = [];
        for (let j = 0; j + 1 < flat.length; j += 2) { const i = flat[j], k = Number(y) * 400 + flat[j + 1]; list.push([i, k]); if (k < first[i]) first[i] = k; }
        years[y] = list;
      }
      const all = []; for (let i = 0; i < n; i++) all.push([i, isFinite(first[i]) ? first[i] : 0]);
      all.sort((a, b) => a[1] - b[1]);
      this._tmSrc = tm;
      this._tm = { n, first, all, years, list: Object.keys(years).sort().reverse() };
      return this._tm;
    }
    /** Selection in play order: [[tileIndex, key, isNewThatYear]]; `all` = everything up to now (cumulative). */
    _tileOrder(tm) {
      const m = this._tileModel(tm), y = this._tsel && m.years[this._tsel] ? this._tsel : "all";
      if (y === "all") return { y, rows: m.all.map(([i, k]) => [i, k, false]) };
      return { y, rows: m.years[y].map(([i, k]) => [i, k, Math.floor(m.first[i] / 400) === Number(y)]) };
    }
    /** Largest fully covered N×N square among the first `count` rows (DP on the view grid). */
    _maxSquare(tm, rows, count) {
      const v = tm.view, W = v.x1 - v.x0 + 1, H = v.y1 - v.y0 + 1;
      if (W * H > 600000) return null;
      const g = new Uint8Array(W * H), t = tm.tiles;
      for (let r = 0; r < count; r++) { const i = rows[r][0], x = t[2 * i] - v.x0, y = t[2 * i + 1] - v.y0; if (x >= 0 && y >= 0 && x < W && y < H) g[y * W + x] = 1; }
      const dp = new Uint16Array(W * H); let best = 0, bx = 0, by = 0;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        const k = y * W + x; if (!g[k]) continue;
        const s = x && y ? 1 + Math.min(dp[k - 1], dp[k - W], dp[k - W - 1]) : 1;
        dp[k] = s; if (s > best) { best = s; bx = x - s + 1; by = y - s + 1; }
      }
      return best ? { x: v.x0 + bx, y: v.y0 + by, s: best } : null;
    }
    /** Idle map like the web/iOS dashboard: my z14 tiles, current square (gold), active target (green dashed),
     *  year filter and history playback (no reel export). */
    _tilesSvg(tm, w = 640) {
      const v = tm && tm.view;
      if (!v) return "";
      const ll = (x, y) => [Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / Z))) * 180 / Math.PI, (x / Z) * 360 - 180];
      const ar = (v.y1 - v.y0 + 1) / (v.x1 - v.x0 + 1);
      const h = Math.round(Math.min(480, Math.max(220, w * ar)));
      const proj = projection([ll(v.x0, v.y0), ll(v.x1 + 1, v.y1 + 1)], w, h, 8);
      if (!proj) return "";
      this._tproj = proj;
      const { y, rows } = this._tileOrder(tm), t = tm.tiles;
      let rects = "";
      for (const [i, , nw] of rows) {
        const [x0, y0, s] = proj.tile(t[2 * i], t[2 * i + 1]);
        rects += `<rect class="own${nw ? " nw" : ""}" x="${x0.toFixed(1)}" y="${y0.toFixed(1)}" width="${s.toFixed(1)}" height="${s.toFixed(1)}"/>`;
      }
      const sq = y === "all" && !this._playT ? tm.square : this._maxSquare(tm, rows, rows.length);
      const tg = tm.target, tt = this.t, m = this._tileModel(tm);
      const tgBox = tg ? this._boxSvg(tg.x0, tg.y0, tg.x1, tg.y1, "tgt", `${tg.x1 - tg.x0 + 1}×${tg.y1 - tg.y0 + 1}`) : "";
      const sqBox = `<g id="ghsq">${sq ? this._boxSvg(sq.x, sq.y, sq.x + sq.s - 1, sq.y + sq.s - 1, "sq", `${sq.s}×${sq.s}`) : ""}</g>`;
      const chips = [["all", tt.allYears], ...m.list.slice(0, 8).map((yy) => [yy, yy])]
        .map(([k, l]) => `<button class="chip ${k === y ? "on" : ""}" data-tyear="${esc(k)}">${esc(l)}</button>`).join("");
      return `<svg class="map tilesmap" viewBox="0 0 ${w} ${h}" role="img"><style id="ghcut"></style>${gridSvg(proj)}<g id="ghtl">${rects}</g>${tgBox}${sqBox}
          <text id="ghdate" class="tdate" x="12" y="${h - 12}"></text></svg>
        <div class="tbar"><button class="chip play" data-tplay="1">${esc(this._playTimer ? "⏸ " + tt.pause : "▶ " + tt.play)}</button>${chips}</div>`;
    }
    _boxSvg(x0, y0, x1, y1, cls, label) {
      const proj = this._tproj, [ax, ay] = proj.tile(x0, y0), [bx, by] = proj.tile(x1 + 1, y1 + 1);
      const lab = label ? `<text class="sqlab ${cls}" x="${(bx - 4).toFixed(1)}" y="${(cls === "sq" ? by + 16 : ay - 6).toFixed(1)}" text-anchor="end">${esc(label)}</text>` : "";
      return `<rect class="${cls}" x="${ax.toFixed(1)}" y="${ay.toFixed(1)}" width="${(bx - ax).toFixed(1)}" height="${(by - ay).toFixed(1)}"/>${lab}`;
    }
    /** Playback frame: show the first part of the selection (CSS nth-child cut), recompute the square, show the date. */
    _tileFrame(frac) {
      const tm = this._data && this._data.tiles, root = this.shadowRoot;
      if (!tm || !root) return;
      const { rows } = this._tileOrder(tm), k = Math.max(0, Math.min(rows.length, Math.round(frac * rows.length)));
      const cut = root.getElementById("ghcut"), sqg = root.getElementById("ghsq"), date = root.getElementById("ghdate");
      if (cut) cut.textContent = k < rows.length ? `#ghtl rect:nth-child(n+${k + 1}){display:none}` : "";
      if (sqg) { const sq = this._maxSquare(tm, rows, k); sqg.innerHTML = sq ? this._boxSvg(sq.x, sq.y, sq.x + sq.s - 1, sq.y + sq.s - 1, "sq", `${sq.s}×${sq.s}`) : ""; }
      if (date) {
        const key = k ? rows[k - 1][1] : rows.length ? rows[0][1] : 0, yy = Math.floor(key / 400), doy = key % 400;
        date.textContent = key ? new Date(Date.UTC(yy, 0, doy)).toLocaleDateString(this._hass?.locale?.language || undefined, { day: "numeric", month: "short", year: "numeric" }) : "";
      }
    }
    _togglePlay() {
      if (this._playTimer) { clearInterval(this._playTimer); this._playTimer = null; this._playT = 0; this._render(); return; }
      const DUR = 12000, STEP = 80, t0 = Date.now();
      this._playT = 0.0001;
      this._playTimer = setInterval(() => {
        const f = Math.min(1, (Date.now() - t0) / DUR);
        this._playT = f;
        this._tileFrame(f);
        if (f >= 1) { clearInterval(this._playTimer); this._playTimer = null; this._playT = 0; setTimeout(() => this._render(), 1500); }
      }, STEP);
      this._render();
    }
    _routeSvg(r, w = 640, h = 220) {
      const pts = (r.line || []).flat();
      const proj = projection(pts, w, h);
      if (!proj) return "";
      return `<svg class="map small" viewBox="0 0 ${w} ${h}" role="img">${gridSvg(proj)}${(r.line || []).map((p) => `<path class="route" d="${path(proj, p)}"/>`).join("")}</svg>`;
    }
    _stat(label, value, cls = "", unit = "") { return `<div class="st ${cls}"><b>${esc(value)}${unit ? `<small> ${esc(unit)}</small>` : ""}</b><span>${esc(label)}</span></div>`; }
    _moment(m) {
      const t = this.t, who = m.me ? "" : m.who ? esc(m.who) + ": " : "";
      const k = m.kind, dd = m.data || {};
      const txt = k === "tiles" ? fmt(t.mTiles, { n: dd.count ?? 0 }) : k === "new_square" ? fmt(t.mSquare, { from: dd.from ?? "?", to: dd.to ?? "?" })
        : k === "off_route" ? t.mOff : k === "back_on_route" ? t.mBack : k === "finished" ? t.mFinished : t.mStarted;
      const time = new Date(m.createdAt).toLocaleTimeString(this._hass?.locale?.language || undefined, { hour: "2-digit", minute: "2-digit" });
      return `<div class="row"><span class="dot ${k === "tiles" || k === "new_square" ? "t" : ""}"></span><span class="grow">${who}${esc(txt)}</span><span class="muted">${esc(time)}</span></div>`;
    }

    _render() {
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });
      const t = this.t, d = this._data, nf = new Intl.NumberFormat(this._hass?.locale?.language || undefined, { maximumFractionDigits: 1 });
      let body;
      if (!d && !this._error) body = `<div class="pad muted">${esc(t.loading)}</div>`;
      else if (!d) body = `<div class="pad muted">${esc(t.error)}</div>`;
      else {
        const s = d.state || {}, exts = this._ext(), ctx = this._ctx();
        const title = this._config.title || exts.map((e) => e.title && e.title(d, ctx)).find(Boolean) || s.routeName || "Gridhunt";
        const head = `<div class="head">${LOGO}<b class="grow">${esc(title)}</b>${s.riding ? `<span class="pill">${esc(t.live)}</span>` : ""}</div>`;
        const extSections = exts.map((e) => (e.sections && e.sections(d, ctx)) || "").join("");
        if (s.riding) {
          const age = s.position ? s.position.ageSec : null;
          const status = age == null ? "" : age > 120 ? `<span class="warn">${esc(fmt(t.noSignal, { m: Math.round(age / 60) }))}</span>` : `<span class="muted">${esc(fmt(t.updated, { s: age }))}</span>`;
          const stats = (s.progress
            ? this._stat(t.done, nf.format(s.progress.doneKm), "", t.km) + this._stat(t.left, nf.format(s.progress.leftKm), "", t.km) + this._stat(t.progress, nf.format(s.progress.pct), "", "%")
            : this._stat(t.distance, nf.format(s.distanceKm || 0), "", t.km))
            + this._stat(t.tiles, "+" + ((s.tiles && s.tiles.mine) || 0), "t") + (s.square && s.square.size ? this._stat(t.square, s.square.size + "×" + s.square.size) : "");
          const map = this._config.map === "live-page" && s.liveUrl
            ? `<iframe class="frame" src="${esc(s.liveUrl)}" referrerpolicy="no-referrer" allow="fullscreen"></iframe>`
            : this._mapSvg(d);
          const moments = ((d.live && d.live.moments) || []).slice(0, 8).map((m) => this._moment(m)).join("");
          body = `${head}<div class="sub">${status}${s.offRoute ? ` <span class="warn">· ${esc(t.offRoute)}</span>` : ""}${s.liveUrl ? ` <a href="${esc(s.liveUrl)}" target="_blank" rel="noreferrer">${esc(t.open)}</a>` : ""}</div>
            <div class="mapbox">${map}</div><div class="stats">${stats}</div>${extSections}
            ${moments ? `<h3>${esc(t.moments)}</h3><div class="list">${moments}</div>` : ""}`;
        } else {
          const st = d.stats || {}, l = s.lastRide;
          const last = l ? `<div class="last"><span class="muted">${esc(t.lastRide)}</span> <b>${esc(l.name || "")}</b> · ${esc(nf.format(l.distanceKm))} ${esc(t.km)} · +${esc(l.tiles)} ${esc(t.tiles)}</div>` : "";
          const routes = d.routes || [];
          const tilesMap = this._tilesSvg(d.tiles);
          // with the tile map the route map opens only after a tap (less height); without it the first route as before
          const sel = this._routeId || (!tilesMap && routes[0] && routes[0].id);
          if (sel && this._routeId !== sel && !this._route) queueMicrotask(() => this._pickRoute(sel));
          const routeList = routes.length
            ? `<div class="chips">${routes.slice(0, 8).map((r) => `<button class="chip ${r.id === sel ? "on" : ""}" data-route="${esc(r.id)}">${esc(r.name)} · ${esc(nf.format(r.km))} ${esc(t.km)}</button>`).join("")}</div>
               ${sel && this._route && !this._route.error ? `<div class="mapbox">${this._routeSvg(this._route)}</div>` : ""}`
            : `<div class="muted">${esc(t.noRoutes)}</div>`;
          // jeden wiersz: znak, „Teraz nikt nie jedzie”, liczniki (zawija się na wąskim ekranie)
          body = `<div class="idlehead">${LOGO}<div class="idle" title="${esc(title)}">${esc(t.nobody)}</div>
            <div class="stats inline">${this._stat(t.total, nf.format(st.tilesZ14 || 0))}${this._stat(t.square, (st.uber || 0) + "×" + (st.uber || 0))}${this._stat(t.year, "+" + (st.newThisYear || 0), "t")}${st.rides ? this._stat(t.rides, st.rides.count) : ""}</div></div>${last}
            ${tilesMap ? `<div class="mapbox">${tilesMap}</div>` : ""}
            ${extSections}<h3>${esc(t.routes)}</h3>${routeList}`;
        }
      }
      // keep what the user is typing across refreshes (inputs with an id)
      const kept = [...this.shadowRoot.querySelectorAll("input[id]")].map((i) => [i.id, i.value, this.shadowRoot.activeElement === i]);
      this.shadowRoot.innerHTML = `<style>${GridhuntCard.css}</style><ha-card>${body}</ha-card>`;
      for (const [id, v, focused] of kept) { const i = this.shadowRoot.getElementById(id); if (i) { i.value = v; if (focused) i.focus(); } }
      this.shadowRoot.querySelectorAll("[data-route]").forEach((b) => b.addEventListener("click", () => {
        if (this._routeId === b.dataset.route && this._data && this._data.tiles) { this._routeId = null; this._route = null; this._render(); }
        else this._pickRoute(b.dataset.route);
      }));
      this.shadowRoot.querySelectorAll("[data-tyear]").forEach((b) => b.addEventListener("click", () => {
        if (this._playTimer) { clearInterval(this._playTimer); this._playTimer = null; this._playT = 0; }
        this._tsel = b.dataset.tyear; this._render();
      }));
      this.shadowRoot.querySelectorAll("[data-tplay]").forEach((b) => b.addEventListener("click", () => this._togglePlay()));
      if (this._playTimer && this._playT) this._tileFrame(this._playT);
      for (const ext of this._ext()) if (ext.bind) ext.bind(this.shadowRoot, this._data, this._ctx());
    }
  }
  GridhuntCard.css = `
    :host{--gh-accent:var(--primary-color,#2447e0);--gh-mark-tile:#5b7bff;--gh-square:#f5b82e;--gh-target:#22c55e;--gh-tile:#e69f00;--gh-live:#d6336c}
    ha-card{display:block;padding:16px;overflow:hidden}.st small{font-size:.5em;font-weight:700;color:var(--secondary-text-color)}
    .head{display:flex;align-items:center;gap:10px;font-size:1.25em}.grow{flex:1;min-width:0}
    .logo{width:24px;height:24px;flex:none;display:block}
    .pill{background:var(--gh-live);color:#fff;font-weight:800;font-size:.65em;letter-spacing:.06em;padding:3px 9px;border-radius:999px}
    .sub{margin:4px 0 10px;font-size:.9em}.sub a{color:var(--gh-accent);margin-left:6px}
    .muted{color:var(--secondary-text-color)}.warn{color:var(--gh-live);font-weight:600}
    .mapbox{border-radius:12px;overflow:hidden;background:var(--secondary-background-color,rgba(127,127,127,.08));margin:8px 0}
    svg.map{display:block;width:100%;height:auto;max-height:min(55vh,420px)}svg.map.small{max-height:220px}
    .grid{stroke:var(--divider-color,rgba(127,127,127,.25));stroke-width:.6;fill:none}
    .route{fill:none;stroke:var(--gh-accent);stroke-opacity:.45;stroke-width:6;stroke-linecap:round;stroke-linejoin:round}
    .trail{fill:none;stroke:var(--gh-accent);stroke-width:4;stroke-linecap:round;stroke-linejoin:round}
    .own{fill:var(--gh-mark-tile);fill-opacity:.5;stroke:var(--gh-mark-tile);stroke-opacity:.35;stroke-width:.5}
    .sq{fill:none;stroke:var(--gh-square);stroke-width:3}.tgt{fill:none;stroke:var(--gh-target);stroke-width:3;stroke-dasharray:10 6}
    .sqlab{font:700 13px sans-serif;stroke:none}.sqlab.sq{fill:var(--gh-square)}.sqlab.tgt{fill:var(--gh-target)}
    svg.tilesmap{max-height:min(60vh,480px)}.own.nw{fill:var(--gh-tile);stroke:var(--gh-tile);fill-opacity:.7}
    .tdate{font:700 15px sans-serif;fill:var(--primary-text-color,#212121);paint-order:stroke;stroke:var(--card-background-color,#fff);stroke-width:3}
    .tbar{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0 2px}.chip.play{font-weight:700}
    .mine{fill:var(--gh-tile);fill-opacity:.45;stroke:var(--gh-tile);stroke-width:1}
    .me{fill:var(--gh-accent);stroke:#fff;stroke-width:3}.me-halo{fill:var(--gh-accent);opacity:.2}
    .frame{width:100%;height:min(60vh,480px);border:0;display:block}
    .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));gap:6px;text-align:center;margin:8px 0}
    .st b{display:block;font-size:1.6em;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.1}.st span{font-size:.8em;color:var(--secondary-text-color)}
    .st.t b{color:var(--gh-tile)}
    h3{font-size:.8em;text-transform:uppercase;letter-spacing:.06em;color:var(--secondary-text-color);margin:14px 0 4px}
    .row{display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--divider-color,rgba(127,127,127,.2))}.row:last-child{border-bottom:0}
    .dot{width:9px;height:9px;border-radius:50%;background:var(--gh-accent)}.dot.t{background:var(--gh-tile)}
    .idlehead{display:flex;align-items:center;gap:12px 16px;flex-wrap:wrap}.idlehead .logo{width:32px;height:32px}
    .idle{font-size:1.3em;font-weight:700;margin:0;flex:1 1 180px}.stats.inline{flex:2 1 360px;margin:0}.last{margin-bottom:6px}
    .chips{display:flex;gap:6px;flex-wrap:wrap}.chip{border:1px solid var(--divider-color,#ccc);background:none;color:inherit;border-radius:999px;padding:6px 12px;font:inherit;font-size:.85em;cursor:pointer}
    .chip.on{background:var(--gh-accent);border-color:var(--gh-accent);color:#fff}
    .pad{padding:8px 0}
  `;
  GridhuntCard.helpers = { projection, path, tilesSvg, esc, fmt, merc };

  if (!customElements.get("gridhunt-card")) customElements.define("gridhunt-card", GridhuntCard);
  window.customCards = window.customCards || [];
  if (!window.customCards.some((c) => c.type === "gridhunt-card")) {
    window.customCards.push({ type: "gridhunt-card", name: "Gridhunt", description: "Live ride, tiles, square and planned routes from Gridhunt." });
  }
  window.gridhuntCardExtensions = window.gridhuntCardExtensions || [];
  console.info(`%c GRIDHUNT-CARD %c ${VERSION} `, "background:#2447e0;color:#fff;font-weight:700", "");
})();
