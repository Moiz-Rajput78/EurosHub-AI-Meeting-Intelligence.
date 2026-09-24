import {
  CheckCircle2,
  FileAudio,
  LoaderCircle,
  UploadCloud,
  Video,
} from "lucide-react";

import {
  useRef,
  useState,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import {
  analyzeMeeting,
  diarizeMeeting,
  getMeetingStatus,
  processMeetingAudio,
  transcribeMeeting,
  uploadMeeting,
} from "../lib/api";


type StepStatus =
  | "pending"
  | "running"
  | "complete"
  | "skipped"
  | "failed";


interface ProcessingStep {
  key: string;
  label: string;
  description: string;
  status: StepStatus;
  progress: number;
}


const INITIAL_STEPS: ProcessingStep[] = [
  {
    key: "upload",
    label: "Upload recording",
    description:
      "Securely save the meeting file.",
    status: "pending",
    progress: 0,
  },
  {
    key: "audio",
    label: "Process audio",
    description:
      "Validate media and normalize audio with FFmpeg.",
    status: "pending",
    progress: 0,
  },
  {
    key: "transcribe",
    label: "Transcribe meeting",
    description:
      "Generate a complete timestamped transcript.",
    status: "pending",
    progress: 0,
  },
  {
    key: "diarize",
    label: "Detect speakers",
    description:
      "Identify speaker turns using diarization.",
    status: "pending",
    progress: 0,
  },
  {
    key: "analyze",
    label: "Generate intelligence",
    description:
      "Create structured AI meeting notes.",
    status: "pending",
    progress: 0,
  },
];


export function UploadPage() {
  const navigate =
    useNavigate();

  const inputRef =
    useRef<HTMLInputElement>(
      null,
    );

  const [
    file,
    setFile,
  ] = useState<File | null>(
    null,
  );

  const [
    title,
    setTitle,
  ] = useState("");

  const [
    steps,
    setSteps,
  ] = useState<
    ProcessingStep[]
  >(INITIAL_STEPS);

  const [
    processing,
    setProcessing,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );


  function updateStep(
    key: string,
    status: StepStatus,
    progress?: number,
  ) {
    setSteps(
      (current) =>
        current.map(
          (step) =>
            step.key === key
              ? {
                  ...step,
                  status,
                  progress:
                    progress === undefined
                      ? step.progress
                      : Math.max(
                          0,
                          Math.min(
                            100,
                            Math.round(
                              progress,
                            ),
                          ),
                        ),
                }
              : step,
        ),
    );
  }


  function startProgressPolling(
    meetingId: number,
  ) {
    let stopped = false;
    let requestInFlight = false;

    async function poll() {
      if (
        stopped ||
        requestInFlight
      ) {
        return;
      }

      requestInFlight = true;

      try {
        const current =
          await getMeetingStatus(
            meetingId,
          );

        if (stopped) {
          return;
        }

        if (
          current.status ===
          "PROCESSING_AUDIO"
        ) {
          updateStep(
            "audio",
            "running",
            current.progress_percent,
          );
        } else if (
          current.status ===
          "TRANSCRIBING"
        ) {
          updateStep(
            "transcribe",
            "running",
            current.progress_percent,
          );
        } else if (
          current.status ===
          "DIARIZING"
        ) {
          updateStep(
            "diarize",
            "running",
          );
        } else if (
          current.status ===
          "GENERATING_NOTES"
        ) {
          updateStep(
            "analyze",
            "running",
            current.progress_percent,
          );
        } else if (
          current.status ===
          "COMPLETED"
        ) {
          updateStep(
            "analyze",
            "complete",
            100,
          );
        }
      } catch {
        // A temporary polling failure should not interrupt
        // the real processing request. The next poll retries.
      } finally {
        requestInFlight = false;
      }
    }

    void poll();

    const intervalId =
      window.setInterval(
        () => {
          void poll();
        },
        500,
      );

    return () => {
      stopped = true;

      window.clearInterval(
        intervalId,
      );
    };
  }


  function handleFile(
    selectedFile: File | null,
  ) {
    if (!selectedFile) {
      return;
    }

    setFile(
      selectedFile,
    );

    if (!title.trim()) {
      const baseName =
        selectedFile.name.replace(
          /\.[^/.]+$/,
          "",
        );

      setTitle(
        baseName,
      );
    }

    setError(null);
  }


  async function handleSubmit() {
    if (
      !file ||
      processing
    ) {
      return;
    }

    setError(null);

    setSteps(
      INITIAL_STEPS.map(
        (step) => ({
          ...step,
        }),
      ),
    );

    setProcessing(true);

    let meetingId:
      | number
      | null = null;

    let stopProgressPolling:
      | (() => void)
      | null = null;

    try {
      updateStep(
        "upload",
        "running",
      );

      const uploaded =
        await uploadMeeting(
          file,
          title,
        );

      meetingId =
        uploaded.id;

      updateStep(
        "upload",
        "complete",
        100,
      );

      stopProgressPolling =
        startProgressPolling(
          meetingId,
        );

      updateStep(
        "audio",
        "running",
        0,
      );

      await processMeetingAudio(
        meetingId,
      );

      updateStep(
        "audio",
        "complete",
        100,
      );

      updateStep(
        "transcribe",
        "running",
        0,
      );

      await transcribeMeeting(
        meetingId,
      );

      updateStep(
        "transcribe",
        "complete",
        100,
      );

      updateStep(
        "diarize",
        "running",
      );

      try {
        await diarizeMeeting(
          meetingId,
        );

        updateStep(
          "diarize",
          "complete",
        );
      } catch {
        updateStep(
          "diarize",
          "skipped",
        );
      }

      updateStep(
        "analyze",
        "running",
        0,
      );

      await analyzeMeeting(
        meetingId,
      );

      updateStep(
        "analyze",
        "complete",
        100,
      );

      window.setTimeout(
        () => {
          navigate(
            `/meetings/${meetingId}`,
          );
        },
        600,
      );
    } catch (caught) {
      const message =
        caught instanceof Error
          ? caught.message
          : "Meeting processing failed.";

      setError(message);

      setSteps(
        (current) =>
          current.map(
            (step) =>
              step.status ===
              "running"
                ? {
                    ...step,
                    status:
                      "failed",
                  }
                : step,
          ),
      );
    } finally {
      stopProgressPolling?.();
      setProcessing(false);
    }
  }


  return (
    <div className="mx-auto w-full min-w-0 max-w-5xl overflow-x-hidden px-3 py-5 sm:px-5 sm:py-7 lg:px-8 lg:py-8">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight text-white sm:text-2xl">
          Upload meeting
        </h1>

        <p className="mt-2 max-w-2xl break-words text-sm leading-6 text-slate-500">
          Upload an audio or video
          recording. Meeting Intelligence
          will process the entire meeting
          automatically.
        </p>
      </div>

      <div className="mt-5 grid min-w-0 gap-4 sm:mt-7 sm:gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <section className="min-w-0 rounded-2xl border border-white/8 bg-[#0d111b] p-4 sm:p-5 lg:p-6">
          <label className="block text-sm font-medium text-slate-200">
            Meeting title
          </label>

          <input
            value={title}
            disabled={processing}
            onChange={(event) =>
              setTitle(
                event.target.value,
              )
            }
            placeholder="Weekly team meeting"
            className="mt-2 w-full min-w-0 rounded-xl border border-white/8 bg-[#080b12] px-3 py-3 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-indigo-500/50 disabled:opacity-60 sm:px-4"
          />

          <div
            role="button"
            tabIndex={
              processing
                ? -1
                : 0
            }
            onClick={() =>
              !processing &&
              inputRef.current?.click()
            }
            onKeyDown={(event) => {
              if (
                (
                  event.key ===
                    "Enter" ||
                  event.key ===
                    " "
                ) &&
                !processing
              ) {
                event.preventDefault();

                inputRef.current?.click();
              }
            }}
            onDragOver={(event) => {
              event.preventDefault();
            }}
            onDrop={(event) => {
              event.preventDefault();

              if (!processing) {
                handleFile(
                  event
                    .dataTransfer
                    .files[0] ??
                    null,
                );
              }
            }}
            className={[
              "mt-4 min-w-0 rounded-2xl border border-dashed border-white/12 bg-[#080b12] px-3 py-8 text-center transition sm:mt-5 sm:px-5 sm:py-10 lg:px-6 lg:py-12",
              processing
                ? "cursor-not-allowed opacity-60"
                : "cursor-pointer hover:border-indigo-500/40 hover:bg-indigo-500/[0.025]",
            ].join(" ")}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".mp3,.wav,.m4a,.mp4,.webm,audio/*,video/*"
              className="hidden"
              disabled={processing}
              onChange={(event) =>
                handleFile(
                  event.target
                    .files?.[0] ??
                    null,
                )
              }
            />

            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-indigo-500/15 bg-indigo-500/10 text-indigo-300 sm:h-14 sm:w-14">
              <UploadCloud
                size={22}
              />
            </div>

            <h2 className="mx-auto mt-4 max-w-full break-words text-sm font-semibold leading-5 text-slate-200 sm:mt-5">
              Drop your meeting
              recording here
            </h2>

            <p className="mt-2 break-words text-[11px] leading-5 text-slate-500 sm:text-xs">
              MP3, WAV, M4A, MP4 or
              WEBM
            </p>

            <div className="mt-5 inline-flex max-w-full items-center justify-center rounded-lg border border-white/8 bg-white/5 px-3 py-2 text-xs font-medium text-slate-300 sm:mt-6">
              Choose file
            </div>
          </div>

          {file && (
            <div className="mt-4 flex min-w-0 items-center gap-3 rounded-xl border border-white/8 bg-white/[0.025] p-3 sm:gap-4 sm:p-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-300">
                {file.type.startsWith(
                  "video/",
                ) ? (
                  <Video
                    size={18}
                  />
                ) : (
                  <FileAudio
                    size={18}
                  />
                )}
              </div>

              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-slate-200">
                  {file.name}
                </div>

                <div className="mt-1 text-xs text-slate-500">
                  {(
                    file.size /
                    1024 /
                    1024
                  ).toFixed(2)}{" "}
                  MB
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="mt-4 min-w-0 break-words rounded-xl border border-red-500/20 bg-red-500/8 p-3 text-sm leading-6 text-red-300 sm:p-4">
              {error}
            </div>
          )}

          <button
            type="button"
            disabled={
              !file ||
              processing
            }
            onClick={() =>
              void handleSubmit()
            }
            className="mt-4 flex w-full min-w-0 items-center justify-center gap-2 rounded-xl bg-indigo-500 px-3 py-3 text-center text-sm font-semibold leading-5 text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-40 sm:mt-5 sm:px-4"
          >
            {processing && (
              <LoaderCircle
                size={17}
                className="shrink-0 animate-spin"
              />
            )}

            <span className="min-w-0 break-words">
              {processing
                ? "Processing meeting..."
                : "Process meeting"}
            </span>
          </button>
        </section>

        <section className="min-w-0 rounded-2xl border border-white/8 bg-[#0d111b] p-4 sm:p-5 lg:p-6">
          <div className="min-w-0">
            <h2 className="font-semibold text-white">
              Processing pipeline
            </h2>

            <p className="mt-1 break-words text-xs leading-5 text-slate-500">
              Each stage uses the real
              backend processing services.
            </p>
          </div>

          <div className="mt-5 min-w-0 space-y-1 sm:mt-6">
            {steps.map(
              (
                step,
                index,
              ) => (
                <div
                  key={step.key}
                  className="relative flex min-w-0 gap-3 pb-5 sm:gap-4 sm:pb-6"
                >
                  {index <
                    steps.length -
                      1 && (
                    <div className="absolute left-[15px] top-8 h-[calc(100%-18px)] w-px bg-white/8" />
                  )}

                  <div
                    className={[
                      "relative z-10 mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border",
                      step.status ===
                      "complete"
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                        : step.status ===
                            "running"
                          ? "border-indigo-500/30 bg-indigo-500/10 text-indigo-300"
                          : step.status ===
                              "failed"
                            ? "border-red-500/30 bg-red-500/10 text-red-300"
                            : step.status ===
                                "skipped"
                              ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                              : "border-white/8 bg-[#080b12] text-slate-600",
                    ].join(
                      " ",
                    )}
                  >
                    {step.status ===
                    "complete" ? (
                      <CheckCircle2
                        size={15}
                      />
                    ) : step.status ===
                      "running" ? (
                      <LoaderCircle
                        size={15}
                        className="animate-spin"
                      />
                    ) : (
                      <span className="text-[11px] font-semibold">
                        {index + 1}
                      </span>
                    )}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex min-w-0 items-center justify-between gap-3">
                      <div className="break-words text-sm font-medium text-slate-200">
                        {step.label}
                      </div>

                      {[
                        "audio",
                        "transcribe",
                        "analyze",
                      ].includes(
                        step.key,
                      ) &&
                        (step.status ===
                          "running" ||
                          step.status ===
                            "complete") && (
                          <span className="shrink-0 text-xs font-semibold tabular-nums text-indigo-300">
                            {step.progress}%
                          </span>
                        )}
                    </div>

                    {[
                      "audio",
                      "transcribe",
                      "analyze",
                    ].includes(
                      step.key,
                    ) &&
                      (step.status ===
                        "running" ||
                        step.status ===
                          "complete") && (
                        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-white/8">
                          <div
                            className="h-full rounded-full bg-indigo-500 transition-[width] duration-300"
                            style={{
                              width: `${step.progress}%`,
                            }}
                          />
                        </div>
                      )}

                    <div className="mt-1 break-words text-xs leading-5 text-slate-500">
                      {
                        step.description
                      }
                    </div>

                    {step.status ===
                      "skipped" && (
                      <div className="mt-1 break-words text-xs leading-5 text-amber-300">
                        Diarization was
                        unavailable.
                        Processing continued
                        with the transcript.
                      </div>
                    )}

                    {step.status ===
                      "failed" && (
                      <div className="mt-1 text-xs leading-5 text-red-300">
                        This processing stage
                        failed.
                      </div>
                    )}
                  </div>
                </div>
              ),
            )}
          </div>
        </section>
      </div>
    </div>
  );
}