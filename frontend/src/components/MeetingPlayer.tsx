import {
  Headphones,
  Play,
  Video,
} from "lucide-react";

import type {
  MutableRefObject,
} from "react";


interface Props {
  meetingId: number;

  filename: string;

  mediaUrl: string;

  mediaRef: MutableRefObject<
    HTMLMediaElement | null
  >;
}


function isVideoFile(
  filename: string,
) {
  const extension =
    filename
      .split(".")
      .pop()
      ?.toLowerCase();

  return [
    "mp4",
    "webm",
    "mov",
    "mkv",
  ].includes(
    extension ?? "",
  );
}


export function MeetingPlayer({
  filename,
  mediaUrl,
  mediaRef,
}: Props) {
  const video =
    isVideoFile(
      filename,
    );

  return (
    <section className="min-w-0 overflow-hidden rounded-2xl border border-white/8 bg-[#0d111b]">
      <div className="flex min-w-0 items-center justify-between gap-3 border-b border-white/8 px-4 py-3 sm:px-5 sm:py-4 lg:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/8 bg-white/5 text-indigo-300">
            {video ? (
              <Video size={17} />
            ) : (
              <Headphones
                size={17}
              />
            )}
          </div>

          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-white">
              Meeting recording
            </h2>

            <p className="mt-0.5 truncate text-[11px] text-slate-600 sm:text-xs">
              {filename}
            </p>
          </div>
        </div>

        <div className="hidden shrink-0 items-center gap-1.5 text-xs text-slate-600 lg:flex">
          <Play size={12} />

          Click a transcript timestamp
          to jump
        </div>
      </div>

      {video ? (
        <div className="aspect-video w-full overflow-hidden bg-black">
          <video
            ref={(element) => {
              mediaRef.current =
                element;
            }}
            src={mediaUrl}
            controls
            preload="metadata"
            playsInline
            className="h-full w-full object-contain"
          >
            Your browser does not
            support video playback.
          </video>
        </div>
      ) : (
        <div className="p-4 sm:p-5 lg:p-6">
          <audio
            ref={(element) => {
              mediaRef.current =
                element;
            }}
            src={mediaUrl}
            controls
            preload="metadata"
            className="w-full max-w-full"
          >
            Your browser does not
            support audio playback.
          </audio>
        </div>
      )}
    </section>
  );
}