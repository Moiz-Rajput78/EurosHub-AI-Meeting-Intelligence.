import {
  ChevronDown,
  Download,
  FileText,
} from "lucide-react";

import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  getMeetingExportUrl,
} from "../lib/api";


interface Props {
  meetingId: number;
}


export function ExportMenu({
  meetingId,
}: Props) {
  const [
    open,
    setOpen,
  ] = useState(false);

  const containerRef =
    useRef<HTMLDivElement | null>(
      null,
    );


  useEffect(() => {
    function handleClick(
      event: MouseEvent,
    ) {
      if (
        containerRef.current &&
        !containerRef.current.contains(
          event.target as Node,
        )
      ) {
        setOpen(false);
      }
    }

    document.addEventListener(
      "mousedown",
      handleClick,
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleClick,
      );
    };
  }, []);


  function download(
    format: "txt" | "md" | "pdf",
  ) {
    const url =
      getMeetingExportUrl(
        meetingId,
        format,
      );

    window.open(
      url,
      "_blank",
      "noopener,noreferrer",
    );

    setOpen(false);
  }


  return (
    <div
      ref={containerRef}
      className="relative w-full sm:w-auto"
    >
      <button
        type="button"
        onClick={() =>
          setOpen(
            (current) =>
              !current,
          )
        }
        className="inline-flex h-9 w-full items-center justify-center gap-1.5 rounded-lg border border-white/8 bg-white/5 px-3 text-[13px] font-medium text-slate-300 transition hover:bg-white/8 hover:text-white sm:w-auto"
      >
        <Download
          size={14}
        />

        Export

        <ChevronDown
          size={12}
          className={[
            "transition-transform",
            open
              ? "rotate-180"
              : "",
          ].join(" ")}
        />
      </button>

      {open && (
        <div className="absolute left-0 right-0 top-[calc(100%+8px)] z-50 overflow-hidden rounded-xl border border-white/10 bg-[#111722] p-1.5 shadow-2xl shadow-black/40 sm:left-auto sm:right-0 sm:w-48">
          <button
            type="button"
            onClick={() =>
              download(
                "pdf",
              )
            }
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-slate-300 transition hover:bg-white/6 hover:text-white"
          >
            <FileText
              size={15}
              className="text-red-300"
            />

            Export PDF
          </button>

          <button
            type="button"
            onClick={() =>
              download(
                "md",
              )
            }
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-slate-300 transition hover:bg-white/6 hover:text-white"
          >
            <FileText
              size={15}
              className="text-indigo-300"
            />

            Export Markdown
          </button>

          <button
            type="button"
            onClick={() =>
              download(
                "txt",
              )
            }
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-slate-300 transition hover:bg-white/6 hover:text-white"
          >
            <FileText
              size={15}
              className="text-slate-400"
            />

            Export TXT
          </button>
        </div>
      )}
    </div>
  );
}
