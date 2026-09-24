import {
  AlertTriangle,
  CheckCircle2,
  Info,
  X,
} from "lucide-react";

import {
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  AppDialogContext,
  type AlertDialogOptions,
  type ConfirmDialogOptions,
  type DialogTone,
  type PromptDialogOptions,
} from "./appDialog";


type ConfirmDialogState = {
  kind: "confirm";
  options: ConfirmDialogOptions;
  resolve: (value: boolean) => void;
};


type PromptDialogState = {
  kind: "prompt";
  options: PromptDialogOptions;
  resolve: (
    value: string | null,
  ) => void;
};


type AlertDialogState = {
  kind: "alert";
  options: AlertDialogOptions;
  resolve: () => void;
};


type DialogState =
  | ConfirmDialogState
  | PromptDialogState
  | AlertDialogState;


function iconForTone(
  tone: DialogTone,
) {
  if (tone === "danger") {
    return {
      icon: AlertTriangle,
      wrapperClass:
        "border-red-500/20 bg-red-500/10 text-red-300",
    };
  }

  if (tone === "success") {
    return {
      icon: CheckCircle2,
      wrapperClass:
        "border-emerald-500/20 bg-emerald-500/10 text-emerald-300",
    };
  }

  return {
    icon: Info,
    wrapperClass:
      "border-indigo-500/20 bg-indigo-500/10 text-indigo-300",
  };
}


export function AppDialogProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [
    dialog,
    setDialog,
  ] = useState<DialogState | null>(
    null,
  );

  const [
    promptValue,
    setPromptValue,
  ] = useState("");

  const inputRef =
    useRef<HTMLInputElement | null>(
      null,
    );


  useEffect(() => {
    if (!dialog) {
      return;
    }

    const previousOverflow =
      document.body.style.overflow;

    document.body.style.overflow =
      "hidden";

    return () => {
      document.body.style.overflow =
        previousOverflow;
    };
  }, [
    dialog,
  ]);


  useEffect(() => {
    if (
      dialog?.kind !== "prompt"
    ) {
      return;
    }

    const timeoutId =
      window.setTimeout(
        () => {
          inputRef.current?.focus();
          inputRef.current?.select();
        },
        0,
      );

    return () => {
      window.clearTimeout(
        timeoutId,
      );
    };
  }, [
    dialog,
  ]);


  useEffect(() => {
    if (!dialog) {
      return;
    }

    const activeDialog =
      dialog;

    function handleKeyDown(
      event: KeyboardEvent,
    ) {
      if (
        event.key !==
        "Escape"
      ) {
        return;
      }

      if (
        activeDialog.kind ===
        "confirm"
      ) {
        activeDialog.resolve(
          false,
        );
      } else if (
        activeDialog.kind ===
        "prompt"
      ) {
        activeDialog.resolve(
          null,
        );
      } else {
        activeDialog.resolve();
      }

      setDialog(null);
    }

    window.addEventListener(
      "keydown",
      handleKeyDown,
    );

    return () => {
      window.removeEventListener(
        "keydown",
        handleKeyDown,
      );
    };
  }, [
    dialog,
  ]);


  const contextValue =
    useMemo(
      () => ({
        confirm:
          (
            options: ConfirmDialogOptions,
          ) =>
            new Promise<boolean>(
              (resolve) => {
                setDialog({
                  kind: "confirm",
                  options,
                  resolve,
                });
              },
            ),

        prompt:
          (
            options: PromptDialogOptions,
          ) =>
            new Promise<string | null>(
              (resolve) => {
                setPromptValue(
                  options.defaultValue ??
                    "",
                );

                setDialog({
                  kind: "prompt",
                  options,
                  resolve,
                });
              },
            ),

        alert:
          (
            options: AlertDialogOptions,
          ) =>
            new Promise<void>(
              (resolve) => {
                setDialog({
                  kind: "alert",
                  options,
                  resolve,
                });
              },
            ),
      }),
      [],
    );


  function closeAsCancel() {
    if (!dialog) {
      return;
    }

    if (
      dialog.kind ===
      "confirm"
    ) {
      dialog.resolve(
        false,
      );
    } else if (
      dialog.kind ===
      "prompt"
    ) {
      dialog.resolve(
        null,
      );
    } else {
      dialog.resolve();
    }

    setDialog(null);
  }


  function handleConfirm() {
    if (!dialog) {
      return;
    }

    if (
      dialog.kind ===
      "confirm"
    ) {
      dialog.resolve(
        true,
      );

      setDialog(null);

      return;
    }

    if (
      dialog.kind ===
      "prompt"
    ) {
      const value =
        promptValue.trim();

      if (!value) {
        return;
      }

      dialog.resolve(
        value,
      );

      setDialog(null);

      return;
    }

    dialog.resolve();

    setDialog(null);
  }


  const tone =
    dialog?.options.tone ??
    "default";

  const toneIcon =
    iconForTone(
      tone,
    );

  const ToneIcon =
    toneIcon.icon;

  const primaryButtonClass =
    tone === "danger"
      ? "bg-red-500 text-white hover:bg-red-400"
      : "bg-indigo-500 text-white hover:bg-indigo-400";


  return (
    <AppDialogContext.Provider
      value={contextValue}
    >
      {children}

      {dialog && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 px-4 py-6 backdrop-blur-[2px]"
          onMouseDown={(
            event,
          ) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              closeAsCancel();
            }
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="app-dialog-title"
            aria-describedby={
              dialog.options
                .description
                ? "app-dialog-description"
                : undefined
            }
            className="w-full max-w-md overflow-hidden rounded-2xl border border-white/10 bg-[#111722] shadow-2xl shadow-black/40"
          >
            <div className="flex items-start gap-4 p-5 sm:p-6">
              <div
                className={[
                  "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border",
                  toneIcon.wrapperClass,
                ].join(" ")}
              >
                <ToneIcon
                  size={18}
                />
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h2
                      id="app-dialog-title"
                      className="break-words text-base font-semibold text-white"
                    >
                      {
                        dialog.options
                          .title
                      }
                    </h2>

                    {dialog.options
                      .description && (
                      <p
                        id="app-dialog-description"
                        className="mt-2 break-words text-sm leading-6 text-slate-400"
                      >
                        {
                          dialog.options
                            .description
                        }
                      </p>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={
                      closeAsCancel
                    }
                    className="shrink-0 rounded-lg p-2 text-slate-500 transition hover:bg-white/5 hover:text-slate-300"
                    aria-label="Close dialog"
                  >
                    <X
                      size={17}
                    />
                  </button>
                </div>

                {dialog.kind ===
                  "prompt" && (
                  <form
                    className="mt-5"
                    onSubmit={(
                      event,
                    ) => {
                      event.preventDefault();

                      handleConfirm();
                    }}
                  >
                    <input
                      ref={inputRef}
                      value={
                        promptValue
                      }
                      onChange={(
                        event,
                      ) =>
                        setPromptValue(
                          event.target
                            .value,
                        )
                      }
                      placeholder={
                        dialog.options
                          .placeholder
                      }
                      className="w-full rounded-xl border border-white/10 bg-[#080b12] px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-indigo-500/50"
                    />
                  </form>
                )}
              </div>
            </div>

            <div className="flex flex-col-reverse gap-2 border-t border-white/8 bg-white/[0.015] px-5 py-4 sm:flex-row sm:justify-end sm:px-6">
              {dialog.kind !==
                "alert" && (
                <button
                  type="button"
                  onClick={
                    closeAsCancel
                  }
                  className="inline-flex w-full items-center justify-center rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-white/8 hover:text-white sm:w-auto"
                >
                  {
                    dialog.options
                      .cancelLabel ??
                    "Cancel"
                  }
                </button>
              )}

              <button
                type="button"
                onClick={
                  handleConfirm
                }
                disabled={
                  dialog.kind ===
                    "prompt" &&
                  !promptValue.trim()
                }
                className={[
                  "inline-flex w-full items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto",
                  primaryButtonClass,
                ].join(" ")}
              >
                {dialog.kind ===
                "alert"
                  ? dialog.options
                      .actionLabel ??
                    "OK"
                  : dialog.options
                      .confirmLabel ??
                    "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppDialogContext.Provider>
  );
}