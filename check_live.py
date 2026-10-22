import urllib.request

url = "https://rrwx0.github.io/Yakutia-radar-IMERG-with-modificated-SharpPy/"
r = urllib.request.urlopen(url, timeout=60)
body = r.read().decode("utf-8", "replace")
print("status", r.status, "bytes", len(body))
print("modelToggle", 'id="modelToggle"' in body)
print("modelSelect", "modelSelect" in body)
print("hud gone", 'class="hud"' not in body)
print("models_api_page", "sharppy.html" in body)