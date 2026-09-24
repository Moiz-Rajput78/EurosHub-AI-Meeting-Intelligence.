import {
  ArrowRight,
  AudioLines,
  CheckCircle2,
  Clock3,
  FileAudio,
  Mic2,
  Plus,
  Users,
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
  getMeetings,
} from "../lib/api";

import {
  StatusBadge,
} from "../components/StatusBadge";

import type {
  MeetingListItem,
} from "../types";


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
    return "—";
  }

  const totalMinutes =
    Math.floor(seconds / 60);

  const remainingSeconds =
    Math.round(seconds % 60);

  return `${totalMinutes}m ${remainingSeconds}s`;
}


export function DashboardPage() {
  const [
    meetings,
    setMeetings,
  ] = useState<MeetingListItem[]>([]);

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
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);


  const stats =
    useMemo(() => {
      const completed =
        meetings.filter(
          (meeting) =>
            meeting.status ===
            "COMPLETED",
        ).length;

      const processing =
        meetings.filter(
          (meeting) =>
            ![
              "COMPLETED",
              "FAILED",
              "UPLOADED",
            ].includes(
              meeting.status,
            ),
        ).length;

      const totalSpeakers =
        meetings.reduce(
          (
            total,
            meeting,
          ) =>
            total +
            meeting.speaker_count,
          0,
        );

      return {
        total: meetings.length,
        completed,
        processing,
        speakers: totalSpeakers,
      };
    }, [
      meetings,
    ]);


  const cards = [
    {
      label:
        "Total meetings",
      value:
        stats.total,
      icon:
        FileAudio,
      description:
        "Recordings in your workspace",
    },
    {
      label:
        "Completed",
      value:
        stats.completed,
      icon:
        CheckCircle2,
      description:
        "Fully analyzed meetings",
    },
    {
      label:
        "Processing",
      value:
        stats.processing,
      icon:
        Clock3,
      description:
        "Currently being processed",
    },
    {
      label:
        "Detected speakers",
      value:
        stats.speakers,
      icon:
        Users,
      description:
        "Across analyzed meetings",
    },
  ];


  return (
    <div className="mx-auto w-full min-w-0 max-w-[1500px] overflow-x-hidden px-3 py-5 sm:px-5 sm:py-7 lg:px-8 lg:py-10">
      <section className="relative min-w-0 overflow-hidden rounded-2xl border border-white/8 bg-gradient-to-br from-[#121827] via-[#0e1320] to-[#0b0f18] p-5 shadow-2xl shadow-black/20 sm:rounded-3xl sm:p-7 lg:p-9">
        <div className="pointer-events-none absolute right-[-100px] top-[-100px] h-64 w-64 rounded-full bg-indigo-500/15 blur-3xl sm:h-72 sm:w-72" />

        <div className="relative flex min-w-0 flex-col gap-6 lg:flex-row lg:items-center lg:justify-between lg:gap-8">
          <div className="min-w-0 max-w-3xl">
            <div className="mb-4 inline-flex max-w-full items-center gap-2 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-3 py-1 text-[11px] font-medium text-indigo-300 sm:text-xs">
              <Mic2
                size={13}
                className="shrink-0"
              />

              <span className="truncate">
                AI meeting intelligence
              </span>
            </div>

            <h1 className="max-w-full break-words text-2xl font-semibold tracking-tight text-white sm:max-w-2xl sm:text-3xl lg:text-4xl">
              Turn every meeting into
              clear, actionable
              intelligence.
            </h1>

            <p className="mt-4 max-w-full break-words text-sm leading-6 text-slate-400 sm:max-w-2xl sm:text-base sm:leading-7">
              Upload a meeting recording
              and automatically generate
              a timestamped transcript,
              speaker-aware notes,
              decisions, tasks, and open
              issues.
            </p>
          </div>

          <Link
            to="/upload"
            className="inline-flex w-full min-w-0 items-center justify-center gap-2 rounded-xl bg-indigo-500 px-4 py-3 text-sm font-semibold text-white shadow-xl shadow-indigo-950/30 transition hover:bg-indigo-400 sm:w-auto sm:px-5 lg:shrink-0"
          >
            <Plus
              size={17}
              className="shrink-0"
            />

            <span>
              New meeting
            </span>
          </Link>
        </div>
      </section>

      <section className="mt-5 grid min-w-0 grid-cols-1 gap-3 sm:mt-6 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
        {cards.map(
          ({
            label,
            value,
            icon: Icon,
            description,
          }) => (
            <div
              key={label}
              className="min-w-0 rounded-2xl border border-white/8 bg-[#0d111b] p-4 sm:p-5"
            >
              <div className="flex min-w-0 items-center justify-between gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/8 bg-white/5 text-indigo-300">
                  <Icon
                    size={18}
                  />
                </div>

                <span className="shrink-0 text-2xl font-semibold tracking-tight text-white">
                  {value}
                </span>
              </div>

              <h2 className="mt-4 break-words text-sm font-medium text-slate-200 sm:mt-5">
                {label}
              </h2>

              <p className="mt-1 break-words text-xs leading-5 text-slate-500">
                {description}
              </p>
            </div>
          ),
        )}
      </section>

      <section className="mt-5 min-w-0 overflow-hidden rounded-2xl border border-white/8 bg-[#0d111b] sm:mt-6">
        <div className="flex min-w-0 items-start justify-between gap-3 border-b border-white/8 px-4 py-4 sm:items-center sm:px-5 lg:px-6">
          <div className="min-w-0">
            <h2 className="font-semibold text-white">
              Recent meetings
            </h2>

            <p className="mt-1 max-w-full break-words text-xs leading-5 text-slate-500">
              Your latest uploaded and
              analyzed recordings.
            </p>
          </div>

          <Link
            to="/meetings"
            className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-indigo-300 hover:text-indigo-200 sm:gap-1.5 sm:text-sm"
          >
            <span>
              View all
            </span>

            <ArrowRight
              size={15}
            />
          </Link>
        </div>

        {loading && (
          <div className="p-8 text-center text-sm text-slate-500">
            Loading meetings...
          </div>
        )}

        {!loading &&
          error && (
            <div className="p-8 text-center text-sm text-red-300">
              {error}
            </div>
          )}

        {!loading &&
          !error &&
          meetings.length ===
            0 && (
            <div className="flex flex-col items-center justify-center px-4 py-12 text-center sm:px-6 sm:py-16">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/8 bg-white/5 text-indigo-300">
                <AudioLines
                  size={24}
                />
              </div>

              <h3 className="mt-5 font-medium text-slate-200">
                No meetings yet
              </h3>

              <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
                Upload your first recording
                to generate transcripts and
                structured AI notes.
              </p>

              <Link
                to="/upload"
                className="mt-6 inline-flex w-full max-w-[260px] items-center justify-center rounded-xl bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-400 sm:w-auto"
              >
                Upload meeting
              </Link>
            </div>
          )}

        {!loading &&
          !error &&
          meetings.length >
            0 && (
            <div className="divide-y divide-white/6">
              {meetings
                .slice(
                  0,
                  6,
                )
                .map(
                  (meeting) => (
                    <Link
                      key={
                        meeting.id
                      }
                      to={`/meetings/${meeting.id}`}
                      className="flex min-w-0 flex-col gap-4 px-4 py-4 transition hover:bg-white/[0.025] sm:flex-row sm:items-center sm:justify-between sm:px-5 sm:py-5 lg:px-6"
                    >
                      <div className="flex min-w-0 items-start gap-3 sm:items-center sm:gap-4">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/8 bg-white/5 text-indigo-300 sm:h-11 sm:w-11">
                          <AudioLines
                            size={19}
                          />
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="break-words text-sm font-medium text-slate-100 sm:truncate">
                            {
                              meeting.title
                            }
                          </div>

                          <div className="mt-1 flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500 sm:text-xs">
                            <span className="break-words">
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
                                meeting.speaker_count
                              }{" "}
                              speakers
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="pl-[52px] sm:pl-0">
                        <StatusBadge
                          status={
                            meeting.status
                          }
                        />
                      </div>
                    </Link>
                  ),
                )}
            </div>
          )}
      </section>
    </div>
  );
}