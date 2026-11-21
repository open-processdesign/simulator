import { describe, expect, it, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithApp } from "@/test/render";
import userEvent from "@testing-library/user-event";
import i18n from "@/i18n";
import en from "@locales/en.json";
import tr from "@locales/tr.json";
import { App } from "@/App";
import { STEPS, stepFromHash } from "@/steps";

function keys(obj: object, prefix = ""): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    v && typeof v === "object" ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
  );
}

describe("app shell", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("shows the five workflow steps with the first one current", () => {
    renderWithApp(<App />);
    const nav = screen.getByRole("navigation", { name: "Workflow steps" });
    const links = nav.querySelectorAll("a");
    expect([...links].map((a) => a.textContent)).toEqual([
      "1Components",
      "2Thermodynamics",
      "3Flowsheet",
      "4Run",
      "5Results",
    ]);
    expect(screen.getByRole("link", { current: "step" })).toHaveTextContent("Components");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Components");
  });

  it("navigates between steps", async () => {
    const user = userEvent.setup();
    renderWithApp(<App />);
    await user.click(screen.getByRole("link", { name: /Flowsheet/ }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Flowsheet");
    expect(screen.getByRole("link", { current: "step" })).toHaveTextContent("Flowsheet");
  });

  it("switches the interface to Turkish", async () => {
    const user = userEvent.setup();
    renderWithApp(<App />);
    await user.selectOptions(screen.getByRole("combobox", { name: "Language" }), "tr");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Bileşenler");
    expect(screen.getByRole("navigation", { name: "İş akışı adımları" })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("tr");
  });
});

describe("steps", () => {
  it("reads the step from the URL hash and falls back to the first step", () => {
    expect(stepFromHash("#/run")).toBe("run");
    expect(stepFromHash("#results")).toBe("results");
    expect(stepFromHash("#/nope")).toBe(STEPS[0]);
    expect(stepFromHash("")).toBe(STEPS[0]);
  });
});

describe("locales", () => {
  it("English and Turkish have the same keys", () => {
    expect(keys(tr).sort()).toEqual(keys(en).sort());
  });
});
