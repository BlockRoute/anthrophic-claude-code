"""Keep https://deals.propcomp.org in sync with the source's Active listings.

  python3 refresh.py plan    compare source vs live page; write work/plan.json
  python3 refresh.py build   rebuild the page from work/plan.json, deploy it, then verify it
  python3 refresh.py verify  check the live page's addresses and prices against the source

Between the two steps, every entry in work/plan.json "add" must get its
headline, play, desc and hl written in our own words (needs_copy -> false).
"""
import json
import re
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
LIVE = "https://deals.propcomp.org"
SOURCE_MEDIA = "https://static.wixstatic.com/media/"
ACCOUNT = "bc127d6f8eab67841d465df0d44564af"
SCRIPT = "propcomp-deals"
MAX_PHOTOS = 6
PHOTO_BUDGET = 2_600_000  # stay under the Worker's 3 MB upload limit
NUMBER_WORDS = "Zero One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve Thirteen Fourteen Fifteen".split()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def scrape(*args):
    out = subprocess.run(["node", str(HERE / "scrape.js"), *args], capture_output=True, text=True, timeout=240)
    if out.returncode:
        sys.exit(f"scrape {args} failed: {out.stderr[-500:]}")
    return json.loads(out.stdout)


def money(text):
    m = re.search(r"\$\s*([\d,.]+)\s*([kKmM]?)", text or "")
    if not m:
        return None
    n = float(m.group(1).replace(",", ""))
    return int(n * {"k": 1_000, "m": 1_000_000}.get(m.group(2).lower(), 1))


def after(lines, label):
    """Value on the same line after 'Label:' or, if empty, the next line."""
    for i, l in enumerate(lines):
        if re.match(rf"^{label}\s*:", l, re.I):
            v = l.split(":", 1)[1].strip()
            return v or (lines[i + 1] if i + 1 < len(lines) else "")
    return ""


def comp_spec(text):
    """'3 Beds, 2 Bath, 1,564 sqft' -> '3 bd · 2 ba · 1,564 sq ft'"""
    beds = re.search(r"([\d.]+)\s*Beds?", text, re.I)
    baths = re.search(r"([\d.]+)\s*Baths?", text, re.I)
    sqft = re.search(r"([\d,]+)\s*sq\s*ft", text, re.I)
    parts = [f"{beds.group(1)} bd" if beds else "", f"{baths.group(1)} ba" if baths else "", f"{sqft.group(1)} sq ft" if sqft else ""]
    return " · ".join(p for p in parts if p) or text.strip()


def section(lines, start_pat, end_pat):
    out, on = [], False
    for l in lines:
        if on and re.match(end_pat, l, re.I):
            break
        if on:
            out.append(l)
        if re.match(start_pat, l, re.I):
            on = True
    return out


def parse_detail(card, d):
    lines = d["lines"]
    addr_line = next((l for l in lines if re.search(r",\s*[A-Z]{2}\s+\d{5}", l)), card["address"])
    m = re.match(r"^(.*?[.,])\s+(.*)$", addr_line)
    street, city = (m.group(1), m.group(2)) if m else (addr_line, "")
    area = re.sub(r",\s*[A-Z]{2}.*$", "", city).strip() or card["address"]
    price = money(next((l for l in lines if l.lower().startswith("available for")), "")) or card["price"]
    buy_now = next((l for l in lines if l.lower().startswith("buy it now")), "")
    lot = re.search(r"([\d.]+)\s*Acre", " ".join(lines), re.I)
    taxes = after(lines, "Taxes")
    tm = re.match(r"(\$[\d,]+)\s*/\s*(\d{4})", taxes)
    year = re.sub(r"\D", "", after(lines, "Year built"))
    comps_text = " ".join(section(lines, r"^(As-Is\s+)?Comps?:", r"^Property Highlights"))
    comps = [
        [c[1].strip(" ,"), comp_spec(c[0]), c[2].strip().replace("Listed for", "Listed at").replace("Pending for", "Pending at")]
        for c in re.findall(r"\d\.\s*(.+?)\s+-\s+(.+?)\s+((?:Sold|Listed|Pending)\b.*?\d{1,2}/\d{1,2}/\d{2,4})", comps_text)
    ]
    pid_line = next((l for l in lines if l.upper().startswith("PID")), "")
    pid = pid_line.split(":", 1)[1].strip() if ":" in pid_line and pid_line.split(":", 1)[1].strip() else after(lines, "PID")
    legal = next((l.split(":", 1)[1].strip() for l in lines if l.lower().startswith("legal desc")), "")
    start = next((i for i, l in enumerate(lines) if "BY APPT ONLY" in l.upper()), 0)
    stop = next((i for i, l in enumerate(lines) if i > start and re.match(r"^(ARV|As-Is|Comps?|Property Highlights)", l, re.I)), len(lines))
    beds, baths = card["beds"], card["baths"]
    return {
        "id": re.sub(r"[^a-z0-9]+", "-", street.lower()).strip("-")[:40],
        "slug": card["slug"],
        "photos": [],
        "headline": "",
        "street": street,
        "city": city,
        "area": area,
        "price": price,
        "alt": f"Buy-it-now price: ${money(buy_now):,}" if money(buy_now) else None,
        "arv": money(after(lines, "ARV")),
        "beds": after(lines, "Beds") or beds,
        "baths": after(lines, "Baths?") or baths,
        "bb": f"{beds} / {baths}",
        "sqft": int(re.sub(r"\D", "", card["sqft"]) or 0),
        "year": int(year) if year else None,
        "taxes": f"{tm.group(1)} ({tm.group(2)})" if tm else taxes,
        "lot": float(lot.group(1)) if lot else None,
        "play": "",
        "desc": "",
        "hl": [],
        "comps": comps,
        "pid": pid,
        "legal": legal,
        "needs_copy": True,
        "source_notes": {
            "headline": lines[lines.index("Active") + 1] if "Active" in lines[:-1] else "",
            "description": " ".join(lines[start + 1:stop]),
            "highlights": section(lines, r"^Property Highlights", r"^PID"),
        },
        "source_images": d["images"][:MAX_PHOTOS],
    }


def plan():
    WORK.mkdir(exist_ok=True)
    live = json.loads(fetch(f"{LIVE}/data.json"))
    cards = scrape("home")
    if len(cards) < 5:
        sys.exit(f"Only {len(cards)} listing cards found on the source page; its layout may have changed. Nothing changed.")
    active = {c["slug"]: c for c in cards if c["status"].lower() == "active" and c["slug"]}
    keep = [d for d in live if d["slug"] in active]
    remove = [{"slug": d["slug"], "street": d["street"],
               "status": next((c["status"] for c in cards if c["slug"] == d["slug"]), "no longer listed")}
              for d in live if d["slug"] not in active]
    known = {d["slug"] for d in live}
    add = [parse_detail(c, scrape("detail", c["slug"])) for s, c in active.items() if s not in known]
    updates, conflicts = [], []
    for d in keep:
        src = parse_detail(active[d["slug"]], scrape("detail", d["slug"]))
        u, c = sync_facts(d, src, active[d["slug"]])
        updates += u
        conflicts += c
    for d in add:
        conflicts += price_conflict(d, d, active[d["slug"]])
    p = {"keep": keep, "remove": remove, "add": add, "updates": updates, "conflicts": conflicts}
    (WORK / "plan.json").write_text(json.dumps(p, indent=1))
    print(json.dumps({"keep": [d["street"] for d in keep], "remove": remove,
                      "add": [d["street"] for d in add], "updates": updates, "conflicts": conflicts}, indent=1))


def lead_number(v):
    m = re.match(r"\s*([\d.]+)", str(v or ""))
    return float(m.group(1)) if m else None


def price_conflict(d, src, card):
    """The source's card and its listing page disagree on price: flag it, don't guess."""
    if card["price"] and src["price"] and card["price"] != src["price"]:
        note = (f"The asking price is being confirmed (${src['price']:,} vs ${card['price']:,} in seller materials). "
                "Contact Daniel to confirm before making an offer.")
        d["note"] = note
        return [{"street": d["street"], "field": "price", "listing_page": src["price"], "card": card["price"],
                 "kept": d["price"]}]
    return []


def sync_facts(d, src, card):
    """Bring key facts of a listed deal in line with the source; return (updates, conflicts)."""
    updates = []
    conflicts = price_conflict(d, src, card)
    if not conflicts and src["price"] and src["price"] != d["price"]:
        updates.append({"street": d["street"], "field": "price", "from": d["price"], "to": src["price"]})
        d["price"] = src["price"]
    for field in ("street", "city", "alt", "arv", "sqft", "year", "lot", "taxes", "pid"):
        new, old = src.get(field), d.get(field)
        if new in (None, "", 0) or new == old:
            continue
        updates.append({"street": d["street"], "field": field, "from": old, "to": new})
        d[field] = new
    for field in ("beds", "baths"):
        if lead_number(src[field]) is not None and lead_number(src[field]) != lead_number(d[field]):
            updates.append({"street": d["street"], "field": field, "from": d[field], "to": src[field]})
            d[field] = src[field]
    bb = f"{card['beds']} / {card['baths']}"
    if card["beds"] and bb != d["bb"]:
        updates.append({"street": d["street"], "field": "bb", "from": d["bb"], "to": bb})
        d["bb"] = bb
    if not conflicts and d.get("note", "").startswith("The asking price is being confirmed"):
        d.pop("note")
        updates.append({"street": d["street"], "field": "note", "from": "price being confirmed", "to": None})
    return updates, conflicts


def verify(deals):
    """Re-read the live page and the source; fail loudly if any address or price disagrees."""
    live = {d["slug"]: d for d in json.loads(fetch(f"{LIVE}/data.json"))}
    expected = {d["slug"]: d for d in deals}
    problems = [f"{d['street']}: missing from live page" for s, d in expected.items() if s not in live]
    problems += [f"{d['street']}: on live page but not expected" for s, d in live.items() if s not in expected]
    cards = {c["slug"]: c for c in scrape("home")}
    for s, d in live.items():
        if s not in expected:
            continue
        for f in ("street", "city", "price"):
            if d.get(f) != expected[s].get(f):
                problems.append(f"{d['street']}: live {f} {d.get(f)!r} != built {expected[s].get(f)!r}")
        card = cards.get(s)
        if not card or card["status"].lower() != "active":
            problems.append(f"{d['street']}: no longer Active on the source")
            continue
        number = re.match(r"[\d&\s-]+", d["street"])
        if number and number.group(0).strip() not in card["address"]:
            problems.append(f"{d['street']}: street number not in source address {card['address']!r}")
        if card["price"] != d["price"] and not d.get("note", "").startswith("The asking price is being confirmed"):
            problems.append(f"{d['street']}: live price ${d['price']:,} != source ${card['price']:,}")
    if problems:
        sys.exit("VERIFY FAILED:\n  " + "\n  ".join(problems))
    print(f"Verified {len(live)} live deals: addresses and prices match the source "
          f"(price conflicts in the source are flagged on the page).")


def save_photo(raw, dest, width):
    from io import BytesIO
    im = Image.open(BytesIO(raw)).convert("RGB")
    im.thumbnail((width, width))
    im.save(dest, quality=58, optimize=True, progressive=True)


def build():
    p = json.loads((WORK / "plan.json").read_text())
    missing = [d["street"] for d in p["add"] if d.get("needs_copy")]
    if missing:
        sys.exit(f"Write headline/play/desc/hl and set needs_copy=false first for: {missing}")
    out = WORK / "site"
    (out / "img").mkdir(parents=True, exist_ok=True)
    deals = list(p["keep"])
    for d in p["keep"]:
        for i in d["photos"]:
            f = out / "img" / f"{d['slug']}-{i}.jpg"
            if not f.exists():
                f.write_bytes(fetch(f"{LIVE}/img/{d['slug']}-{i}.jpg"))
    for d in p["add"]:
        d = dict(d)
        photos = []
        for i, name in enumerate(d.pop("source_images")):
            try:
                raw = fetch(f"{SOURCE_MEDIA}{name}/v1/fill/w_1000,h_680,q_75/p.jpg")
            except Exception:
                continue
            save_photo(raw, out / "img" / f"{d['slug']}-{i}.jpg", 760)
            photos.append(i)
        d["photos"] = photos
        d.pop("source_notes", None)
        d.pop("needs_copy", None)
        deals.append(d)
    if not deals:
        sys.exit("No active deals left; not publishing an empty page. Review manually.")

    # Trim photo counts until the bundle fits the Worker size limit.
    def size():
        return sum((out / "img" / f"{d['slug']}-{i}.jpg").stat().st_size for d in deals for i in d["photos"])
    while size() > PHOTO_BUDGET:
        biggest = max(deals, key=lambda d: len(d["photos"]))
        if len(biggest["photos"]) <= 2:
            sys.exit("Photos still exceed the size budget at 2 per property; review manually.")
        biggest["photos"] = biggest["photos"][:-1]

    html = (HERE / "template.html").read_text()
    html = html.replace("/*DEALS_JSON*/", json.dumps(deals, ensure_ascii=False).replace("</", "<\\/"))
    html = html.replace("{{UPDATED}}", date.today().strftime("%b %-d, %Y"))
    html = html.replace("{{COUNT_WORD}}", NUMBER_WORDS[len(deals)] if len(deals) < len(NUMBER_WORDS) else str(len(deals)))
    (out / "index.html").write_text(html)
    (out / "data.json").write_text(json.dumps(deals, indent=1, ensure_ascii=False))
    (out / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    deploy(out, deals)
    verify(deals)


def deploy(out, deals):
    imgs = [f"{d['slug']}-{i}.jpg" for d in deals for i in d["photos"]]
    js = ['import html from "./index.html";', 'import robots from "./robots.txt";', 'import data from "./data.json.txt";']
    js += [f'import i{n} from "./img/{f}";' for n, f in enumerate(imgs)]
    js.append("const IMG={" + ",".join(f'"/img/{f}":i{n}' for n, f in enumerate(imgs)) + "};")
    js.append("""export default{async fetch(req){const p=new URL(req.url).pathname;
if(IMG[p])return new Response(IMG[p],{headers:{"content-type":"image/jpeg","cache-control":"public, max-age=86400"}});
if(p==="/robots.txt")return new Response(robots,{headers:{"content-type":"text/plain"}});
if(p==="/data.json")return new Response(data,{headers:{"content-type":"application/json","cache-control":"no-store"}});
if(p==="/"||p==="/index.html")return new Response(html,{headers:{"content-type":"text/html; charset=utf-8","x-robots-tag":"noindex","cache-control":"no-cache"}});
return new Response("Not found",{status:404});}};""")
    (out / "worker.js").write_text("\n".join(js))
    (out / "data.json.txt").write_text((out / "data.json").read_text())
    (out / "metadata.json").write_text(json.dumps({"main_module": "worker.js", "compatibility_date": "2025-01-01"}))
    form = ["-F", "metadata=@metadata.json;type=application/json",
            "-F", "worker.js=@worker.js;filename=worker.js;type=application/javascript+module",
            "-F", "index.html=@index.html;filename=index.html;type=text/plain",
            "-F", "robots.txt=@robots.txt;filename=robots.txt;type=text/plain",
            "-F", "data.json.txt=@data.json.txt;filename=data.json.txt;type=text/plain"]
    for f in imgs:
        form += ["-F", f"img/{f}=@img/{f};filename=img/{f};type=application/octet-stream"]
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/workers/scripts/{SCRIPT}"
    r = subprocess.run(["curl", "-sS", "-m", "180", "-X", "PUT", url, *form], cwd=out, capture_output=True, text=True)
    res = json.loads(r.stdout or "{}")
    if not res.get("success"):
        sys.exit(f"Deploy failed: {res.get('errors') or r.stderr[-500:]}")
    live = json.loads(fetch(f"{LIVE}/data.json"))
    print(f"Deployed {len(deals)} deals; live data.json lists {len(live)}: " + ", ".join(d["street"] for d in live))


if __name__ == "__main__":
    {"plan": plan, "build": build, "verify": lambda: verify(json.loads(fetch(f"{LIVE}/data.json")))}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
