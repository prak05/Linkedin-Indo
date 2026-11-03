// Motion + accent audit for index.html (PRD 16.5).
// Run: open index.html?audit, or paste this file into the DevTools console.
// Results print as a table and are stored on <html data-audit="..."> for headless checks.
(() => {
  const BANNED = new Set(['linear', 'ease', 'ease-in', 'ease-out']);
  const ALLOWED = new Set(['transform', 'opacity', 'clip-path', 'none']);
  const ACCENT = 'rgb(153, 27, 27)';
  const results = [];
  const report = (id, pass, detail) => results.push({ id, result: pass === null ? 'MANUAL' : pass ? 'PASS' : 'FAIL', detail });
  const toMs = (v) => v.split(',').map((s) => s.trim()).map((s) => (s.endsWith('ms') ? parseFloat(s) : parseFloat(s) * 1000));
  const fns = (v) => v.match(/cubic-bezier\([^)]*\)|steps\([^)]*\)|[a-z-]+/g) || [];
  // Shorthands containing var() keep their longhands empty in CSSOM, so parse the shorthand text:
  // each comma part is "<name|property> <duration> <curve> [<delay>]".
  const parts = (v) => (v || '').split(/,(?![^(]*\))/).map((p) => p.trim()).filter((p) => p && p !== 'none');
  const parse = (p) => {
    const times = (p.match(/(?:^|\s)(\d*\.?\d+)(ms|s)\b/g) || []).map((t) => (t.trim().endsWith('ms') ? parseFloat(t) : parseFloat(t) * 1000));
    return { name: p.split(/\s+/)[0], dur: times[0] || 0, delay: times[1] || 0, words: p.replace(/cubic-bezier\([^)]*\)|var\([^)]*\)/g, '').split(/\s+/) };
  };

  function run() {
    const sheet = [...document.styleSheets].find((s) => s.ownerNode && s.ownerNode.id === 'motion');
    const rules = [...sheet.cssRules].filter((r) => r instanceof CSSStyleRule);
    const keyframes = [...sheet.cssRules].filter((r) => r instanceof CSSKeyframesRule);

    // MO-1 / MO-2: load groups and the gaps between them
    const load = rules.filter((r) => /^\.(ld-|rail-)[\w-]+$/.test(r.selectorText) && parts(r.style.getPropertyValue('animation')).length);
    const byDelay = new Map();
    for (const r of load) {
      const d = parse(parts(r.style.getPropertyValue('animation'))[0]).delay;
      byDelay.set(d, [...(byDelay.get(d) || []), r.selectorText]);
    }
    const delays = [...byDelay.keys()].sort((a, b) => a - b);
    const gaps = delays.slice(1).map((d, i) => d - delays[i]);
    report('MO-1', delays.length >= 6, `${delays.length} distinct start times: ${delays.map((d) => `${d}ms [${byDelay.get(d).join(' ')}]`).join(', ')}`);
    report('MO-2', gaps.every((g) => g >= 50 && g <= 80), `gaps ${gaps.join(', ')} ms; drawer lines 60 ms`);

    // MO-3 / MO-4 / MO-7 over stylesheet rules
    const badFn = [], badDur = [], badProp = [];
    const checkDur = (where, d) => { if (d > 0 && !(d < 200 || (d >= 400 && d <= 600))) badDur.push(`${where} ${d}ms`); };
    for (const r of rules) {
      for (const kind of ['transition', 'animation']) {
        for (const p of parts(r.style.getPropertyValue(kind))) {
          const { name, dur, words } = parse(p);
          if (dur === 0) continue;
          for (const w of words) if (BANNED.has(w)) badFn.push(`${r.selectorText}: ${w}`);
          checkDur(r.selectorText, dur);
          if (kind === 'transition' && !ALLOWED.has(name)) badProp.push(`${r.selectorText}: ${name}`);
        }
      }
    }
    for (const k of keyframes) for (const f of k.cssRules) for (const p of f.style) if (!ALLOWED.has(p)) badProp.push(`@keyframes ${k.name}: ${p}`);

    // Runtime: every element (and its ::before/::after) that actually transitions
    let animating = 0;
    for (const el of document.querySelectorAll('*')) {
      for (const pseudo of [null, '::before', '::after']) {
        const cs = getComputedStyle(el, pseudo);
        const durs = toMs(cs.transitionDuration);
        if (!durs.some((d) => d > 0)) continue;
        animating++;
        const where = el.id ? `#${el.id}` : `${el.tagName.toLowerCase()}.${[...el.classList].join('.')}${pseudo || ''}`;
        for (const f of fns(cs.transitionTimingFunction)) if (BANNED.has(f)) badFn.push(`${where}: ${f}`);
        durs.forEach((d) => checkDur(where, d));
        for (const p of cs.transitionProperty.split(',').map((x) => x.trim())) if (!ALLOWED.has(p)) badProp.push(`${where}: ${p}`);
      }
    }
    report('MO-3', badFn.length === 0, badFn.length ? badFn.slice(0, 8).join('; ') : `no banned curves (${animating} transitioning boxes checked)`);
    report('MO-4', badDur.length === 0, badDur.length ? badDur.slice(0, 8).join('; ') : 'all durations <200 ms or 400–600 ms');

    // MO-5: heading travel
    const rise = keyframes.find((k) => k.name === 'k-rise10');
    const from = rise && rise.cssRules[0].style;
    const px = from ? parseFloat((from.transform.match(/translateY\(([\d.]+)px\)/) || [])[1]) : NaN;
    const headUses = rules.some((r) => r.selectorText === '.ld-head' && /^k-rise10\b/.test(r.style.getPropertyValue('animation')));
    report('MO-5', headUses && px >= 8 && px <= 12 && from.opacity === '0', `.ld-head rises ${px}px from opacity ${from && from.opacity}`);

    report('MO-6', null, 'MANUAL: open/close each panel; record at 60 fps; content clips, siblings slide, nothing appears in one frame');
    report('MO-7', badProp.length === 0, badProp.length ? badProp.slice(0, 8).join('; ') : 'only transform / opacity / clip-path animate');
    report('MO-8', null, 'MANUAL: Performance trace, 4x CPU throttle, load + 3 panel changes + drawer; no long frames, ≥55 fps');
    report('MO-9', null, `MANUAL: emulate prefers-reduced-motion (currently ${matchMedia('(prefers-reduced-motion: reduce)').matches ? 'ON' : 'off'}) and repeat MO-6`);

    // Accent budget: visible accent-filled boxes over viewport area
    const vw = innerWidth, vh = innerHeight;
    let area = 0;
    const clipArea = (r) => Math.max(0, Math.min(r.right, vw) - Math.max(r.left, 0)) * Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0));
    for (const el of document.querySelectorAll('*')) {
      if (getComputedStyle(el).backgroundColor === ACCENT) area += clipArea(el.getBoundingClientRect());
    }
    document.querySelectorAll('.panel[data-open]').forEach((p) => {
      const r = p.getBoundingClientRect();
      area += clipArea({ left: r.left, right: r.left + 2, top: r.top, bottom: r.bottom });
    });
    const pct = (100 * area) / (vw * vh);
    report('ACCENT', pct < 5, `${pct.toFixed(3)}% of viewport`);

    console.table(results);
    document.documentElement.dataset.audit = JSON.stringify(results);
  }

  // Wait for the load sequence (about 1 s) to settle.
  setTimeout(run, document.readyState === 'complete' ? 0 : 1800);
})();
