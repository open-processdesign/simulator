import { beforeEach, describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import i18n from "@/i18n";
import { emptyFlowsheet } from "@/opd/types";
import { renderWithApp } from "@/test/render";
import { UnitSetProvider } from "@/units/UnitSetProvider";
import { ProfileCharts } from "./ProfileChart";

// Display-only profile; real profiles come from the engine.
const profile = {
  axis: { name: "stage", unit: "1", values: [1, 2, 3] },
  series: {
    temperature: { unit: "K", values: [353.15, 363.15, 373.15] },
    liquid_flow: { unit: "mol/s", values: [10, 12, 5] },
    vapor_flow: { unit: "mol/s", values: [0, 15, 15] },
    x_a: { unit: "1", values: [0.9, 0.5, 0.1] },
    x_b: { unit: "1", values: [0.1, 0.5, 0.9] },
  },
};
const doc = { ...emptyFlowsheet("t"), components: [{ id: "a", name: "alpha", cas: "1-1-1" }, { id: "b", name: "beta", cas: "2-2-2" }] };

describe("stage profiles", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("draws two charts with a legend and direct labels, and offers a table in the unit set", async () => {
    const user = userEvent.setup();
    renderWithApp(<UnitSetProvider initial="METRIC"><ProfileCharts unitId="T-1" profile={profile} doc={doc} /></UnitSetProvider>, doc);
    const region = screen.getByRole("region", { name: "Profiles of T-1" });
    expect(within(region).getByRole("img", { name: "Temperature [°C]" })).toBeInTheDocument();
    expect(within(region).getByRole("img", { name: "Liquid mole fraction" })).toBeInTheDocument();
    expect(within(region).getAllByText("alpha").length).toBeGreaterThanOrEqual(1);

    await user.click(within(region).getByRole("button", { name: "Show table" }));
    const rows = within(region).getAllByRole("row");
    expect(rows[0].textContent).toBe("StageT [°C]L [kmol/h]V [kmol/h]x alphax beta");
    expect(within(rows[1]).getAllByRole("cell").map((c) => c.textContent)).toEqual(["1", "80.00", "36.000", "0.000", "0.9000", "0.1000"]);
  });

  it("draws heat-exchanger T–Q curves with ΔT in the table", async () => {
    const user = userEvent.setup();
    const heat = {
      axis: { name: "duty", unit: "W", values: [0, 30000, 44000, 47000] },
      series: {
        hot_temperature: { unit: "K", values: [330, 373.15, 373.15, 450] },
        cold_temperature: { unit: "K", values: [300, 340, 360, 363.15] },
      },
    };
    renderWithApp(<UnitSetProvider initial="METRIC"><ProfileCharts unitId="E-1" profile={heat} doc={doc} /></UnitSetProvider>, doc);
    const region = screen.getByRole("region", { name: "Profiles of E-1" });
    expect(within(region).getByText(/heat curves/)).toBeInTheDocument();
    expect(within(region).getByRole("img", { name: "Temperature [°C]" })).toBeInTheDocument();
    expect(within(region).queryByRole("img", { name: "Mole fraction" })).toBeNull();
    await user.click(within(region).getByRole("button", { name: "Show table" }));
    const rows = within(region).getAllByRole("row");
    expect(rows[0].textContent).toMatch(/^Duty \[.+\]Hot side \[°C\]Cold side \[°C\]ΔT \[.+\]$/);
    expect(within(rows[3]).getAllByRole("cell").slice(1).map((c) => c.textContent)).toEqual(["100.00", "86.85", "13.15"]);
  });
});

