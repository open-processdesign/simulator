import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import "./i18n";
import { App } from "./App";
import { EngineProvider } from "./engine/EngineProvider";
import { FlowsheetProvider } from "./state/FlowsheetProvider";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <EngineProvider>
      <FlowsheetProvider>
        <App />
      </FlowsheetProvider>
    </EngineProvider>
  </StrictMode>,
);
