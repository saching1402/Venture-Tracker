#!/usr/bin/env python3
"""Merge batch JSON files into site/tracker.json.

Usage: python3 merge.py [--prev path/to/previous/tracker.json] [--asof YYYY-MM-DD]
Reads data/firms_*.json and data/companies_*.json. companies_b8.json (marquee refresh)
takes precedence for financial fields. If --prev is given, valuation / revenue changes
versus the previous snapshot are appended to the change log.
"""
import json, glob, re, sys, os, argparse, datetime

ap = argparse.ArgumentParser()
ap.add_argument("--prev", default=None)
ap.add_argument("--asof", default=datetime.date.today().isoformat())
ap.add_argument("--data", default="data")
ap.add_argument("--out", default="site/tracker.json")
args = ap.parse_args()

# canonical firm ids -> regex patterns matched against lowercased names / ids
CANON = [
    ("accel", r"\baccel\b(?!\s*-?\s*kkr)"), ("a16z", r"\ba16z\b|andreessen"),
    ("lux", r"\blux\b"), ("iconiq", r"\biconiq"), ("dcvc", r"\bdcvc\b|data collective"),
    ("playground", r"\bplayground\b"), ("radical", r"\bradical\b"),
    ("lightspeed", r"lightspeed|\blsvp\b"), ("ivp", r"\bivp\b|institutional venture partners"),
    ("khosla", r"khosla"), ("spark", r"\bspark capital\b|^spark$"), ("thrive", r"\bthrive\b"),
    ("factorial", r"factorial"), ("founders-fund", r"founders fund|^ff$|foundersfund"),
    ("sound", r"sound ventures|^sound$"), ("kleiner", r"kleiner|^kp$"), ("sequoia", r"sequoia"),
    ("benchmark", r"\bbenchmark\b"), ("bessemer", r"bessemer|^bvp$"), ("innovia", r"in+ovia"),
    ("general-catalyst", r"general catalyst|^gc$"), ("nea", r"\bnea\b|new enterprise associates"),
    ("insight", r"insight partners|insight venture|^insight$"), ("menlo", r"menlo ventures|^menlo$"),
    ("greylock", r"greylock"), ("eclipse", r"\beclipse\b"), ("coatue", r"coatue"),
    ("deerfield", r"deerfield"), ("index", r"index ventures|^index$"), ("true", r"true ventures|^true$"),
    ("ribbit", r"ribbit"), ("sosv", r"\bsosv\b"), ("walden-catalyst", r"walden catalyst"),
    ("tiger", r"tiger global|^tiger$"), ("battery", r"battery ventures|^battery$"),
    ("alleycorp", r"alley ?corp"), ("bcv", r"bain capital ventures|^bcv$"), ("jmi", r"\bjmi\b"),
    ("tcv", r"\btcv\b|technology crossover"), ("8vc", r"\b8vc\b"), ("dragoneer", r"dragoneer"),
    ("greenoaks", r"greenoaks"), ("felicis", r"felicis"), ("conviction", r"\bconviction\b"),
    ("elad-gil", r"elad gil"), ("redpoint", r"redpoint"), ("usv", r"union square|^usv$"),
    ("atomico", r"atomico"), ("balderton", r"balderton"), ("hyt", r"\bhyt\b|华业天成"),
    ("monolith", r"monolith|砺思"),
]
CANON_IDS = {c for c, _ in CANON}

KNOWN_IDS = set()  # firm ids present in the snapshot (includes managers added in the app)


def canon_firm(s):
    if not s:
        return None
    t = str(s).strip().lower()
    if t in CANON_IDS or t in KNOWN_IDS:
        return t
    t2 = re.sub(r"[_\-]+", " ", t)
    for cid, pat in CANON:
        if re.search(pat, t2):
            return cid
    return None

def slug(name):
    s = name.lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\b(inc|corp|corporation|ltd|llc|technologies|labs?|co)\b\.?", "", s)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s

ALIAS = {"anysphere": "cursor", "cursoranysphere": "cursor", "safesuperintelligence": "ssi",
         "ssisafesuperintelligence": "ssi", "thinkingmachines": "thinkingmachines",
         "xaicorp": "xai", "spacexspaceexplorationtechnologies": "spacex",
         "spaceexplorationtechnologies": "spacex", "openaigroup": "openai",
         "scaleai": "scale", "scale": "scale", "cohereai": "cohere", "figureai": "figure",
         "characterai": "character", "metamaterials": "metamaterials",
         "robinhoodmarkets": "robinhood", "envedabiosciences": "enveda", "sundayrobotics": "sunday",
         "facebook": "metaplatforms", "meta": "metaplatforms", "anduril": "andurilindustries", "chimefinancial": "chime"}

def ckey(c):
    k = slug(c.get("name") or c.get("id") or "")
    k = ALIAS.get(k, k)
    if k.endswith("ai") and len(k) > 4 and k not in ("openai", "xai"):
        k2 = k[:-2]
        k = ALIAS.get(k2, k2)
    return k

def load(pattern):
    out = []
    for f in sorted(glob.glob(os.path.join(args.data, pattern))):
        try:
            d = json.load(open(f))
        except Exception as e:
            print("SKIP", f, e, file=sys.stderr)
            continue
        if isinstance(d, dict):
            d = d.get("firms") or d.get("companies") or list(d.values())
        b = re.search(r"_(b\d+)", f)
        for x in d:
            if isinstance(x, dict):
                x["_batch"] = b.group(1) if b else "x"
                out.append(x)
    return out

def num(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None

def dkey(d):
    return str(d or "")

# ---------------- firms ----------------
firms = {}
_all_firms = load("firms_*.json")
KNOWN_IDS.update(str(f.get("id")).strip().lower() for f in _all_firms if f.get("id"))
for f in _all_firms:
    cid = canon_firm(f.get("id")) or canon_firm(f.get("name")) or slug(f.get("name", "x"))
    f["id"] = cid
    if cid in firms:  # keep richer
        if len(json.dumps(f)) > len(json.dumps(firms[cid])):
            firms[cid] = f
    else:
        firms[cid] = f

# ---------------- companies ----------------
comps = {}
order = load("companies_*.json")
# non-b8 first, b8 last so it overrides financial scalars
order.sort(key=lambda c: 1 if c.get("_batch") == "b8" else 0)
FIN = ["latest_valuation_usd_bn", "valuation_date", "valuation_label", "total_raised_usd_bn",
       "revenue_metric", "revenue_usd_bn", "revenue_date", "revenue_label", "growth",
       "profitability", "employees", "status", "ceo"]
TEXT = ["website", "hq", "founded", "description", "sector", "notes"]

for c in order:
    k = ckey(c)
    if not k:
        continue
    gps = []
    for g in c.get("gp_positions") or []:
        fid = canon_firm(g.get("firm_id")) or canon_firm(g.get("firm"))
        if fid:
            g = dict(g); g["firm_id"] = fid
            gps.append(g)
    c["gp_positions"] = gps
    if k not in comps:
        c["id"] = k
        comps[k] = c
        continue
    m = comps[k]
    is_b8 = c.get("_batch") == "b8"
    # valuation: b8 wins; else later date wins
    if is_b8 or (num(c.get("latest_valuation_usd_bn")) is not None and dkey(c.get("valuation_date")) > dkey(m.get("valuation_date"))):
        for f_ in ["latest_valuation_usd_bn", "valuation_date", "valuation_label"]:
            if c.get(f_) is not None:
                m[f_] = c[f_]
    if is_b8 or (num(c.get("revenue_usd_bn")) is not None and dkey(c.get("revenue_date")) > dkey(m.get("revenue_date"))):
        for f_ in ["revenue_metric", "revenue_usd_bn", "revenue_date", "revenue_label", "growth"]:
            if c.get(f_) is not None:
                m[f_] = c[f_]
    for f_ in ["total_raised_usd_bn", "profitability", "employees", "status", "ceo"]:
        if c.get(f_) is not None and (is_b8 or m.get(f_) is None):
            m[f_] = c[f_]
    for f_ in TEXT:
        if c.get(f_) and (not m.get(f_) or (f_ in ("description", "notes") and is_b8 and len(str(c[f_])) > 20)):
            m[f_] = c[f_]
    for f_ in ["focus_tags", "other_investors", "sources"]:
        seen = {str(x).lower() for x in (m.get(f_) or [])}
        for x in c.get(f_) or []:
            if str(x).lower() not in seen:
                m.setdefault(f_, []).append(x); seen.add(str(x).lower())
    vh = {(str(v.get("date"))[:7], (v.get("round") or "").lower()): v for v in (m.get("valuation_history") or [])}
    for v in c.get("valuation_history") or []:
        key = (str(v.get("date"))[:7], (v.get("round") or "").lower())
        if key not in vh or (is_b8 and v.get("post_money_usd_bn") is not None):
            vh[key] = v
    m["valuation_history"] = list(vh.values())
    have = {g["firm_id"]: g for g in m.get("gp_positions") or []}
    for g in gps:
        if g["firm_id"] not in have:
            m.setdefault("gp_positions", []).append(g); have[g["firm_id"]] = g
        else:
            h = have[g["firm_id"]]
            for f_ in ["first_invest_year", "entry_round", "fund", "lead"]:
                if h.get(f_) in (None, "") and g.get(f_) not in (None, ""):
                    h[f_] = g[f_]

# public market caps / status overrides
for pf in ["public_caps.json", "overrides.json"]:
    p = os.path.join(args.data, pf)
    if os.path.exists(p):
        try:
            for o in json.load(open(p)):
                k = o.get("id") if o.get("id") in comps else ckey(o)
                c = comps.get(k)
                if not c:
                    continue
                if num(o.get("market_cap_usd_bn")) is not None:
                    c["latest_valuation_usd_bn"] = num(o["market_cap_usd_bn"])
                    c["valuation_date"] = o.get("date") or args.asof[:7]
                    c["valuation_label"] = o.get("label") or "REPORTED"
                    c["valuation_basis"] = "Market cap"
                if o.get("status"):
                    c["status"] = o["status"]
                nr = o.get("new_round")
                if isinstance(nr, dict) and num(nr.get("post_money_usd_bn")) is not None:
                    hist = c.setdefault("valuation_history", [])
                    if not any(str(h.get("date"))[:7] == str(nr.get("date"))[:7] and num(h.get("post_money_usd_bn")) == num(nr["post_money_usd_bn"]) for h in hist):
                        hist.append(nr)
                    if str(nr.get("date") or "") >= str(c.get("valuation_date") or "") and c.get("valuation_basis") != "Market cap":
                        c["latest_valuation_usd_bn"] = num(nr["post_money_usd_bn"])
                        c["valuation_date"] = nr.get("date")
                        c["valuation_label"] = "REPORTED"
                if o.get("source"):
                    c.setdefault("sources", []).append(o["source"])
                for f_ in ["revenue_usd_bn", "revenue_date", "revenue_metric", "revenue_label", "growth", "notes"]:
                    if o.get(f_) is not None:
                        c[f_] = o[f_]
        except Exception as e:
            print("override error", p, e, file=sys.stderr)

# derive per company
for k, c in comps.items():
    # dedupe rounds: same round name (ignoring amounts in brackets) at a similar post-money
    hist = sorted(c.get("valuation_history") or [], key=lambda v: str(v.get("date")))
    kept = []
    for v in hist:
        rn = re.sub(r"\(.*?\)", "", (v.get("round") or "")).strip().lower()
        pm = num(v.get("post_money_usd_bn"))
        dup = False
        for kv in kept:
            krn = re.sub(r"\(.*?\)", "", (kv.get("round") or "")).strip().lower()
            kpm = num(kv.get("post_money_usd_bn"))
            if rn and rn == krn and (pm is None or kpm is None or abs(pm - kpm) <= 0.08 * max(pm, kpm)):
                if kpm is None and pm is not None:
                    kv["post_money_usd_bn"] = pm
                if not kv.get("lead") and v.get("lead"):
                    kv["lead"] = v["lead"]
                dup = True; break
        if not dup:
            kept.append(v)
    c["valuation_history"] = kept
    vh = [v for v in c.get("valuation_history") or [] if num(v.get("post_money_usd_bn")) is not None]
    vh.sort(key=lambda v: str(v.get("date")))
    c["valuation_history"] = sorted(c.get("valuation_history") or [], key=lambda v: str(v.get("date")))
    lv = num(c.get("latest_valuation_usd_bn"))
    st = (c.get("status") or "Private").lower()
    if lv is None and vh:
        lv = num(vh[-1]["post_money_usd_bn"]); c["latest_valuation_usd_bn"] = lv
        c["valuation_date"] = vh[-1].get("date")
        c["valuation_label"] = c.get("valuation_label") or "REPORTED"
        c["valuation_basis"] = "Last recorded round" if st.startswith("private") else "Last recorded mark (not current)"
    if lv is not None and not c.get("valuation_basis"):
        c["valuation_basis"] = "Market cap" if st.startswith("public") else ("Exit / last mark" if not st.startswith("private") else "Latest round / tender")
    fy = num(c.get("founded")); fm = str(c.get("first_mark_date") or "")[:4]
    early = (fy is not None and fy < 2005) or (fm and fm < "2010")
    last_round = max([str(v.get("date") or "") for v in c.get("valuation_history") or []] or [""])
    c["legacy"] = bool(not st.startswith("private") and early and last_round < "2017")
    c["valuation_stale"] = (not st.startswith("private") and c.get("valuation_basis") == "Last recorded mark (not current)") or str(c.get("valuation_date") or "9999") < "2024"
    c["first_mark_usd_bn"] = num(vh[0]["post_money_usd_bn"]) if vh else None
    c["first_mark_date"] = vh[0].get("date") if vh else None
    c["step_up_x"] = round(lv / c["first_mark_usd_bn"], 1) if lv and c["first_mark_usd_bn"] else None
    rv = num(c.get("revenue_usd_bn"))
    qtr = "quarter" in str(c.get("revenue_metric") or "").lower()
    c["ev_rev_x"] = round(lv / (rv * (4 if qtr else 1)), 1) if lv and rv and rv > 0 else None
    if c["ev_rev_x"] and c["ev_rev_x"] > 1000:
        c["ev_rev_x"] = None  # implausible: likely unit mismatch
    # tracked investors: positions + investor-list matches
    pos = {g["firm_id"] for g in c.get("gp_positions") or []}
    for inv in c.get("other_investors") or []:
        fid = canon_firm(inv)
        if fid and fid not in pos:
            c.setdefault("gp_positions", []).append({"firm_id": fid, "first_invest_year": None, "entry_round": None, "via": "investor list"})
            pos.add(fid)
    for g in c.get("gp_positions") or []:
        y = g.get("first_invest_year")
        ent = None
        if y:
            same = [v for v in vh if str(v.get("date", ""))[:4] == str(y)]
            rnd = (g.get("entry_round") or "").lower()
            byr = [v for v in same if rnd and rnd in (v.get("round") or "").lower()]
            pick = (byr or same)
            if pick:
                ent = num(pick[0]["post_money_usd_bn"])
        g["entry_post_usd_bn"] = ent
        g["markup_x"] = round(lv / ent, 1) if lv and ent else None
    c["tracked_gp_ids"] = sorted(pos)
    c.pop("_batch", None)

# firm derived
for fid, f in firms.items():
    hold = [c for c in comps.values() if fid in c["tracked_gp_ids"]]
    f["n_companies"] = len(hold)
    f["agg_holdings_val_usd_bn"] = round(sum(num(c.get("latest_valuation_usd_bn")) or 0 for c in hold if not c.get("valuation_stale") and not c.get("legacy")), 1)
    f["top_holdings"] = [c["id"] for c in sorted(hold, key=lambda c: -(num(c.get("latest_valuation_usd_bn")) or 0))[:25]]
    f.pop("_batch", None)
# firms referenced but not profiled
for c in comps.values():
    for fid in c["tracked_gp_ids"]:
        if fid not in firms:
            firms[fid] = {"id": fid, "name": fid, "stub": True}

# recent rounds feed (2026) from history
rounds = []
for c in comps.values():
    for v in c.get("valuation_history") or []:
        if str(v.get("date", "")) >= "2025-07":
            rounds.append({"company_id": c["id"], "date": v.get("date"), "round": v.get("round"),
                           "post_money_usd_bn": num(v.get("post_money_usd_bn")), "lead": v.get("lead")})
rounds.sort(key=lambda r: str(r["date"]), reverse=True)

# changes vs previous snapshot
changes = []
refresh_log = []
if args.prev and os.path.exists(args.prev):
    prev = json.load(open(args.prev))
    changes = prev.get("changes", [])
    refresh_log = prev.get("refresh_log", [])
    pc = {c["id"]: c for c in prev.get("companies", [])}
    for k, c in comps.items():
        p = pc.get(k)
        if not p:
            changes.append({"date": args.asof, "company_id": k, "type": "added", "detail": "Added to tracker"})
            continue
        for fld, lab in [("latest_valuation_usd_bn", "Valuation"), ("revenue_usd_bn", c.get("revenue_metric") or "Revenue")]:
            a, b = num(p.get(fld)), num(c.get(fld))
            if a and b and abs(b - a) / a > 0.005:
                changes.append({"date": args.asof, "company_id": k, "type": fld, "from": a, "to": b,
                                "detail": f"{lab} ${a:g}bn → ${b:g}bn ({(b/a-1)*100:+.0f}%)"})
        if p.get("status") != c.get("status"):
            changes.append({"date": args.asof, "company_id": k, "type": "status", "detail": f"Status: {p.get('status')} → {c.get('status')}"})
refresh_log.append({"date": args.asof, "firms": len(firms), "companies": len(comps)})

out = {"asof": args.asof, "refresh_log": refresh_log, "firms": sorted(firms.values(), key=lambda f: f.get("name", "").lower()),
       "companies": sorted(comps.values(), key=lambda c: -(num(c.get("latest_valuation_usd_bn")) or 0)),
       "recent_rounds": rounds[:400], "changes": changes[-2000:]}
os.makedirs(os.path.dirname(args.out), exist_ok=True)
json.dump(out, open(args.out, "w"), ensure_ascii=False, separators=(",", ":"))
print(f"firms={len(firms)} companies={len(comps)} rounds={len(rounds)} bytes={os.path.getsize(args.out)}")
