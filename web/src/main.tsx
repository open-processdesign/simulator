import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import "./i18n";
import { App } from "./App";
import { EngineProvider } from "./engine/EngineProvider";
import { FlowsheetProvider } from "./state/FlowsheetProvider";
import { RunProvider } from "./state/RunProvider";
import { SelectionProvider } from "./state/SelectionProvider";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <EngineProvider>
      <FlowsheetProvider persist>
        <RunProvider>
          <SelectionProvider>
            <App />
          </SelectionProvider>
        </RunProvider>
      </FlowsheetProvider>
    </EngineProvider>
  </StrictMode>,
);
