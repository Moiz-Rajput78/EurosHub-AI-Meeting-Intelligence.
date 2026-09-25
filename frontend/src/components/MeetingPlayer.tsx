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
    <section className="meeting-player min-w-0 overflow-hidden rounded-2xl border border-white/8 bg-black shadow-2xl shadow-black/20">
      {video ? (
        <div className="meeting-player-video relative w-full overflow-hidden bg-black">
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
        <div className="meeting-audio-shell flex min-h-[190px] flex-col justify-between gap-6 p-5 sm:p-6">
          <div className="flex min-w-0 items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-white/8 bg-white/5 text-indigo-300">
              <Headphones
                size={21}
              />
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2 text-sm font-semibold text-white">
                <Video
                  size={15}
                  className="text-indigo-300"
                />
                Meeting recording
              </div>

              <p className="mt-1 truncate text-xs text-slate-500">
                {filename}
              </p>
            </div>
          </div>

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

          <div className="flex items-center gap-2 text-xs text-slate-600">
            <Play size={12} />
            Click any transcript timestamp to jump to that moment.
          </div>
        </div>
      )}
    </section>
  );
}
