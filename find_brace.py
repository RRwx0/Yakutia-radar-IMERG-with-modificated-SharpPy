import re
from pathlib import Path

s = Path("client/app.js").read_text(encoding="utf-8")
lines = s.split("\n")
depth = 0
for k, ln in enumerate(lines):
    cleaned = re.sub(r"//.*", "", ln)
    cleaned = re.sub(r'"(?:[^"\\]|\\.)*"', '""', cleaned)
    cleaned = re.sub(r"'(?:[^'\\]|\\.)*'", "''", cleaned)
    opens = cleaned.count("{") + cleaned.count("(") + cleaned.count("[")
    closes = cleaned.count("}") + cleaned.count(")") + cleaned.count("]")
    depth += opens - closes
    if depth < 0:
        print("neg at line", k + 1, "depth", depth, repr(ln.strip()[:80]))
        break
print("end depth", depth)