// Rebuilds the star-trails photograph as a long exposure.
// Layers: starless sky plate, animated trails (measured from the photo), tree silhouettes,
// then the photograph itself fades in once every trail has reached its full length.
(() => {
  const hero = document.querySelector('.exposure');
  if (!hero) return;
  const canvas = hero.querySelector('canvas');
  const ctx = canvas.getContext('2d');
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const DURATION = 5200;            // ms for the trails to reach full length
  const POS = { x: 0.5, y: 0.58 };  // must match object-position in style.css
  let data, map;
  // trails.json holds where each trail ends in the photo (tools/refine-trails.py); round caps reach half a
  // line width past that, so pull each end in by it.
  const width = core => Math.max(0.9, Math.min(core * 0.7, 3.5));

  function layout() {
    const dpr = Math.min(devicePixelRatio || 1, 2);
    const w = canvas.clientWidth, h = canvas.clientHeight;
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    const s = Math.max(w / data.w, h / data.h);  // object-fit: cover
    map = { s, x: (w - data.w * s) * POS.x, y: (h - data.h * s) * POS.y, dpr };
  }

  function draw(t) {
    const { s, x, y, dpr } = map;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.translate(x, y); ctx.scale(s, s);
    ctx.lineCap = 'round';
    for (const [ax, ay, bx, by, [r, g, b], peak, core] of data.segs) {
      // trails grow from their lower-left end toward the upper right
      const ex = bx + (ax - bx) * t, ey = by + (ay - by) * t;
      ctx.strokeStyle = `rgb(${r},${g},${b})`;
      ctx.lineWidth = width(core);
      ctx.shadowColor = peak > 60 ? `rgba(${r},${g},${b},.8)` : 'transparent';
      ctx.shadowBlur = peak > 60 ? 2.5 * s * dpr : 0;
      ctx.beginPath(); ctx.moveTo(bx, by); ctx.lineTo(ex, ey); ctx.stroke();
    }
  }

  function develop() { done = true; hero.classList.add('developed'); }

  async function start() {
    data = await (await fetch(hero.dataset.trails)).json();
    for (const seg of data.segs) {
      const [ax, ay, bx, by, , , core] = seg;
      const len = Math.hypot(bx - ax, by - ay);
      const k = Math.min(width(core) / 2, len * 0.4) / len;  // at most 40% per end, so no trail inverts
      const dx = (bx - ax) * k, dy = (by - ay) * k;
      seg[0] = ax + dx; seg[1] = ay + dy; seg[2] = bx - dx; seg[3] = by - dy;
    }
    data.segs.sort((p, q) => p[5] - q[5]);  // faint trails first, bright ones on top
    layout();
    if (still) { draw(1); develop(); return; }
    let t0;
    const frame = now => {
      t0 ??= now;
      const t = Math.min((now - t0) / DURATION, 1);
      if (canvas.width !== Math.round(canvas.clientWidth * map.dpr) || canvas.height !== Math.round(canvas.clientHeight * map.dpr)) layout();
      draw(1 - Math.pow(1 - t, 2));
      if (t < 1) requestAnimationFrame(frame); else develop();
    };
    requestAnimationFrame(frame);
  }

  // the hero's height follows its text, so watch the canvas rather than the window
  let done = false;
  new ResizeObserver(() => { if (data && done) { layout(); draw(1); } }).observe(canvas);
  // wait for the plate so the sky and the trails appear together
  const plate = hero.querySelector('.plate');
  (plate.complete ? Promise.resolve() : new Promise(r => plate.addEventListener('load', r, { once: true }))).then(start);
})();
