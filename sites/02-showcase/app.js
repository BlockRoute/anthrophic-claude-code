'use strict';
/* ============ The Yoon Lab — engine ============ */
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
const $ = (s, r) => (r || document).querySelector(s);

/* ---------- router ---------- */
const isGuide = () => /\/guide\/?$/.test(location.pathname) || location.hash === '#/guide';
function setRoute(g) {
  document.body.classList.toggle('guide-mode', g);
  window.scrollTo(0, 0);
}
document.addEventListener('click', (e) => {
  const r = e.target.closest('[data-route]');
  if (r) {
    e.preventDefault();
    if (r.dataset.route === 'guide') location.hash = '#/guide';
    else { location.hash = ''; try { history.replaceState({}, '', location.pathname); } catch (_) {} }
    setRoute(r.dataset.route === 'guide');
    return;
  }
  const s = e.target.closest('[data-scroll]');
  if (s && document.body.classList.contains('guide-mode')) { location.hash = ''; setRoute(false); }
});
addEventListener('hashchange', () => setRoute(isGuide()));
addEventListener('popstate', () => setRoute(isGuide()));
setRoute(isGuide());

/* ---------- reveals ---------- */
const ro = new IntersectionObserver((es) => es.forEach((en) => {
  if (en.isIntersecting) { en.target.classList.add('in'); ro.unobserve(en.target); }
}), { threshold: 0.12 });
document.querySelectorAll('.rv').forEach((el) => ro.observe(el));

/* ---------- ticker clock ---------- */
function tickClock() {
  const d = new Date();
  $('#tickClock').textContent = 'Lab time ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}
tickClock(); setInterval(tickClock, 1000);

/* ---------- toast ---------- */
let toastT;
function toast(html) {
  const t = $('#toast');
  t.innerHTML = html;
  t.classList.add('show');
  clearTimeout(toastT);
  toastT = setTimeout(() => t.classList.remove('show'), 3400);
}

/* ================= STATION 1 — Concierge ================= */
(function chatbot() {
  const log = $('#chatLog'), chipsEl = $('#chips'), form = $('#chatForm'), input = $('#chatInput');
  const scrollLog = () => { log.scrollTop = log.scrollHeight; };

  function addMsg(kind, html) {
    const d = document.createElement('div');
    d.className = 'msg ' + kind;
    d.innerHTML = html;
    log.appendChild(d);
    scrollLog();
    return d;
  }
  let typingEl = null;
  function showTyping() {
    typingEl = document.createElement('div');
    typingEl.className = 'typing';
    typingEl.innerHTML = '<i></i><i></i><i></i>';
    log.appendChild(typingEl); scrollLog();
  }
  function hideTyping() { if (typingEl) { typingEl.remove(); typingEl = null; } }

  function setChips(list) {
    chipsEl.innerHTML = '';
    list.forEach(([label, val]) => {
      const b = document.createElement('button');
      b.type = 'button'; b.textContent = label;
      b.addEventListener('click', () => handleUser(val || label));
      chipsEl.appendChild(b);
    });
  }

  const DAYS = ['Tue, Jul 28', 'Wed, Jul 29', 'Fri, Jul 31'];
  const TIMES = ['9:20 AM', '11:40 AM', '2:10 PM', '4:30 PM'];
  let flow = null; // null | 'day' | 'time' | {day} | 'name'
  let booking = {};

  function botSay(html, chips, delay) {
    showTyping();
    setTimeout(() => {
      hideTyping();
      addMsg('bot', html);
      if (chips) setChips(chips); else setChips(DEFAULT_CHIPS);
    }, REDUCED ? 60 : (delay || 700 + Math.min(html.length * 6, 900)));
  }

  const DEFAULT_CHIPS = [
    ['📅 Book a cleaning', 'Book a cleaning'],
    ['💳 Insurance?', 'Do you take my insurance?'],
    ['🕐 Hours & location', 'What are your hours?'],
    ['💲 Prices', 'How much is a cleaning?'],
  ];

  function handleUser(text) {
    addMsg('user', text.replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c])));
    setChips([]);
    route(text.toLowerCase());
  }

  function route(t) {
    // booking flow states
    if (flow === 'day') {
      const pick = DAYS.find((d) => t.includes(d.toLowerCase()) || t.includes(d.split(',')[0].toLowerCase()) || t.includes(d.match(/\d+/)[0]));
      if (pick) {
        booking.day = pick; flow = 'time';
        botSay(`${pick} it is. These times are open with Dr. Park:`, TIMES.map((x) => [x, x]));
        return;
      }
    }
    if (flow === 'time') {
      const pick = TIMES.find((x) => t.includes(x.toLowerCase().replace(' ', '')) || t.includes(x.toLowerCase()));
      if (pick) {
        booking.time = pick; flow = 'name';
        botSay('Perfect. What name should I put on the appointment?', []);
        return;
      }
    }
    if (flow === 'name') {
      const name = t.replace(/[^a-z\s'-]/gi, '').trim().split(/\s+/).map((w) => w[0] ? w[0].toUpperCase() + w.slice(1) : '').join(' ') || 'Guest';
      flow = null;
      botSay(`All set, ${name}! 🎉<span class="conf">CONFIRMED — Cleaning · ${booking.day} · ${booking.time} · Dr. Park<br>A reminder will text you the day before.</span>Anything else I can help with?`,
        [['💳 Insurance?', 'Do you take my insurance?'], ['🕐 Hours', 'What are your hours?'], ['🔁 Start over', 'Book a cleaning']], 900);
      toast('Concierge just <b>booked an appointment</b> — that’s the demo. In production this writes to your real calendar.');
      return;
    }
    // intents
    if (/(book|appoint|schedule|cleaning|visit|checkup|check-up)/.test(t)) {
      flow = 'day'; booking = {};
      botSay('Happy to! I checked the calendar — the next openings for a cleaning are:', DAYS.map((d) => [d, d]));
    } else if (/(ouch|pain|hurt|emergency|broke|chipped|swollen|bleed)/.test(t)) {
      flow = null;
      botSay('That sounds urgent — I’m skipping the script. ☎️ <b>Call us right now at (555) 014-2200</b> and press 1; Dr. Park keeps two same-day slots for emergencies. If it’s after hours, the recording gives the on-call line.',
        [['📅 Book a regular visit', 'Book a cleaning'], ['🕐 Hours', 'What are your hours?']], 500);
    } else if (/(insurance|delta|aetna|cigna|metlife|coverage|in-network)/.test(t)) {
      botSay('We’re in-network with <b>Delta Dental, Aetna, Cigna and MetLife</b>, and we file out-of-network claims for everyone else. Bring your member ID and we verify benefits before you’re in the chair — no surprise bills.');
    } else if (/(price|cost|much|fee|pay)/.test(t)) {
      botSay('Straight answers: a <b>cleaning + exam is $129</b> (new patients $99, includes X-rays). Whitening runs $349, and we show every price before treatment — always.');
    } else if (/(hour|open|close|location|address|where|parking)/.test(t)) {
      botSay('We’re at <b>410 Juniper Row, Vienna VA</b> — free parking behind the building. Open <b>Mon–Fri 8am–6pm, Sat 9am–1pm</b>. Tuesdays we stay late until 8pm for the 9-to-5 crowd.');
    } else if (/(human|person|someone|staff|front desk|talk)/.test(t)) {
      botSay('Of course — you can reach the front desk at <b>(555) 014-2200</b>, Mon–Sat during open hours. Or leave your number and Maria will call you back within the hour.');
    } else if (/(thank|thanks|great|awesome|cool)/.test(t)) {
      botSay('Anytime! That’s what I’m here for — 24/7, no coffee required. ☕');
    } else if (/(hi|hello|hey)\b/.test(t)) {
      botSay('Hi there! I’m Juniper, the studio’s concierge. I can book visits, check insurance, or answer anything about the practice.');
    } else {
      botSay('I want to get that exactly right, so I’ve flagged it for the front desk — Maria will follow up within the hour. Meanwhile, I <b>can</b> book visits, check insurance, or share prices and hours.');
    }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const v = input.value.trim();
    if (!v) return;
    input.value = '';
    handleUser(v);
  });

  // opening
  setTimeout(() => {
    botSay('Welcome to <b>Juniper Dental Studio</b> 👋 — I’m the after-hours concierge. It’s outside office hours right now, but I can still book you in, check your insurance, or answer questions.', DEFAULT_CHIPS, 500);
  }, 800);
})();

/* ================= STATION 2 — Pulse ================= */
(function dashboard() {
  const S1 = '#2a78d6', S2 = '#eb6834', GRID = '#e1e0d9', AXIS = '#c3c2b7', MUTED = '#898781', INK = '#101114';
  const DPR = Math.min(devicePixelRatio || 1, 2);

  function prep(cv) {
    const r = cv.getBoundingClientRect();
    cv.width = r.width * DPR; cv.height = r.height * DPR;
    const g = cv.getContext('2d');
    g.setTransform(DPR, 0, 0, DPR, 0, 0);
    return [g, r.width, r.height];
  }

  /* ---- state ---- */
  const hours = ['8a', '9a', '10a', '11a', '12p', '1p', '2p', '3p', '4p', '5p'];
  const target = [3, 5, 6, 6, 4, 4, 6, 6, 5, 3];
  let line = [2, 4, 7, 5, 3, 4, 5, 0, 0, 0];
  let liveIdx = 6; // currently filling 2p
  const channels = [['Referrals', 34], ['Google', 27], ['Website', 19], ['Instagram', 11], ['Walk-in', 6]];
  const tiles = [
    { lbl: 'Revenue MTD', val: 48210, fmt: (v) => '$' + Math.round(v).toLocaleString(), delta: '+12.4% vs last month', up: true, arrow: '▲', spark: [31, 33, 34, 37, 36, 39, 42, 44, 43, 46, 48] },
    { lbl: 'Bookings today', val: 23, fmt: (v) => Math.round(v), delta: '+4 since 9am', up: true, arrow: '▲', spark: [2, 5, 9, 12, 14, 15, 18, 19, 21, 22, 23] },
    { lbl: 'Avg response time', val: 42, fmt: (v) => Math.round(v) + 's', delta: '18s faster with concierge', up: true, arrow: '▼', spark: [95, 90, 84, 71, 66, 60, 55, 51, 48, 44, 42] },
    { lbl: 'Questions deflected', val: 78, fmt: (v) => Math.round(v) + '%', delta: 'handled without staff', up: true, arrow: '▲', spark: [55, 58, 61, 64, 66, 69, 71, 73, 75, 77, 78] },
  ];

  /* ---- tiles ---- */
  const tilesEl = $('#tiles');
  tiles.forEach((t, i) => {
    const d = document.createElement('div');
    d.className = 'tile';
    d.innerHTML = `<p class="lbl">${t.lbl}</p><p class="val" id="tv${i}">${t.fmt(t.val)}</p>
      <p class="delta ${t.up ? 'up' : 'down'}">${t.arrow} ${t.delta}</p><canvas id="sp${i}"></canvas>`;
    tilesEl.appendChild(d);
  });
  function drawSpark(i) {
    const cv = $('#sp' + i); if (!cv) return;
    const [g, w, h] = prep(cv);
    const d = tiles[i].spark, mn = Math.min(...d), mx = Math.max(...d);
    const X = (k) => 2 + (k / (d.length - 1)) * (w - 10);
    const Y = (v) => h - 3 - ((v - mn) / (mx - mn || 1)) * (h - 8);
    g.beginPath();
    d.forEach((v, k) => k ? g.lineTo(X(k), Y(v)) : g.moveTo(X(k), Y(v)));
    g.strokeStyle = S1; g.lineWidth = 2; g.lineJoin = 'round'; g.stroke();
    g.lineTo(X(d.length - 1), h); g.lineTo(X(0), h); g.closePath();
    g.fillStyle = 'rgba(42,120,214,.10)'; g.fill();
    const lx = X(d.length - 1), ly = Y(d[d.length - 1]);
    g.beginPath(); g.arc(lx, ly, 3, 0, 7); g.fillStyle = S1; g.fill();
    g.beginPath(); g.arc(lx, ly, 4.5, 0, 7); g.strokeStyle = '#FCFCFB'; g.lineWidth = 2; g.stroke();
  }

  /* ---- line chart ---- */
  const lc = $('#lineChart'), lTip = $('#lineTip');
  const LP = { l: 30, r: 12, t: 12, b: 24 };
  let lGeom = null;
  function drawLine() {
    const [g, w, h] = prep(lc);
    const maxY = 8;
    const X = (i) => LP.l + (i / (hours.length - 1)) * (w - LP.l - LP.r);
    const Y = (v) => LP.t + (1 - v / maxY) * (h - LP.t - LP.b);
    lGeom = { X, Y, w, h };
    // grid
    g.strokeStyle = GRID; g.lineWidth = 1;
    for (let v = 0; v <= maxY; v += 2) {
      g.beginPath(); g.moveTo(LP.l, Y(v)); g.lineTo(w - LP.r, Y(v)); g.stroke();
      g.fillStyle = MUTED; g.font = '10px "Spline Sans Mono", monospace'; g.textAlign = 'right';
      g.fillText(v, LP.l - 7, Y(v) + 3);
    }
    g.textAlign = 'center';
    hours.forEach((hh, i) => { g.fillStyle = MUTED; g.fillText(hh, X(i), h - 8); });
    // baseline
    g.strokeStyle = AXIS; g.beginPath(); g.moveTo(LP.l, Y(0)); g.lineTo(w - LP.r, Y(0)); g.stroke();
    // target (dashed reference)
    g.setLineDash([5, 5]); g.strokeStyle = MUTED; g.lineWidth = 1.5; g.beginPath();
    target.forEach((v, i) => i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v)));
    g.stroke(); g.setLineDash([]);
    // actual area+line up to liveIdx
    g.beginPath();
    for (let i = 0; i <= liveIdx; i++) i ? g.lineTo(X(i), Y(line[i])) : g.moveTo(X(i), Y(line[i]));
    g.strokeStyle = S1; g.lineWidth = 2; g.lineJoin = 'round'; g.stroke();
    g.lineTo(X(liveIdx), Y(0)); g.lineTo(X(0), Y(0)); g.closePath();
    g.fillStyle = 'rgba(42,120,214,.09)'; g.fill();
    // live endpoint
    const ex = X(liveIdx), ey = Y(line[liveIdx]);
    g.beginPath(); g.arc(ex, ey, 4, 0, 7); g.fillStyle = S1; g.fill();
    g.beginPath(); g.arc(ex, ey, 6, 0, 7); g.strokeStyle = '#FCFCFB'; g.lineWidth = 2; g.stroke();
  }
  lc.addEventListener('pointermove', (e) => {
    if (!lGeom) return;
    const r = lc.getBoundingClientRect();
    const px = e.clientX - r.left;
    let best = 0, bd = 1e9;
    for (let i = 0; i <= liveIdx; i++) { const d = Math.abs(lGeom.X(i) - px); if (d < bd) { bd = d; best = i; } }
    lTip.style.opacity = 1;
    lTip.style.left = lGeom.X(best) + 'px';
    lTip.style.top = (lGeom.Y(line[best]) + 16) + 'px';
    lTip.innerHTML = `${hours[best]} — <b>${line[best]} booked</b> · target ${target[best]}`;
  });
  lc.addEventListener('pointerleave', () => { lTip.style.opacity = 0; });

  /* ---- bar chart (single hue: magnitude) ---- */
  const bc = $('#barChart'), bTip = $('#barTip');
  const BP = { l: 78, r: 34, t: 8, b: 8 };
  let bGeom = null;
  function drawBars() {
    const [g, w, h] = prep(bc);
    const mx = Math.max(...channels.map((c) => c[1]));
    const rowH = (h - BP.t - BP.b) / channels.length;
    const X = (v) => BP.l + (v / mx) * (w - BP.l - BP.r);
    bGeom = { rowH, X, w };
    channels.forEach(([name, v], i) => {
      const y = BP.t + i * rowH + rowH * 0.18, bh = rowH * 0.58;
      g.fillStyle = MUTED; g.font = '11px "Spline Sans Mono", monospace'; g.textAlign = 'right'; g.textBaseline = 'middle';
      g.fillText(name, BP.l - 9, y + bh / 2 + 1);
      // rounded end bar
      const bw = Math.max(X(v) - BP.l, 4);
      g.fillStyle = S1;
      g.beginPath();
      g.moveTo(BP.l, y);
      g.lineTo(BP.l + bw - 4, y);
      g.arcTo(BP.l + bw, y, BP.l + bw, y + 4, 4);
      g.lineTo(BP.l + bw, y + bh - 4);
      g.arcTo(BP.l + bw, y + bh, BP.l + bw - 4, y + bh, 4);
      g.lineTo(BP.l, y + bh);
      g.closePath(); g.fill();
      g.fillStyle = INK; g.textAlign = 'left'; g.font = '11.5px "Spline Sans Mono", monospace';
      g.fillText(v, BP.l + bw + 8, y + bh / 2 + 1);
    });
    g.strokeStyle = AXIS; g.beginPath(); g.moveTo(BP.l, BP.t); g.lineTo(BP.l, h - BP.b); g.stroke();
  }
  bc.addEventListener('pointermove', (e) => {
    if (!bGeom) return;
    const r = bc.getBoundingClientRect();
    const i = Math.floor((e.clientY - r.top - 8) / bGeom.rowH);
    if (i < 0 || i >= channels.length) { bTip.style.opacity = 0; return; }
    const [name, v] = channels[i];
    bTip.style.opacity = 1;
    bTip.style.left = (e.clientX - r.left) + 'px';
    bTip.style.top = (e.clientY - r.top - 6) + 'px';
    bTip.innerHTML = `${name} — <b>${v} new patients</b> (${Math.round(v / channels.reduce((a, c) => a + c[1], 0) * 100)}%)`;
  });
  bc.addEventListener('pointerleave', () => { bTip.style.opacity = 0; });

  /* ---- narration ---- */
  const narr = $('#narrLine');
  const NARR = [
    () => `11:0${Math.floor(Math.random() * 9)} — Bookings are running ${line[liveIdx] >= target[liveIdx] ? 'ahead of' : 'just under'} target. ${line[liveIdx] >= target[liveIdx] ? 'The 2pm block is nearly full — consider opening Dr. Park’s hold slots.' : 'The concierge is nudging waitlisted patients toward 2pm.'}`,
    () => `Referrals are your strongest channel this week (34) — the thank-you automation is due for 6 patients today.`,
    () => `Response time is down to ${Math.round(tiles[2].val)}s since the concierge went live — before it was 4½ minutes.`,
    () => `Heads-up: Thursday looks light after 3pm. One targeted recall campaign usually fills 3–4 of those slots.`,
    () => `Deflection at ${Math.round(tiles[3].val)}% — front desk is answering ${Math.round((1 - tiles[3].val / 100) * 40)} of ~40 daily questions instead of all of them.`,
  ];
  let ni = 0;
  function typeNarr(text) {
    if (REDUCED) { narr.textContent = text; return; }
    narr.textContent = '';
    let k = 0;
    (function step() {
      narr.textContent = text.slice(0, ++k);
      if (k < text.length) setTimeout(step, 12);
    })();
  }

  /* ---- live loop ---- */
  function drawAll() { tiles.forEach((_, i) => drawSpark(i)); drawLine(); drawBars(); }
  let ticks = 0;
  function tick() {
    ticks++;
    // tile drift
    tiles[0].val += Math.random() * 120;
    if (Math.random() < 0.35) { tiles[1].val += 1; line[liveIdx] = Math.min(8, line[liveIdx] + 1); }
    tiles[2].val = Math.max(31, tiles[2].val + (Math.random() - 0.55) * 2);
    tiles[3].val = Math.min(84, Math.max(70, tiles[3].val + (Math.random() - 0.45)));
    tiles.forEach((t, i) => {
      t.spark.push(i === 2 ? t.val : t.spark[t.spark.length - 1] + (i === 0 ? 1 : Math.random() * 1.4));
      if (t.spark.length > 12) t.spark.shift();
      $('#tv' + i).textContent = t.fmt(t.val);
    });
    if (ticks % 10 === 0 && liveIdx < hours.length - 1) liveIdx++;
    if (ticks % 4 === 1) typeNarr(NARR[ni++ % NARR.length]());
    drawAll();
  }
  drawAll();
  typeNarr('Live since 8:00am — everything below updates as the (simulated) day unfolds.');
  setInterval(tick, 2500);
  addEventListener('resize', drawAll);
})();

/* ================= STATION 3 — Orbit ================= */
(function crm() {
  const AV = ['#2a78d6', '#eb6834', '#1baf7a', '#4a3aa7', '#e87ba4'];
  const STAGES = ['Reconnect', 'In conversation', 'Committed'];
  const PEOPLE = [
    { id: 0, name: 'Maya Okafor', role: 'Owner · Okafor Physio', stage: 1, warm: 'hot', score: 86,
      facts: ['Met at Vienna Biz Breakfast', 'Two kids — Zola & Sam', 'Hates email, loves texts', 'Asked about no-show rates'],
      last: 'Called 3 days ago — wants the dashboard demo her partner can see.',
      draft: 'Hi Maya — promised follow-through: here’s a 3-min video of the no-show dashboard using (fake) clinic data. If it clicks, I’ll set up the live version with your numbers next week. Say hi to Zola’s soccer team 🙂' },
    { id: 1, name: 'Rob Tran', role: 'GM · Tran Auto Group', stage: 0, warm: 'cool', score: 41,
      facts: ['Last spoke 5 months ago', 'Was mid-renovation then', 'Brother-in-law does his site', 'Big on Costco runs'],
      last: 'Went quiet after the showroom reopened in March.',
      draft: 'Rob! Saw the showroom reopening photos — the lighting turned out great. No pitch: just curious how the first quarter back has treated you. If service-lane wait times are still the headache, I have something small worth 15 minutes.' },
    { id: 2, name: 'Priya Raman', role: 'Broker · Keystone Realty', stage: 2, warm: 'hot', score: 93,
      facts: ['Signed for concierge + CRM', 'Kickoff next Tuesday', 'Prefers 7am calls', 'Marathon in October'],
      last: 'Contract signed Friday. Kickoff scheduled.',
      draft: 'Priya — before Tuesday’s kickoff: I’ll bring the intake checklist and the first-week plan. Only homework on your side is exporting the contact CSV (5 minutes, I’ll walk you through it). How’s training week going?' },
    { id: 3, name: 'Dee Alvarez', role: 'Owner · Deleon Bakery', stage: 1, warm: 'warm', score: 64,
      facts: ['Referral from Priya', 'Instagram is her whole funnel', 'Opens at 5am — call early', 'Wants catering pre-orders'],
      last: 'Emailed pricing questions Monday — answered, no reply yet.',
      draft: 'Hi Dee — following up on the pricing note with something more useful than numbers: a mock-up of what catering pre-orders could look like on your Instagram bio link. Two taps from story to order. Want me to send it over?' },
    { id: 4, name: 'Sam Whitfield', role: 'Principal · Whitfield Law', stage: 0, warm: 'warm', score: 55,
      facts: ['Old college roommate', 'Firm drowning in intake forms', 'Mentioned AI twice last dinner', 'Bourbon collector'],
      last: 'Dinner two weeks ago — “we should talk shop sometime.”',
      draft: 'Sam — you said “talk shop sometime” and I’m collecting. Trade you one bourbon for 20 minutes on what document automation actually looks like for a firm your size. Thursday after 5?' },
  ];
  let sel = 0;

  const pipe = $('#pipe'), detail = $('#detail');

  function initials(n) { return n.split(' ').map((w) => w[0]).join(''); }

  function renderPipe() {
    pipe.innerHTML = '';
    STAGES.forEach((st, si) => {
      const wrapEl = document.createElement('div');
      wrapEl.className = 'stage';
      const members = PEOPLE.filter((p) => p.stage === si);
      wrapEl.innerHTML = `<h4><span>${st}</span><span>${members.length}</span></h4>`;
      members.forEach((p) => {
        const b = document.createElement('button');
        b.className = 'contact' + (p.id === sel ? ' sel' : '');
        b.setAttribute('aria-pressed', p.id === sel);
        b.innerHTML = `<span class="av" style="background:${AV[p.id]}">${initials(p.name)}</span>
          <span><span class="nm">${p.name}</span><br><span class="meta">${p.role}</span></span>
          <span class="warm ${p.warm}">${p.warm.toUpperCase()}</span>`;
        b.addEventListener('click', () => { sel = p.id; renderPipe(); renderDetail(); });
        wrapEl.appendChild(b);
      });
      pipe.appendChild(wrapEl);
    });
  }

  let typeT = null;
  function typeDraft(el, text) {
    clearTimeout(typeT);
    if (REDUCED) { el.innerHTML = text; return; }
    let k = 0;
    el.innerHTML = '<span class="caret"></span>';
    (function step() {
      k += 2;
      el.innerHTML = text.slice(0, k) + '<span class="caret"></span>';
      if (k < text.length) typeT = setTimeout(step, 14);
      else el.innerHTML = text;
    })();
  }

  function renderDetail() {
    const p = PEOPLE[sel];
    detail.innerHTML = `
      <div class="who">
        <span class="av" style="background:${AV[p.id]}">${initials(p.name)}</span>
        <div><h3>${p.name}</h3><p>${p.role} · ${STAGES[p.stage].toUpperCase()}</p></div>
        <div class="score"><b>${p.score}</b><span>warmth</span></div>
      </div>
      <ul class="facts">${p.facts.map((f) => `<li>${f}</li>`).join('')}</ul>
      <p style="font-size:13.5px;color:var(--muted);font-family:var(--mono)">LAST TOUCH — ${p.last}</p>
      <div class="draft"><p class="dh"><i></i> AI-drafted follow-up · edits welcome</p><p id="draftText"></p></div>
      <div class="actions">
        <button class="abtn primary" id="sendBtn">Send it →</button>
        <button class="abtn" id="logBtn">Log a call</button>
        <button class="abtn" id="advBtn" ${p.stage === 2 ? 'disabled style="opacity:.4;cursor:default"' : ''}>Advance stage ↦</button>
      </div>`;
    typeDraft($('#draftText'), p.draft);
    $('#sendBtn').addEventListener('click', () => {
      p.score = Math.min(99, p.score + 4);
      toast(`Follow-up to <b>${p.name}</b> queued. Orbit set a reminder to nudge in 4 days if no reply.`);
      renderDetail();
    });
    $('#logBtn').addEventListener('click', () => {
      p.score = Math.min(99, p.score + 6);
      if (p.warm === 'cool') p.warm = 'warm'; else if (p.warm === 'warm') p.warm = 'hot';
      p.last = 'Call logged just now — Orbit re-scored the relationship.';
      toast(`Call with <b>${p.name}</b> logged — warmth up, next follow-up re-drafted.`);
      renderPipe(); renderDetail();
    });
    $('#advBtn').addEventListener('click', () => {
      if (p.stage < 2) {
        p.stage++;
        toast(`<b>${p.name}</b> moved to “${STAGES[p.stage]}”. Orbit adjusted the cadence for this stage.`);
        renderPipe(); renderDetail();
      }
    });
  }

  renderPipe();
  renderDetail();
})();
