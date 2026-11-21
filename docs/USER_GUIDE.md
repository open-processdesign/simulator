# User guide

Open Process Design runs in your browser: https://open-processdesign.github.io/simulator/
Results are for education and preliminary design. Verify them before use.

## 1. Components
Search by name, formula or CAS number and add the components of your process. The table shows molar mass and normal boiling point.

## 2. Thermodynamics
Choose a property method:
- **Ideal (Raoult)** — low pressure, similar molecules.
- **Peng–Robinson / SRK** — hydrocarbons and gases, also at high pressure.
- **NRTL** — polar, non-ideal liquids at low pressure (alcohol–water).
- **UNIQUAC** — like NRTL, with molecular size and surface (r, q) from UNIFAC groups and two parameters per pair.

The table shows the binary parameters and where they come from (database, your value, or missing → neutral value). You can type your own value; "use database value" undoes it.

## 3. Flowsheet
- Drag units from the palette (or click them). Connect an **outlet (right)** to an **inlet (left)** to make a stream.
- Click a unit to set it up in the side panel. Click a feed to enter temperature (or vapour fraction), pressure, flow and composition.
- Status dot: grey = not checked yet, hollow green = inputs complete, amber = something missing, red = error, filled green = solved.
- Delete or Backspace removes the selected unit or stream.

## 4. Run
Shows what is still missing, with a link to each place. Press **Run**.

## 5. Results
- Stream table, unit results and messages; click a stream or message to jump to it on the canvas.
- Columns and plug-flow reactors also show profiles (charts and a table).
- **Export CSV** saves the results for Excel.

## Units and language
Top right: unit set (SI, Metric, English) and language (English, Türkçe). Files are always stored in SI.

## Files
**File → Save as file** keeps your process as `.opd.json`; **File → Open…** loads it again. **File → Examples** has ready-made processes. Your last process is also kept in this browser.

## Units available
Feed, product, mixer, splitter, flash, heater/cooler, heat exchanger, valve, pump, compressor, conversion reactor, CSTR, PFR, equilibrium reactor, shortcut column (FUG), distillation column (rigorous). Recycle loops are solved automatically.

**Heat exchanger zones.** The exchanger splits its duty into zones (default 10, side panel → *Zone analysis*) and adds a zone boundary at every bubble or dew point inside it. UA is the sum over the zones, the *minimum approach* is the internal pinch, and the Results page draws the T–Q heat curves. A temperature cross inside the exchanger is reported even when both ends look fine. Example: *Steam-heated vaporizer*.
