import os
import sys
import requests

USERNAME = "jabaharjagadishbaral"
TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")

if not TOKEN:
    print("No token found. Set GH_PAT (recommended) or GITHUB_TOKEN.")
    sys.exit(1)

HEADERS = {"Authorization": f"bearer {TOKEN}"}
GRAPHQL_URL = "https://api.github.com/graphql"


def run_query(query, variables=None):
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables or {}},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        print(data["errors"])
        sys.exit(1)
    return data["data"]


def fetch_user_data():
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          totalCount
          nodes {
            stargazerCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node { name }
              }
            }
          }
        }
      }
    }
    """
    data = run_query(query, {"login": USERNAME})
    return data["user"]


def compute_streaks(weeks):
    days = []
    for w in weeks:
        days.extend(w["contributionDays"])
    days.sort(key=lambda d: d["date"])

    longest = 0
    running = 0
    for d in days:
        if d["contributionCount"] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0

    current = 0
    for d in reversed(days):
        if d["contributionCount"] > 0:
            current += 1
        else:
            break

    return current, longest


def main():
    user = fetch_user_data()
    cc = user["contributionsCollection"]

    total_stars = sum(r["stargazerCount"] for r in user["repositories"]["nodes"])
    total_commits = cc["totalCommitContributions"]
    total_prs = cc["totalPullRequestContributions"]
    total_issues = cc["totalIssueContributions"]
    current_streak, longest_streak = compute_streaks(
        cc["contributionCalendar"]["weeks"]
    )

    lang_bytes = {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            lang_bytes[name] = lang_bytes.get(name, 0) + edge["size"]

    total_bytes = sum(lang_bytes.values()) or 1
    top_langs = sorted(lang_bytes.items(), key=lambda kv: kv[1], reverse=True)[:5]

    lang_colors = {
        "Python": "#3776ab",
        "Java": "#e76f00",
        "JavaScript": "#f1e05a",
        "HTML": "#e34c26",
        "CSS": "#563d7c",
        "TypeScript": "#3178c6",
        "Jupyter Notebook": "#DA5B0B",
        "C": "#555555",
        "C++": "#f34b7d",
    }
    default_color = "#7c3aed"

    stats_svg = f'''<svg width="480" height="200" viewBox="0 0 480 200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <clipPath id="statsRounded"><rect width="480" height="200" rx="16"/></clipPath>
    <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2563eb"/>
      <stop offset="100%" stop-color="#7c3aed"/>
    </linearGradient>
  </defs>
  <g clip-path="url(#statsRounded)">
    <rect width="480" height="200" fill="#111827"/>
    <text x="20" y="30" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="bold" fill="#ffffff">GitHub Stats</text>

    <g transform="translate(90,115)">
      <circle r="55" fill="none" stroke="#ffffff10" stroke-width="10"/>
      <circle r="55" fill="none" stroke="url(#ringGrad)" stroke-width="10" stroke-linecap="round"
        stroke-dasharray="345" stroke-dashoffset="345" transform="rotate(-90)">
        <animate attributeName="stroke-dashoffset" from="345" to="60" dur="1.6s" begin="0.3s" fill="freeze"/>
      </circle>
      <text text-anchor="middle" dy="-2" font-family="Segoe UI, Arial, sans-serif" font-size="20" font-weight="bold" fill="#ffffff">{total_commits}</text>
      <text text-anchor="middle" dy="16" font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="#93c5fd">commits/yr</text>
    </g>

    <g font-family="Segoe UI, Arial, sans-serif" font-size="13" fill="#c4b5fd">
      <text x="190" y="60">⭐ Total Stars</text>
      <text x="440" y="60" text-anchor="end" fill="#38bdf8">{total_stars}</text>

      <text x="190" y="90">📦 Repos</text>
      <text x="440" y="90" text-anchor="end" fill="#38bdf8">{user["repositories"]["totalCount"]}</text>

      <text x="190" y="120">🔀 Pull Requests</text>
      <text x="440" y="120" text-anchor="end" fill="#93c5fd">{total_prs}</text>

      <text x="190" y="150">🐛 Issues</text>
      <text x="440" y="150" text-anchor="end" fill="#93c5fd">{total_issues}</text>

      <text x="190" y="180">🔥 Streak: {current_streak}d current / {longest_streak}d best</text>
    </g>
  </g>
</svg>
'''

    lang_rows = ""
    y = 58
    for i, (name, size) in enumerate(top_langs):
        pct = round((size / total_bytes) * 100, 1)
        bar_w = round((size / total_bytes) * 360)
        color = lang_colors.get(name, default_color)
        lang_rows += f'''
      <text x="20" y="{y}">{name}</text>
      <rect x="90" y="{y-10}" width="360" height="12" rx="6" fill="#ffffff10"/>
      <rect x="90" y="{y-10}" height="12" rx="6" fill="{color}" width="0"><animate attributeName="width" from="0" to="{bar_w}" dur="1s" begin="{0.3 + i*0.2}s" fill="freeze"/></rect>
      <text x="460" y="{y}" text-anchor="end">{pct}%</text>
'''
        y += 30

    langs_svg = f'''<svg width="480" height="200" viewBox="0 0 480 200" xmlns="http://www.w3.org/2000/svg">
  <defs><clipPath id="langsRounded"><rect width="480" height="200" rx="16"/></clipPath></defs>
  <g clip-path="url(#langsRounded)">
    <rect width="480" height="200" fill="#111827"/>
    <text x="20" y="30" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="bold" fill="#ffffff">Most Used Languages</text>
    <g font-family="Segoe UI, Arial, sans-serif" font-size="13" fill="#c4b5fd">{lang_rows}
    </g>
  </g>
</svg>
'''

    with open("stats.svg", "w", encoding="utf-8") as f:
        f.write(stats_svg)

    with open("langs.svg", "w", encoding="utf-8") as f:
        f.write(langs_svg)

    print("stats.svg and langs.svg regenerated with live data.")


if __name__ == "__main__":
    main()
