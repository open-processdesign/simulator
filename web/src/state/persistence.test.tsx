import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import i18n from "@/i18n";
import { FileMenu } from "@/components/FileMenu";
import { EXAMPLES } from "@/examples";
import { emptyFlowsheet, type Flowsheet } from "@/opd/types";
import { renderWithApp } from "@/test/render";
import { useFlowsheet } from "./FlowsheetProvider";
import { fileName, loadDraft, parseDocument, saveDraft } from "./persistence";

function DocProbe() {
  const { doc } = useFlowsheet();
  return <pre data-testid="doc">{JSON.stringify(doc)}</pre>;
}
const currentDoc = () => JSON.parse(screen.getByTestId("doc").textContent ?? "{}") as Flowsheet;

describe("persistence helpers", () => {
  it("parses OPD files and rejects others", () => {
    expect(parseDocument("{").ok).toBe(false);
    expect(parseDocument('{"format":"x"}')).toEqual({ ok: false, reason: "format" });
    const doc = emptyFlowsheet("A");
    expect(parseDocument(JSON.stringify(doc))).toEqual({ ok: true, doc });
  });

  it("makes file names from process names", () => {
    expect(fileName({ ...emptyFlowsheet("Benzene–toluene column") })).toBe("benzene-toluene-column.opd.json");
    expect(fileName({ ...emptyFlowsheet("Çözücü geri kazanımı") })).toBe("cozucu-geri-kazanimi.opd.json");
  });

  it("keeps a draft in this browser", () => {
    const doc = { ...emptyFlowsheet("Draft"), components: [{ id: "water", name: "water", cas: "7732-18-5" }] };
    saveDraft(doc);
    expect(loadDraft()).toEqual(doc);
    window.localStorage.setItem("opd.draft", "not json");
    expect(loadDraft()).toBeNull();
  });

  it("ships the example gallery", () => {
    expect(EXAMPLES.map((e) => e.file).sort()).toEqual([
      "benzene-toluene-column.opd.json", "benzene-toluene-rigorous-column.opd.json", "ethane-cracking-pfr.opd.json", "flash-drum.opd.json", "hda-recycle-loop.opd.json", "methanol-water-column-nrtl.opd.json"]);
  });
});

describe("file menu", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
    window.location.hash = "";
  });

  it("opens an example (after confirming) and saves the document as a file", async () => {
    const user = userEvent.setup();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderWithApp(<><FileMenu /><DocProbe /></>, { ...emptyFlowsheet("Mine"), components: [{ id: "a", name: "a", cas: "71-43-2" }] });
    await user.click(screen.getByRole("button", { name: "File" }));
    const menu = screen.getByRole("menu", { name: "File" });
    await user.click(within(menu).getByRole("menuitem", { name: /HDA|hydrodealkylation/i }));
    expect(confirm).toHaveBeenCalledOnce();
    expect(currentDoc().name).toMatch(/hydrodealkylation/i);
    expect(window.location.hash).toBe("#/flowsheet");

    const createObjectURL = vi.fn(() => "blob:x");
    Object.assign(URL, { createObjectURL, revokeObjectURL: vi.fn() });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    await user.click(screen.getByRole("button", { name: "File" }));
    await user.click(screen.getByRole("menuitem", { name: "Save as file" }));
    expect(click).toHaveBeenCalledOnce();
    const blob = (createObjectURL.mock.calls[0] as unknown as [Blob])[0];
    const saved = JSON.parse(await blob.text());
    expect(saved.format).toBe("opd-flowsheet");
    expect(saved.results).toBeUndefined();
    confirm.mockRestore();
    click.mockRestore();
  });

  it("opens a file and reports files that are not flowsheets", async () => {
    const user = userEvent.setup();
    renderWithApp(<><FileMenu /><DocProbe /></>);
    const input = screen.getByLabelText("Open…", { selector: "input" });
    await user.upload(input, new File(['{"hello": 1}'], "notes.json", { type: "application/json" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("notes.json is not an Open Process Design flowsheet");

    const good = { ...emptyFlowsheet("From disk"), components: [{ id: "water", name: "water", cas: "7732-18-5" }] };
    await user.upload(input, new File([JSON.stringify(good)], "x.opd.json", { type: "application/json" }));
    await waitFor(() => expect(currentDoc().name).toBe("From disk"));
  });
});
