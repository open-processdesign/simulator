# Demo video

`docs/media/demo.mp4` (1920×1080, 30 fps, ~98 s) is recorded from the real app with the real
engine — nothing in it is mocked.

1. Build the web app against a local Pyodide distribution and the three wheels
   (see `web/src/engine/engine.spike.test.ts`): `VITE_PYODIDE_URL=/pyodide/ VITE_WHEELS=/wheels/thermo-….whl,… npx vite build`.
2. Serve the build (with `pyodide/` and `wheels/` next to `index.html`) on `localhost:4181`.
3. `python record.py` — Playwright drives Chrome, injects a cursor and caption bar, records one
   video and logs the time of every segment (the engine boot and solver waits are cut out).
4. `python cards.py` — title, validation and end cards.
5. Each segment and card is encoded with `libx264 -crf 20 -preset veryfast`, faded in/out inside
   its own file, and the files are joined with the concat demuxer (`-c copy`).
