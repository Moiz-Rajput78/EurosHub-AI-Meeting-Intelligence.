import {
  AudioLines,
  Plus,
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
      timeStyle: "short",
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
              // Keep current data and retry next interval.
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
    <div className="mx-auto flex w-full min-w-0 max-w-[1540px] flex-col gap-5 overflow-x-hidden px-3 py-4 sm:px-5 sm:py-6 lg:px-7 lg:py-7">
      <div className="flex min-w-0 flex-col gap-4 rounded-2xl border border-white/8 bg-[#0d111b] p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5 lg:p-6">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold tracking-tight text-white sm:text-2xl">
            Meetings
          </h1>

          <p className="mt-1 max-w-2xl break-words text-sm leading-6 text-slate-500">
            Browse, search, reopen, and
            manage all processed recordings.
          </p>
        </div>

        <Link
          to="/upload"
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400 sm:w-auto sm:shrink-0"
        >
          <Plus
            size={16}
          />

          New meeting
        </Link>
      </div>

      <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-2xl border border-white/8 bg-[#0d111b]">
        <div className="shrink-0 border-b border-white/8 p-4 sm:p-5">
          <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
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

            <div className="text-xs text-slate-500">
              {
                filteredMeetings.length
              }{" "}
              {filteredMeetings.length ===
              1
                ? "meeting"
                : "meetings"}
            </div>
          </div>
        </div>

        <div className="max-h-[calc(100vh-260px)] min-h-[320px] overflow-y-auto">
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
              <div className="flex min-h-[320px] flex-col items-center justify-center p-10 text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/8 bg-white/5 text-indigo-300">
                  <AudioLines
                    size={24}
                  />
                </div>

                <h2 className="mt-4 text-sm font-medium text-slate-200">
                  No meetings found
                </h2>

                <p className="mt-2 max-w-sm text-xs leading-5 text-slate-500">
                  Try a different search or
                  upload a new recording.
                </p>
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

                            <div className="mt-2 flex min-w-0 flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] text-slate-500 sm:text-xs">
                              <span>
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
      </section>
    </div>
  );
}
