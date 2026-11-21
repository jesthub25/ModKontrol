import json, sys, time, urllib.request, urllib.parse
out = open(sys.argv[1], "w", encoding="utf-8")
facets = json.dumps([["project_type:mod"]])
seen = set()
for offset in range(0, 3000, 100):
    q = urllib.parse.urlencode({"index": "downloads", "limit": 100, "offset": offset, "facets": facets})
    req = urllib.request.Request("https://api.modrinth.com/v2/search?" + q, headers={"User-Agent": "jesthub25/ModKontrol-bootstrap"})
    for attempt in range(5):
        try:
            data = json.load(urllib.request.urlopen(req, timeout=30)); break
        except Exception as e:
            time.sleep(3)
    for h in data["hits"]:
        if h["slug"] in seen: continue
        seen.add(h["slug"])
        out.write("\t".join([h["slug"], h["title"].replace("\t"," "), ",".join(h.get("categories", [])), h.get("client_side",""), h.get("server_side",""), str(h.get("downloads",0))]) + "\n")
    time.sleep(0.4)
out.close()
print("mods:", len(seen))
