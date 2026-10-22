import pathlib
p = pathlib.Path("server/app.py")
s = p.read_text(encoding="utf-8")
s = s.replace('app = FastAPI(title="DMRL Sakha — nowcasting service", version="1.0")', 'app = FastAPI(title="IMERG Sakha — precipitation nowcasting", version="1.0")')
p.write_text(s, encoding="utf-8")
print("title ok")
