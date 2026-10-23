from pathlib import Path

p = Path("client/app.js")
s = p.read_text(encoding="utf-8")
i = s.find("const CLASSES = [")
j = s.find("];", i) + 2
new = """const CLASSES = [
    [10, "следы", "#9fdbe0"], [15, "слабые", "#7cc4d8"], [20, "небольшие", "#5da8c6"],
    [25, "умеренные", "#7fc98f"], [30, "умеренный дождь", "#c9d66b"], [35, "сильные", "#e8d15a"],
    [40, "очень сильные", "#e8a84c"], [45, "ливневые", "#e07a52"], [50, "гроза/град", "#d5605a"],
    [1e9, "экстремальные", "#6f4f9e"]
  ];"""
s = s[:i] + new + s[j:]
p.write_text(s, encoding="utf-8")
print("classes ok", "6f4f9e" in s)