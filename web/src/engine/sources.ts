/**
 * The Python package `engine/opd_engine`, bundled as text so the worker can write it
 * into Pyodide's file system. Vite inlines the files at build time.
 */
const files = import.meta.glob("../../../engine/opd_engine/**/*.py", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

export const OPD_ENGINE_SOURCES: Record<string, string> = Object.fromEntries(
  Object.entries(files).map(([path, text]) => [path.replace(/^.*\/opd_engine\//, ""), text]),
);
