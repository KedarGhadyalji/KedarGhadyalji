#!/usr/bin/env python3
"""
Generates the dynamic profile cards straight from the GitHub GraphQL API and
writes them to /profile as plain SVG files (Rose Dusk theme).

No third-party image hosts (vercel / heroku / demolab) are involved, so the
cards can't "stop loading" because someone else's server is down or rate-limited.

Usage (in CI):   GH_TOKEN=... GH_USER=KedarGhadyalji python scripts/generate_cards.py
Local preview:   python scripts/generate_cards.py --mock
"""
import glob
import json
import os
import random
import re
import sys
import textwrap
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import escape

# ---- Themes: Rose Dusk (dark) + Rose Dawn (light) ---------------------------
THEMES = {
    "dark": dict(BG="#191724", BORDER="#403D52", ACCENT="#EBBCBA", ACCENT2="#C4A7E7", TEXT="#E0DEF4",
                 MUTED="#908CAA", GRID="#2A273F", CHIP="#26233A", CHIPB="#524F67",
                 LANG_COLORS=["#EBBCBA", "#C4A7E7", "#9CCFD8", "#F6C177", "#EA9A97", "#31748F", "#E0DEF4", "#908CAA"]),
    "light": dict(BG="#FFFAF3", BORDER="#E4D8CE", ACCENT="#B4637A", ACCENT2="#907AA9", TEXT="#575279",
                  MUTED="#797593", GRID="#EFE6DE", CHIP="#F2E9E1", CHIPB="#D9CBBF",
                  LANG_COLORS=["#B4637A", "#907AA9", "#56949F", "#EA9D34", "#D7827E", "#286983", "#575279", "#9893A5"]),
}
MODE = "dark"


def set_theme(mode):
    """Swap the module-level colour constants so every card function renders in that theme."""
    global MODE
    MODE = mode
    globals().update(THEMES[mode])


set_theme("dark")
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "profile")
USER = os.environ.get("GH_USER", "KedarGhadyalji")
TOKEN = os.environ.get("GH_TOKEN", "")
MOCK = "--mock" in sys.argv
README_PATH = os.environ.get("README_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "README.md"))
PROJECTS_PATH = os.environ.get("PROJECTS_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "projects.json"))


# ---- Data -------------------------------------------------------------------
def gql(query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json",
                 "User-Agent": "profile-cards"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


PROFILE_Q = """
query($login:String!){
  user(login:$login){
    name createdAt
    followers{totalCount}
    pullRequests{totalCount}
    issues{totalCount}
    repositoriesContributedTo(first:1, contributionTypes:[COMMIT,ISSUE,PULL_REQUEST,REPOSITORY]){totalCount}
    contributionsCollection{totalCommitContributions restrictedContributionsCount}
    repositories(first:100, ownerAffiliations:OWNER, isFork:false){
      totalCount
      nodes{
        stargazerCount
        languages(first:10, orderBy:{field:SIZE, direction:DESC}){edges{size node{name}}}
      }
    }
  }
}"""

CAL_Q = """
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    contributionsCollection(from:$from,to:$to){
      contributionCalendar{weeks{contributionDays{date contributionCount}}}
    }
  }
}"""


def fetch_real():
    u = gql(PROFILE_Q, {"login": USER})["user"]
    repos = u["repositories"]["nodes"]
    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]

    created = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00")).year
    today = date.today()
    days = {}
    for year in range(created, today.year + 1):
        frm = f"{year}-01-01T00:00:00Z"
        to = f"{year}-12-31T23:59:59Z"
        data = gql(CAL_Q, {"login": USER, "from": frm, "to": to})["user"]
        for w in data["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]

    cc = u["contributionsCollection"]
    return {
        "name": u["name"] or USER,
        "stars": sum(r["stargazerCount"] for r in repos),
        "commits": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "contributed_to": u["repositoriesContributedTo"]["totalCount"],
        "repos": u["repositories"]["totalCount"],
        "followers": u["followers"]["totalCount"],
        "langs": langs,
        "days": days,
    }


def fetch_mock():
    random.seed(7)
    today = date.today()
    days = {}
    for i in range(900):
        d = today - timedelta(days=i)
        days[d.isoformat()] = 0 if random.random() < 0.35 else random.randint(1, 9)
    for i in range(0, 12):  # a recent streak
        days[(today - timedelta(days=i)).isoformat()] = random.randint(1, 6)
    return {
        "name": "Kedar Ghadyalji", "stars": 14, "commits": 612, "prs": 23, "issues": 6,
        "contributed_to": 9, "repos": 27, "followers": 31,
        "langs": {"JavaScript": 52000, "TypeScript": 31000, "Python": 24000, "CSS": 12000,
                  "HTML": 9000, "Java": 4000, "C++": 2500},
        "days": days,
    }


# ---- Helpers ----------------------------------------------------------------
def fmt_d(d):
    return f"{d:%b} {d.day}"


def card(w, h, inner, label):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}">
<defs>
  <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{ACCENT}" stop-opacity=".45"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{ACCENT2}"/><stop offset="1" stop-color="{ACCENT}"/>
  </linearGradient>
</defs>
<style>
  .title{{font:700 17px {FONT};fill:{ACCENT}}}
  .lbl{{font:500 13px {FONT};fill:{MUTED}}}
  .val{{font:700 14px {FONT};fill:{TEXT}}}
  .big{{font:800 32px {FONT};fill:{TEXT}}}
  .mid{{font:700 14px {FONT};fill:{ACCENT}}}
  .sub{{font:400 12px {FONT};fill:{MUTED}}}
  .ax{{font:400 11px {FONT};fill:{MUTED}}}
  .pt{{font:600 10px {FONT};fill:{TEXT}}}
  .in{{animation:fade .8s ease both}}
  @keyframes fade{{from{{opacity:0}}}}
</style>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>
{inner}
</svg>"""


def write(name, svg):
    name = name.replace(".svg", f"-{MODE}.svg")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", name)


# ---- Cards ------------------------------------------------------------------
def stats_card(d):
    W, H = 495, 195
    last_year = date.today() - timedelta(days=365)
    year_total = sum(c for k, c in d["days"].items() if date.fromisoformat(k) > last_year)
    rows = [("Total Stars", d["stars"]), ("Commits (past year)", d["commits"]),
            ("Pull Requests", d["prs"]), ("Issues", d["issues"]),
            ("Contributed To", d["contributed_to"]), ("Public Repos", d["repos"])]
    out = f'<text x="25" y="35" class="title">{escape(d["name"])}\'s GitHub Stats</text>'
    for i, (k, v) in enumerate(rows):
        y = 66 + i * 22
        out += (f'<g class="in" style="animation-delay:{i * 0.1:.1f}s">'
                f'<rect x="25" y="{y - 9}" width="8" height="8" rx="2" fill="{ACCENT2}"/>'
                f'<text x="44" y="{y}" class="lbl">{k}</text>'
                f'<text x="250" y="{y}" class="val" text-anchor="end">{v:,}</text></g>')
    # ring: contributions in the past year (target 1000 for a full ring)
    cx, cy, r = 392, 92, 38
    circ = 2 * 3.14159265 * r
    frac = min(year_total / 1000, 1)
    out += (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{GRID}" stroke-width="8"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#bar)" stroke-width="8" stroke-linecap="round" '
            f'stroke-dasharray="{circ * frac:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cy})"/>'
            f'<text x="{cx}" y="{cy + 7}" class="val" text-anchor="middle" style="font-size:20px">{year_total:,}</text>'
            f'<text x="{cx}" y="{cy + 58}" class="sub" text-anchor="middle">contributions</text>'
            f'<text x="{cx}" y="{cy + 73}" class="sub" text-anchor="middle">in the past year</text>')
    write("stats.svg", card(W, H, out, "GitHub stats"))


def langs_card(d):
    W, H = 495, 195
    items = sorted(d["langs"].items(), key=lambda kv: kv[1], reverse=True)
    top, rest = items[:7], sum(v for _, v in items[7:])
    if rest:
        top.append(("Other", rest))
    total = sum(v for _, v in top) or 1
    out = f'<text x="25" y="35" class="title">Most Used Languages</text>'
    # stacked bar
    bx, bw, by = 25, W - 50, 52
    out += f'<clipPath id="r"><rect x="{bx}" y="{by}" width="{bw}" height="12" rx="6"/></clipPath><g clip-path="url(#r)">'
    x = bx
    for i, (n, v) in enumerate(top):
        w = bw * v / total
        out += f'<rect x="{x:.2f}" y="{by}" width="{w + 0.5:.2f}" height="12" fill="{LANG_COLORS[i % len(LANG_COLORS)]}"/>'
        x += w
    out += "</g>"
    for i, (n, v) in enumerate(top):
        col, row = divmod(i, 4)
        lx, ly = 25 + col * 235, 96 + row * 25
        out += (f'<g class="in" style="animation-delay:{i * 0.08:.2f}s">'
                f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{LANG_COLORS[i % len(LANG_COLORS)]}"/>'
                f'<text x="{lx + 18}" y="{ly}" class="val" style="font-weight:600">{escape(n)}</text>'
                f'<text x="{lx + 205}" y="{ly}" class="lbl" text-anchor="end">{100 * v / total:.1f}%</text></g>')
    write("top-langs.svg", card(W, H, out, "Most used languages"))


def streak_stats(days):
    today = date.today()
    counts = {date.fromisoformat(k): v for k, v in days.items() if date.fromisoformat(k) <= today}
    total = sum(counts.values())
    first = min((k for k, v in counts.items() if v > 0), default=today)

    # current streak (today may still be empty)
    cur_end = today if counts.get(today, 0) > 0 else today - timedelta(days=1)
    cur, d = 0, cur_end
    while counts.get(d, 0) > 0:
        cur += 1
        d -= timedelta(days=1)
    cur_start = cur_end - timedelta(days=cur - 1) if cur else None

    # longest streak
    best, run, run_start, best_range = 0, 0, None, None
    day = min(counts) if counts else today
    while day <= today:
        if counts.get(day, 0) > 0:
            run += 1
            run_start = run_start or day
            if run > best:
                best, best_range = run, (run_start, day)
        else:
            run, run_start = 0, None
        day += timedelta(days=1)
    return total, first, cur, (cur_start, cur_end), best, best_range


def streak_card(d):
    W, H = 990, 150
    total, first, cur, cur_rng, best, best_rng = streak_stats(d["days"])
    cols = [
        (W / 6, f"{total:,}", "Total Contributions", f"{fmt_d(first)}, {first.year} - Present"),
        (W / 2, f"{cur}", "Current Streak", f"{fmt_d(cur_rng[0])} - {fmt_d(cur_rng[1])}" if cur else "Commit today to start one"),
        (5 * W / 6, f"{best}", "Longest Streak",
         f"{fmt_d(best_rng[0])} - {fmt_d(best_rng[1])}" if best_rng else "-"),
    ]
    out = ""
    for i, (cx, big, label, sub) in enumerate(cols):
        out += (f'<g class="in" style="animation-delay:{i * 0.15:.2f}s">'
                f'<text x="{cx:.0f}" y="62" class="big" text-anchor="middle">{big}</text>'
                f'<text x="{cx:.0f}" y="92" class="mid" text-anchor="middle">{label}</text>'
                f'<text x="{cx:.0f}" y="114" class="sub" text-anchor="middle">{sub}</text></g>')
    out += (f'<rect x="{W / 3:.0f}" y="30" width="1.5" height="90" rx=".75" fill="{BORDER}"/>'
            f'<rect x="{2 * W / 3:.0f}" y="30" width="1.5" height="90" rx=".75" fill="{BORDER}"/>')
    # progress bar under the current streak (full at 30 days)
    frac = min(cur / 30, 1)
    out += (f'<rect x="{W / 2 - 50:.0f}" y="124" width="100" height="4" rx="2" fill="{GRID}"/>'
            f'<rect x="{W / 2 - 50:.0f}" y="124" width="{100 * frac:.0f}" height="4" rx="2" fill="url(#bar)"/>')
    write("streak.svg", card(W, H, out, "Contribution streak"))


def activity_card(d, span=60):
    W, H = 990, 300
    today = date.today()
    pts = [(today - timedelta(days=span - 1 - i)) for i in range(span)]
    vals = [d["days"].get(p.isoformat(), 0) for p in pts]
    vmax = max(max(vals), 4)
    step = 1 if vmax <= 6 else 2 if vmax <= 12 else 5 if vmax <= 30 else 10
    ymax = ((vmax + step - 1) // step) * step

    L, R, T, B = 52, W - 28, 62, H - 44
    xs = [L + (R - L) * i / (span - 1) for i in range(span)]
    ys = [B - (B - T) * v / ymax for v in vals]

    out = f'<text x="28" y="36" class="title">Contribution Activity</text>'
    best_i = max(range(span), key=lambda i: (vals[i], i))  # latest day wins ties
    best_txt = f" · best day {fmt_d(pts[best_i])} ({vals[best_i]})" if vals[best_i] else ""
    out += f'<text x="{W - 28}" y="36" class="sub" text-anchor="end">last {span} days · {sum(vals)} contributions{best_txt}</text>'
    for t in range(0, ymax + 1, step):
        y = B - (B - T) * t / ymax
        out += (f'<line x1="{L}" y1="{y:.1f}" x2="{R}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>'
                f'<text x="{L - 10}" y="{y + 4:.1f}" class="ax" text-anchor="end">{t}</text>')
    for i in range(0, span, 10):
        out += f'<text x="{xs[i]:.1f}" y="{H - 18}" class="ax" text-anchor="middle">{fmt_d(pts[i])}</text>'
    out += f'<text x="{xs[-1]:.1f}" y="{H - 18}" class="ax" text-anchor="end">{fmt_d(pts[-1])}</text>'

    # one bar per day; only the best day, today and a few of the tallest days get a number
    colw = (R - L) / (span - 1)
    bw = colw * 0.64
    labelled = {best_i}
    if vals[-1]:
        labelled.add(span - 1)
    for v, i in sorted(((v, i) for i, v in enumerate(vals) if v), key=lambda t: (-t[0], -t[1])):
        if len(labelled) >= 6:
            break
        if all(abs(i - j) >= 3 for j in labelled):  # keep numbers from crowding each other
            labelled.add(i)

    for i, (x, y, v) in enumerate(zip(xs, ys, vals)):
        if not v:
            continue
        if i == best_i:
            fill, op = ACCENT, 1
        elif i in labelled:
            fill, op = ACCENT2, 0.9
        else:
            fill, op = ACCENT, 0.45
        out += (f'<rect x="{x - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{B - y:.1f}" rx="2" '
                f'fill="{fill}" fill-opacity="{op}"/>')
        if i in labelled:
            out += f'<text x="{x:.1f}" y="{y - 6:.1f}" class="pt" text-anchor="middle">{v}</text>'
    # Native tooltips: only shown when the SVG is opened on its own (GitHub shows README images as plain <img>).
    for i, (x, v) in enumerate(zip(xs, vals)):
        tip = f"{pts[i]:%a}, {fmt_d(pts[i])}: {v} contribution{'s' if v != 1 else ''}"
        out += f'<rect x="{x - colw / 2:.1f}" y="{T}" width="{colw:.1f}" height="{B - T}" fill="transparent"><title>{tip}</title></rect>'
    write("activity.svg", card(W, H, out, "Contribution activity graph"))


def ellipsize(text, n):
    return text if len(text) <= n else text[: n - 1].rstrip() + "\u2026"


def star_pts(cx, cy, r):
    import math
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append(f"{cx + rad * math.cos(ang):.1f},{cy + rad * math.sin(ang):.1f}")
    return " ".join(pts)


REPO_Q = "query($o:String!,$n:String!){repository(owner:$o,name:$n){stargazerCount forkCount}}"


def repo_stats(repo):
    if MOCK:
        return random.randint(0, 9), random.randint(0, 3)
    try:
        r = gql(REPO_Q, {"o": repo.split("/")[0], "n": repo.split("/")[1]})["repository"]
        return r["stargazerCount"], r["forkCount"]
    except Exception as e:  # missing or private repo: show the card without stats
        print(f"  note: no stats for {repo} ({str(e)[:60]})")
        return None, None


def project_card(p, idx, stars, forks):
    W, H = 495, 256
    out = (f'<rect x="24" y="19" width="12" height="15" rx="2.5" fill="none" stroke="{ACCENT}" stroke-width="1.6"/>'
           f'<rect x="27" y="23" width="6" height="1.6" rx=".8" fill="{ACCENT}"/>'
           f'<text x="46" y="32" class="title" style="font-size:16px">{escape(ellipsize(p["title"], 26))}</text>')

    kind = ellipsize(p.get("kind", ""), 22)
    if kind:
        kw = int(len(kind) * 6.4 + 20)
        out += (f'<rect x="{W - 24 - kw}" y="17" width="{kw}" height="22" rx="11" fill="none" stroke="{ACCENT2}" stroke-width="1"/>'
                f'<text x="{W - 24 - kw / 2:.0f}" y="32" class="sub" text-anchor="middle" style="fill:{ACCENT2}">{escape(kind)}</text>')

    lines = textwrap.wrap(p["description"].strip(), 58)
    if len(lines) > 3:
        lines = lines[:2] + [ellipsize(" ".join(lines[2:]), 58)]
    for i, ln in enumerate(lines):
        out += f'<text x="24" y="{66 + i * 18}" class="lbl" style="fill:{TEXT};font-weight:400">{escape(ln)}</text>'

    if p.get("highlight"):
        out += (f'<polygon points="30,129 35,134 30,139 25,134" fill="{ACCENT}"/>'
                f'<text x="44" y="138" class="lbl" style="fill:{ACCENT};font-weight:600">{escape(ellipsize(p["highlight"], 52))}</text>')

    x, y = 24, 156
    for t in p["stack"]:
        w = int(len(t) * 6.6 + 20)
        if x + w > W - 24:
            x, y = 24, y + 30
        if y > 186:
            break
        out += (f'<rect x="{x}" y="{y}" width="{w}" height="23" rx="11.5" fill="{CHIP}" stroke="{CHIPB}"/>'
                f'<text x="{x + w / 2:.0f}" y="{y + 16}" class="sub" text-anchor="middle" style="fill:{TEXT}">{escape(t)}</text>')
        x += w + 8

    if stars is not None:
        fx, fy = 24, 239
        out += (f'<polygon points="{star_pts(fx + 7, fy - 5, 7)}" fill="none" stroke="{MUTED}" stroke-width="1.4" stroke-linejoin="round"/>'
                f'<text x="{fx + 20}" y="{fy}" class="lbl">{stars:,}</text>')
        fx += 20 + int(len(str(stars)) * 7.5) + 18
        out += (f'<g fill="none" stroke="{MUTED}" stroke-width="1.4" stroke-linecap="round">'
                f'<circle cx="{fx + 3}" cy="{fy - 10}" r="2.2"/><circle cx="{fx + 11}" cy="{fy - 10}" r="2.2"/>'
                f'<circle cx="{fx + 7}" cy="{fy}" r="2.2"/>'
                f'<path d="M{fx + 3} {fy - 7.8}v2q0 2 2 2h4q2 0 2-2v-2M{fx + 7} {fy - 4}v1.8"/></g>'
                f'<text x="{fx + 20}" y="{fy}" class="lbl">{forks:,}</text>')
    out += (f'<text x="{W - 24}" y="239" class="sub" text-anchor="end" style="fill:{MUTED}">View repository \u2192</text>')
    write(f"project-{idx + 1}.svg", card(W, H, f'<g class="in" style="animation-delay:{idx * 0.08:.2f}s">{out}</g>', f'Project {p["title"]}'))


def load_projects():
    try:
        return json.load(open(PROJECTS_PATH, encoding="utf-8"))
    except FileNotFoundError:
        print("no data/projects.json, skipping project cards")
        return []


def update_readme_projects(projects):
    def pic(name, w, alt):
        return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="profile/{name}-dark.svg"/>'
                f'<img src="profile/{name}-light.svg" width="{w}" alt="{alt}"/></picture>')
    cells = "\n".join(
        f'<a href="https://github.com/{escape(p["repo"])}">{pic(f"project-{i + 1}", "49%", escape(p["title"]) + " project card")}</a>'
        for i, p in enumerate(projects))
    block = f'<!--PROJECTS:START-->\n<div align="center">\n\n{cells}\n\n</div>\n<!--PROJECTS:END-->'
    try:
        text = open(README_PATH, encoding="utf-8").read()
    except FileNotFoundError:
        return
    new, n = re.subn(r"<!--PROJECTS:START-->.*?<!--PROJECTS:END-->", lambda _: block, text, flags=re.S)
    if n:
        open(README_PATH, "w", encoding="utf-8").write(new)
        print("updated projects section in README")
    else:
        print("README has no PROJECTS markers; cards written but README not changed")


def main():
    if not MOCK and not TOKEN:
        sys.exit("GH_TOKEN is not set (use --mock for a local preview).")
    data = fetch_mock() if MOCK else fetch_real()
    projects = load_projects()
    stats = {p["repo"]: repo_stats(p["repo"]) for p in projects}  # fetched once, drawn in both themes

    # clear cards from older layouts (unsuffixed files, retired pins, removed projects)
    for pattern in ("pin-*.svg", "project-*.svg", "stats*.svg", "top-langs*.svg", "streak*.svg", "activity*.svg"):
        for old in glob.glob(os.path.join(OUT_DIR, pattern)):
            os.remove(old)

    for mode in ("dark", "light"):
        set_theme(mode)
        stats_card(data)
        langs_card(data)
        streak_card(data)
        activity_card(data)
        for i, p in enumerate(projects):
            project_card(p, i, *stats[p["repo"]])
    if projects:
        update_readme_projects(projects)


if __name__ == "__main__":
    main()
