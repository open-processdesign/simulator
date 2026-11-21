"""Record the demo: one continuous Playwright video plus a log of segment times.

The engine boot (Pyodide download) and solver waits are cut later with ffmpeg using the log.
A visible cursor and a caption bar are injected into the page so they appear in the video.
"""
import json
import time
from playwright.sync_api import sync_playwright

W, H = 1600, 900
URL = "http://localhost:4181/"

CURSOR_JS = """
(() => {
  const add = () => {
    if (document.getElementById('__cursor')) return;
    const c = document.createElement('div');
    c.id = '__cursor';
    Object.assign(c.style, {position:'fixed', left:'0px', top:'0px', width:'18px', height:'18px',
      marginLeft:'-9px', marginTop:'-9px', borderRadius:'50%', background:'rgba(232,108,28,0.85)',
      border:'2px solid #fff', boxShadow:'0 1px 4px rgba(0,0,0,.35)', zIndex:2147483647,
      pointerEvents:'none', transition:'transform .08s'});
    document.body.appendChild(c);
    const cap = document.createElement('div');
    cap.id = '__caption';
    Object.assign(cap.style, {position:'fixed', left:'50%', bottom:'44px', transform:'translateX(-50%)',
      maxWidth:'1200px', padding:'14px 26px', borderRadius:'10px', background:'rgba(28,27,26,0.92)',
      color:'#fff', font:'500 26px/1.35 Inter, Geist, system-ui, sans-serif', textAlign:'center',
      borderLeft:'6px solid #E86C1C', zIndex:2147483646, pointerEvents:'none', display:'none'});
    document.body.appendChild(cap);
    window.addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
    window.addEventListener('mousedown', () => { c.style.transform = 'scale(0.7)'; }, true);
    window.addEventListener('mouseup', () => { c.style.transform = 'scale(1)'; }, true);
  };
  if (document.body) add(); else document.addEventListener('DOMContentLoaded', add);
})();
"""

log = []
T0 = None


def now():
    return time.time() - T0


def main():
    global T0
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome")
        ctx = b.new_context(viewport={"width": W, "height": H}, record_video_dir="/tmp/video/raw",
                            record_video_size={"width": W, "height": H})
        T0 = time.time()
        pg = ctx.new_page()
        pg.add_init_script(CURSOR_JS)
        pg.on("dialog", lambda d: d.accept())
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)[:200]))
        pg.goto(URL)
        pg.get_by_text("Engine ready").wait_for(timeout=240000)
        pg.mouse.move(W / 2, H / 2)

        def caption(text):
            pg.evaluate("t => { const c = document.getElementById('__caption'); c.textContent = t; c.style.display = t ? 'block' : 'none'; }", text)

        def start(name, text):
            caption(text)
            pg.wait_for_timeout(250)
            log.append({"seg": name, "start": now()})

        def stop():
            log[-1]["end"] = now()

        def move_to(locator, steps=18):
            box = locator.bounding_box()
            x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            pg.mouse.move(x, y, steps=steps)
            pg.wait_for_timeout(200)
            return x, y

        def click(locator, pause=500):
            locator.scroll_into_view_if_needed()
            move_to(locator)
            locator.click()
            pg.wait_for_timeout(pause)

        def run_and_wait():
            click(pg.get_by_role("banner").get_by_role("button", name="Run"), pause=100)
            stop()
            pg.get_by_text("Solved in").wait_for(timeout=240000)
            pg.wait_for_timeout(300)

        def nav(name):
            return pg.get_by_role("navigation", name="Workflow steps").get_by_role("link", name=name)

        def open_example(name):
            click(pg.get_by_role("button", name="File"), pause=400)
            click(pg.get_by_role("menuitem", name=name), pause=1200)

        # 1. Components — search and add.
        start("components", "Pick components from a database of 1,300+ chemicals")
        box = pg.get_by_role("searchbox")
        click(box, pause=200)
        box.type("toluene", delay=90)
        pg.wait_for_timeout(900)
        click(pg.locator("ul[aria-label] button").first, pause=600)
        box.fill("")
        box.type("hydrogen", delay=90)
        pg.wait_for_timeout(700)
        click(pg.locator("ul[aria-label] button").first, pause=900)
        stop()

        # 2. HDA template: flowsheet.
        start("hda_open", "Open a full process: toluene hydrodealkylation with two recycles")
        open_example("HDA benzene plant — template (Turton topology)")
        pg.wait_for_timeout(1500)
        click(pg.locator('.react-flow__node[data-id="R-101"]'), pause=1800)
        caption("Every unit is set in the side panel — no pop-up windows")
        pg.wait_for_timeout(2200)
        click(pg.locator('.react-flow__node[data-id="SP-101"]'), pause=1500)
        caption("One click runs the whole flowsheet in your browser")
        pg.wait_for_timeout(800)
        run_and_wait()

        # 3. HDA results.
        start("hda_results", "Recycle loops converge automatically (Wegstein); results open in the stream table")
        click(nav("Results"), pause=1500)
        pg.mouse.wheel(0, 350)
        pg.wait_for_timeout(2200)
        pg.mouse.wheel(0, 500)
        pg.wait_for_timeout(2500)
        stop()

        # 4. Thermodynamics.
        start("thermo", "Property methods: Ideal, Peng–Robinson, SRK, NRTL, UNIQUAC — with their binary parameters")
        open_example("Methanol–water column (NRTL)")
        click(nav("Thermodynamics"), pause=1500)
        click(pg.get_by_role("radio", name="UNIQUAC").first if pg.get_by_role("radio", name="UNIQUAC").count() else pg.get_by_text("UNIQUAC").first, pause=2500)
        click(pg.get_by_role("radio", name="NRTL").first if pg.get_by_role("radio", name="NRTL").count() else pg.get_by_text("NRTL").first, pause=1200)
        stop()
        start("column_run", "A rigorous distillation column: MESH equations on every stage")
        open_example("Benzene–toluene rigorous column")
        click(pg.locator('.react-flow__node[data-id="T-1"]'), pause=2200)
        run_and_wait()

        start("column", "Stage profiles: temperature and compositions, as a chart or a table")
        click(nav("Results"), pause=800)
        region = pg.locator("section[aria-label^='Profiles of']").first
        region.scroll_into_view_if_needed()
        move_to(region)
        pg.wait_for_timeout(1200)
        box = region.bounding_box()
        pg.mouse.move(box["x"] + box["width"] * 0.15, box["y"] + box["height"] * 0.55, steps=10)
        pg.mouse.move(box["x"] + box["width"] * 0.42, box["y"] + box["height"] * 0.55, steps=40)
        pg.wait_for_timeout(1500)
        stop()

        # 5. Heat exchanger zones.
        start("hx_zones", "Heat exchangers are split into zones, so condensing and boiling are rated correctly")
        open_example("Steam-heated vaporizer (zone analysis)")
        click(pg.locator('.react-flow__node[data-id="E-101"]'), pause=1800)
        run_and_wait()
        start("hx_curves", "The T–Q heat curves show the internal pinch")
        click(nav("Results"), pause=800)
        region = pg.locator("section[aria-label^='Profiles of']").first
        region.scroll_into_view_if_needed()
        move_to(region)
        pg.wait_for_timeout(3000)
        stop()

        # 6. Shell-and-tube geometry.
        start("geometry", "Shell-and-tube geometry: Kern's method gives U, area and pressure drops")
        open_example("Toluene cooler, shell-and-tube rating")
        click(pg.locator('.react-flow__node[data-id="E-101"]'), pause=800)
        panel = pg.get_by_role("group", name="Shell-and-tube geometry")
        if panel.count():
            panel.scroll_into_view_if_needed()
            move_to(panel)
        pg.wait_for_timeout(2500)
        run_and_wait()
        start("geometry_results", "Film coefficients, U, F-factor, velocities and pressure drops")
        click(nav("Results"), pause=800)
        unit_results = pg.get_by_text("Overall U").first
        unit_results.scroll_into_view_if_needed()
        move_to(unit_results)
        pg.wait_for_timeout(3000)
        stop()

        # 7. Unit sets and Turkish.
        start("units", "SI, metric or English units — and the whole interface in Turkish")
        click(pg.get_by_role("combobox", name="Units"), pause=300)
        pg.get_by_role("combobox", name="Units").select_option("METRIC")
        pg.wait_for_timeout(1500)
        lang = pg.get_by_role("combobox", name="Language")
        click(lang, pause=300)
        lang.select_option("tr")
        pg.wait_for_timeout(2500)
        stop()

        caption("")
        ctx.close()
        b.close()
        json.dump({"segments": log, "errors": errors}, open("/tmp/video/log.json", "w"), indent=1)
        print(json.dumps(log, indent=1), errors)


main()
