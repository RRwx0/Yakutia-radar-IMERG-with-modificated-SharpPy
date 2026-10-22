import re

a = open("client/app.js", encoding="utf-8").read()
h = open("client/index.html", encoding="utf-8").read()
ids = set(re.findall(r'el\("([\w]+)"\)', a))
present = set(re.findall(r'id="([\w]+)"', h))
missing = sorted(i for i in ids if i not in present)
print("missing ids:", missing)
print("dbzToRate refs:", a.count("dbzToRate"))
print("hudTopCell refs:", a.count("hudTopCell"))
print("els now:", len(ids))
