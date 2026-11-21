/** The five workflow steps, in order (docs/DESIGN_SYSTEM.md → Layout). */
export const STEPS = ["components", "thermo", "flowsheet", "run", "results"] as const;
export type Step = (typeof STEPS)[number];

/** Read the step from the URL hash (`#/flowsheet`); hash routing keeps GitHub Pages simple. */
export function stepFromHash(hash: string): Step {
  const value = hash.replace(/^#\/?/, "");
  return (STEPS as readonly string[]).includes(value) ? (value as Step) : STEPS[0];
}
