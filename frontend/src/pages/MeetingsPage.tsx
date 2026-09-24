import {
  AudioLines,
  Search,
  Trash2,
} from "lucide-react";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Link,
} from "react-router-dom";

import {
  deleteMeeting,
  getMeetings,
} from "../lib/api";

import {
  StatusBadge,
} from "../components/StatusBadge";
import {
  useAppDialog,
} from "../components/appDialog";

import type {
  MeetingListItem,
} from "../types";




const ACTIVE_STATUSES = new Set([
  "PROCESSING_AUDIO",
  "TRANSCRIBING",
  "DIARIZING",
  "GENERATING_NOTES",
]);

function formatDate(
  value: string,
) {
  return new Intl.DateTimeFormat(
    undefined,
    {
      dateStyle: "medium",
    },
  ).format(
    new Date(value),
  );
}


function formatDuration(
  seconds: number | null,
) {
  if (!seconds) {
    return "Not processed";
  }

  const minutes =
    Math.floor(seconds / 60);

  const remaining =
    Math.round(seconds % 60);

  return `${minutes}m ${remaining}s`;
}


export function MeetingsPage() {
  const {
    confirm,
    alert,
  } = useAppDialog();

  const [
    meetings,
    setMeetings,
  ] = useState<MeetingListItem[]>([]);

  const [
    search,
    setSearch,
  ] = useState("");

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );

  const [
    deletingId,
    setDeletingId,
  ] = useState<number | null>(
    null,
  );


  useEffect(() => {
    let cancelled = false;

    getMeetings()
      .then((result) => {
        if (cancelled) {
          return;
        }

        setMeetings(
          result.meetings,
        );

        setError(null);
      })
      .catch((caught: unknown) => {
        if (cancelled) {
          return;
        }

        setError(
          caught instanceof Error
            ? caught.message
            : "Unable to load meetings.",
        );
      })
      .finally(() => {
        if (cancelled) {
          return;
        }

        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);


  const hasActiveMeetings =
    meetings.some(
      (meeting) =>
        ACTIVE_STATUSES.has(
          meeting.status,
        ),
    );


  useEffect(() => {
    if (!hasActiveMeetings) {
      return;
    }

    let cancelled = false;

    const intervalId =
      window.setInterval(
        () => {
          void getMeetings()
            .then((result) => {
              if (cancelled) {
                return;
              }

              setMeetings(
                result.meetings,
              );
            })
            .catch(() => {
              // Keep the current list during a transient
              // polling failure. The next interval retries.
            });
        },
        1000,
      );

    return () => {
      cancelled = true;

      window.clearInterval(
        intervalId,
      );
    };
  }, [
    hasActiveMeetings,
  ]);


  const filteredMeetings =
    useMemo(() => {
      const query =
        search
          .trim()
          .toLowerCase();

      if (!query) {
        return meetings;
      }

      return meetings.filter(
        (meeting) =>
          meeting.title
            .toLowerCase()
            .includes(query) ||
          meeting.original_filename
            .toLowerCase()
            .includes(query),
      );
    }, [
      meetings,
      search,
    ]);


  async function handleDelete(
    meeting: MeetingListItem,
  ) {
    const confirmed =
      await confirm({
        title: "Delete meeting?",
        description:
          `“${meeting.title}” and its transcript, speakers, notes, and stored files will be permanently removed. This action cannot be undone.`,
        confirmLabel:
          "Delete meeting",
        cancelLabel: "Keep meeting",
        tone: "danger",
      });

    if (!confirmed) {
      return;
    }

    try {
      setDeletingId(
        meeting.id,
      );

      await deleteMeeting(
        meeting.id,
      );

      setMeetings(
        (current) =>
          current.filter(
            (item) =>
              item.id !==
              meeting.id,
          ),
      );
    } catch (caught) {
      await alert({
        title:
          "Unable to delete meeting",
        description:
          caught instanceof Error
            ? caught.message
            : "The meeting could not be deleted. Please try again.",
        actionLabel: "Close",
        tone: "danger",
      });
    } finally {
      setDeletingId(null);
    }
  }


  return (
    <div className="mx-auto w-full min-w-0 max-w-[1500px] overflow-x-hidden px-3 py-5 sm:px-5 sm:py-7 lg:px-8 lg:py-8">
      <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-end sm:justify-between sm:gap-5">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold tracking-tight text-white sm:text-2xl">
            Meetings
          </h1>

          <p className="mt-2 max-w-full break-words text-sm leading-6 text-slate-500">
            Browse and manage all
            recorded meetings.
          </p>
        </div>

        <Link
          to="/upload"
          className="inline-flex w-full items-center justify-center rounded-xl bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400 sm:w-auto sm:shrink-0"
        >
          Upload meeting
        </Link>
      </div>

      <div className="mt-5 min-w-0 overflow-hidden rounded-2xl border border-white/8 bg-[#0d111b] sm:mt-7">
        <div className="border-b border-white/8 p-4 sm:p-5">
          <div className="relative w-full min-w-0 sm:max-w-md">
            <Search
              size={17}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-600"
            />

            <input
              value={search}
              onChange={(event) =>
                setSearch(
                  event.target.value,
                )
              }
              placeholder="Search meetings..."
              className="w-full min-w-0 rounded-xl border border-white/8 bg-[#080b12] py-2.5 pl-10 pr-4 text-sm text-slate-200 outline-none transition placeholder:text-slate-600 focus:border-indigo-500/50"
            />
          </div>
        </div>

        {loading && (
          <div className="p-8 text-center text-sm text-slate-500 sm:p-10">
            Loading meetings...
          </div>
        )}

        {!loading &&
          error && (
            <div className="p-8 text-center text-sm text-red-300 sm:p-10">
              {error}
            </div>
          )}

        {!loading &&
          !error &&
          filteredMeetings.length ===
            0 && (
            <div className="p-10 text-center text-sm text-slate-500 sm:p-12">
              No meetings found.
            </div>
          )}

        {!loading &&
          !error &&
          filteredMeetings.length >
            0 && (
            <div className="divide-y divide-white/6">
              {filteredMeetings.map(
                (meeting) => (
                  <div
                    key={meeting.id}
                    className="min-w-0 p-4 transition hover:bg-white/[0.02] sm:p-5 lg:px-6"
                  >
                    <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center sm:justify-between sm:gap-5">
                      <Link
                        to={`/meetings/${meeting.id}`}
                        className="flex min-w-0 flex-1 items-start gap-3 sm:items-center sm:gap-4"
                      >
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/8 bg-white/5 text-indigo-300 sm:h-11 sm:w-11">
                          <AudioLines
                            size={19}
                          />
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="break-words text-sm font-medium text-white sm:truncate">
                            {meeting.title}
                          </div>

                          <div className="mt-1 break-words text-[11px] leading-5 text-slate-600 sm:truncate sm:text-xs">
                            {
                              meeting.original_filename
                            }
                          </div>

                          <div className="mt-2 grid min-w-0 grid-cols-2 gap-x-3 gap-y-1.5 text-[11px] text-slate-500 sm:flex sm:flex-wrap sm:gap-x-4 sm:gap-y-1 sm:text-xs">
                            <span className="min-w-0 break-words">
                              {formatDate(
                                meeting.created_at,
                              )}
                            </span>

                            <span>
                              {formatDuration(
                                meeting.duration,
                              )}
                            </span>

                            <span>
                              {
                                meeting
                                  .transcript_segment_count
                              }{" "}
                              segments
                            </span>

                            <span>
                              {
                                meeting.speaker_count
                              }{" "}
                              speakers
                            </span>
                          </div>
                        </div>
                      </Link>

                      <div className="flex min-w-0 items-center justify-between gap-3 pl-[52px] sm:shrink-0 sm:justify-end sm:pl-0">
                        <StatusBadge
                          status={
                            meeting.status
                          }
                          progressPercent={
                            meeting.progress_percent
                          }
                        />

                        <button
                          type="button"
                          disabled={
                            deletingId ===
                            meeting.id
                          }
                          onClick={() =>
                            void handleDelete(
                              meeting,
                            )
                          }
                          className="shrink-0 rounded-lg p-2 text-slate-600 transition hover:bg-red-500/10 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-40"
                          title="Delete meeting"
                          aria-label={`Delete ${meeting.title}`}
                        >
                          <Trash2
                            size={17}
                          />
                        </button>
                      </div>
                    </div>
                  </div>
                ),
              )}
            </div>
          )}
      </div>
    </div>
  );
}
