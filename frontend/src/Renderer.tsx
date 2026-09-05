import React, { useCallback } from "react";

import {
  Renderer as OpenUIRenderer,
  type ParseResult,
} from "@openuidev/react-lang";

import { openuiLibrary } from "@openuidev/react-ui";


// ============================================================
// TYPES
// ============================================================

type FormState = Record<string, unknown>;

type OpenUIActionEvent = {
  type?: unknown;
  humanFriendlyMessage?: unknown;
  formState?: unknown;
};

type RendererProps = {
  ui: string | null | undefined;
  isStreaming?: boolean;
  onAction?: (
    message: string,
    formState?: FormState,
  ) => void;
};


// ============================================================
// RENDERER
// ============================================================

const Renderer: React.FC<RendererProps> = ({
  ui,
  isStreaming = false,
  onAction,
}) => {
  // ==========================================================
  // OPENUI ACTION
  // ==========================================================

  const handleAction = useCallback(
    (event: unknown) => {
      console.debug(
        "ZENUI OPENUI ACTION:",
        event,
      );

      if (
        !event ||
        typeof event !== "object"
      ) {
        return;
      }

      const action =
        event as OpenUIActionEvent;

      /*
       * ZenUI currently uses the OpenUI action
       * to continue the conversation.
       *
       * The renderer itself does not decide
       * what the action means.
       */
      if (
        action.type !==
        "continue_conversation"
      ) {
        return;
      }

      if (
        typeof action.humanFriendlyMessage !==
        "string"
      ) {
        return;
      }

      const message =
        action.humanFriendlyMessage.trim();

      if (!message) {
        return;
      }


      // --------------------------------------------------------
      // Extract form state when supplied by OpenUI.
      // --------------------------------------------------------

      let formState:
        | FormState
        | undefined;

      if (
        action.formState &&
        typeof action.formState === "object" &&
        !Array.isArray(action.formState)
      ) {
        formState =
          action.formState as FormState;
      }


      // --------------------------------------------------------
      // Give the action back to App.tsx.
      // --------------------------------------------------------

      onAction?.(
        message,
        formState,
      );
    },
    [onAction],
  );


  // ==========================================================
  // OPENUI STATE
  // ==========================================================

  const handleStateUpdate = useCallback(
    (state: Record<string, unknown>) => {
      console.debug(
        "ZENUI OPENUI STATE:",
        state,
      );
    },
    [],
  );


  // ==========================================================
  // PARSE RESULT
  // ==========================================================

  const handleParseResult = useCallback(
    (result: ParseResult | null) => {
      console.debug(
        "ZENUI OPENUI PARSE RESULT:",
        result,
      );

      if (!result) {
        return;
      }

      if (
        result.meta?.errors?.length
      ) {
        console.error(
          "ZENUI OPENUI PARSE ERRORS:",
          result.meta.errors,
        );
      }

      if (
        result.meta?.unresolved?.length
      ) {
        console.warn(
          "ZENUI OPENUI UNRESOLVED:",
          result.meta.unresolved,
        );
      }

      if (
        result.meta?.orphaned?.length
      ) {
        console.warn(
          "ZENUI OPENUI ORPHANED:",
          result.meta.orphaned,
        );
      }
    },
    [],
  );


  // ==========================================================
  // CHECK IF THERE'S ANYTHING TO RENDER
  // ==========================================================

  const response =
    typeof ui === "string"
      ? ui.trim()
      : "";

  if (!response) {
    return null;
  }


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div
      className="zenui-openui"
      data-openui-renderer="true"
    >
      <OpenUIRenderer
        response={response}
        library={openuiLibrary}
        isStreaming={isStreaming}
        onAction={handleAction}
        onStateUpdate={handleStateUpdate}
        onParseResult={handleParseResult}
        onError={(errors) => {
          console.error(
            "ZENUI OPENUI RENDER ERRORS:",
            errors,
          );
        }}
      />
    </div>
  );
};


export default Renderer;