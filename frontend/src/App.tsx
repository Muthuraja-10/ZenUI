import {
  useCallback,
  useRef,
  useState,
} from "react";

import type {
  FormEvent,
  KeyboardEvent,
} from "react";

import "./App.css";

import Renderer from "./Renderer";


// ============================================================
// CONFIGURATION
// ============================================================

const API_URL =
  import.meta.env.VITE_API_URL ??
  "http://127.0.0.1:8000/api/chat";


// ============================================================
// TYPES
// ============================================================

type FormState = Record<string, unknown>;

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  ui: string | null;
};

type ChatResponse = {
  session_id?: string;
  message?: string | null;
  ui?: string | null;
  ui_plan?: unknown;
  resource_data?: unknown;
  tool_calls?: unknown;
  tool_results?: unknown;
};


// ============================================================
// HELPERS
// ============================================================

function createId(): string {
  return crypto.randomUUID();
}

function createSessionId(): string {
  return crypto.randomUUID();
}


// ============================================================
// APP
// ============================================================

function App() {
  const [messages, setMessages] =
    useState<ChatMessage[]>([]);

  const [input, setInput] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const sessionIdRef =
    useRef(createSessionId());


  // ==========================================================
  // SEND MESSAGE
  // ==========================================================

  const sendMessage = useCallback(
    async (
      message: string,
      formState: FormState = {},
      addUserMessage = true,
    ) => {
      const trimmed =
        message.trim();

      if (!trimmed || loading) {
        return;
      }

      setError(null);

      // --------------------------------------------------------
      // User message
      // --------------------------------------------------------

      if (addUserMessage) {
        const userMessage: ChatMessage = {
          id: createId(),
          role: "user",
          content: trimmed,
          ui: null,
        };

        setMessages((current) => [
          ...current,
          userMessage,
        ]);
      }

      setInput("");
      setLoading(true);


      try {
        // ------------------------------------------------------
        // Backend request
        // ------------------------------------------------------

        const response =
          await fetch(API_URL, {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              message: trimmed,

              session_id:
                sessionIdRef.current,

              form_state:
                formState,
            }),
          });


        if (!response.ok) {
          const text =
            await response.text();

          throw new Error(
            text ||
              `Request failed with status ${response.status}`,
          );
        }


        // ------------------------------------------------------
        // Backend response
        // ------------------------------------------------------

        const data =
          (await response.json()) as ChatResponse;


        // ------------------------------------------------------
        // Session
        // ------------------------------------------------------

        if (
          typeof data.session_id ===
          "string" &&
          data.session_id.trim()
        ) {
          sessionIdRef.current =
            data.session_id;
        }


        // ------------------------------------------------------
        // Developer diagnostics
        //
        // IMPORTANT:
        // These stay in the browser console.
        // They are NOT rendered into the UI.
        // ------------------------------------------------------

        console.group(
          "========== ZENUI RESPONSE ==========",
        );

        console.log(
          "SESSION:",
          data.session_id,
        );

        console.log(
          "MESSAGE:",
          data.message,
        );

        console.log(
          "UI:",
          data.ui,
        );

        console.log(
          "UI PLAN:",
          data.ui_plan,
        );

        console.log(
          "RESOURCE DATA:",
          data.resource_data,
        );

        console.log(
          "TOOL CALLS:",
          data.tool_calls,
        );

        console.log(
          "TOOL RESULTS:",
          data.tool_results,
        );

        console.groupEnd();


        // ------------------------------------------------------
        // Assistant message
        // ------------------------------------------------------

        const assistantMessage: ChatMessage = {
          id: createId(),
          role: "assistant",

          content:
            typeof data.message ===
            "string"
              ? data.message.trim()
              : "",

          ui:
            typeof data.ui ===
            "string" &&
            data.ui.trim()
              ? data.ui
              : null,
        };


        setMessages((current) => [
          ...current,
          assistantMessage,
        ]);
      } catch (requestError) {
        console.error(
          "ZENUI CHAT ERROR:",
          requestError,
        );

        setError(
          requestError instanceof Error
            ? requestError.message
            : "Unable to contact ZenUI.",
        );
      } finally {
        setLoading(false);
      }
    },
    [loading],
  );


  // ==========================================================
  // FORM SUBMIT
  // ==========================================================

  const handleSubmit = (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    void sendMessage(input);
  };


  // ==========================================================
  // TEXTAREA KEYBOARD
  // ==========================================================

  const handleInputKeyDown = (
    event: KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      if (!loading && input.trim()) {
        void sendMessage(input);
      }
    }
  };


  // ==========================================================
  // OPENUI ACTION
  // ==========================================================

  const handleRendererAction = useCallback(
    (
      message: string,
      formState?: FormState,
    ) => {
      /*
       * OpenUI actions are returned to ZenUI
       * as normal conversational requests.
       *
       * The frontend does NOT interpret the
       * business meaning of the action.
       */

      void sendMessage(
        message,
        formState ?? {},
        true,
      );
    },
    [sendMessage],
  );


  // ==========================================================
  // NEW CHAT
  // ==========================================================

  const handleNewChat = () => {
    if (loading) {
      return;
    }

    sessionIdRef.current =
      createSessionId();

    setMessages([]);
    setInput("");
    setError(null);
  };


  // ==========================================================
  // QUICK PROMPT
  // ==========================================================

  const handleQuickPrompt = (
    prompt: string,
  ) => {
    if (loading) {
      return;
    }

    void sendMessage(prompt);
  };


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div className="zenui-app">

      {/* ======================================================
          HEADER
          ====================================================== */}

      <header className="zenui-header">

        <div className="zenui-brand">

          <div className="zenui-brand-mark">
            Z
          </div>

          <div className="zenui-brand-copy">

            <div className="zenui-brand-name">
              ZenUI
            </div>

            <div className="zenui-brand-subtitle">
              Intelligent enterprise workspace
            </div>

          </div>

        </div>


        <div className="zenui-header-actions">

          <div className="zenui-status">
            <span className="zenui-status-dot" />
            Connected
          </div>

          <button
            type="button"
            className="zenui-new-chat"
            onClick={handleNewChat}
            disabled={loading}
          >
            New chat
          </button>

        </div>

      </header>


      {/* ======================================================
          MAIN
          ====================================================== */}

      <main className="zenui-main">

        <section
          className={
            messages.length === 0
              ? "zenui-conversation zenui-conversation-empty"
              : "zenui-conversation"
          }
        >

          {/* ==================================================
              EMPTY / WELCOME STATE
              ================================================== */}

          {messages.length === 0 && (
            <div className="zenui-welcome">

              <div className="zenui-welcome-badge">
                AI-powered enterprise workspace
              </div>

              <h1>
                What do you need?
              </h1>

              <p>
                Describe your task in natural language.
                ZenUI understands your intent and generates
                the interface needed to work with it.
              </p>


              <div className="zenui-example-grid">

                <button
                  type="button"
                  onClick={() =>
                    handleQuickPrompt(
                      "Show purchase orders",
                    )
                  }
                  disabled={loading}
                >
                  <span className="zenui-example-title">
                    Show purchase orders
                  </span>

                  <span className="zenui-example-description">
                    Explore purchase order information
                  </span>
                </button>


                <button
                  type="button"
                  onClick={() =>
                    handleQuickPrompt(
                      "Show our sales",
                    )
                  }
                  disabled={loading}
                >
                  <span className="zenui-example-title">
                    Show our sales
                  </span>

                  <span className="zenui-example-description">
                    Explore sales information
                  </span>
                </button>


                <button
                  type="button"
                  onClick={() =>
                    handleQuickPrompt(
                      "Show employees",
                    )
                  }
                  disabled={loading}
                >
                  <span className="zenui-example-title">
                    Show employees
                  </span>

                  <span className="zenui-example-description">
                    Explore employee information
                  </span>
                </button>


                <button
                  type="button"
                  onClick={() =>
                    handleQuickPrompt(
                      "Show customers",
                    )
                  }
                  disabled={loading}
                >
                  <span className="zenui-example-title">
                    Show customers
                  </span>

                  <span className="zenui-example-description">
                    Explore customer information
                  </span>
                </button>

              </div>

            </div>
          )}


          {/* ==================================================
              CONVERSATION
              ================================================== */}

          {messages.length > 0 && (
            <div className="zenui-message-list">

              {messages.map((message) => (

                <article
                  key={message.id}
                  className={
                    message.role === "user"
                      ? "zenui-message zenui-message-user"
                      : "zenui-message zenui-message-assistant"
                  }
                >

                  {/* ==========================================
                      USER
                      ========================================== */}

                  {message.role === "user" && (
                    <div className="zenui-user-message">

                      <div className="zenui-user-bubble">
                        {message.content}
                      </div>

                    </div>
                  )}


                  {/* ==========================================
                      ASSISTANT
                      ========================================== */}

                  {message.role === "assistant" && (
                    <div className="zenui-assistant-message">

                      <div className="zenui-assistant-avatar">
                        Z
                      </div>

                      <div className="zenui-assistant-content">

                        {message.content && (
                          <div className="zenui-assistant-text">
                            {message.content}
                          </div>
                        )}


                        {message.ui && (
                          <div className="generated-ui">

                            <Renderer
                              ui={message.ui}
                              isStreaming={false}
                              onAction={
                                handleRendererAction
                              }
                            />

                          </div>
                        )}

                      </div>

                    </div>
                  )}

                </article>

              ))}


              {/* ==============================================
                  LOADING
                  ============================================== */}

              {loading && (
                <div className="zenui-message zenui-message-assistant">

                  <div className="zenui-assistant-message">

                    <div className="zenui-assistant-avatar">
                      Z
                    </div>

                    <div className="zenui-thinking">

                      <span />
                      <span />
                      <span />

                      <span className="zenui-thinking-text">
                        Thinking…
                      </span>

                    </div>

                  </div>

                </div>
              )}

            </div>
          )}


          {/* ==================================================
              ERROR
              ================================================== */}

          {error && (
            <div className="zenui-error">

              <div className="zenui-error-content">

                <strong>
                  Something went wrong
                </strong>

                <span>
                  {error}
                </span>

              </div>

              <button
                type="button"
                onClick={() =>
                  setError(null)
                }
              >
                Dismiss
              </button>

            </div>
          )}

        </section>


        {/* ====================================================
            COMPOSER
            ==================================================== */}

        <div className="zenui-composer-area">

          <form
            className="zenui-composer"
            onSubmit={handleSubmit}
          >

            <textarea
              value={input}
              onChange={(event) =>
                setInput(event.target.value)
              }
              onKeyDown={handleInputKeyDown}
              placeholder="Ask ZenUI anything..."
              rows={1}
              disabled={loading}
              aria-label="Message ZenUI"
            />

            <button
              type="submit"
              className="zenui-send-button"
              disabled={
                loading ||
                !input.trim()
              }
              aria-label="Send message"
            >
              {loading ? "…" : "↑"}
            </button>

          </form>

          <div className="zenui-composer-hint">
            Enter to send · Shift + Enter for a new line
          </div>

        </div>

      </main>

    </div>
  );
}

export default App;