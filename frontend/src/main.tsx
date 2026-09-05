import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";

import {
  ThemeProvider,
  defaultLightTheme,
} from "@openuidev/react-ui";

import "@openuidev/react-ui/components.css";
import "@openuidev/react-ui/styles/index.css";

import "./index.css";

ReactDOM.createRoot(
  document.getElementById("root")!
).render(
  <React.StrictMode>
    <ThemeProvider
      mode="light"
      lightTheme={defaultLightTheme}
    >
      <App />
    </ThemeProvider>
  </React.StrictMode>
);