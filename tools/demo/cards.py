from playwright.sync_api import sync_playwright
CSS = """
body{margin:0;width:1920px;height:1080px;background:#F7F6F3;font-family:Inter,system-ui,sans-serif;color:#1C1B1A;
display:flex;flex-direction:column;justify-content:center;padding:0 180px;box-sizing:border-box}
.logo{width:72px;height:72px;border-radius:16px;background:#E86C1C;color:#fff;font:700 44px/72px Inter;text-align:center;margin-bottom:40px}
h1{font:600 84px/1.1 Inter;margin:0 0 28px;letter-spacing:-1px}
p{font:400 38px/1.45 Inter;color:#4A4744;margin:0 0 14px}
.acc{color:#E86C1C;font-weight:600}
ul{font:400 34px/1.6 Inter;color:#4A4744;margin:10px 0 0;padding-left:34px}
"""
CARDS = {
 "title": """<div class=logo>O</div><h1>Open Process Design</h1>
<p>A free, open-source process simulator that runs in your browser.</p>
<p class=acc>Components → Thermodynamics → Flowsheet → Run → Results</p>""",
 "validation": """<h1>Checked against published cases</h1>
<ul><li>Cumene Unit 800 (Turton, CHEMCAD table): duties within 3 %</li>
<li>DME Unit 200: adiabatic reactor outlet within 2.6 K</li>
<li>VLE vs experiment: methanol–water, ethanol–water azeotrope</li>
<li>184 engine tests · every number comes from the engine</li></ul>""",
 "end": """<div class=logo>O</div><h1>Try it now</h1>
<p class=acc>open-processdesign.github.io/simulator</p>
<p>Source: github.com/open-processdesign/simulator</p>
<p>For education and preliminary design — verify results before use.</p>""",
}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome")
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    for name, html in CARDS.items():
        pg.set_content(f"<html><head><style>{CSS}</style></head><body>{html}</body></html>")
        pg.screenshot(path=f"/tmp/video/cards/{name}.jpg", type="jpeg", quality=92)
    b.close()
