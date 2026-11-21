import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import i18n from "@/i18n";
import { emptyFlowsheet, type Flowsheet } from "@/opd/types";
import { renderWithApp } from "@/test/render";
import { ComponentsPage } from "./ComponentsPage";
import { ThermoPage } from "./ThermoPage";

function withComponents(...items: [string, string, string][]): Flowsheet {
  return { ...emptyFlowsheet("t"), components: items.map(([id, name, cas]) => ({ id, name, cas })) };
}

describe("Components page", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("searches, adds and removes components", async () => {
    const user = userEvent.setup();
    renderWithApp(<ComponentsPage />);
    expect(screen.getByText(/No components yet/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Search components"), "toluene");
    await user.click(screen.getByRole("button", { name: "Add toluene" }));
    const table = screen.getByRole("table");
    expect(within(table).getByText("toluene")).toBeInTheDocument();
    expect(within(table).getByText("108-88-3")).toBeInTheDocument();
    expect(within(table).getByText("92.14")).toBeInTheDocument(); // molar mass from the index
    expect(screen.getByText("Components in this process (1)")).toBeInTheDocument();
    // Already added components cannot be added twice.
    expect(screen.queryByRole("button", { name: "Add toluene" })).toBeNull();

    await user.click(screen.getByRole("button", { name: "Remove toluene" }));
    expect(screen.getByText(/No components yet/)).toBeInTheDocument();
  });

  it("formats numbers with a decimal comma in Turkish", async () => {
    await i18n.changeLanguage("tr");
    renderWithApp(<ComponentsPage />, withComponents(["toluene", "toluene", "108-88-3"]));
    expect(screen.getByText("92,14")).toBeInTheDocument();
  });
});

describe("Thermodynamics page", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("switches the property method; Raoult needs no k_ij", async () => {
    const user = userEvent.setup();
    renderWithApp(<ThermoPage />, withComponents(["benzene", "benzene", "71-43-2"], ["toluene", "toluene", "108-88-3"]));
    expect(screen.getByRole("radio", { name: /^Peng–Robinson/ })).toBeChecked();
    expect(screen.getByRole("radio", { name: /^NRTL/ })).toBeEnabled();
    await user.click(screen.getByRole("radio", { name: /^Ideal/ }));
    expect(screen.getByText("Raoult's law uses no binary parameters.")).toBeInTheDocument();
  });

  it("shows k_ij sources from the engine and accepts a user value with a decimal comma", async () => {
    const user = userEvent.setup();
    renderWithApp(
      <ThermoPage />,
      withComponents(["methane", "methane", "74-82-8"], ["co2", "carbon dioxide", "124-38-9"], ["benzene", "benzene", "71-43-2"]),
    );
    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows.map((r) => r.textContent)).toEqual([
      "methane – carbon dioxideDatabase",
      "methane – benzeneMissing → 0",
      "carbon dioxide – benzeneMissing → 0",
    ]);
    expect(within(rows[0]).getByRole("textbox")).toHaveValue("0.0978");
    expect(screen.getByText(/Pairs without a value use k_ij = 0/)).toBeInTheDocument();

    const input = within(rows[2]).getByRole("textbox");
    await user.clear(input);
    await user.type(input, "0,05{Enter}");
    await waitFor(() => expect(within(screen.getAllByRole("row")[3]).getByText("User")).toBeInTheDocument());
    expect(within(screen.getAllByRole("row")[3]).getByRole("textbox")).toHaveValue("0.0500");

    await user.click(screen.getByRole("button", { name: "Use database value" }));
    await waitFor(() => expect(within(screen.getAllByRole("row")[3]).getByText("Missing → 0")).toBeInTheDocument());
  });

  it("shows NRTL b_ij, b_ji and α with sources and accepts user values", async () => {
    const user = userEvent.setup();
    const doc = withComponents(["methanol", "methanol", "67-56-1"], ["water", "water", "7732-18-5"], ["benzene", "benzene", "71-43-2"]);
    renderWithApp(<ThermoPage />, { ...doc, thermo: { package: "NRTL" } });
    expect(screen.getByText("NRTL binary parameters (τ_ij = b_ij / T)")).toBeInTheDocument();
    const table = await screen.findByRole("table");
    expect(within(table).getAllByRole("columnheader").map((h) => h.textContent)).toEqual(
      ["Pair", "b_ij [K]", "b_ji [K]", "α_ij", "Source", ""]);
    const rows = within(table).getAllByRole("row").slice(1);
    expect(within(rows[0]).getByRole("textbox", { name: "b_ij [K] for methanol–water" })).toHaveValue("-95.13");
    expect(within(rows[0]).getByRole("textbox", { name: "b_ji [K] for water–methanol" })).toHaveValue("398.95");
    expect(within(rows[0]).getByText("Database")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Missing → 0")).toBeInTheDocument();
    expect(screen.getByText(/treated as ideal/)).toBeInTheDocument();

    const b = within(rows[1]).getByRole("textbox", { name: "b_ji [K] for benzene–methanol" });
    await user.clear(b);
    await user.type(b, "250,5{Enter}");
    await waitFor(() => expect(within(screen.getAllByRole("row")[2]).getByText("User")).toBeInTheDocument());
    expect(within(screen.getAllByRole("row")[2]).getByRole("textbox", { name: "b_ji [K] for benzene–methanol" })).toHaveValue("250.50");
  });
});
