import re

src = open("client/app.js", encoding="utf-8").read()
s = re.sub(r"`(?:\\.|[^`\\])*`", "``", src)
s = re.sub(r"'(?:\\.|[^'\\])*'", "''", s)
s = re.sub(r'"(?:\\.|[^"\\])*"', '""', s)
s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
s = re.sub(r"//[^\n]*", "", s)
pairs = {")": "(", "]": "[", "}": "{"}
stack = []
for i, ch in enumerate(s):
    if ch in "([{":
        stack.append((ch, i))
    elif ch in ")]}":
        if not stack or stack[-1][0] != pairs[ch]:
            line = s.count("\n", 0, i) + 1
            raise SystemExit(f"unbalanced {ch} at line {line}")
        stack.pop()
print("brackets OK, depth left:", len(stack))
