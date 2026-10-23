from pathlib import Path

# --- app.js STOPS ---
p = Path("client/app.js")
s = p.read_text(encoding="utf-8")
i = s.find("const STOPS = [")
j = s.find("];", i) + 2
new = """const STOPS = [
    [5, "#c9f2e5"], [8, "#9fdbe0"], [12, "#7cc4d8"], [16, "#5da8c6"],
    [20, "#7fc98f"], [25, "#8fc874"], [30, "#c9d66b"], [35, "#e8d15a"],
    [40, "#e8a84c"], [45, "#e07a52"], [50, "#d5605a"], [55, "#b44a6d"],
    [60, "#9450a6"], [65, "#6f4f9e"], [70, "#503e8e"]
  ];"""
s = s[:i] + new + s[j:]
p.write_text(s, encoding="utf-8")
print("app.js ok", "503e8e" in s)

# --- server/app.py class_of ---
p2 = Path("server/app.py")
s2 = p2.read_text(encoding="utf-8")
old = """        (10, "следы", "#a4f8f1"),
        (15, "слабые", "#6db8e1"),
        (20, "небольшие", "#3f8fd2"),
        (25, "умеренные", "#00833e"),
        (30, "умеренный дождь", "#00971f"),
        (35, "сильные", "#8fd600"),
        (40, "очень сильные", "#fdcb00"),
        (45, "ливневые", "#ff9810"),
        (50, "гроза/град", "#ff2d2d"),
        (1000, "экстремальные", "#ce0000"),"""
new2 = """        (10, "следы", "#c9f2e5"),
        (15, "слабые", "#9fdbe0"),
        (20, "небольшие", "#7cc4d8"),
        (25, "умеренные", "#7fc98f"),
        (30, "умеренный дождь", "#c9d66b"),
        (35, "сильные", "#e8d15a"),
        (40, "очень сильные", "#e8a84c"),
        (45, "ливневые", "#e07a52"),
        (50, "гроза/град", "#d5605a"),
        (60, "экстремальные", "#9450a6"),
        (1000, "экстремальные", "#6f4f9e"),"""
if old in s2:
    s2 = s2.replace(old, new2)
    p2.write_text(s2, encoding="utf-8")
    print("server ok")
else:
    print("server old NOT found")