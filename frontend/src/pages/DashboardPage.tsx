import {
  CheckCircle2,
  Clock3,
  FileAudio,
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

import type {
  MeetingListItem,
} from "../types";


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
            : "Unable to load meeting statistics.",
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
        "Uploaded recordings",
    },
    {
      label:
        "Completed",
      value:
        stats.completed,
      icon:
        CheckCircle2,
      description:
        "Fully analyzed",
    },
    {
      label:
        "Processing",
      value:
        stats.processing,
      icon:
        Clock3,
      description:
        "Currently running",
    },
    {
      label:
        "Detected speakers",
      value:
        stats.speakers,
      icon:
        Users,
      description:
        "Across all meetings",
    },
  ];


  return (
    <div className="dashboard-screen mx-auto flex h-full w-full max-w-[1520px] min-w-0 flex-col gap-4 overflow-hidden px-4 py-4 sm:px-5 lg:px-6">
      <section className="dashboard-heading shrink-0 rounded-2xl border border-white/8 bg-[#0d111b] px-5 py-5 sm:px-6">
        <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold tracking-tight text-white">
              Meeting Intelligence
            </h1>

            <p className="mt-1 text-sm text-slate-500">
              Your meeting analysis workspace
              at a glance.
            </p>
          </div>

          <Link
            to="/upload"
            className="inline-flex w-full shrink-0 items-center justify-center gap-2 rounded-xl bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400 sm:w-auto"
          >
            <Plus size={16} />

            New meeting
          </Link>
        </div>
      </section>

      <section className="grid shrink-0 grid-cols-2 gap-3 xl:grid-cols-4">
        {cards.map(
          ({
            label,
            value,
            icon: Icon,
            description,
          }) => (
            <div
              key={label}
              className="rounded-2xl border border-white/8 bg-[#0d111b] px-4 py-5 sm:px-5"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/8 bg-white/5 text-indigo-300">
                  <Icon size={17} />
                </div>

                <span className="text-2xl font-semibold tracking-tight text-white">
                  {loading
                    ? "—"
                    : value}
                </span>
              </div>

              <div className="mt-4 text-sm font-medium text-slate-300">
                {label}
              </div>

              <div className="mt-1 text-xs text-slate-500">
                {description}
              </div>
            </div>
          ),
        )}
      </section>

      <section className="flex min-h-0 flex-1 items-center justify-center rounded-2xl border border-white/8 bg-[#0d111b] p-6">
        {error ? (
          <div className="text-center">
            <div className="text-sm font-medium text-red-300">
              Unable to load dashboard
            </div>

            <p className="mt-2 max-w-md text-xs leading-5 text-slate-500">
              {error}
            </p>
          </div>
        ) : (
          <div className="max-w-xl text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-indigo-500/20 bg-indigo-500/10 text-indigo-300">
              <FileAudio
                size={24}
              />
            </div>

            <h2 className="mt-5 text-lg font-semibold text-white">
              Select a meeting from the sidebar
            </h2>

            <p className="mt-2 text-sm leading-6 text-slate-500">
              Your recent meetings are
              available directly under the
              Meetings section in the left
              navigation. Open any meeting to
              review its recording, transcript,
              speakers, and AI notes.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
