# Fill fonts a lemo-opuscar demo page needs but could not download (blocked font hosts) with local DejaVu.
# python3 scripts/setup/fill_fonts.py <demo dir>
import sys, re, pathlib
from fontTools.ttLib import TTFont
demo = pathlib.Path(sys.argv[1])
html = (demo / "index.html").read_text(errors="ignore")
for name in sorted(set(re.findall(r'fonts/([\w.\-]+\.(?:ttf|otf|woff2?))', html))):
    p = demo / "fonts" / name
    if p.exists() and p.stat().st_size > 1000: continue
    mono = "Mono" in name
    src = "/usr/share/fonts/truetype/dejavu/" + ("DejaVuSansMono.ttf" if mono else "DejaVuSans.ttf")
    f = TTFont(src); p.parent.mkdir(exist_ok=True)
    if name.endswith(".woff2"): f.flavor = "woff2"
    elif name.endswith(".woff"): f.flavor = "woff"
    f.save(p); print("filled", name)
