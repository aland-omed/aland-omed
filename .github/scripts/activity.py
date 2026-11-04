#!/usr/bin/env python3
"""Draws assets for the profile README from live GitHub data: dist/activity.svg.
Needs: fonttools, env GITHUB_TOKEN, USER_LOGIN. Text is outlined from Hanken Grotesk (OFL)."""
import datetime, json, os, sys, urllib.request
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

VOID, FIELD, CORE, SIGNAL = "#080A1E", "#141830", "#F4EFEB", "#FF3D00"
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = {w: TTFont(os.path.join(HERE, "..", "fonts", f"HankenGrotesk-{w}.ttf")) for w in ("ExtraBold", "SemiBold", "Medium")}
LOGIN = os.environ.get("USER_LOGIN", "aland-omed")


def measure(t, w, size, track=0):
    f = FONTS[w]; cm = f.getBestCmap(); hm = f["hmtx"]; s = size / f["head"].unitsPerEm
    return sum(hm[cm.get(ord(c), cm[32])][0] for c in t) * s + track * max(len(t) - 1, 0)


def tp(t, w, size, x, y, fill, anchor="start", track=0, op=1):
    f = FONTS[w]; cm = f.getBestCmap(); hm = f["hmtx"]; gs = f.getGlyphSet(); s = size / f["head"].unitsPerEm
    wd = measure(t, w, size, track)
    cx = x - (wd / 2 if anchor == "middle" else wd if anchor == "end" else 0)
    pen = SVGPathPen(gs, ntos=lambda v: ("%.1f" % v).rstrip("0").rstrip("."))
    for c in t:
        g = cm.get(ord(c), cm[32])
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, cx, y)))
        cx += hm[g][0] * s + track
    o = f' opacity="{op}"' if op != 1 else ""
    return f'<path d="{pen.getCommands()}" fill="{fill}"{o}/>'


QUERY = """query($login:String!){user(login:$login){followers{totalCount}
repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:100){totalCount nodes{stargazerCount
languages(first:6,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}
contributionsCollection{totalCommitContributions contributionCalendar{totalContributions
weeks{contributionDays{contributionCount date}}}}}}"""


def fetch():
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
                                 headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"], "Content-Type": "application/json", "User-Agent": "profile-readme"})
    d = json.load(urllib.request.urlopen(req))
    if "errors" in d: sys.exit(str(d["errors"]))
    return d["data"]["user"]


def build(u):
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    today = datetime.date.today().isoformat()
    counts = [d["contributionCount"] for d in days if d["date"] <= today]
    longest = cur = 0
    for c in counts:
        cur = cur + 1 if c else 0; longest = max(longest, cur)
    cur = 0
    for c in reversed(counts):
        if c: cur += 1
        elif cur or c == 0 and counts[-1] == 0 and cur == 0 and False: break
        else:
            continue  # today with no commits yet does not break the streak
    repos = u["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)
    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:6]
    tot = sum(v for _, v in top) or 1

    W, H = 1280, 420
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub activity">',
         f'<rect width="{W}" height="{H}" fill="{VOID}"/>']
    tiles = [(f"{cal['totalContributions']:,}", "contributions", "in the last year"), (str(cur), "day streak", "current"),
             (str(longest), "day streak", "longest this year"), (str(sum(1 for c in counts if c)), "active days", "days with a contribution")]
    tw = 285
    for i, (n, a, b) in enumerate(tiles):
        x = 40 + i * (tw + 20)
        o.append(f'<rect x="{x}" y="20" width="{tw}" height="130" rx="16" fill="{FIELD}" stroke="{CORE}" stroke-opacity=".12"/>')
        sz = 58 if len(n) < 5 else 46
        o.append(tp(n, "ExtraBold", sz, x + 24, 88, SIGNAL, track=-1.5))
        o.append(tp(a, "SemiBold", 17, x + 24 + measure(n, "ExtraBold", sz, -1.5) + 12, 84, CORE))
        o.append(tp(b, "Medium", 12.5, x + 24, 126, CORE, track=.2, op=.55))
    # heatmap
    o.append(tp("CONTRIBUTIONS", "SemiBold", 12, 40, 200, SIGNAL, track=3))
    weeks = cal["weeks"]; cs, gp = 18, 4
    x0 = 40 + (1200 - len(weeks) * (cs + gp) + gp) / 2
    mx = max([d["contributionCount"] for w in weeks for d in w["contributionDays"]] + [1])
    for wi, w in enumerate(weeks):
        for di, d in enumerate(w["contributionDays"]):
            c = d["contributionCount"]
            if d["date"] > today: continue
            lvl = 0 if c == 0 else max(1, min(4, int(4 * (c / mx) ** 0.5 + 0.999)))
            fill, op = (FIELD, 1) if lvl == 0 else (SIGNAL, (.25, .5, .75, 1)[lvl - 1])
            o.append(f'<rect x="{x0 + wi*(cs+gp):.0f}" y="{220 + di*(cs+gp)}" width="{cs}" height="{cs}" rx="4" fill="{fill}" fill-opacity="{op}"/>')
    o.append(tp(f"updated {datetime.date.today().isoformat()}", "Medium", 11, W - 40, H - 22, CORE, "end", 1, .35))
    o.append("</svg>")
    return "".join(o)


if __name__ == "__main__":
    os.makedirs("dist", exist_ok=True)
    open("dist/activity.svg", "w").write(build(fetch()))
    print("dist/activity.svg written")
