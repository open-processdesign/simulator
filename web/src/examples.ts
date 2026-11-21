import type { Flowsheet } from "@/opd/types";

/** Example flowsheets from the repository's `examples/` folder, bundled at build time. */
const files = import.meta.glob("../../examples/*.opd.json", { eager: true, import: "default" }) as Record<string, Flowsheet>;

export const EXAMPLES: { file: string; doc: Flowsheet }[] = Object.entries(files)
  .map(([path, doc]) => ({ file: path.replace(/^.*\//, ""), doc }))
  .sort((a, b) => a.doc.name.localeCompare(b.doc.name));
