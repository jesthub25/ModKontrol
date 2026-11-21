import json, sys, time, os, re, io, zipfile, threading, urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor
UA = {"User-Agent": "jesthub25/ModKontrol-modscan (github.com/jesthub25/ModKontrol)"}
lock = threading.Lock(); last = [0.0]
def req(url, binary=False, api=True, timeout=60, headers=None):
    h = dict(UA); h.update(headers or {})
    for attempt in range(5):
        if api:
            with lock:
                w = 0.21 - (time.time() - last[0])
                if w > 0: time.sleep(w)
                last[0] = time.time()
        try:
            d = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout).read()
            return d if binary else json.loads(d)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(15); continue
            if e.code in (404, 410, 403): return None
            time.sleep(2)
        except Exception:
            time.sleep(2)
    return None

BAD = re.compile(r"[%|§\n\r\t]")
def pick_keys(langs, ids):
    cands = []
    for ns, data in langs:
        for k, v in data.items():
            if not isinstance(v, str): continue
            if len(v) < 2 or len(v) > 16 or BAD.search(v) or BAD.search(k): continue
            kl = k.lower()
            if not any(i and i in kl for i in ids): continue
            score = 0 if kl.startswith("key.") else 1 if kl.startswith("modmenu.") else 2 if kl.startswith(("category.", "key.categor")) else 3
            cands.append((score, len(v), k, v))
    cands.sort()
    out, seen = [], set()
    for c in cands:
        if c[2] in seen: continue
        seen.add(c[2]); out.append((c[2], c[3]))
        if len(out) >= 2: break
    return out

def parse_jar(blob):
    ids, names, langs = [], [], []
    try:
        z = zipfile.ZipFile(io.BytesIO(blob))
    except Exception:
        return ids, names, langs
    for n in z.namelist():
        try:
            if n in ("fabric.mod.json", "quilt.mod.json"):
                j = json.loads(z.read(n).decode("utf-8", "ignore"), strict=False)
                if n == "quilt.mod.json": j = j.get("quilt_loader", {}); j.setdefault("name", j.get("metadata", {}).get("name"))
                if j.get("id"): ids.append(j["id"]); names.append(j.get("name") or j["id"])
            elif n in ("META-INF/mods.toml", "META-INF/neoforge.mods.toml"):
                t = z.read(n).decode("utf-8", "ignore")
                for m in re.finditer(r'modId\s*=\s*"([^"]+)"', t): ids.append(m.group(1))
                for m in re.finditer(r'displayName\s*=\s*"([^"]+)"', t): names.append(m.group(1))
            elif re.match(r"assets/[^/]+/lang/en_us\.json$", n):
                ns = n.split("/")[1]
                try: langs.append((ns, json.loads(z.read(n).decode("utf-8", "ignore"), strict=False)))
                except Exception: pass
        except Exception:
            pass
    return ids, names, langs

def best_version(versions):
    if not versions: return None
    def ok(v): return any(g.startswith("1.21") for g in v.get("game_versions", []))
    for v in versions:
        if ok(v) and any(l in ("fabric", "neoforge", "quilt") for l in v.get("loaders", [])): return v
    for v in versions:
        if ok(v): return v
    return versions[0]

def scan_mod(hit):
    slug = hit["slug"]
    vers = req("https://api.modrinth.com/v2/project/%s/version" % urllib.parse.quote(slug))
    v = best_version(vers)
    ids, names, keys = [], [], []
    if v:
        f = next((x for x in v["files"] if x.get("primary")), v["files"][0] if v["files"] else None)
        if f and f.get("size", 0) < 40_000_000 and f["url"].endswith(".jar"):
            blob = req(f["url"], binary=True, api=False, timeout=120)
            if blob:
                ids, names, langs = parse_jar(blob)
                keys = pick_keys(langs, [i.lower() for i in ids] + [slug.lower(), slug.replace("-", "").lower(), slug.replace("-", "_").lower()])
    return {"slug": slug, "title": hit["title"], "categories": hit.get("categories", []), "client": hit.get("client_side"),
            "downloads": hit.get("downloads", 0), "ids": sorted(set(ids)), "keys": keys}

def search(limit_total):
    facets = json.dumps([["project_type:mod"], ["client_side:required", "client_side:optional"]])
    hits, seen = [], set()
    for off in range(0, limit_total, 100):
        d = req("https://api.modrinth.com/v2/search?" + urllib.parse.urlencode({"index": "downloads", "limit": 100, "offset": off, "facets": facets}))
        if not d: continue
        for h in d["hits"]:
            if h["slug"] not in seen: seen.add(h["slug"]); hits.append(h)
    return hits

def github_jars(repo, token):
    h = {"Authorization": "Bearer " + token} if token else {}
    rels = req("https://api.github.com/repos/%s/releases?per_page=5" % repo, api=False, headers=h) or []
    for r in rels:
        for a in r.get("assets", []):
            n = a["name"].lower()
            if n.endswith(".jar") and "sources" not in n and "dev" not in n and a.get("size", 0) < 60_000_000:
                return a["browser_download_url"]
    return None

if __name__ == "__main__":
    total = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
    hits = search(total)
    print("search hits", len(hits), flush=True)
    results = []
    with ThreadPoolExecutor(8) as ex:
        for i, r in enumerate(ex.map(scan_mod, hits)):
            results.append(r)
            if i % 100 == 0: print("scanned", i, flush=True)
    token = os.environ.get("GITHUB_TOKEN", "")
    extra = {"CCBlueX/LiquidBounce": "liquidbounce", "Wurst-Imperium/Wurst7": "wurst", "MeteorDevelopment/meteor-client": "meteor-client",
             "cabaletta/baritone": "baritone", "Pan4ur/ThunderHack-Recode": "thunderhack", "AntiCope/meteor-rejects": "meteor-rejects",
             "etianl/Trouser-Streak": "trouser-streak", "hashalite/Freecam": "freecam", "Bleach-Client/Bleach-Hack": "bleachhack",
             "AutismInc/Tanuki": "tanuki", "Wurst-Imperium/WI-Zoom": "wi-zoom", "xNasuni/meteor-mod-detector": "x"}
    for repo, slug in extra.items():
        try:
            url = github_jars(repo, token)
            if not url: print("no jar", repo); continue
            blob = req(url, binary=True, api=False, timeout=180)
            ids, names, langs = parse_jar(blob or b"")
            keys = pick_keys(langs, [i.lower() for i in ids] + [slug, slug.replace("-", "")])
            results.append({"slug": slug, "title": names[0] if names else slug, "categories": ["github"], "client": "required",
                            "downloads": 0, "ids": sorted(set(ids)), "keys": keys, "repo": repo})
            print("github", repo, ids[:3], keys, flush=True)
        except Exception as e:
            print("github fail", repo, e)
    json.dump(results, open(sys.argv[1], "w"), ensure_ascii=False, indent=0)
    print("done", len(results), "with keys", sum(1 for r in results if r["keys"]))
