"""Builds the glass dashboard SVGs for the GitHub profile README.

Edit content.json to change the words, then run:  python scripts/build.py
The GitHub Action runs this daily so the dashboard numbers stay fresh.
"""
import datetime as dt
import html
import json
import os
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DATA = json.loads((ROOT / "content.json").read_text(encoding="utf-8"))
USER = DATA["username"]

SANS = ("'Segoe UI Variable Display','Segoe UI','SF Pro Display',-apple-system,"
        "'Helvetica Neue','Leelawadee UI','Noto Sans Thai',Arial,sans-serif")
MONO = "'JetBrains Mono','SF Mono',Menlo,Consolas,monospace"

# Ember palette: warm black base, orange glow, amber highlights.
INK = "#F7EFE6"
MUTED = "#B3A496"
DIM = "#7A6C60"
ORANGE = "#FF7A1A"
AMBER = "#FFB547"
EMBER = "#FF4D2E"
SAND = "#FFD9A8"
LIVE = "#7CF29A"

LANG_COLORS = {
    "Python": ORANGE, "C#": AMBER, "TypeScript": "#FF9E6B", "JavaScript": SAND,
    "MQL5": EMBER, "C++": "#E0663F", "C": "#A8968A",
}
# Only programming languages I actually write. Repos sometimes carry vendored
# stuff (e.g. a Git installer folder full of HTML docs and Perl), so anything
# not listed here, markup included, stays out of the bar.
MY_LANGS = set(LANG_COLORS)


def esc(s):
    return html.escape(str(s), quote=True)


def text_w(s, size, mono=False):
    """Rough text width, good enough to size pills."""
    return len(s) * size * (0.61 if mono else 0.56)


# ---------- shared pieces ----------

def defs(blobs):
    blob_svg = "".join(
        f'<circle class="b{i % 3}" cx="{x}" cy="{y}" r="{r}" fill="{c}" opacity="{o}"/>'
        for i, (x, y, r, c, o) in enumerate(blobs)
    )
    return f"""
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#140C07"/><stop offset="1" stop-color="#070504"/>
  </linearGradient>
  <linearGradient id="glass" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#FFF4E8" stop-opacity="0.10"/>
    <stop offset="1" stop-color="#FFF4E8" stop-opacity="0.025"/>
  </linearGradient>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#FFE2C2" stop-opacity="0.42"/>
    <stop offset="0.45" stop-color="#FFE2C2" stop-opacity="0.07"/>
    <stop offset="1" stop-color="{ORANGE}" stop-opacity="0.30"/>
  </linearGradient>
  <linearGradient id="fire" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{SAND}"/><stop offset="0.45" stop-color="{AMBER}"/>
    <stop offset="1" stop-color="{ORANGE}"/>
  </linearGradient>
  <linearGradient id="heat" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{AMBER}"/><stop offset="1" stop-color="{EMBER}"/>
  </linearGradient>
  <filter id="blur" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="62"/>
  </filter>
  <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/>
    <feColorMatrix values="0 0 0 0 1  0 0 0 0 0.9  0 0 0 0 0.8  0 0 0 0.04 0"/></filter>
  <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
    <path d="M32 0 H0 V32" fill="none" stroke="#FFFFFF" stroke-opacity="0.035"/>
  </pattern>
  <g id="blobs" filter="url(#blur)">{blob_svg}</g>
</defs>
<style>
  .b0 {{ animation: drift 18s ease-in-out infinite alternate; }}
  .b1 {{ animation: drift 24s ease-in-out infinite alternate-reverse; }}
  .b2 {{ animation: drift 30s ease-in-out infinite alternate; }}
  @keyframes drift {{ from {{ transform: translate(0,0); }} to {{ transform: translate(40px,-25px); }} }}
  .pulse {{ animation: pulse 2.4s ease-in-out infinite; }}
  @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .3; }} }}
  .rise {{ animation: rise .9s cubic-bezier(.2,.7,.2,1) both; }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: none; }} }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>"""


def canvas(w, h, blobs, body, label, grid=True):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">
<title>{esc(label)}</title>
{defs(blobs)}
<clipPath id="frame"><rect width="{w}" height="{h}" rx="24"/></clipPath>
<g clip-path="url(#frame)">
  <rect width="{w}" height="{h}" fill="url(#bg)"/>
  {'<rect width="%d" height="%d" fill="url(#grid)"/>' % (w, h) if grid else ''}
  <use href="#blobs"/>
  <rect width="{w}" height="{h}" filter="url(#grain)"/>
</g>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="24" fill="none" stroke="#FFD9A8" stroke-opacity="0.12"/>
{body}
</svg>
"""


def glass(x, y, w, h, r=20):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="url(#glass)" '
            f'stroke="url(#edge)" stroke-width="1"/>'
            f'<path d="M{x + r} {y + 0.5} H{x + w - r}" stroke="#FFF4E8" stroke-opacity="0.4" '
            f'stroke-width="1" stroke-linecap="round"/>')


def t(x, y, s, size=14, fill=INK, weight=400, mono=False, anchor="start", extra=""):
    fam = MONO if mono else SANS
    return (f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" {extra}>{esc(s)}</text>')


def label(x, y, s, fill=AMBER, anchor="start"):
    return t(x, y, s, 11, fill, 600, True, anchor, 'letter-spacing="3"')


def pill(x, y, s, size=12, fill=INK, dot=None, mono=True, bg_op=0.07, pulse=False):
    pad = 12 + (12 if dot else 0)
    w = text_w(s, size, mono) + pad + 12
    h = size + 14
    out = (f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{h}" rx="{h / 2}" fill="#FFF4E8" '
           f'fill-opacity="{bg_op}" stroke="#FFD9A8" stroke-opacity="0.14"/>')
    if dot:
        cls = ' class="pulse"' if pulse else ""
        out += f'<circle{cls} cx="{x + 14}" cy="{y + h / 2}" r="3.5" fill="{dot}"/>'
    out += t(x + pad, y + h / 2 + size * 0.36, s, size, fill, 500, mono)
    return out, w


def pct(f):
    return "<1%" if 0 < f < .005 else f"{100 * f:.0f}%"


def write(name, svg):
    path = ASSETS / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")
    print("wrote", path.relative_to(ROOT))


# ---------- data ----------

def fetch(url, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-builder", "Accept": accept})
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def contributions():
    page = fetch(f"https://github.com/users/{USER}/contributions", "text/html")
    dates = dict(re.findall(r'data-date="([\d-]+)" id="([^"]+)"', page))
    by_id = {v: k for k, v in dates.items()}
    days = {d: 0 for d in dates}
    for cid, text in re.findall(r'for="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
        m = re.match(r"([\d,]+) contribution", text)
        if cid in by_id and m:
            days[by_id[cid]] = int(m.group(1).replace(",", ""))
    return dict(sorted(days.items()))


def languages():
    repos = json.loads(fetch(f"https://api.github.com/users/{USER}/repos?per_page=100"))
    totals = {}
    for repo in repos:
        if repo["fork"]:
            continue
        langs = json.loads(fetch(repo["languages_url"]))
        for k, v in langs.items():
            if k not in MY_LANGS:
                continue
            totals[k] = totals.get(k, 0) + v
    return len([r for r in repos if not r["fork"]]), totals


# ---------- animated pieces (SMIL, so it plays inside GitHub's <img>) ----------

def motto(x, y, s, size=30):
    """Types the motto out letter by letter, holds, erases, loops. A light
    sweep runs across the letters the whole time."""
    cw = size * 0.475  # rough advance per character at this weight
    n = len(s)
    dur, type_end, hold_end, erase_end = 9.0, 2.4, 7.4, 8.2
    times, widths = [0.0], [0.0]
    for k in range(1, n + 1):
        times.append(type_end * k / n)
        widths.append(k * cw)
    times.append(hold_end)
    widths.append(n * cw)
    for k in range(n - 1, -1, -2):
        times.append(hold_end + (erase_end - hold_end) * (n - k) / n)
        widths.append(k * cw)
    times.append(dur)
    widths.append(0.0)
    kt = ";".join(f"{v / dur:.4f}" for v in times)
    wv = ";".join(f"{v:.1f}" for v in widths)
    xv = ";".join(f"{x + v + 3:.1f}" for v in widths)
    top = y - size
    return f"""
<defs>
  <linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="{x - 200}" y1="0" x2="{x + 200}" y2="0">
    <stop offset="0" stop-color="{INK}"/><stop offset=".42" stop-color="{INK}"/>
    <stop offset=".5" stop-color="{AMBER}"/><stop offset=".58" stop-color="{INK}"/>
    <stop offset="1" stop-color="{INK}"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="-200 0;{n * cw + 200:.0f} 0"
      dur="3.2s" repeatCount="indefinite"/>
  </linearGradient>
  <clipPath id="typed"><rect x="{x - 4}" y="{top - 6}" height="{size + 16}" width="0">
    <animate attributeName="width" values="{wv}" keyTimes="{kt}" dur="{dur}s" calcMode="discrete" repeatCount="indefinite"/>
  </rect></clipPath>
</defs>
<g clip-path="url(#typed)">{t(x, y, s, size, "url(#shine)", 700, extra='letter-spacing="-.4"')}</g>
<rect x="{x}" y="{top + 2}" width="3" height="{size + 2}" rx="1.5" fill="{ORANGE}">
  <animate attributeName="x" values="{xv}" keyTimes="{kt}" dur="{dur}s" calcMode="discrete" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur=".8s" repeatCount="indefinite"/>
</rect>"""


def ember_bot(x, y):
    """Small original mascot: a robot with a flame on its antenna. It bobs,
    blinks, looks around and waves while sparks drift up."""
    ease = 'calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1"'
    sparks = "".join(
        f'<circle cx="{dx}" cy="-128" r="{r}" fill="{c}" opacity="0">'
        f'<animate attributeName="cy" values="-128;{-128 - rise}" dur="{d}s" begin="{bg}s" repeatCount="indefinite"/>'
        f'<animate attributeName="cx" values="{dx};{dx + drift}" dur="{d}s" begin="{bg}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0;1;0" dur="{d}s" begin="{bg}s" repeatCount="indefinite"/>'
        f'</circle>'
        for dx, r, c, rise, drift, d, bg in [
            (-4, 2.2, AMBER, 70, -14, 1.8, 0), (5, 1.6, SAND, 90, 12, 2.3, .6),
            (0, 1.8, ORANGE, 60, 6, 1.6, 1.1), (-8, 1.3, SAND, 80, -20, 2.6, 1.6),
            (9, 2.0, AMBER, 75, 18, 2.0, .3),
        ]
    )
    shell = "#2A1A10"
    return f"""
<defs>
  <radialGradient id="glow" cx=".5" cy=".5" r=".5">
    <stop offset="0" stop-color="{ORANGE}" stop-opacity=".55"/><stop offset="1" stop-color="{ORANGE}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="shell" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#3D2616"/><stop offset="1" stop-color="{shell}"/>
  </linearGradient>
</defs>
<g transform="translate({x} {y}) scale(1.3)">
  <circle cx="0" cy="-70" r="78" fill="url(#glow)">
    <animate attributeName="r" values="72;84;72" dur="2.8s" repeatCount="indefinite"/>
  </circle>
  <ellipse cx="0" cy="0" rx="32" ry="5" fill="#000" opacity=".5">
    <animate attributeName="rx" values="32;25;32" dur="2.8s" {ease} keyTimes="0;.5;1" repeatCount="indefinite"/>
  </ellipse>
  <g>
    <animateTransform attributeName="transform" type="translate" values="0 0;0 -9;0 0" keyTimes="0;.5;1"
      dur="2.8s" {ease} repeatCount="indefinite"/>
    <!-- legs -->
    <rect x="-16" y="-16" width="10" height="13" rx="4" fill="{shell}" stroke="#FFD9A8" stroke-opacity=".15"/>
    <rect x="6" y="-16" width="10" height="13" rx="4" fill="{shell}" stroke="#FFD9A8" stroke-opacity=".15"/>
    <!-- body -->
    <rect x="-25" y="-50" width="50" height="38" rx="13" fill="url(#shell)" stroke="url(#edge)"/>
    <circle cx="0" cy="-31" r="7" fill="url(#heat)">
      <animate attributeName="opacity" values="1;.45;1" dur="1.4s" repeatCount="indefinite"/>
    </circle>
    <!-- left arm -->
    <rect x="-35" y="-46" width="9" height="25" rx="4.5" fill="#3A2416"/>
    <!-- right arm, waving -->
    <g>
      <animateTransform attributeName="transform" type="rotate"
        values="0 30 -44;0 30 -44;-150 30 -44;-120 30 -44;-150 30 -44;-120 30 -44;-150 30 -44;0 30 -44;0 30 -44"
        keyTimes="0;.45;.52;.57;.62;.67;.72;.8;1" dur="5s" repeatCount="indefinite"/>
      <rect x="26" y="-46" width="9" height="25" rx="4.5" fill="#3A2416"/>
      <circle cx="30.5" cy="-20" r="5.5" fill="{ORANGE}"/>
    </g>
    <circle cx="-30.5" cy="-20" r="5.5" fill="{ORANGE}"/>
    <!-- antenna + flame -->
    <path d="M0 -112 V-124" stroke="{SAND}" stroke-width="2.5" stroke-linecap="round"/>
    <g transform="translate(0 -125)">
      <g>
        <animateTransform attributeName="transform" type="scale" values="1 1;.85 1.2;1.1 .9;.95 1.1;1 1"
          dur=".7s" repeatCount="indefinite"/>
        <path d="M0 0 C-9 -4 -8 -14 0 -24 C8 -14 9 -4 0 0 Z" fill="url(#heat)"/>
        <path d="M0 -2 C-4 -4 -4 -9 0 -14 C4 -9 4 -4 0 -2 Z" fill="{SAND}"/>
      </g>
    </g>
    {sparks}
    <!-- head -->
    <rect x="-47" y="-96" width="7" height="20" rx="3.5" fill="{ORANGE}"/>
    <rect x="40" y="-96" width="7" height="20" rx="3.5" fill="{ORANGE}"/>
    <rect x="-41" y="-114" width="82" height="60" rx="19" fill="url(#shell)" stroke="url(#edge)"/>
    <rect x="-41" y="-114" width="82" height="30" rx="19" fill="#FFF4E8" fill-opacity=".06"/>
    <rect x="-31" y="-104" width="62" height="36" rx="13" fill="#0B0604"/>
    <g>
      <animateTransform attributeName="transform" type="translate" values="0 0;0 0;5 0;5 0;-5 0;-5 0;0 0"
        keyTimes="0;.3;.36;.55;.61;.85;1" dur="7s" repeatCount="indefinite"/>
      <rect x="-17" y="-94" width="11" height="15" rx="5" fill="{AMBER}">
        <animate attributeName="height" values="15;15;2;15;15" keyTimes="0;.9;.94;.98;1" dur="4s" repeatCount="indefinite"/>
        <animate attributeName="y" values="-94;-94;-87.5;-94;-94" keyTimes="0;.9;.94;.98;1" dur="4s" repeatCount="indefinite"/>
      </rect>
      <rect x="6" y="-94" width="11" height="15" rx="5" fill="{AMBER}">
        <animate attributeName="height" values="15;15;2;15;15" keyTimes="0;.9;.94;.98;1" dur="4s" repeatCount="indefinite"/>
        <animate attributeName="y" values="-94;-94;-87.5;-94;-94" keyTimes="0;.9;.94;.98;1" dur="4s" repeatCount="indefinite"/>
      </rect>
    </g>
    <path d="M-6 -74 Q0 -70 6 -74" fill="none" stroke="{ORANGE}" stroke-width="2" stroke-linecap="round"/>
  </g>
</g>"""


# ---------- cards ----------

def hero():
    W, H = 1000, 400
    blobs = [(60, 40, 210, ORANGE, .55), (1000, 400, 230, EMBER, .40), (560, 0, 150, AMBER, .25)]
    live = len(DATA["projects"])
    b = ['<g class="rise">']
    s, _ = pill(56, 48, f"{live} PROJECTS LIVE", 11, INK, LIVE, pulse=True)
    b.append(s)
    b.append(t(56, 160, DATA["name_first"], 70, INK, 700, extra='letter-spacing="-2"'))
    b.append(t(56, 232, DATA["name_last"], 70, "url(#fire)", 700, extra='letter-spacing="-2"'))
    b.append(t(60, 276, DATA["role"].upper(), 13, AMBER, 600, True, extra='letter-spacing="2.5"'))
    b.append('</g>')
    b.append(motto(58, 334, DATA["motto"]))
    b.append(ember_bot(526, 372))

    x, y, w, h = 616, 48, 336, 304
    b.append('<g class="rise" style="animation-delay:.15s">')
    b.append(glass(x, y, w, h, 22))
    b.append(label(x + 24, y + 38, "ID"))
    b.append(t(x + w - 24, y + 38, f"@{USER}", 11, DIM, 500, True, "end"))
    b.append(f'<circle cx="{x + 52}" cy="{y + 88}" r="28" fill="url(#heat)"/>')
    b.append(t(x + 52, y + 97, DATA["nickname"][0], 25, "#140C07", 800, anchor="middle"))
    b.append(t(x + 94, y + 84, DATA["nickname"], 21, INK, 600))
    b.append(t(x + 94, y + 105, "Computer Engineer in training", 12.5, MUTED))
    b.append(f'<path d="M{x + 24} {y + 136} H{x + w - 24}" stroke="#FFD9A8" stroke-opacity=".12"/>')
    for i, (k, v) in enumerate(DATA["id_card"]):
        yy = y + 168 + i * 34
        b.append(t(x + 24, yy, k.upper(), 10.5, DIM, 600, True, extra='letter-spacing="1.2"'))
        b.append(t(x + 108, yy, v, 13.5, INK, 500))
    b.append('</g>')
    write("hero.svg", canvas(W, H, blobs, "\n".join(b), f"{DATA['name_first']} {DATA['name_last']}"))


def section(slug, name, right):
    W, H = 1000, 56
    body = (f'<circle cx="34" cy="28" r="4" fill="url(#heat)"/>'
            + t(50, 32.5, name.upper(), 12, INK, 600, True, extra='letter-spacing="3.5"')
            + f'<path d="M{50 + text_w(name, 12, True) + len(name) * 3.5 + 16:.0f} 28 '
              f'H{966 - text_w(right, 11, True) - 16:.0f}" '
              f'stroke="url(#fire)" stroke-opacity=".35"/>'
            + t(966, 32, right, 11, DIM, 500, True, "end"))
    write(f"sections/{slug}.svg", canvas(W, H, [(900, 28, 90, ORANGE, .35)], body, name, grid=False))


def project(p, i):
    W, H = 490, 316
    palettes = [(ORANGE, EMBER), (AMBER, ORANGE), (EMBER, AMBER)]
    c1, c2 = palettes[i % 3]
    blobs = [(450, 20, 130, c1, .55), (20, 316, 120, c2, .28)]
    b = [glass(16, 16, W - 32, H - 32, 20)]
    b.append(t(W - 40, 74, f"{i + 1:02d}", 46, "#FFF4E8", 700, anchor="end",
               extra='fill-opacity=".07" letter-spacing="-2"'))
    s, w = pill(38, 38, p["category"].upper(), 10.5, MUTED)
    b.append(s)
    s, _ = pill(38 + w + 8, 38, "Live", 10.5, INK, LIVE, pulse=True)
    b.append(s)
    b.append(t(38, 112, p["title"], 27, INK, 700, extra='letter-spacing="-.5"'))
    for j, line in enumerate(p["lines"]):
        b.append(t(38, 145 + j * 21, line, 14, MUTED))
    x = 38
    for tag in p["tags"]:
        s, w = pill(x, 214, tag, 11, INK, bg_op=.05)
        b.append(s)
        x += w + 8
    b.append(f'<path d="M38 256 H{W - 38}" stroke="#FFD9A8" stroke-opacity=".1"/>')
    b.append(t(38, 280, "↗  " + p["show"], 11.5, AMBER, 500, True))
    write(f"projects/{p['slug']}.svg", canvas(W, H, blobs, "\n".join(b), p["title"]))


def stack():
    W, H = 1000, 210
    blobs = [(60, 30, 150, AMBER, .22), (960, 200, 170, ORANGE, .45)]
    b = []
    dots = [ORANGE, AMBER, SAND]
    for r, (name, items) in enumerate(DATA["stack"]):
        y = 30 + r * 56
        b.append(glass(30, y, 940, 44, 22))
        b.append(t(54, y + 27, name, 13, MUTED, 600))
        x = 170
        for item in items:
            s, w = pill(x, y + 9, item, 11.5, INK, dots[r], bg_op=.06)
            b.append(s)
            x += w + 8
    write("stack.svg", canvas(W, H, blobs, "\n".join(b), "Stack"))


def dashboard():
    W, H = 1000, 340
    blobs = [(940, 30, 190, ORANGE, .5), (80, 340, 180, EMBER, .35), (520, 180, 120, AMBER, .15)]
    days = contributions()
    total = sum(days.values())
    active = sum(1 for v in days.values() if v)
    repo_count, langs = languages()
    today = dt.date.today()

    b = [t(970, 26, f"updated {today:%d %b %Y}", 10.5, DIM, 500, True, "end")]
    tiles = [(f"{total:,}", "contributions this year"), (str(active), "active days this year"),
             (str(len(DATA["projects"])), "projects live"), (str(repo_count), "public repos")]
    tw, gap = 220, 20
    for i, (num, name) in enumerate(tiles):
        x = 30 + i * (tw + gap)
        b.append(f'<g class="rise" style="animation-delay:{i * .08:.2f}s">')
        b.append(glass(x, 40, tw, 104, 18))
        b.append(t(x + 22, 98, num, 40, "url(#fire)" if i == 0 else INK, 700, extra='letter-spacing="-1"'))
        b.append(t(x + 22, 124, name, 12.5, MUTED))
        b.append('</g>')

    weeks = 31
    b.append(glass(30, 164, 540, 150, 18))
    b.append(label(52, 192, "LAST 31 WEEKS", MUTED))
    ramp = ["#FFFFFF", "#5A2A12", "#A3470F", ORANGE, AMBER]
    start = today - dt.timedelta(days=(today.weekday() + 1) % 7 + 7 * (weeks - 1))  # a Sunday
    cell, step = 12, 15.4
    for wk in range(weeks):
        for dow in range(7):
            d = start + dt.timedelta(days=wk * 7 + dow)
            if d > today:
                continue
            n = days.get(d.isoformat(), 0)
            lvl = 0 if n == 0 else 1 if n < 3 else 2 if n < 6 else 3 if n < 10 else 4
            op = ".06" if lvl == 0 else "1"
            b.append(f'<rect x="{52 + wk * step:.1f}" y="{204 + dow * step:.1f}" width="{cell}" '
                     f'height="{cell}" rx="3" fill="{ramp[lvl]}" fill-opacity="{op}"/>')

    b.append(glass(590, 164, 380, 150, 18))
    b.append(label(612, 192, "CODE BY LANGUAGE", MUTED))
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:6]
    whole = sum(v for _, v in top) or 1
    x0, bw = 612, 336
    x = x0
    for name, v in top:
        seg = bw * v / whole
        b.append(f'<rect x="{x:.1f}" y="208" width="{max(seg - 2, 1):.1f}" height="8" rx="4" '
                 f'fill="{LANG_COLORS[name]}"/>')
        x += seg
    for i, (name, v) in enumerate(top):
        cx = x0 + (i % 2) * 176
        cy = 244 + (i // 2) * 24
        b.append(f'<circle cx="{cx + 5}" cy="{cy - 4}" r="4.5" fill="{LANG_COLORS[name]}"/>')
        b.append(t(cx + 18, cy, name, 13, INK, 500))
        b.append(t(cx + 156, cy, pct(v / whole), 12, DIM, 500, True, "end"))
    write("dashboard.svg", canvas(W, H, blobs, "\n".join(b), "Live GitHub dashboard"))


ICONS = {
    "portfolio": '<circle cx="0" cy="0" r="8" fill="none" stroke="{c}" stroke-width="1.6"/>'
                 '<ellipse cx="0" cy="0" rx="3.5" ry="8" fill="none" stroke="{c}" stroke-width="1.4"/>'
                 '<path d="M-8 0 H8" stroke="{c}" stroke-width="1.4"/>',
    "linkedin": '<rect x="-8" y="-8" width="16" height="16" rx="3.5" fill="{c}"/>'
                '<text x="0" y="4.5" font-family="Arial" font-weight="700" font-size="10.5" '
                'fill="#140C07" text-anchor="middle">in</text>',
    "email": '<rect x="-8.5" y="-6" width="17" height="12" rx="2.5" fill="none" stroke="{c}" stroke-width="1.6"/>'
             '<path d="M-8 -5 L0 1 L8 -5" fill="none" stroke="{c}" stroke-width="1.6"/>',
    "instagram": '<rect x="-8" y="-8" width="16" height="16" rx="5" fill="none" stroke="{c}" stroke-width="1.6"/>'
                 '<circle r="3.6" fill="none" stroke="{c}" stroke-width="1.6"/><circle cx="4.4" cy="-4.4" r="1.1" fill="{c}"/>',
    "facebook": '<circle r="8.5" fill="{c}"/><text x="1" y="5.5" font-family="Arial" font-weight="700" '
                'font-size="13" fill="#140C07" text-anchor="middle">f</text>',
}


def buttons():
    for key, name, _ in DATA["links"]:
        W, H = 180, 56
        main = key == "portfolio"
        c = "#140C07" if main else INK
        fill = 'url(#fire)' if main else 'url(#bg)'
        body = (f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="28" fill="{fill}" '
                f'stroke="url(#edge)"/>'
                + ('' if main else f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="28" fill="url(#glass)"/>')
                + f'<g transform="translate(34 28)">{ICONS[key].format(c=c)}</g>'
                + t(56, 33, name, 14.5, c, 600))
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
               f'role="img" aria-label="{esc(name)}"><title>{esc(name)}</title>{defs([])}{body}</svg>\n')
        write(f"links/{key}.svg", svg)


if __name__ == "__main__":
    import sys
    if "--dashboard" not in sys.argv:
        hero()
        section("dashboard", "Activity", "auto-updated daily")
        section("projects", "Projects", f"{len(DATA['projects'])} live")
        section("stack", "Stack", "what I build with")
        section("contact", "Contact", "say hi")
        for i, p in enumerate(DATA["projects"]):
            project(p, i)
        stack()
        buttons()
    dashboard()
