"""Generate monochrome GitHub stats cards (assets/stats.svg, assets/graph.svg).

Runs in GitHub Actions with GITHUB_TOKEN; locally: GITHUB_TOKEN=$(gh auth token) python scripts/stats.py
"""
import datetime as dt
import json
import os
import urllib.request
from html import escape

USER = os.environ.get("GH_USER", "NikitaDm1trievich")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")

BG, BORDER, FG, MUTED, GRID = "#0d1117", "#30363d", "#ffffff", "#c9d1d9", "#21262d"
FONT = "'Segoe UI',Ubuntu,'Helvetica Neue',Sans-Serif"

QUERY = """
query($login: String!, $from: DateTime!) {
  user(login: $login) {
    name
    repositories(ownerAffiliations: OWNER, first: 100, privacy: PUBLIC) {
      totalCount
      nodes { stargazerCount }
    }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
    year: contributionsCollection(from: $from) {
      totalCommitContributions
      restrictedContributionsCount
    }
    last: contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def gql():
    year_start = dt.datetime(dt.date.today().year, 1, 1).isoformat() + "Z"
    body = json.dumps({"query": QUERY, "variables": {"login": USER, "from": year_start}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]


def stats_card(u):
    stars = sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
    commits = u["year"]["totalCommitContributions"] + u["year"]["restrictedContributionsCount"]
    total = u["last"]["contributionCalendar"]["totalContributions"]
    rows = [
        ("★", "Total Stars Earned", stars),
        ("⎇", f"Total Commits ({dt.date.today().year})", commits),
        ("⇄", "Total PRs", u["pullRequests"]["totalCount"]),
        ("◉", "Total Issues", u["issues"]["totalCount"]),
        ("▣", "Contributed to", u["repositoriesContributedTo"]["totalCount"]),
    ]
    lines = []
    for i, (icon, label, value) in enumerate(rows):
        y = 70 + i * 25
        lines.append(
            f'<text x="25" y="{y}" fill="{FG}" font-size="14">{icon}</text>'
            f'<text x="50" y="{y}" fill="{MUTED}" font-size="14" font-weight="600">{escape(label)}:</text>'
            f'<text x="250" y="{y}" fill="{FG}" font-size="14" font-weight="700">{value}</text>'
        )
    name = escape(u["name"] or USER)
    # ring shows contributions in the last year, capped at 365 for the arc
    frac = min(total, 365) / 365
    circ = 2 * 3.14159 * 40
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="467" height="195" viewBox="0 0 467 195" font-family="{FONT}">
  <rect x="0.5" y="0.5" width="466" height="194" rx="4.5" fill="{BG}" stroke="{BORDER}"/>
  <text x="25" y="35" fill="{FG}" font-size="18" font-weight="600">{name}'s GitHub Stats</text>
  {''.join(lines)}
  <g transform="translate(390 100)">
    <circle r="40" fill="none" stroke="{GRID}" stroke-width="6"/>
    <circle r="40" fill="none" stroke="{FG}" stroke-width="6" stroke-linecap="round"
      stroke-dasharray="{circ * frac:.1f} {circ:.1f}" transform="rotate(-90)"/>
    <text y="4" text-anchor="middle" fill="{FG}" font-size="22" font-weight="700">{total}</text>
    <text y="22" text-anchor="middle" fill="{MUTED}" font-size="10">last year</text>
  </g>
</svg>
"""


def graph_card(u, days=31):
    all_days = [d for w in u["last"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    pts = all_days[-days:]
    W, H, L, R, T, B = 900, 300, 60, 20, 50, 50
    pw, ph = W - L - R, H - T - B
    top = max(4, max(p["contributionCount"] for p in pts))
    xs = [L + i * pw / (len(pts) - 1) for i in range(len(pts))]
    ys = [T + ph - p["contributionCount"] / top * ph for p in pts]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"{L},{T + ph} {line} {L + pw},{T + ph}"
    grid, labels = [], []
    for i in range(5):
        v = round(top * i / 4)
        y = T + ph - ph * i / 4
        grid.append(f'<line x1="{L}" x2="{L + pw}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}"/>')
        labels.append(f'<text x="{L - 10}" y="{y + 4:.1f}" text-anchor="end" fill="{MUTED}" font-size="11">{v}</text>')
    for x, p in zip(xs, pts):
        labels.append(f'<text x="{x:.1f}" y="{T + ph + 18}" text-anchor="middle" fill="{MUTED}" font-size="10">{int(p["date"][-2:])}</text>')
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{FG}"/>' for x, y in zip(xs, ys))
    name = escape(u["name"] or USER)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="4.5" fill="{BG}" stroke="{BORDER}"/>
  <text x="{W / 2}" y="30" text-anchor="middle" fill="{FG}" font-size="16" font-weight="600">{name}'s Contribution Graph</text>
  {''.join(grid)}
  <polygon points="{area}" fill="{FG}" opacity="0.08"/>
  <polyline points="{line}" fill="none" stroke="{FG}" stroke-width="2"/>
  {dots}
  {''.join(labels)}
  <text x="{W / 2}" y="{H - 10}" text-anchor="middle" fill="{MUTED}" font-size="11">Days</text>
  <text x="18" y="{T + ph / 2}" text-anchor="middle" fill="{MUTED}" font-size="11" transform="rotate(-90 18 {T + ph / 2})">Contributions</text>
</svg>
"""


def main():
    u = gql()
    os.makedirs(OUT, exist_ok=True)
    for name, svg in (("stats.svg", stats_card(u)), ("graph.svg", graph_card(u))):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)


if __name__ == "__main__":
    main()
