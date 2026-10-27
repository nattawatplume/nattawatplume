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

INK = "#F4F1EA"
MUTED = "#A09DB3"
DIM = "#6E6A85"
GOLD = "#E8C887"
VIOLET = "#7C6CFF"
TEAL = "#2DD4E6"

LANG_COLORS = {
    "Python": "#7C9CFF", "TypeScript": "#2DD4E6", "JavaScript": GOLD,
    "HTML": "#FF8A7A", "CSS": "#B98CFF", "MQL5": "#5BE3A8", "C++": "#F27BC0",
    "C": "#9AA4B8",
}
# Only programming languages I actually write. Repos sometimes carry vendored
# stuff (e.g. a Git installer folder full of HTML docs and Perl), and markup
# would drown out the real code, so HTML/CSS are left out of the bar.
MY_LANGS = set(LANG_COLORS) - {"HTML", "CSS"}


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
    <stop offset="0" stop-color="#0B0A16"/><stop offset="1" stop-color="#05050B"/>
  </linearGradient>
  <linearGradient id="glass" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.10"/>
    <stop offset="1" stop-color="#FFFFFF" stop-opacity="0.03"/>
  </linearGradient>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.38"/>
    <stop offset="0.45" stop-color="#FFFFFF" stop-opacity="0.08"/>
    <stop offset="1" stop-color="#FFFFFF" stop-opacity="0.18"/>
  </linearGradient>
  <linearGradient id="gold" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#F7E3B5"/><stop offset="0.5" stop-color="{GOLD}"/>
    <stop offset="1" stop-color="#B8925A"/>
  </linearGradient>
  <linearGradient id="aurora" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{VIOLET}"/><stop offset="1" stop-color="{TEAL}"/>
  </linearGradient>
  <filter id="blur" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="60"/>
  </filter>
  <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/>
    <feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.035 0"/></filter>
  <g id="blobs" filter="url(#blur)">{blob_svg}</g>
</defs>
<style>
  .b0 {{ animation: drift 18s ease-in-out infinite alternate; }}
  .b1 {{ animation: drift 24s ease-in-out infinite alternate-reverse; }}
  .b2 {{ animation: drift 30s ease-in-out infinite alternate; }}
  @keyframes drift {{ from {{ transform: translate(0,0); }} to {{ transform: translate(40px,-25px); }} }}
  .pulse {{ animation: pulse 2.4s ease-in-out infinite; }}
  @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .35; }} }}
  .rise {{ animation: rise .9s cubic-bezier(.2,.7,.2,1) both; }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: none; }} }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>"""


def canvas(w, h, blobs, body, label):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">
<title>{esc(label)}</title>
{defs(blobs)}
<clipPath id="frame"><rect width="{w}" height="{h}" rx="26"/></clipPath>
<g clip-path="url(#frame)">
  <rect width="{w}" height="{h}" fill="url(#bg)"/>
  <use href="#blobs"/>
  <rect width="{w}" height="{h}" filter="url(#grain)"/>
</g>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="26" fill="none" stroke="#FFFFFF" stroke-opacity="0.10"/>
{body}
</svg>
"""


def glass(x, y, w, h, r=20):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="url(#glass)" '
            f'stroke="url(#edge)" stroke-width="1"/>'
            f'<path d="M{x + r} {y + 0.5} H{x + w - r}" stroke="#FFFFFF" stroke-opacity="0.35" '
            f'stroke-width="1" stroke-linecap="round"/>')


def t(x, y, s, size=14, fill=INK, weight=400, mono=False, anchor="start", extra=""):
    fam = MONO if mono else SANS
    return (f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" {extra}>{esc(s)}</text>')


def pill(x, y, s, size=12, fill=INK, dot=None, mono=True, bg_op=0.07):
    pad = 12 + (12 if dot else 0)
    w = text_w(s, size, mono) + pad + 12
    h = size + 14
    out = (f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{h}" rx="{h / 2}" fill="#FFFFFF" '
           f'fill-opacity="{bg_op}" stroke="#FFFFFF" stroke-opacity="0.12"/>')
    if dot:
        out += f'<circle cx="{x + 14}" cy="{y + h / 2}" r="3.5" fill="{dot}"/>'
    out += t(x + pad, y + h / 2 + size * 0.36, s, size, fill, 500, mono)
    return out, w


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
    for cid, label in re.findall(r'for="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
        m = re.match(r"([\d,]+) contribution", label)
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


# ---------- cards ----------

def hero():
    W, H = 1000, 420
    blobs = [(120, 60, 200, VIOLET, .55), (980, 380, 220, TEAL, .35), (640, 40, 140, GOLD, .22)]
    b = []
    b.append(f'<g class="rise">')
    b.append('<circle class="pulse" cx="62" cy="64" r="4.5" fill="#5BE3A8"/>')
    b.append(t(76, 69, DATA["now"].upper(), 12, MUTED, 500, True, extra='letter-spacing="1.5"'))
    b.append(t(56, 150, DATA["name_first"], 64, INK, 700, extra='letter-spacing="-1.5"'))
    b.append(t(56, 218, DATA["name_last"], 64, "url(#gold)", 700, extra='letter-spacing="-1.5"'))
    b.append(t(56, 268, DATA["headline"], 22, INK, 500))
    for i, line in enumerate(DATA["intro"]):
        b.append(t(56, 302 + i * 23, line, 15.5, MUTED))
    b.append(t(56, 384, DATA["intro_th"], 14, DIM))
    b.append('</g>')

    # glass ID card on the right
    x, y, w, h = 616, 56, 336, 308
    b.append(f'<g class="rise" style="animation-delay:.15s">')
    b.append(glass(x, y, w, h, 22))
    b.append(t(x + 24, y + 38, "ID", 11, GOLD, 600, True, extra='letter-spacing="3"'))
    b.append(t(x + w - 24, y + 38, f"@{USER}", 11, DIM, 500, True, "end"))
    b.append(f'<circle cx="{x + 52}" cy="{y + 88}" r="28" fill="url(#aurora)" opacity=".9"/>')
    b.append(t(x + 52, y + 96, DATA["nickname"][0], 24, "#0B0A16", 700, anchor="middle"))
    b.append(t(x + 94, y + 84, DATA["nickname"], 20, INK, 600))
    b.append(t(x + 94, y + 104, "Computer Engineering", 12.5, MUTED))
    b.append(f'<path d="M{x + 24} {y + 136} H{x + w - 24}" stroke="#FFFFFF" stroke-opacity=".1"/>')
    for i, (k, v) in enumerate(DATA["id_card"]):
        yy = y + 168 + i * 34
        b.append(t(x + 24, yy, k.upper(), 10.5, DIM, 600, True, extra='letter-spacing="1.2"'))
        b.append(t(x + 108, yy, v, 13.5, INK, 500))
    b.append('</g>')
    write("hero.svg", canvas(W, H, blobs, "\n".join(b), f"{DATA['name_first']} {DATA['name_last']}"))


def focus():
    W, H = 1000, 250
    blobs = [(200, 250, 160, TEAL, .28), (820, 0, 180, VIOLET, .45)]
    b = [t(40, 46, "WHAT I WORK ON", 11.5, GOLD, 600, True, extra='letter-spacing="3"')]
    cw, gap = 296, 18
    for i, f in enumerate(DATA["focus"]):
        x = 40 + i * (cw + gap)
        y = 66
        b.append(f'<g class="rise" style="animation-delay:{i * .12:.2f}s">')
        b.append(glass(x, y, cw, 156, 18))
        b.append(t(x + 22, y + 34, f["key"], 22, "url(#gold)", 700, extra='letter-spacing="2"'))
        b.append(t(x + cw - 22, y + 34, f["title"], 12.5, MUTED, 500, anchor="end"))
        for j, line in enumerate(f["lines"]):
            b.append(t(x + 22, y + 66 + j * 21, line, 14.5, INK))
        b.append(t(x + 22, y + 138, f["used"], 11, DIM, 500, True))
        b.append('</g>')
    write("focus.svg", canvas(W, H, blobs, "\n".join(b), "What I work on"))


def project(p, i):
    W, H = 490, 300
    palettes = [(VIOLET, TEAL), (TEAL, GOLD), (GOLD, VIOLET), (VIOLET, "#F27BC0")]
    c1, c2 = palettes[i % 4]
    blobs = [(430, 30, 130, c1, .55), (40, 300, 120, c2, .30)]
    status_dot = {"Live": "#5BE3A8", "Research": GOLD, "Prototype": TEAL}.get(p["status"], VIOLET)
    b = [glass(18, 18, W - 36, H - 36, 20)]
    s, w = pill(40, 40, p["category"].upper(), 10.5, MUTED)
    b.append(s)
    s, _ = pill(40 + w + 8, 40, p["status"], 10.5, INK, status_dot)
    b.append(s)
    b.append(t(W - 42, 60, "↗", 20, GOLD, 500, anchor="end"))
    b.append(t(40, 112, p["title"], 28, INK, 700, extra='letter-spacing="-.5"'))
    for j, line in enumerate(p["lines"]):
        b.append(t(40, 146 + j * 21, line, 14, MUTED))
    x = 40
    for tag in p["tags"]:
        s, w = pill(x, 236, tag, 11, INK, bg_op=.05)
        b.append(s)
        x += w + 8
    write(f"projects/{p['slug']}.svg", canvas(W, H, blobs, "\n".join(b), p["title"]))


def stack():
    W, H = 1000, 250
    blobs = [(80, 40, 150, GOLD, .18), (950, 230, 170, VIOLET, .45)]
    b = [t(40, 46, "TOOLBOX", 11.5, GOLD, 600, True, extra='letter-spacing="3"')]
    dots = [GOLD, TEAL, VIOLET]
    for r, (label, items) in enumerate(DATA["stack"]):
        y = 74 + r * 56
        b.append(glass(40, y, 920, 44, 22))
        b.append(t(62, y + 27, label, 13, MUTED, 600))
        x = 184
        for item in items:
            s, w = pill(x, y + 9, item, 11.5, INK, dots[r], bg_op=.06)
            b.append(s)
            x += w + 8
    write("stack.svg", canvas(W, H, blobs, "\n".join(b), "Toolbox"))


def dashboard():
    W, H = 1000, 380
    blobs = [(900, 40, 190, VIOLET, .5), (120, 380, 180, TEAL, .3), (520, 200, 120, GOLD, .15)]
    days = contributions()
    total = sum(v for d, v in days.items())
    active = sum(1 for v in days.values() if v)
    repo_count, langs = languages()
    today = dt.date.today()

    b = [t(40, 46, "LIVE DASHBOARD", 11.5, GOLD, 600, True, extra='letter-spacing="3"'),
         t(960, 46, f"updated {today:%d %b %Y}", 11, DIM, 500, True, "end")]

    tiles = [(f"{total:,}", "contributions this year"), (str(active), "active days this year"),
             (str(repo_count), "public repos"), (str(len(langs)), "languages I write")]
    tw, gap = 215, 20
    for i, (num, label) in enumerate(tiles):
        x = 40 + i * (tw + gap)
        b.append(f'<g class="rise" style="animation-delay:{i * .08:.2f}s">')
        b.append(glass(x, 66, tw, 104, 18))
        b.append(t(x + 22, 124, num, 38, "url(#gold)" if i == 0 else INK, 700, extra='letter-spacing="-1"'))
        b.append(t(x + 22, 150, label, 12.5, MUTED))
        b.append('</g>')

    # heatmap, last N weeks
    weeks = 30
    b.append(glass(40, 190, 520, 160, 18))
    b.append(t(62, 218, "Last 30 weeks", 13, MUTED, 600))
    ramp = ["#FFFFFF", "#3B2F7A", "#5B47C9", "#8B7BFF", GOLD]
    start = today - dt.timedelta(days=today.weekday() + 1 + 7 * (weeks - 1))  # a Sunday
    cell, step = 12, 15.4
    for wk in range(weeks):
        for dow in range(7):
            d = start + dt.timedelta(days=wk * 7 + dow)
            if d > today:
                continue
            n = days.get(d.isoformat(), 0)
            lvl = 0 if n == 0 else 1 if n < 3 else 2 if n < 6 else 3 if n < 10 else 4
            op = ".06" if lvl == 0 else "1"
            b.append(f'<rect x="{62 + wk * step:.1f}" y="{234 + dow * step:.1f}" width="{cell}" '
                     f'height="{cell}" rx="3" fill="{ramp[lvl]}" fill-opacity="{op}"/>')

    # languages
    b.append(glass(580, 190, 380, 160, 18))
    b.append(t(602, 218, "Code in my repos", 13, MUTED, 600))
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    whole = sum(langs.values()) or 1
    x0, bw = 602, 336
    x = x0
    for name, v in top:
        seg = bw * v / whole
        b.append(f'<rect x="{x:.1f}" y="236" width="{max(seg - 2, 1):.1f}" height="8" rx="4" '
                 f'fill="{LANG_COLORS.get(name, "#9AA4B8")}"/>')
        x += seg
    for i, (name, v) in enumerate(top):
        cx = x0 + (i % 2) * 170
        cy = 272 + (i // 2) * 26
        b.append(f'<circle cx="{cx + 5}" cy="{cy - 4}" r="4.5" fill="{LANG_COLORS.get(name, "#9AA4B8")}"/>')
        b.append(t(cx + 18, cy, name, 13, INK, 500))
        b.append(t(cx + 150, cy, f"{100 * v / whole:.0f}%", 12, DIM, 500, True, "end"))
    write("dashboard.svg", canvas(W, H, blobs, "\n".join(b), "Live GitHub dashboard"))


ICONS = {
    "portfolio": '<circle cx="0" cy="0" r="8" fill="none" stroke="{c}" stroke-width="1.6"/>'
                 '<ellipse cx="0" cy="0" rx="3.5" ry="8" fill="none" stroke="{c}" stroke-width="1.4"/>'
                 '<path d="M-8 0 H8" stroke="{c}" stroke-width="1.4"/>',
    "linkedin": '<rect x="-8" y="-8" width="16" height="16" rx="3.5" fill="{c}"/>'
                '<text x="0" y="4.5" font-family="Arial" font-weight="700" font-size="10.5" '
                'fill="#0B0A16" text-anchor="middle">in</text>',
    "email": '<rect x="-8.5" y="-6" width="17" height="12" rx="2.5" fill="none" stroke="{c}" stroke-width="1.6"/>'
             '<path d="M-8 -5 L0 1 L8 -5" fill="none" stroke="{c}" stroke-width="1.6"/>',
    "instagram": '<rect x="-8" y="-8" width="16" height="16" rx="5" fill="none" stroke="{c}" stroke-width="1.6"/>'
                 '<circle r="3.6" fill="none" stroke="{c}" stroke-width="1.6"/><circle cx="4.4" cy="-4.4" r="1.1" fill="{c}"/>',
    "facebook": '<circle r="8.5" fill="{c}"/><text x="1" y="5.5" font-family="Arial" font-weight="700" '
                'font-size="13" fill="#0B0A16" text-anchor="middle">f</text>',
}


def buttons():
    for key, label, _ in DATA["links"]:
        W, H = 180, 56
        c = GOLD if key == "portfolio" else INK
        body = (f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="28" fill="url(#bg)" '
                f'stroke="url(#edge)"/>'
                f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="28" fill="url(#glass)"/>'
                f'<g transform="translate(34 28)">{ICONS[key].format(c=c)}</g>'
                + t(56, 33, label, 14.5, c, 600))
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
               f'role="img" aria-label="{esc(label)}"><title>{esc(label)}</title>{defs([])}{body}</svg>\n')
        write(f"links/{key}.svg", svg)


def footer():
    W, H = 1000, 90
    blobs = [(500, 120, 200, VIOLET, .45)]
    body = t(500, 52, "Thanks for stopping by. Say hi any time.", 15, MUTED, 500, anchor="middle")
    write("footer.svg", canvas(W, H, blobs, body, "Thanks for stopping by"))


if __name__ == "__main__":
    import sys
    only_dashboard = "--dashboard" in sys.argv
    if not only_dashboard:
        hero()
        focus()
        for i, p in enumerate(DATA["projects"]):
            project(p, i)
        stack()
        buttons()
        footer()
    dashboard()
