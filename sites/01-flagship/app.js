'use strict';
/* ============ Daniel Yoon — flagship engine ============ */
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ---------- router (path + hash, /guide) ---------- */
const isGuidePath = () =>
  /\/guide\/?$/.test(location.pathname) || location.hash === '#/guide';

function setRoute(guide) {
  document.body.classList.toggle('guide-mode', guide);
  window.scrollTo(0, 0);
}
function navigate(guide) {
  try {
    const base = location.pathname.replace(/guide\/?$/, '');
    history.pushState({}, '', guide ? base.replace(/\/?$/, '/') + 'guide' : base || '/');
  } catch (e) {
    location.hash = guide ? '#/guide' : '';
  }
  setRoute(guide);
}
document.addEventListener('click', (e) => {
  const r = e.target.closest('[data-route]');
  if (r) {
    e.preventDefault();
    navigate(r.dataset.route === 'guide');
    return;
  }
  const s = e.target.closest('[data-scroll]');
  if (s && document.body.classList.contains('guide-mode')) {
    navigate(false); // let the default anchor jump proceed on the restored page
  }
});
addEventListener('popstate', () => setRoute(isGuidePath()));
addEventListener('hashchange', () => setRoute(isGuidePath()));
setRoute(isGuidePath());

/* ---------- nav background ---------- */
const nav = document.getElementById('nav');
addEventListener('scroll', () => nav.classList.toggle('scrolled', scrollY > 40), { passive: true });

/* ---------- marquee: duplicate for seamless loop ---------- */
const track = document.getElementById('marqueeTrack');
if (track) track.innerHTML += track.innerHTML;

/* ---------- reveal observer ---------- */
const ro = new IntersectionObserver((es) => {
  es.forEach((en) => {
    if (en.isIntersecting) { en.target.classList.add('in'); ro.unobserve(en.target); }
  });
}, { threshold: 0.12 });
document.querySelectorAll('.rv').forEach((el) => ro.observe(el));

/* ---------- stat counters ---------- */
const co = new IntersectionObserver((es) => {
  es.forEach((en) => {
    if (!en.isIntersecting) return;
    co.unobserve(en.target);
    const el = en.target, end = +el.dataset.count, t0 = performance.now(), dur = 1500;
    if (REDUCED) { el.textContent = end; return; }
    (function tick(now) {
      const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(end * e);
      if (p < 1) requestAnimationFrame(tick);
    })(t0);
  });
}, { threshold: 0.6 });
document.querySelectorAll('[data-count]').forEach((el) => co.observe(el));

/* ============ WebGL particle engine (no libraries) ============ */
(function engine() {
  const canvas = document.getElementById('stage');
  const gl = canvas.getContext('webgl', { antialias: false, alpha: true, powerPreference: 'high-performance' });
  if (!gl) { canvas.style.display = 'none'; return; }

  const MOBILE = matchMedia('(max-width: 760px)').matches;
  const N = MOBILE ? 7000 : 14000;

  /* ---- helpers ---- */
  const rnd = Math.random;
  const gauss = (k) => (rnd() + rnd() + rnd() - 1.5) * k;

  function makeShape(fill) {
    const a = new Float32Array(N * 3);
    fill(a);
    return a;
  }
  // uniformly sample a list of segments [x1,y1,z1,x2,y2,z2]
  function fillSegments(arr, i0, i1, segs, jitter) {
    const lens = segs.map((s) => Math.hypot(s[3] - s[0], s[4] - s[1], s[5] - s[2]));
    const total = lens.reduce((a, b) => a + b, 0);
    for (let i = i0; i < i1; i++) {
      let d = rnd() * total, k = 0;
      while (d > lens[k] && k < segs.length - 1) { d -= lens[k]; k++; }
      const s = segs[k], t = lens[k] ? d / lens[k] : 0, j = i * 3;
      arr[j]     = s[0] + (s[3] - s[0]) * t + gauss(jitter);
      arr[j + 1] = s[1] + (s[4] - s[1]) * t + gauss(jitter);
      arr[j + 2] = s[2] + (s[5] - s[2]) * t + gauss(jitter);
    }
  }
  // point on rounded-rect perimeter, param u in [0,1)
  function rrect(u, w, h, r) {
    const sw = w - 2 * r, sh = h - 2 * r, arc = Math.PI * r / 2;
    const L = 2 * sw + 2 * sh + 4 * arc;
    let d = u * L;
    const P = (x, y) => [x, y];
    if (d < sw) return P(-sw / 2 + d, h / 2);                       d -= sw;
    if (d < arc) { const a = Math.PI / 2 - d / r; return P(sw / 2 + Math.cos(a) * r, sh / 2 + Math.sin(a) * r); } d -= arc;
    if (d < sh) return P(w / 2, sh / 2 - d);                        d -= sh;
    if (d < arc) { const a = -d / r; return P(sw / 2 + Math.cos(a) * r, -sh / 2 + Math.sin(a) * r); } d -= arc;
    if (d < sw) return P(sw / 2 - d, -h / 2);                       d -= sw;
    if (d < arc) { const a = -Math.PI / 2 - d / r; return P(-sw / 2 + Math.cos(a) * r, -sh / 2 + Math.sin(a) * r); } d -= arc;
    if (d < sh) return P(-w / 2, -sh / 2 + d);                      d -= sh;
    const a = Math.PI + (d / r); return P(-sw / 2 + Math.cos(a) * r, sh / 2 + Math.sin(a) * r);
  }
  function fillRRect(arr, i0, i1, cx, cy, cz, w, h, r, jitter) {
    for (let i = i0; i < i1; i++) {
      const [x, y] = rrect(rnd(), w, h, r), j = i * 3;
      arr[j] = cx + x + gauss(jitter); arr[j + 1] = cy + y + gauss(jitter); arr[j + 2] = cz + gauss(jitter);
    }
  }
  function fillCircle(arr, i0, i1, cx, cy, cz, r, jitter) {
    for (let i = i0; i < i1; i++) {
      const a = rnd() * Math.PI * 2, j = i * 3;
      arr[j] = cx + Math.cos(a) * r + gauss(jitter); arr[j + 1] = cy + Math.sin(a) * r + gauss(jitter); arr[j + 2] = cz + gauss(jitter);
    }
  }
  const slice = (f) => Math.floor(N * f);

  /* ---- shape 0: torus knot ---- */
  const shpKnot = makeShape((a) => {
    for (let i = 0; i < N; i++) {
      const t = rnd() * Math.PI * 2, p = 2, q = 3;
      const R = (Math.cos(q * t) + 2) * 0.42;
      const j = i * 3;
      a[j]     = R * Math.cos(p * t) + gauss(0.075);
      a[j + 1] = R * Math.sin(p * t) + gauss(0.075);
      a[j + 2] = Math.sin(q * t) * 0.42 + gauss(0.075);
    }
  });

  /* ---- shape 1: browser frame ---- */
  const shpBrowser = makeShape((a) => {
    let i = 0;
    const frameEnd = slice(0.42);
    fillRRect(a, i, frameEnd, 0, 0, 0, 2.35, 1.55, 0.1, 0.012); i = frameEnd;
    const barEnd = slice(0.5); // top bar divider
    fillSegments(a, i, barEnd, [[-1.175, 0.52, 0, 1.175, 0.52, 0]], 0.008); i = barEnd;
    const dotsEnd = slice(0.56); // traffic dots
    const dE = Math.floor((dotsEnd - i) / 3);
    fillCircle(a, i, i + dE, -1.0, 0.645, 0, 0.032, 0.006);
    fillCircle(a, i + dE, i + 2 * dE, -0.88, 0.645, 0, 0.032, 0.006);
    fillCircle(a, i + 2 * dE, dotsEnd, -0.76, 0.645, 0, 0.032, 0.006); i = dotsEnd;
    const urlEnd = slice(0.63); // url pill
    fillRRect(a, i, urlEnd, 0.12, 0.645, 0, 1.3, 0.13, 0.065, 0.006); i = urlEnd;
    const txtEnd = slice(0.85); // text lines, left column
    const lines = [];
    const lengths = [0.9, 0.75, 0.85, 0.6, 0.8];
    lengths.forEach((L, k) => lines.push([-1.02, 0.28 - k * 0.17, 0, -1.02 + L, 0.28 - k * 0.17, 0]));
    fillSegments(a, i, txtEnd, lines, 0.008); i = txtEnd;
    // media block right with diagonal
    fillRRect(a, i, slice(0.96), 0.62, -0.13, 0, 0.95, 0.85, 0.06, 0.008); i = slice(0.96);
    fillSegments(a, i, N, [[0.19, -0.5, 0, 1.05, 0.24, 0], [0.19, 0.24, 0, 1.05, -0.5, 0]], 0.008);
    // gentle z-curvature
    for (let k = 0; k < N; k++) a[k * 3 + 2] += Math.sin(a[k * 3] * 0.8) * 0.12;
  });

  /* ---- shape 2: bar chart ---- */
  const shpChart = makeShape((a) => {
    let i = 0;
    const floorEnd = slice(0.16);
    const fl = [];
    for (let x = -1.1; x <= 1.101; x += 0.44) fl.push([x, -0.85, -0.55, x, -0.85, 0.55]);
    for (let z = -0.55; z <= 0.551; z += 0.275) fl.push([-1.1, -0.85, z, 1.1, -0.85, z]);
    fillSegments(a, i, floorEnd, fl, 0.006); i = floorEnd;
    const heights = [0.35, 0.62, 0.48, 0.95, 0.78, 1.35, 1.08, 1.62, 0.55, 0.88, 1.2, 1.5];
    const bars = [];
    let bi = 0;
    for (let gx = 0; gx < 6; gx++) for (let gz = 0; gz < 2; gz++) {
      const x = -0.95 + gx * 0.38, z = -0.28 + gz * 0.56, h = heights[bi++ % heights.length], w = 0.13;
      const y0 = -0.85, y1 = y0 + h;
      // 4 vertical edges + top square
      bars.push([x - w, y0, z - w, x - w, y1, z - w], [x + w, y0, z - w, x + w, y1, z - w],
                [x - w, y0, z + w, x - w, y1, z + w], [x + w, y0, z + w, x + w, y1, z + w],
                [x - w, y1, z - w, x + w, y1, z - w], [x - w, y1, z + w, x + w, y1, z + w],
                [x - w, y1, z - w, x - w, y1, z + w], [x + w, y1, z - w, x + w, y1, z + w]);
    }
    fillSegments(a, i, slice(0.9), bars, 0.01); i = slice(0.9);
    // rising trend line above the bars
    const tr = [];
    let px = -0.95, py = -0.3;
    for (let k = 1; k <= 6; k++) {
      const nx = -0.95 + k * 0.38, ny = -0.3 + k * 0.17 + Math.sin(k * 2.1) * 0.08;
      tr.push([px, py, 0, nx, ny, 0]); px = nx; py = ny;
    }
    fillSegments(a, i, N, tr, 0.012);
  });

  /* ---- shape 3: cube lattice ---- */
  const shpLattice = makeShape((a) => {
    const segs = [], s = 0.21, gap = 0.62;
    for (let X = -1; X <= 1; X++) for (let Y = -1; Y <= 1; Y++) for (let Z = -1; Z <= 1; Z++) {
      const cx = X * gap, cy = Y * gap, cz = Z * gap;
      const c = [[-s,-s,-s],[s,-s,-s],[s,s,-s],[-s,s,-s],[-s,-s,s],[s,-s,s],[s,s,s],[-s,s,s]];
      const E = [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
      E.forEach(([m, n]) => segs.push([cx + c[m][0], cy + c[m][1], cz + c[m][2], cx + c[n][0], cy + c[n][1], cz + c[n][2]]));
    }
    fillSegments(a, 0, N, segs, 0.008);
  });

  /* ---- shape 4: chat bubbles ---- */
  const shpChat = makeShape((a) => {
    let i = 0;
    fillRRect(a, i, slice(0.34), -0.32, 0.42, 0.1, 1.65, 0.95, 0.28, 0.012); i = slice(0.34);
    fillSegments(a, i, slice(0.4), [[-1.0, -0.05, 0.1, -1.22, -0.38, 0.1], [-1.22, -0.38, 0.1, -0.72, -0.05, 0.1]], 0.01); i = slice(0.4);
    const tl = [[-0.9, 0.62, 0.1, 0.15, 0.62, 0.1], [-0.9, 0.42, 0.1, 0.32, 0.42, 0.1], [-0.9, 0.22, 0.1, -0.1, 0.22, 0.1]];
    fillSegments(a, i, slice(0.62), tl, 0.008); i = slice(0.62);
    fillRRect(a, i, slice(0.88), 0.52, -0.62, -0.15, 1.25, 0.72, 0.26, 0.012); i = slice(0.88);
    fillSegments(a, i, slice(0.93), [[1.02, -0.98, -0.15, 1.28, -1.24, -0.15], [1.28, -1.24, -0.15, 0.78, -0.98, -0.15]], 0.01); i = slice(0.93);
    const dE = Math.floor((N - i) / 3);
    fillCircle(a, i, i + dE, 0.28, -0.62, -0.15, 0.055, 0.008);
    fillCircle(a, i + dE, i + 2 * dE, 0.52, -0.62, -0.15, 0.055, 0.008);
    fillCircle(a, i + 2 * dE, N, 0.76, -0.62, -0.15, 0.055, 0.008);
  });

  /* ---- shape 5: relationship network (constellation shell) ---- */
  const shpNet = makeShape((a) => {
    const nodes = [];
    const NN = 26, golden = Math.PI * (3 - Math.sqrt(5));
    for (let k = 0; k < NN; k++) {
      const y = 1 - (k / (NN - 1)) * 2;
      const rr = Math.sqrt(1 - y * y), th = golden * k;
      const R = 0.95 + gauss(0.12);
      nodes.push([Math.cos(th) * rr * R, y * R * 0.85, Math.sin(th) * rr * R]);
    }
    nodes.push([0, 0, 0]); // hub
    const edges = [];
    nodes.forEach((nd, idx) => {
      if (idx === nodes.length - 1) return;
      const dists = nodes.map((o, oi) => [Math.hypot(nd[0]-o[0], nd[1]-o[1], nd[2]-o[2]), oi])
        .filter(([, oi]) => oi !== idx && oi !== nodes.length - 1).sort((x, y) => x[0] - y[0]);
      for (let e = 0; e < 2; e++) {
        const o = nodes[dists[e][1]];
        edges.push([nd[0], nd[1], nd[2], o[0], o[1], o[2]]);
      }
      if (idx % 4 === 0) edges.push([nd[0], nd[1], nd[2], 0, 0, 0]); // spokes to hub
    });
    const nodeEnd = slice(0.34), per = Math.floor(nodeEnd / nodes.length);
    nodes.forEach((nd, k) => {
      const i0 = k * per, i1 = k === nodes.length - 1 ? nodeEnd : (k + 1) * per;
      const r = k === nodes.length - 1 ? 0.11 : 0.055;
      for (let i = i0; i < i1; i++) {
        const j = i * 3;
        const u = rnd() * Math.PI * 2, v = Math.acos(2 * rnd() - 1);
        a[j] = nd[0] + Math.sin(v) * Math.cos(u) * r;
        a[j + 1] = nd[1] + Math.sin(v) * Math.sin(u) * r;
        a[j + 2] = nd[2] + Math.cos(v) * r;
      }
    });
    fillSegments(a, nodeEnd, N, edges, 0.005);
  });

  /* ---- shape 6: galaxy disc (baked tilt so it reads as a disc) ---- */
  const shpGalaxy = makeShape((a) => {
    const tilt = -0.95, ct = Math.cos(tilt), st = Math.sin(tilt);
    for (let i = 0; i < N; i++) {
      const arm = i % 3, u = rnd();
      const r = Math.sqrt(u) * 1.35;
      const ang = r * 2.4 + arm * (Math.PI * 2 / 3) + gauss(0.22 * (1 - r / 1.6));
      const x = Math.cos(ang) * r + gauss(0.02);
      const y = gauss(0.1) * (1 - r / 1.6);
      const z = Math.sin(ang) * r + gauss(0.02);
      const j = i * 3;
      a[j] = x;
      a[j + 1] = y * ct - z * st;
      a[j + 2] = y * st + z * ct;
    }
  });

  const SHAPES = [shpKnot, shpBrowser, shpChart, shpLattice, shpChat, shpNet, shpGalaxy];
  // per-shape horizontal bias in clip space (panels alternate sides)
  const OFFS = MOBILE ? [0, 0, 0, 0, 0, 0, 0] : [0, -0.42, 0.42, -0.42, 0.42, -0.42, 0];
  const HERO_OFF = MOBILE ? 0 : 0.22; // hero/ thesis text sits left, bias field right

  /* ---- GL setup ---- */
  const VS = `
attribute vec3 aFrom; attribute vec3 aTo; attribute vec4 aSeed;
uniform float uT, uTime, uAspect, uSize, uDrift, uOffN;
uniform vec2 uRot;
varying float vMix; varying float vFade;
void main(){
  float st = clamp(uT * 1.35 - aSeed.x * 0.35, 0.0, 1.0);
  float e = st * st * (3.0 - 2.0 * st);
  vec3 p = mix(aFrom, aTo, e);
  p += normalize(p + vec3(0.0001)) * sin(e * 3.14159) * 0.22 * (aSeed.y - 0.5);
  p.x += sin(uTime * 0.50 + aSeed.y * 6.283) * 0.02 * uDrift;
  p.y += cos(uTime * 0.43 + aSeed.z * 6.283) * 0.02 * uDrift;
  p.z += sin(uTime * 0.61 + aSeed.w * 6.283) * 0.02 * uDrift;
  float cy = cos(uRot.x), sy = sin(uRot.x);
  p = vec3(p.x * cy + p.z * sy, p.y, -p.x * sy + p.z * cy);
  float cx = cos(uRot.y), sx = sin(uRot.y);
  p = vec3(p.x, p.y * cx - p.z * sx, p.y * sx + p.z * cx);
  vec3 mv = p + vec3(0.0, 0.0, -2.7);
  float persp = -1.0 / mv.z;
  gl_Position = vec4(mv.x * persp / uAspect + uOffN, mv.y * persp, -mv.z * 0.1, 1.0);
  gl_PointSize = max(uSize * (0.45 + aSeed.w) * persp, 1.0);
  vMix = aSeed.z;
  vFade = smoothstep(4.4, 1.6, -mv.z);
}`;
  const FS = `
precision mediump float;
varying float vMix; varying float vFade;
uniform vec3 uColA, uColB; uniform float uAlpha;
void main(){
  vec2 uv = gl_PointCoord - 0.5;
  float d = length(uv);
  float a = smoothstep(0.5, 0.06, d);
  vec3 col = mix(uColA, uColB, vMix);
  col += vec3(0.20, 0.16, 0.11) * smoothstep(0.14, 0.0, d);
  gl_FragColor = vec4(col, a * vFade * uAlpha);
}`;
  function sh(type, src) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }
  const prog = gl.createProgram();
  gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS));
  gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
  gl.useProgram(prog);

  const U = {};
  ['uT','uTime','uAspect','uSize','uDrift','uOffN','uRot','uColA','uColB','uAlpha'].forEach(n => U[n] = gl.getUniformLocation(prog, n));
  gl.uniform3f(U.uColA, 0.87, 0.58, 0.34);   // copper
  gl.uniform3f(U.uColB, 0.55, 0.61, 0.96);   // periwinkle
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
  gl.disable(gl.DEPTH_TEST);

  const seeds = new Float32Array(N * 4);
  for (let i = 0; i < N * 4; i++) seeds[i] = rnd();
  function buf(data, dynamic) {
    const b = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, data, dynamic ? gl.DYNAMIC_DRAW : gl.STATIC_DRAW);
    return b;
  }
  let fromArr = new Float32Array(shpKnot), toArr = new Float32Array(shpKnot);
  const bFrom = buf(fromArr, true), bTo = buf(toArr, true), bSeed = buf(seeds, false);
  function attrib(name, b, size) {
    const loc = gl.getAttribLocation(prog, name);
    gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
  }
  attrib('aFrom', bFrom, 3); attrib('aTo', bTo, 3); attrib('aSeed', bSeed, 4);

  /* ---- morph state ---- */
  // architectural shapes hold a gentle oscillation; organic shapes spin
  const SPINS = [1, 0, 0, 1, 0, 1, 1];
  let curShape = 0, t = 1, offTarget = HERO_OFF, offCur = HERO_OFF;
  let dimTarget = 1, dimCur = 1, rotY = 0;
  function morphTo(idx) {
    if (idx === curShape) return;
    const eAll = Math.min(1, t) ; const e = eAll * eAll * (3 - 2 * eAll);
    for (let i = 0; i < N * 3; i++) fromArr[i] = fromArr[i] + (toArr[i] - fromArr[i]) * e;
    toArr.set(SHAPES[idx]);
    gl.bindBuffer(gl.ARRAY_BUFFER, bFrom); gl.bufferSubData(gl.ARRAY_BUFFER, 0, fromArr);
    gl.bindBuffer(gl.ARRAY_BUFFER, bTo);   gl.bufferSubData(gl.ARRAY_BUFFER, 0, toArr);
    t = REDUCED ? 1 : 0;
    curShape = idx;
    // unwind accumulated spin to within half a turn so still shapes settle level
    if (!SPINS[idx]) {
      rotY = rotY % (Math.PI * 2);
      if (rotY > Math.PI) rotY -= Math.PI * 2;
      if (rotY < -Math.PI) rotY += Math.PI * 2;
    }
  }

  /* ---- scroll → shape ---- */
  const shapeSections = [...document.querySelectorAll('[data-shape]')];
  function pickShape() {
    if (document.body.classList.contains('guide-mode')) {
      morphTo(6); offTarget = 0; dimTarget = 0.45; return;
    }
    const mid = innerHeight * 0.5;
    for (const s of shapeSections) {
      const r = s.getBoundingClientRect();
      if (r.top <= mid && r.bottom >= mid) {
        const idx = +s.dataset.shape;
        morphTo(idx);
        offTarget = MOBILE ? 0 : (s.dataset.off !== undefined ? +s.dataset.off : OFFS[idx]);
        dimTarget = s.dataset.dim !== undefined ? +s.dataset.dim : 1;
        return;
      }
    }
  }

  /* ---- sizing ---- */
  let W, H, DPR;
  function resize() {
    DPR = Math.min(devicePixelRatio || 1, 2);
    W = canvas.clientWidth; H = canvas.clientHeight;
    canvas.width = W * DPR; canvas.height = H * DPR;
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.uniform1f(U.uAspect, W / H);
    gl.uniform1f(U.uSize, H * DPR * 0.0085);
  }
  addEventListener('resize', resize);
  resize();

  /* ---- pointer parallax ---- */
  let mx = 0, my = 0, tmx = 0, tmy = 0;
  addEventListener('pointermove', (e) => {
    tmx = (e.clientX / innerWidth - 0.5);
    tmy = (e.clientY / innerHeight - 0.5);
  }, { passive: true });

  gl.uniform1f(U.uDrift, REDUCED ? 0 : 1);

  const BASE_ALPHA = MOBILE ? 0.42 : 0.52;
  let last = performance.now();
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    pickShape();
    if (t < 1) t = Math.min(1, t + dt / 1.25);
    mx += (tmx - mx) * 0.04; my += (tmy - my) * 0.04;
    offCur += (offTarget - offCur) * 0.05;
    dimCur += (dimTarget - dimCur) * 0.05;
    const time = now / 1000;
    if (!REDUCED) {
      if (SPINS[curShape]) rotY += dt * 0.07;
      else rotY += (Math.sin(time * 0.32) * 0.14 - rotY) * 0.03;
    }
    gl.uniform1f(U.uT, t);
    gl.uniform1f(U.uTime, REDUCED ? 0 : time);
    gl.uniform2f(U.uRot, rotY + mx * 0.5, -0.12 + my * 0.35);
    gl.uniform1f(U.uOffN, offCur);
    gl.uniform1f(U.uAlpha, BASE_ALPHA * dimCur);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawArrays(gl.POINTS, 0, N);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();

/* ---------- hero entrance ---------- */
addEventListener('load', () => {
  document.querySelectorAll('.hero .rv, .hero .lm').forEach((el) => el.classList.add('in'));
});
