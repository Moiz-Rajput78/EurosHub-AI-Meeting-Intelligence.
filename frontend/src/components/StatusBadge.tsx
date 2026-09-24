import {
  CircleAlert,
  CircleCheck,
  Clock3,
  LoaderCircle,
} from "lucide-react";

import type {
  MeetingStatus,
} from "../types";


interface Props {
  status: MeetingStatus;
  progressPercent?: number;
}


const PROGRESS_STATUSES: MeetingStatus[] = [
  "PROCESSING_AUDIO",
  "TRANSCRIBING",
  "GENERATING_NOTES",
];


export function StatusBadge({
  status,
  progressPercent,
}: Props) {
  const configurations: Record<
    MeetingStatus,
    {
      label: string;
      className: string;
      icon: typeof CircleCheck;
    }
  > = {
    UPLOADED: {
      label: "Uploaded",
      className:
        "border-slate-700 bg-slate-800/70 text-slate-300",
      icon: Clock3,
    },

    PROCESSING_AUDIO: {
      label: "Processing audio",
      className:
        "border-blue-500/30 bg-blue-500/10 text-blue-300",
      icon: LoaderCircle,
    },

    TRANSCRIBING: {
      label: "Transcribing",
      className:
        "border-violet-500/30 bg-violet-500/10 text-violet-300",
      icon: LoaderCircle,
    },

    DIARIZING: {
      label: "Detecting speakers",
      className:
        "border-cyan-500/30 bg-cyan-500/10 text-cyan-300",
      icon: LoaderCircle,
    },

    GENERATING_NOTES: {
      label: "Generating notes",
      className:
        "border-amber-500/30 bg-amber-500/10 text-amber-300",
      icon: LoaderCircle,
    },

    COMPLETED: {
      label: "Completed",
      className:
        "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
      icon: CircleCheck,
    },

    FAILED: {
      label: "Failed",
      className:
        "border-red-500/30 bg-red-500/10 text-red-300",
      icon: CircleAlert,
    },
  };

  const config =
    configurations[status];

  const Icon = config.icon;

  const spinning = [
    "PROCESSING_AUDIO",
    "TRANSCRIBING",
    "DIARIZING",
    "GENERATING_NOTES",
  ].includes(status);

  const shouldShowProgress =
    PROGRESS_STATUSES.includes(
      status,
    ) &&
    typeof progressPercent ===
      "number";

  const boundedProgress =
    Math.max(
      0,
      Math.min(
        100,
        Math.round(
          progressPercent ?? 0,
        ),
      ),
    );

  return (
    <span
      className={[
        "inline-flex items-center gap-1.5",
        "rounded-full border px-2.5 py-1",
        "text-xs font-medium",
        config.className,
      ].join(" ")}
    >
      <Icon
        size={13}
        className={
          spinning
            ? "animate-spin"
            : ""
        }
      />

      {config.label}

      {shouldShowProgress && (
        <span className="font-semibold tabular-nums">
          {boundedProgress}%
        </span>
      )}
    </span>
  );
}
