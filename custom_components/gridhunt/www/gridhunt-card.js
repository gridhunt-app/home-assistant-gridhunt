/*
 * Gridhunt Lovelace card (served by the Gridhunt integration at /gridhunt_static/gridhunt-card.js).
 *
 *   type: custom:gridhunt-card
 *   entry_id: optional (first Gridhunt entry by default)
 *   map: svg | live-page        (svg = lightweight map drawn in the card; live-page = embedded Gridhunt live page)
 *   basemap: none               (optional: idle tile map without the MapLibre base map, SVG only)
 *   title: optional
 *
 * Strategies (same file): dashboard `strategy: {type: custom:gridhunt}` and view `strategy: {type: custom:gridhunt}`
 * (optional `device_id` limits the view to one account). Builds the owner's "sections" layout from hass.entities.
 *
 * Data: hass.callWS({type: "gridhunt/card"}) every 20 s (riding) / 60 s (idle); route map: gridhunt/route.
 * Extensions: window.gridhuntCardExtensions = [{ id, title(data, ctx), mapLayers(data, proj, ctx), sections(data, ctx) }]
 * may add map layers and sections (loaded as separate scripts when the account has extra features).
 */
(() => {
  const VERSION = "0.1.9";
  const I18N = {
    en: {
      live: "LIVE", nobody: "Nobody is riding right now", lastRide: "Last ride", done: "ridden", left: "to go", tiles: "new tiles",
      square: "square", total: "tiles", year: "this year", rides: "rides", routes: "Planned routes", moments: "Moments", updated: "updated {s} s ago",
      noSignal: "no signal for {m} min", offRoute: "off route", distance: "distance", progress: "progress", noRoutes: "No saved routes yet.", open: "Open full screen",
      mStarted: "Start", mFinished: "Ride finished", mTiles: "+{n} new tiles", mSquare: "New square {from}×{from} → {to}×{to}", mOff: "Left the route", mBack: "Back on route",
      loading: "Loading…", error: "Gridhunt is not available.", km: "km",
      play: "Play the selected years", pause: "Pause", allYearsLong: "All years", years: "Years", moreYears: "More years",
      visited: "Visited", newIn: "New in {y}", record: "Record", position: "Timeline position", stepLabel: "Playback step", speedLabel: "Playback speed",
      step_day: "Day", step_week: "Week", step_month: "Month", step_quarter: "Quarter", step_year: "Year", quarter: "Q{q} {y}",
      modeYears: "Only these years", modeCum: "Whole collection", modeYearsHelp: "<b>Only these years</b>: tiles from rides in the selected years.",
      modeCumHelp: "<b>Whole collection</b>: every tile collected up to the last selected year. With one year, amber shows tiles collected for the first time that year.",
      tapHelp: "Tap a year to add it. Tap a selected year to keep only that one.",
      base: "Base map", baseSimple: "Simple", baseDetailed: "Detailed", overlays: "Overlays", ovTiles: "My tiles", ovGoals: "Square and target",
      kOwned: "visited", kNew: "new in {y}", kSquare: "square", kTarget: "target",
      gestWin: "Use Ctrl + scroll to zoom the map", gestMac: "Use ⌘ + scroll to zoom the map", gestMobile: "Use two fingers to move the map",
      sView: "Gridhunt", sLive: "Live ride", sRide: "Current ride", sAccount: "Account", sRiding: "Riding", sRideDistance: "Distance",
      sDone: "Ridden", sLeft: "To go", sProgress: "Route progress", sNewRide: "New tiles", sTiles: "Tiles", sSquare: "Square",
      sNewYear: "New this year", sLastRide: "Last ride", sNoData: "No Gridhunt entities found. Add the Gridhunt integration first.",
      sDesc: "Live ride, tiles and square from Gridhunt in one view.",
    },
    pl: {
      live: "NA ŻYWO", nobody: "Teraz nikt nie jedzie", lastRide: "Ostatnia jazda", done: "przejechane", left: "do mety", tiles: "nowe kafle",
      square: "kwadrat", total: "kafle", year: "w tym roku", rides: "jazdy", routes: "Zaplanowane trasy", moments: "Momenty", updated: "aktualizacja {s} s temu",
      noSignal: "brak sygnału od {m} min", offRoute: "poza trasą", distance: "dystans", progress: "postęp", noRoutes: "Nie masz jeszcze zapisanych tras.", open: "Pełny ekran",
      mStarted: "Start", mFinished: "Koniec jazdy", mTiles: "+{n} nowych kafli", mSquare: "Nowy kwadrat {from}×{from} → {to}×{to}", mOff: "Zjazd z trasy", mBack: "Z powrotem na trasie",
      loading: "Wczytywanie…", error: "Gridhunt jest niedostępny.", km: "km",
      play: "Odtwórz wybrane lata", pause: "Pauza", allYearsLong: "Wszystkie lata", years: "Lata", moreYears: "Więcej lat",
      visited: "Odwiedzone", newIn: "Nowe w {y}", record: "Rekord", position: "Pozycja osi czasu", stepLabel: "Gradacja odtwarzania", speedLabel: "Prędkość odtwarzania",
      step_day: "Dzień", step_week: "Tydzień", step_month: "Miesiąc", step_quarter: "Kwartał", step_year: "Rok", quarter: "{r} kw. {y}",
      modeYears: "Tylko te lata", modeCum: "Cała kolekcja", modeYearsHelp: "<b>Tylko te lata</b>: kafle z jazd w zaznaczonych latach.",
      modeCumHelp: "<b>Cała kolekcja</b>: wszystkie kafle zdobyte do ostatniego zaznaczonego roku. Przy jednym roku bursztyn pokazuje kafle zdobyte w nim po raz pierwszy.",
      tapHelp: "Dotknij rok, aby go dodać. Dotknij zaznaczony rok, aby zostawić tylko jego.",
      base: "Podkład", baseSimple: "Prosty", baseDetailed: "Szczegółowy", overlays: "Nakładki", ovTiles: "Moje kafle", ovGoals: "Kwadrat i cel",
      kOwned: "zdobyte", kNew: "nowe w {y}", kSquare: "kwadrat", kTarget: "cel",
      gestWin: "Użyj Ctrl + przewijania, aby przybliżyć mapę", gestMac: "Użyj ⌘ + przewijania, aby przybliżyć mapę", gestMobile: "Przesuń mapę dwoma palcami",
      sView: "Gridhunt", sLive: "Jazda na żywo", sRide: "Bieżąca jazda", sAccount: "Konto", sRiding: "Jadę", sRideDistance: "Dystans",
      sDone: "Przejechane", sLeft: "Do mety", sProgress: "Postęp trasy", sNewRide: "Nowe kafle", sTiles: "Kafle", sSquare: "Kwadrat",
      sNewYear: "Nowe w tym roku", sLastRide: "Ostatnia jazda", sNoData: "Nie znaleziono encji Gridhunt. Najpierw dodaj integrację Gridhunt.",
      sDesc: "Jazda na żywo, kafle i kwadrat z Gridhunt w jednym widoku.",
    },
  };
  const fmt = (s, o) => String(s).replace(/\{(\w+)\}/g, (_, k) => String(o[k] ?? ""));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const Z = 2 ** 14;
  /** Gridhunt mark (variant C, geometry from apps/web/src/lib/brand/mark.tsx, tight frame): tile, current square, target. */
  const LOGO = '<svg class="logo" viewBox="17 16 67 67" aria-hidden="true"><rect x="18" y="55" width="27" height="27" rx="2" style="fill:var(--gh-logo-tile)"/><path d="M18 41H59V82" style="fill:none;stroke:var(--gh-logo-square);stroke-width:14"/><path d="M18 22.5H77.5V82" style="fill:none;stroke:var(--gh-logo-target);stroke-width:11;stroke-dasharray:22.31 14.88 44.62 14.88 22.31 1000"/></svg>';

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

  /* ---- History timeline: port of apps/ios/Sources/Timeline.swift + YearFilter.swift (same as web lib/timeline.ts) ---- */
  const NEVER = 2147483647;
  const isLeap = (y) => (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
  const monthLens = (y) => [31, isLeap(y) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  function todayOf(now = new Date()) {
    const y = now.getFullYear();
    return { year: y, doy: Math.round((Date.UTC(y, now.getMonth(), now.getDate()) - Date.UTC(y, 0, 1)) / 864e5) + 1 };
  }
  const lastDay = (y, td) => (y === td.year ? td.doy : isLeap(y) ? 366 : 365);
  const STEPS = ["day", "week", "month", "quarter", "year"];
  const TL = {
    total: (ys, td) => ys.reduce((a, y) => a + lastDay(y, td), 0),
    playhead(pos, ys, td) {
      let p = Math.max(1, Math.min(pos, TL.total(ys, td)));
      for (const y of ys) { const n = lastDay(y, td); if (p <= n) return { year: y, doy: p }; p -= n; }
      const l = ys[ys.length - 1];
      return l == null ? { year: td.year, doy: 1 } : { year: l, doy: lastDay(l, td) };
    },
    positionOf(year, doy, ys, td) {
      let p = 0;
      for (const y of ys) { const n = lastDay(y, td); if (y === year) return p + Math.max(1, Math.min(doy, n)); p += n; }
      return Math.max(1, p);
    },
    monthEnd(y, m0) { const L = monthLens(y); let s = 0; for (let m = 0; m <= Math.max(0, Math.min(11, m0)); m++) s += L[m]; return s; },
    month0(y, doy) { let acc = 0; const L = monthLens(y); for (let m = 0; m < 12; m++) { acc += L[m]; if (doy <= acc) return m; } return 11; },
    /** Next play position for `step` (each tick closes the current unit, then jumps to the end of the next one). */
    advance(pos, step, ys, td) {
      const total = TL.total(ys, td);
      if (step === "day") return Math.min(total, pos + 1);
      if (step === "week") return Math.min(total, pos + 7);
      const ph = TL.playhead(pos, ys, td), yEnd = lastDay(ph.year, td), idx = ys.indexOf(ph.year);
      const at = (y, d) => TL.positionOf(y, d, ys, td);
      if (step === "year") {
        if (ph.doy >= yEnd) { if (idx + 1 < ys.length) { const ny = ys[idx + 1]; return Math.min(total, at(ny, lastDay(ny, td))); } return total; }
        return Math.min(total, at(ph.year, yEnd));
      }
      const m0 = TL.month0(ph.year, ph.doy), unitEnd = step === "month" ? m0 : m0 - (m0 % 3) + 2;
      const end = Math.min(yEnd, TL.monthEnd(ph.year, unitEnd));
      if (ph.doy < end) return at(ph.year, end);
      if (ph.doy >= yEnd) {
        if (idx + 1 >= ys.length) return total;
        const ny = ys[idx + 1];
        return Math.min(total, at(ny, Math.min(lastDay(ny, td), TL.monthEnd(ny, step === "month" ? 0 : 2))));
      }
      const nm0 = step === "month" ? m0 + 1 : unitEnd + 1;
      return at(ph.year, Math.min(yEnd, TL.monthEnd(ph.year, Math.min(11, nm0 + (step === "quarter" ? 2 : 0)))));
    },
  };
  const upperBound = (a, v) => { let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >> 1; if (a[m] <= v) lo = m + 1; else hi = m; } return lo; };
  /** Year chip tap (owner rule 2026-09-29, iOS YearFilter.tap): unselected = add, selected = keep only that year. */
  function tapYear(year, sel, avail) {
    if (!avail.includes(year)) return sel;
    if (sel.has(year)) return new Set([year]);
    return new Set([...sel, year]);
  }
  const allSelected = (sel, avail) => avail.length > 0 && avail.every((y) => sel.has(y));
  /** Tiles of the payload: first visit in history and visits per year. */
  function tileModel(tm) {
    const n = (tm.tiles || []).length / 2, firstY = new Int32Array(n), firstD = new Int32Array(n), per = {};
    for (const [ys, flat] of Object.entries(tm.visits || {})) {
      const y = Number(ys), idx = [], doy = [];
      for (let j = 0; j + 1 < flat.length; j += 2) {
        const i = flat[j], d = flat[j + 1];
        if (i >= n) continue;
        idx.push(i); doy.push(d);
        if (!firstY[i] || y < firstY[i] || (y === firstY[i] && d < firstD[i])) { firstY[i] = y; firstD[i] = d; }
      }
      per[y] = { idx, doy };
    }
    // neighbour grid for the record square (iOS TileGrid): row order + left / up / up-left
    const t = tm.tiles, key = (i) => t[2 * i + 1] * Z + t[2 * i], byKey = new Map();
    for (let i = 0; i < n; i++) byKey.set(key(i), i);
    const left = new Int32Array(n), up = new Int32Array(n), ul = new Int32Array(n);
    for (let i = 0; i < n; i++) { const k = key(i); left[i] = byKey.get(k - 1) ?? -1; up[i] = byKey.get(k - Z) ?? -1; ul[i] = byKey.get(k - Z - 1) ?? -1; }
    const rowOrder = Int32Array.from({ length: n }, (_, i) => i).sort((a, b) => key(a) - key(b));
    const years = Object.keys(per).map(Number).sort((a, b) => a - b);
    return { n, tiles: t, firstY, firstD, per, years, left, up, ul, rowOrder };
  }
  /** Playback index for (years, mode, today): when each tile enters the selection and when it counts as new (iOS TimelineIndex). */
  function timelineIndex(m, ys, mode, td) {
    const newYear = ys.length === 1 && m.years.length && ys[0] > m.years[0] ? ys[0] : null;
    const total = TL.total(ys, td), segStart = {}, segLen = {};
    let acc = 0;
    for (const y of ys) { segStart[y] = acc + 1; segLen[y] = lastDay(y, td); acc += segLen[y]; }
    const entry = (y, d) => {
      if (segStart[y] != null && d <= segLen[y]) return segStart[y] + Math.max(1, d) - 1;
      const ny = ys.find((v) => v > y);
      return ny != null ? segStart[ny] : NEVER;
    };
    const enter = new Int32Array(m.n).fill(NEVER), fresh = new Int32Array(m.n).fill(NEVER);
    if (newYear != null) for (let i = 0; i < m.n; i++) if (m.firstY[i] === newYear) fresh[i] = entry(newYear, m.firstD[i]);
    if (mode === "cum") {
      for (let i = 0; i < m.n; i++) if (m.firstY[i]) enter[i] = entry(m.firstY[i], m.firstD[i]);
    } else {
      for (const y of ys) {
        const p = m.per[y];
        if (!p) continue;
        for (let k = 0; k < p.idx.length; k++) {
          const t = p.idx[k], d = p.doy[k], e = d <= segLen[y] ? segStart[y] + Math.max(1, d) - 1 : entry(y, d);
          if (e < enter[t]) enter[t] = e;
        }
      }
    }
    const sortedEnter = Int32Array.from(enter.filter((e) => e !== NEVER)).sort();
    const sortedFresh = Int32Array.from(fresh.filter((e) => e !== NEVER)).sort();
    return { ys, newYear, total, enter, fresh, sortedEnter, sortedFresh };
  }
  /** Largest fully covered N×N square among tiles with enter ≤ limit (iOS TileGrid.uber). */
  function uberAt(m, ix, limit) {
    const dp = new Int32Array(m.n);
    let best = { s: 0, x: 0, y: 0 };
    for (const i of m.rowOrder) {
      if (ix.enter[i] > limit) continue;
      const l = m.left[i] >= 0 ? dp[m.left[i]] : 0, u = m.up[i] >= 0 ? dp[m.up[i]] : 0, d = m.ul[i] >= 0 ? dp[m.ul[i]] : 0;
      const s = 1 + Math.min(l, u, d);
      dp[i] = s;
      if (s > best.s) best = { s, x: m.tiles[2 * i] - s + 1, y: m.tiles[2 * i + 1] - s + 1 };
    }
    return best;
  }
  const tileLL = (x, y) => [(x / Z) * 360 - 180, (Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / Z))) * 180) / Math.PI];
  const boxRing = (x0, y0, x1, y1) => [tileLL(x0, y0), tileLL(x1 + 1, y0), tileLL(x1 + 1, y1 + 1), tileLL(x0, y1 + 1), tileLL(x0, y0)];
  const ROMAN = ["I", "II", "III", "IV"];
  const STATIC = "/gridhunt_static";
  const BASES = { simple: (dark) => `https://tiles.openfreemap.org/styles/${dark ? "dark" : "positron"}`, detailed: () => "https://tiles.openfreemap.org/styles/liberty" };
  const store = { get(k, d) { try { const v = localStorage.getItem("gridhunt-card." + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem("gridhunt-card." + k, JSON.stringify(v)); } catch { /* private mode */ } } };
  let mlPromise = null;
  /** MapLibre bundled with the integration (www/maplibre); null = no WebGL or not served (card falls back to the SVG map). */
  function loadMapLibre() {
    if (!mlPromise) mlPromise = (async () => {
      const c = document.createElement("canvas");
      if (!(c.getContext("webgl2") || c.getContext("webgl"))) return null;
      const [ml, css] = await Promise.all([import(`${STATIC}/maplibre/maplibre-gl.mjs`), fetch(`${STATIC}/maplibre/maplibre-gl.css`).then((r) => (r.ok ? r.text() : ""))]);
      const lib = ml.default || ml;
      lib.setWorkerUrl(`${STATIC}/maplibre/maplibre-gl-worker.mjs`);
      return { lib, css };
    })().catch(() => null);
    return mlPromise;
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
    connectedCallback() { if (this._hass && !this._timer) this._load(); this._fitMap(); }
    disconnectedCallback() { clearTimeout(this._timer); this._timer = null; if (this._h) this._pause(); }
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
    /* ---- Idle map: tiles on a real base map, year filter and history playback like the iOS Map screen ---- */
    _hist() {
      if (!this._h) {
        this._h = { sel: null, mode: "year", step: store.get("step", "quarter"), speed: store.get("speed", 4), pos: Infinity, playing: false,
          base: store.get("base", "detailed"), ov: store.get("ov", { tiles: true, goals: true }), layers: false, more: false };
        if (!STEPS.includes(this._h.step)) this._h.step = "quarter";
        if (![1, 2, 4, 8].includes(this._h.speed)) this._h.speed = 4;
        if (!BASES[this._h.base]) this._h.base = "detailed";
      }
      return this._h;
    }
    /** Model (per payload) and playback index (per years / mode / day), cached. */
    _histIndex() {
      const tm = this._data && this._data.tiles;
      if (!tm || !tm.view || !(tm.tiles || []).length) return null;
      const sig = `${tm.generated}|${tm.tiles.length}|${tm.tiles[0]}|${tm.tiles[tm.tiles.length - 1]}`;
      if (this._hmSig !== sig) { this._hm = tileModel(tm); this._hmSig = sig; this._ixKey = null; }
      const m = this._hm, h = this._hist();
      // keep the selection across reloads (intersection), else all years (iOS YearFilter.reconcile)
      const kept = h.sel ? m.years.filter((y) => h.sel.has(y)) : [];
      h.sel = new Set(kept.length ? kept : m.years);
      const ys = [...h.sel].sort((a, b) => a - b), td = todayOf();
      const key = `${sig}|${ys.join(",")}|${h.mode}|${td.year}-${td.doy}`;
      if (this._ixKey !== key) { this._ix = timelineIndex(m, ys, h.mode, td); this._ix.td = td; this._ixKey = key; this._uberCache = null; }
      return { m, ix: this._ix, tm };
    }
    _frameOf(m, ix) {
      const h = this._hist(), total = Math.max(ix.total, 1), pos = Math.max(1, Math.min(h.pos, total));
      const count = upperBound(ix.sortedEnter, pos), newCount = upperBound(ix.sortedFresh, pos);
      if (!this._uberCache || this._uberCache.count !== count) this._uberCache = { count, uber: uberAt(m, ix, pos) };
      return { pos, total, count, newCount, uber: this._uberCache.uber, ph: TL.playhead(pos, ix.ys, ix.td), atEnd: pos >= total };
    }
    _yearLabel(ys, avail) {
      if (ys.length === avail.length && ys.length > 1) return this.t.allYearsLong;
      if (ys.length <= 3) return ys.join(" + ");
      return `${ys[0]}…${ys[ys.length - 1]} (${ys.length})`;
    }
    _phLabel(ph, step) {
      const lang = this._hass?.locale?.language || undefined, d = new Date(Date.UTC(ph.year, 0, ph.doy));
      if (step === "year") return String(ph.year);
      if (step === "quarter") return fmt(this.t.quarter, { q: Math.floor(d.getUTCMonth() / 3) + 1, r: ROMAN[Math.floor(d.getUTCMonth() / 3)], y: ph.year });
      if (step === "month") return d.toLocaleDateString(lang, { month: "long", year: "numeric", timeZone: "UTC" });
      return d.toLocaleDateString(lang, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
    }
    /** Controls around the map (rebuilt on render); per-tick updates go through _applyFrame. */
    _histHtml() {
      const hx = this._histIndex();
      if (!hx) return "";
      const { m, ix } = hx, h = this._hist(), t = this.t, fr = this._frameOf(m, ix);
      const allOn = allSelected(h.sel, m.years), nf = new Intl.NumberFormat(this._hass?.locale?.language || undefined);
      const chip = (label, on, attr) => `<button class="ychip${on ? " on" : ""}" ${attr} aria-pressed="${on}">${on ? '<span class="ck">✓</span>' : ""}${esc(label)}</button>`;
      const chips = chip(t.allYearsLong, allOn, 'data-yall="1"') + [...m.years].reverse().map((y) => chip(String(y), h.sel.has(y) && !allOn, `data-year="${y}"`)).join("")
        + `<button class="ychip more" data-ymore="1" aria-label="${esc(t.moreYears)}">⋯</button>`;
      const more = h.more ? `<div class="morebox"><div class="seg"><button class="${h.mode === "year" ? "on" : ""}" data-mode="year">${esc(t.modeYears)}</button><button class="${h.mode === "cum" ? "on" : ""}" data-mode="cum">${esc(t.modeCum)}</button></div>
          <p>${t.modeYearsHelp}</p><p>${t.modeCumHelp}</p><p class="muted">${esc(t.tapHelp)}</p></div>` : "";
      const baseName = h.base === "simple" ? t.baseSimple : t.baseDetailed;
      const layers = h.layers ? `<div class="lpanel"><b>${esc(t.base)}</b>
          ${["simple", "detailed"].map((b) => `<label><input type="radio" name="ghbase" data-base="${b}" ${h.base === b ? "checked" : ""}> ${esc(b === "simple" ? t.baseSimple : t.baseDetailed)}</label>`).join("")}
          <b>${esc(t.overlays)}</b>
          <label><input type="checkbox" data-ov="tiles" ${h.ov.tiles ? "checked" : ""}> ${esc(t.ovTiles)}</label>
          <label><input type="checkbox" data-ov="goals" ${h.ov.goals ? "checked" : ""}> ${esc(t.ovGoals)}</label></div>` : "";
      const PLAY = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l10.5-6.5z"/></svg>', PAUSE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 5h3.6v14H7zM13.4 5H17v14h-3.6z"/></svg>';
      this._icons = { PLAY, PAUSE };
      const steps = STEPS.map((s) => `<option value="${s}" ${s === h.step ? "selected" : ""}>${esc(t["step_" + s])}</option>`).join("");
      const sw = (cls, label) => `<span class="key"><i class="${cls}"></i>${esc(label)}</span>`;
      return `<div class="ychips" role="group" aria-label="${esc(t.years)}">${chips}</div>${more}
        <div class="mapbox hist"><div id="ghmap" class="mapslot">${this._glEl ? "" : this._histSvg(m, ix, fr)}</div>
          <button class="lchip" data-layers="1" aria-expanded="${h.layers}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 2 8l10 5 10-5zm-7.6 8.2L2 12.4l10 5 10-5-2.4-1.2L12 15zm0 4.4L2 16.8l10 5 10-5-2.4-1.2L12 19.4z"/></svg>${esc(baseName)}</button>${layers}</div>
        <div class="eyebrow" id="ghlabel">${esc(this._yearLabel(ix.ys, m.years) + " · " + this._phLabel(fr.ph, h.step))}</div>
        <div class="hstats"><div><b id="ghcount">${esc(nf.format(fr.count))}</b><span>${esc(t.visited)}</span></div>
          ${ix.newYear ? `<div class="nw"><b id="ghnew">${esc(fr.newCount ? "+" + nf.format(fr.newCount) : "0")}</b><span>${esc(fmt(t.newIn, { y: ix.newYear }))}</span></div>` : ""}
          <div><b id="ghrec">${esc(fr.uber.s ? fr.uber.s + "×" + fr.uber.s : "–")}</b><span>${esc(t.record)}</span></div></div>
        <div class="tlbar"><button class="playc" data-tplay="1" aria-label="${esc(h.playing ? t.pause : t.play)}">${h.playing ? PAUSE : PLAY}</button>
          <input id="ghslider" type="range" min="1" max="${Math.max(fr.total, 2)}" step="1" value="${fr.pos}" aria-label="${esc(t.position)}">
          <label class="stepsel"><select id="ghstep" aria-label="${esc(t.stepLabel)}">${steps}</select></label>
          <button class="speed" data-speed="1" aria-label="${esc(t.speedLabel)}">×${h.speed}</button></div>
        <div class="legend">${sw("k-own", t.kOwned)}${ix.newYear ? sw("k-new", fmt(t.kNew, { y: ix.newYear })) : ""}${sw("k-sq", t.kSquare)}${this._data.tiles.target ? sw("k-tgt", t.kTarget) : ""}</div>`;
    }
    _bindHist(root) {
      const h = this._hist(), q = (s) => root.querySelectorAll(s);
      const avail = () => (this._hm ? this._hm.years : []);
      const reset = () => { this._pause(); h.pos = Infinity; this._render(); };
      q("[data-yall]").forEach((b) => b.addEventListener("click", () => { h.sel = new Set(avail()); reset(); }));
      q("[data-year]").forEach((b) => b.addEventListener("click", () => { h.sel = tapYear(Number(b.dataset.year), h.sel, avail()); reset(); }));
      q("[data-ymore]").forEach((b) => b.addEventListener("click", () => { h.more = !h.more; this._render(); }));
      q("[data-mode]").forEach((b) => b.addEventListener("click", () => { h.mode = b.dataset.mode; reset(); }));
      q("[data-layers]").forEach((b) => b.addEventListener("click", () => { h.layers = !h.layers; this._render(); }));
      q("[data-base]").forEach((b) => b.addEventListener("change", () => { h.base = b.dataset.base; store.set("base", h.base); this._glStyle(); this._render(); }));
      q("[data-ov]").forEach((b) => b.addEventListener("change", () => { h.ov = { ...h.ov, [b.dataset.ov]: b.checked }; store.set("ov", h.ov); this._glVisibility(); this._applyFrame(); }));
      q("[data-tplay]").forEach((b) => b.addEventListener("click", () => this._togglePlay()));
      q("[data-speed]").forEach((b) => b.addEventListener("click", () => {
        h.speed = h.speed >= 8 ? 1 : h.speed * 2; store.set("speed", h.speed); b.textContent = "×" + h.speed;
        if (h.playing) this._schedule();
      }));
      const step = root.getElementById("ghstep");
      if (step) step.addEventListener("change", () => { h.step = step.value; store.set("step", h.step); this._applyFrame(); });
      const sl = root.getElementById("ghslider");
      if (sl) sl.addEventListener("input", () => { this._pause(); h.pos = Number(sl.value); this._applyFrame(); });
      const slot = root.getElementById("ghmap");
      if (slot) this._mountMap(slot);
      this._glStyle();
      if (this._glReady) this._applyFrame();
    }
    _togglePlay() {
      const h = this._hist(), ix = this._ix;
      if (h.playing) { this._pause(); this._applyFrame(); return; }
      if (!ix || !ix.total) return;
      if (h.pos >= ix.total) h.pos = 1;
      h.playing = true;
      this._schedule();
      this._applyFrame();
    }
    _schedule() {
      clearInterval(this._playTimer);
      this._playTimer = setInterval(() => this._tick(), Math.max(45, 150 / Math.max(this._hist().speed, 1)));
    }
    _pause() { const h = this._hist(); h.playing = false; clearInterval(this._playTimer); this._playTimer = null; }
    _tick() {
      const h = this._hist(), ix = this._ix, total = ix ? ix.total : 0;
      if (!h.playing || !total) { this._pause(); this._applyFrame(); return; }
      const cur = Math.min(h.pos, total);
      h.pos = TL.advance(cur >= total ? 0 : cur, h.step, ix.ys, ix.td);
      if (h.pos >= total) this._pause();
      this._applyFrame();
    }
    /** Per-tick update: texts, slider, play icon and the map (GL filters or SVG redraw). */
    _applyFrame() {
      const root = this.shadowRoot, hx = this._histIndex();
      if (!root || !hx) return;
      const { m, ix } = hx, h = this._hist(), fr = this._frameOf(m, ix), nf = new Intl.NumberFormat(this._hass?.locale?.language || undefined);
      const set = (id, v) => { const e = root.getElementById(id); if (e && e.textContent !== v) e.textContent = v; };
      set("ghlabel", this._yearLabel(ix.ys, m.years) + " · " + this._phLabel(fr.ph, h.step));
      set("ghcount", nf.format(fr.count));
      set("ghnew", fr.newCount ? "+" + nf.format(fr.newCount) : "0");
      set("ghrec", fr.uber.s ? fr.uber.s + "×" + fr.uber.s : "–");
      const sl = root.getElementById("ghslider");
      if (sl) { sl.max = String(Math.max(fr.total, 2)); sl.value = String(fr.pos); }
      const pb = root.querySelector("[data-tplay]");
      if (pb && this._icons) { const want = h.playing ? "pause" : "play"; if (pb.dataset.icon !== want) { pb.dataset.icon = want; pb.innerHTML = h.playing ? this._icons.PAUSE : this._icons.PLAY; pb.setAttribute("aria-label", h.playing ? this.t.pause : this.t.play); } }
      if (this._map && this._glReady) this._glFrame(fr);
      else { const slot = root.getElementById("ghmap"); if (slot && !this._glEl) slot.innerHTML = this._histSvg(m, ix, fr); }
    }
    /** SVG fallback (no WebGL, or while MapLibre loads): same tiles, square and target without a base map. */
    _histSvg(m, ix, fr, w = 640) {
      const v = this._data.tiles.view, h = this._hist();
      const ar = (v.y1 - v.y0 + 1) / (v.x1 - v.x0 + 1), H = Math.round(Math.min(480, Math.max(220, w * ar)));
      const ll = (x, y) => { const [lo, la] = tileLL(x, y); return [la, lo]; };
      const proj = projection([ll(v.x0, v.y0), ll(v.x1 + 1, v.y1 + 1)], w, H, 8);
      if (!proj) return "";
      this._tproj = proj;
      let rects = "";
      if (h.ov.tiles) for (let i = 0; i < m.n; i++) {
        if (ix.enter[i] > fr.pos) continue;
        const [x0, y0, s] = proj.tile(m.tiles[2 * i], m.tiles[2 * i + 1]);
        if (x0 + s < 0 || y0 + s < 0 || x0 > w || y0 > H) continue;
        rects += `<rect class="own${ix.fresh[i] <= fr.pos ? " nw" : ""}" x="${x0.toFixed(1)}" y="${y0.toFixed(1)}" width="${s.toFixed(1)}" height="${s.toFixed(1)}"/>`;
      }
      const tg = this._data.tiles.target, sq = fr.uber;
      const goals = h.ov.goals ? (tg ? this._boxSvg(tg.x0, tg.y0, tg.x1, tg.y1, "tgt", `${tg.x1 - tg.x0 + 1}×${tg.y1 - tg.y0 + 1}`) : "")
        + (sq.s ? this._boxSvg(sq.x, sq.y, sq.x + sq.s - 1, sq.y + sq.s - 1, "sq", `${sq.s}×${sq.s}`) : "") : "";
      return `<svg class="map tilesmap" viewBox="0 0 ${w} ${H}" role="img">${gridSvg(proj)}<g>${rects}</g>${goals}</svg>`;
    }
    _boxSvg(x0, y0, x1, y1, cls, label) {
      const proj = this._tproj, [ax, ay] = proj.tile(x0, y0), [bx, by] = proj.tile(x1 + 1, y1 + 1);
      const lab = label ? `<text class="sqlab ${cls}" x="${(bx - 4).toFixed(1)}" y="${(cls === "sq" ? by + 16 : ay - 6).toFixed(1)}" text-anchor="end">${esc(label)}</text>` : "";
      return `<rect class="${cls}" x="${ax.toFixed(1)}" y="${ay.toFixed(1)}" width="${(bx - ax).toFixed(1)}" height="${(by - ay).toFixed(1)}"/>${lab}`;
    }
    /* ---- MapLibre ---- */
    _dark() { return !!(this._hass && this._hass.themes && this._hass.themes.darkMode); }
    _baseStyle() { const h = this._hist(); return (BASES[h.base] || BASES.detailed)(this._dark()); }
    /** The GL map lives in one element kept across renders (moved into the new slot). */
    async _mountMap(slot) {
      if (this._config.basemap === "none") return;
      if (this._glEl) { if (this._glEl.parentNode !== slot) { slot.innerHTML = ""; slot.appendChild(this._glEl); this._fitMap(); } return; }
      if (this._glLoading) return;
      this._glLoading = true;
      const ml = await loadMapLibre();
      if (!ml || !this.shadowRoot || !this._histIndex()) { this._glLoading = false; return; }
      const v = this._data.tiles.view, el = document.createElement("div");
      el.className = "glwrap";
      el.innerHTML = `<style>${ml.css}</style><div class="glmap"></div>`;
      const cur = this.shadowRoot.getElementById("ghmap") || slot;
      cur.innerHTML = "";
      cur.appendChild(el);
      this._glEl = el;
      const [w, n] = tileLL(v.x0, v.y0), [e, s] = tileLL(v.x1 + 1, v.y1 + 1), t = this.t;
      try {
        const map = new ml.lib.Map({
          container: el.querySelector(".glmap"), style: this._baseStyle(), bounds: [[w, s], [e, n]], fitBoundsOptions: { padding: 16 },
          attributionControl: { compact: true }, cooperativeGestures: true, dragRotate: false, pitchWithRotate: false, touchPitch: false, maxZoom: 17,
          locale: { "CooperativeGesturesHandler.WindowsHelpText": t.gestWin, "CooperativeGesturesHandler.MacHelpText": t.gestMac, "CooperativeGesturesHandler.MobileHelpText": t.gestMobile },
        });
        map.touchZoomRotate.disableRotation();
        map.addControl(new ml.lib.NavigationControl({ showCompass: false }), "top-right");
        map.on("style.load", () => { this._glReady = true; this._glLayers(); });
        this._map = map;
        this._glStyleUrl = this._baseStyle();
        // The card re-renders its shadow DOM on every filter tap and HA hides/shows views; keep the canvas sized to the slot.
        if (window.ResizeObserver) { this._ro = new ResizeObserver(() => this._fitMap(true)); this._ro.observe(el); }
      } catch (err) {
        this._glEl = null; this._map = null; this._config = { ...this._config, basemap: "none" };
        this._render();
      }
      this._glLoading = false;
    }
    /** Resize the GL canvas to its slot now and after layout settles (Safari/HA report the size late after a move). */
    _fitMap(now) {
      const map = this._map;
      if (!map) return;
      const fit = () => { if (this._map === map && this._glEl && this._glEl.isConnected && this._glEl.clientWidth) { map.resize(); map.triggerRepaint(); } };
      fit();
      if (now) return;
      requestAnimationFrame(() => { fit(); requestAnimationFrame(fit); });
      setTimeout(fit, 250);
    }
    _glStyle() {
      if (!this._map) return;
      const url = this._baseStyle();
      if (url === this._glStyleUrl) return;
      this._glStyleUrl = url;
      this._glReady = false;
      this._map.setStyle(url, { diff: false });
    }
    _glColors() {
      const dark = this._dark();
      return { own: dark ? "#5b7bff" : "#2447e0", ownA: dark ? 0.55 : 0.42, nw: "#d98e04", nwLine: dark ? "#f0b43c" : "#8a5a00", sq: "#f5b82e", tgt: dark ? "#22c55e" : "#168a40" };
    }
    _glLayers() {
      const map = this._map, hx = this._histIndex();
      if (!map || !hx) return;
      const c = this._glColors();
      if (!map.getSource("gh-tiles")) map.addSource("gh-tiles", { type: "geojson", data: { type: "FeatureCollection", features: [] }, buffer: 0, tolerance: 0 });
      if (!map.getSource("gh-goals")) map.addSource("gh-goals", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      if (!map.getLayer("gh-tiles")) map.addLayer({ id: "gh-tiles", type: "fill", source: "gh-tiles", paint: { "fill-color": c.own, "fill-opacity": c.ownA, "fill-antialias": false } });
      if (!map.getLayer("gh-new")) map.addLayer({ id: "gh-new", type: "line", source: "gh-tiles", paint: { "line-color": c.nwLine, "line-width": 0.75 } });
      if (!map.getLayer("gh-tgt")) map.addLayer({ id: "gh-tgt", type: "line", source: "gh-goals", filter: ["==", ["get", "k"], "tgt"], paint: { "line-color": c.tgt, "line-width": 3, "line-dasharray": [3, 2] } });
      if (!map.getLayer("gh-sq")) map.addLayer({ id: "gh-sq", type: "line", source: "gh-goals", filter: ["==", ["get", "k"], "sq"], paint: { "line-color": c.sq, "line-width": 3 } });
      this._glDataKey = null;
      this._glVisibility();
      this._applyFrame();
    }
    _glVisibility() {
      const map = this._map, h = this._hist();
      if (!map || !this._glReady) return;
      const vis = (on) => (on ? "visible" : "none");
      for (const id of ["gh-tiles", "gh-new"]) if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", vis(h.ov.tiles));
      for (const id of ["gh-tgt", "gh-sq"]) if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", vis(h.ov.goals));
    }
    _glFrame(fr) {
      const map = this._map, hx = this._histIndex();
      if (!map || !hx || !map.getSource("gh-tiles")) return;
      const { m, ix } = hx, c = this._glColors();
      if (this._glDataKey !== this._ixKey) {
        this._glDataKey = this._ixKey;
        const features = [];
        for (let i = 0; i < m.n; i++) {
          if (ix.enter[i] === NEVER) continue;
          const x = m.tiles[2 * i], y = m.tiles[2 * i + 1];
          features.push({ type: "Feature", properties: { e: ix.enter[i], f: ix.fresh[i] }, geometry: { type: "Polygon", coordinates: [boxRing(x, y, x, y)] } });
        }
        map.getSource("gh-tiles").setData({ type: "FeatureCollection", features });
        this._glSq = null;
      }
      const L = fr.pos, isNew = ["<=", ["get", "f"], L];
      map.setFilter("gh-tiles", ["<=", ["get", "e"], L]);
      map.setFilter("gh-new", ["all", ["<=", ["get", "e"], L], isNew]);
      map.setPaintProperty("gh-tiles", "fill-color", ["case", isNew, c.nw, c.own]);
      map.setPaintProperty("gh-tiles", "fill-opacity", ["case", isNew, 0.78, c.ownA]);
      const sq = fr.uber, tg = this._data.tiles.target, sqKey = `${sq.s}|${sq.x}|${sq.y}`;
      if (this._glSq !== sqKey) {
        this._glSq = sqKey;
        const f = [];
        if (tg) f.push({ type: "Feature", properties: { k: "tgt" }, geometry: { type: "LineString", coordinates: boxRing(tg.x0, tg.y0, tg.x1, tg.y1) } });
        if (sq.s) f.push({ type: "Feature", properties: { k: "sq" }, geometry: { type: "LineString", coordinates: boxRing(sq.x, sq.y, sq.x + sq.s - 1, sq.y + sq.s - 1) } });
        map.getSource("gh-goals").setData({ type: "FeatureCollection", features: f });
      }
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
      this.toggleAttribute("dark", this._dark());
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
          const tilesMap = this._histHtml();
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
            ${tilesMap}
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
      if (this._data && !(this._data.state || {}).riding && this._data.tiles) this._bindHist(this.shadowRoot);
      for (const ext of this._ext()) if (ext.bind) ext.bind(this.shadowRoot, this._data, this._ctx());
    }
  }
  GridhuntCard.css = `
    :host{--gh-logo-tile:#2447e0;--gh-logo-square:#a87a00;--gh-logo-target:#15803d;--gh-accent:var(--primary-color,#2447e0);--gh-mark-tile:#5b7bff;--gh-square:#f5b82e;--gh-target:#22c55e;--gh-tile:#e69f00;--gh-live:#d6336c;
      --gh-own:#2447e0;--gh-new:#d98e04;--gh-new-line:#8a5a00;--gh-new-ink:#9a6400;--gh-accent-wash:color-mix(in srgb,var(--gh-accent) 14%,var(--card-background-color,#fff));--gh-accent-ink:color-mix(in srgb,var(--gh-accent) 75%,#000)}
    :host([dark]){--gh-logo-tile:#5b7bff;--gh-logo-square:#f5b82e;--gh-logo-target:#22c55e;--gh-own:#5b7bff;--gh-new-line:#f0b43c;--gh-new-ink:#f0b43c;--gh-accent-ink:color-mix(in srgb,var(--gh-accent) 60%,#fff)}
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
    .own{fill:var(--gh-own);fill-opacity:.42;stroke:none}
    .sq{fill:none;stroke:var(--gh-square);stroke-width:3}.tgt{fill:none;stroke:var(--gh-target);stroke-width:3;stroke-dasharray:10 6}
    .sqlab{font:700 13px sans-serif;stroke:none}.sqlab.sq{fill:var(--gh-square)}.sqlab.tgt{fill:var(--gh-target)}
    svg.tilesmap{max-height:min(60vh,480px)}.own.nw{fill:var(--gh-new);fill-opacity:.78;stroke:var(--gh-new-line);stroke-width:.75}
    .ychips{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding:4px 0;margin:6px -16px 0;padding-left:16px;padding-right:16px;
      -webkit-mask:linear-gradient(90deg,transparent 0,#000 16px,#000 calc(100% - 24px),transparent);mask:linear-gradient(90deg,transparent 0,#000 16px,#000 calc(100% - 24px),transparent)}
    .ychips::-webkit-scrollbar{display:none}
    .ychip{flex:none;display:inline-flex;align-items:center;gap:4px;min-height:32px;padding:0 12px;border-radius:999px;cursor:pointer;white-space:nowrap;
      font:500 13px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--secondary-text-color);background:var(--card-background-color,#fff);border:1px solid var(--divider-color,rgba(127,127,127,.3))}
    .ychip.on{font-weight:600;color:var(--gh-accent-ink);background:var(--gh-accent-wash);border-color:color-mix(in srgb,var(--gh-accent) 55%,transparent)}
    .ychip .ck{font-size:11px;font-weight:800}.ychip.more{min-width:44px;justify-content:center;font-weight:700}
    .morebox{margin:6px 0;padding:10px 12px;border-radius:12px;background:var(--secondary-background-color,rgba(127,127,127,.08));font-size:.85em}.morebox p{margin:6px 0}
    .seg{display:flex;border-radius:10px;padding:2px;background:var(--divider-color,rgba(127,127,127,.2));gap:2px}
    .seg button{flex:1;border:0;border-radius:8px;padding:6px 8px;background:none;color:inherit;font:inherit;cursor:pointer}.seg button.on{background:var(--card-background-color,#fff);font-weight:700;box-shadow:0 1px 3px rgba(0,0,0,.15)}
    .mapbox.hist{position:relative}.mapslot{min-height:220px}.glwrap,.glmap{width:100%;height:min(60vh,440px)}.glmap{position:relative}
    .lchip{position:absolute;left:10px;top:10px;z-index:3;display:inline-flex;align-items:center;gap:6px;min-height:34px;padding:0 12px;border-radius:999px;cursor:pointer;
      font:600 13px sans-serif;color:var(--primary-text-color,#111);background:color-mix(in srgb,var(--card-background-color,#fff) 88%,transparent);border:1px solid var(--divider-color,rgba(127,127,127,.3));box-shadow:0 2px 8px rgba(0,0,0,.15);backdrop-filter:blur(8px)}
    .lchip svg{width:16px;height:16px;fill:currentColor}
    .lpanel{position:absolute;left:10px;top:50px;z-index:3;display:flex;flex-direction:column;gap:6px;min-width:190px;padding:10px 12px;border-radius:12px;font-size:.9em;
      background:var(--card-background-color,#fff);color:var(--primary-text-color,#111);border:1px solid var(--divider-color,rgba(127,127,127,.3));box-shadow:0 6px 20px rgba(0,0,0,.2)}
    .lpanel b{font-size:.75em;text-transform:uppercase;letter-spacing:.06em;color:var(--secondary-text-color);margin-top:4px}.lpanel label{display:flex;align-items:center;gap:8px;cursor:pointer}
    .eyebrow{font-size:.75em;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--secondary-text-color);margin:10px 0 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .hstats{display:flex;gap:16px;align-items:flex-start}.hstats div{display:flex;flex-direction:column}.hstats b{font-size:1.5em;font-weight:800;font-variant-numeric:tabular-nums;line-height:1.15}
    .hstats span{font-size:.8em;color:var(--secondary-text-color)}.hstats .nw b{color:var(--gh-new-ink)}
    .tlbar{display:flex;align-items:center;gap:8px;margin:6px 0 2px}
    .playc{flex:none;width:44px;height:44px;border:0;padding:4px;background:none;cursor:pointer;display:grid;place-items:center}
    .playc svg{width:36px;height:36px;border-radius:50%;padding:9px;box-sizing:border-box;background:var(--primary-text-color,#111);fill:var(--card-background-color,#fff)}
    #ghslider{flex:1;min-width:60px;accent-color:var(--gh-accent);height:32px}
    .stepsel select,.speed{min-height:32px;border-radius:999px;border:1px solid var(--divider-color,rgba(127,127,127,.3));background:var(--secondary-background-color,rgba(127,127,127,.08));
      color:var(--primary-text-color,#111);font:600 13px sans-serif;padding:0 12px;cursor:pointer}
    .speed{min-width:44px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
    .legend{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:.8em;color:var(--secondary-text-color);margin:4px 0 2px}.key{display:inline-flex;align-items:center;gap:5px}
    .key i{width:10px;height:10px;border-radius:2px;display:inline-block}.k-own{background:color-mix(in srgb,var(--gh-own) 55%,transparent)}
    .k-new{background:var(--gh-new);box-shadow:inset 0 0 0 1.5px var(--gh-new-line)}.k-sq{box-shadow:inset 0 0 0 2px var(--gh-square)}.k-tgt{border:2px dashed var(--gh-target);box-sizing:border-box}
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
  window.__ghTimeline = TL;

  if (!customElements.get("gridhunt-card")) customElements.define("gridhunt-card", GridhuntCard);
  window.customCards = window.customCards || [];
  if (!window.customCards.some((c) => c.type === "gridhunt-card")) {
    window.customCards.push({ type: "gridhunt-card", name: "Gridhunt", description: "Live ride, tiles, square and planned routes from Gridhunt." });
  }

  /* ---- Dashboard / view strategy (custom:gridhunt) ---- */
  const tr = (hass) => I18N[String(hass?.locale?.language || hass?.language || "en").slice(0, 2)] || I18N.en;
  /** Entity role by registry translation_key (sensor.py, binary_sensor.py, device_tracker.py); entity_id suffix as a fallback. */
  const ROLES = { riding: "riding", position: "position", progress_pct: "progress", distance_done_km: "done", distance_left_km: "left",
    distance_km: "rideDistance", new_tiles: "newRide", square: "square", tiles_total: "tiles", tiles_this_year: "newYear", last_ride: "lastRide" };
  function roleOf(reg) {
    const k = reg.translation_key;
    if (k && ROLES[k]) return ROLES[k];
    const id = String(reg.entity_id || "");
    for (const key of Object.keys(ROLES).sort((a, b) => b.length - a.length)) if (id.endsWith("_" + key)) return ROLES[key];
    return null;
  }
  /** Gridhunt accounts found in hass.entities: [{ device_id, name, roles: {role: entity_id}, extra: [entity_id] }]. */
  function strategyAccounts(hass, onlyDevice) {
    const by = new Map();
    for (const reg of Object.values(hass?.entities || {})) {
      if (reg.platform !== "gridhunt" || reg.hidden || !hass.states?.[reg.entity_id]) continue;
      const dev = reg.device_id || "";
      if (onlyDevice && dev !== onlyDevice) continue;
      if (!by.has(dev)) {
        const d = hass.devices?.[dev];
        by.set(dev, { device_id: dev, name: d?.name_by_user || d?.name || "Gridhunt", entry_id: d?.config_entries?.[0], roles: {}, extra: [] });
      }
      const a = by.get(dev), role = roleOf(reg);
      if (role && !a.roles[role]) a.roles[role] = reg.entity_id;
      else if (!role && reg.entity_id.startsWith("sensor.")) a.extra.push(reg.entity_id);
    }
    return [...by.values()].sort((x, y) => x.name.localeCompare(y.name));
  }
  const ghTile = (entity, name) => ({ type: "tile", entity, ...(name ? { name } : {}), grid_options: { columns: 6 } });
  const ghHeading = (heading, icon) => ({ type: "heading", heading, heading_style: "title", icon });
  function strategyView(config, hass) {
    const t = tr(hass), accounts = strategyAccounts(hass, config?.device_id), many = accounts.length > 1;
    if (!accounts.length) return { type: "sections", max_columns: 3, sections: [{ type: "grid", cards: [{ type: "markdown", content: t.sNoData }] }] };
    const badges = [], sections = [];
    for (const a of accounts) {
      const r = a.roles, pre = many ? a.name + ": " : "", live = [], ride = [], acct = [];
      if (r.riding) badges.push({ type: "entity", entity: r.riding, show_name: true, color: "green" });
      for (const k of ["tiles", "square"]) if (r[k]) badges.push({ type: "entity", entity: r[k], show_name: true });
      live.push(ghHeading(pre + t.sLive, "mdi:map-marker-path"));
      live.push({ type: "custom:gridhunt-card", map: "live-page", ...(many && a.entry_id ? { entry_id: a.entry_id } : {}), grid_options: { columns: "full" } });
      if (r.position) live.push({ type: "map", entities: [{ entity: r.position }], hours_to_show: 12, default_zoom: 14, auto_fit: true, grid_options: { rows: 8 } });
      sections.push({ type: "grid", column_span: 2, cards: live });
      for (const [k, n] of [["riding", "sRiding"], ["rideDistance", "sRideDistance"], ["done", "sDone"], ["left", "sLeft"], ["progress", "sProgress"], ["newRide", "sNewRide"]])
        if (r[k]) ride.push(ghTile(r[k], t[n]));
      for (const [k, n] of [["tiles", "sTiles"], ["square", "sSquare"], ["newYear", "sNewYear"], ["lastRide", "sLastRide"]]) if (r[k]) acct.push(ghTile(r[k], t[n]));
      for (const e of a.extra) acct.push(ghTile(e));
      const cards = [];
      if (ride.length) cards.push(ghHeading(pre + t.sRide, "mdi:bike-fast"), ...ride);
      if (acct.length) cards.push(ghHeading(pre + t.sAccount, "mdi:grid"), ...acct);
      if (cards.length) sections.push({ type: "grid", cards });
    }
    return { type: "sections", max_columns: 3, badges, sections };
  }
  function strategyDashboard(config, hass) {
    const t = tr(hass), view = { title: t.sView, path: "gridhunt", icon: "mdi:bike", strategy: { type: "custom:gridhunt", ...(config?.device_id ? { device_id: config.device_id } : {}) } };
    return { title: t.sView, views: [view] };
  }
  class GridhuntViewStrategy extends HTMLElement { static async generate(config, hass) { return strategyView(config, hass); } }
  class GridhuntDashboardStrategy extends HTMLElement { static async generate(config, hass) { return strategyDashboard(config, hass); } }
  if (!customElements.get("ll-strategy-view-gridhunt")) customElements.define("ll-strategy-view-gridhunt", GridhuntViewStrategy);
  if (!customElements.get("ll-strategy-dashboard-gridhunt")) customElements.define("ll-strategy-dashboard-gridhunt", GridhuntDashboardStrategy);
  // Picker "Community dashboards" (dashboards only; view strategies cannot be picked in the editor yet)
  window.customStrategies = window.customStrategies || [];
  if (!window.customStrategies.some((c) => c.type === "gridhunt" && c.strategyType === "dashboard")) {
    window.customStrategies.push({ type: "gridhunt", strategyType: "dashboard", name: "Gridhunt", description: I18N.en.sDesc, documentationURL: "https://github.com/gridhunt-app/home-assistant-gridhunt" });
  }
  window.gridhuntCardExtensions = window.gridhuntCardExtensions || [];
  console.info(`%c GRIDHUNT-CARD %c ${VERSION} `, "background:#2447e0;color:#fff;font-weight:700", "");
})();
