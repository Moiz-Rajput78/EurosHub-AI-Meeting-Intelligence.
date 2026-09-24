import {
  AlertCircle,
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  CircleHelp,
  ClipboardCheck,
  Clock3,
  Edit3,
  FileText,
  LoaderCircle,
  MessageSquareText,
  RefreshCw,
  Save,
  Search,
  Sparkles,
  Tag,
  UserRound,
  Users,
  X,
} from "lucide-react";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Link,
  useParams,
} from "react-router-dom";

import {
  analyzeMeeting,
  getMeeting,
  getMeetingMediaUrl,
  getMeetingNotes,
  getSpeakers,
  getTranscript,
  updateSpeaker,
  updateTranscriptSegment,
} from "../lib/api";

import {
  ExportMenu,
} from "../components/ExportMenu";

import {
  MeetingPlayer,
} from "../components/MeetingPlayer";

import {
  StatusBadge,
} from "../components/StatusBadge";

import type {
  MeetingDetail,
  MeetingNotesResponse,
  MeetingSpeakersResponse,
  MeetingTranscriptResponse,
  Speaker,
  TranscriptSegment,
} from "../types";


type Tab =
  | "overview"
  | "transcript"
  | "speakers";


function formatTimestamp(
  seconds: number,
) {
  const wholeSeconds =
    Math.floor(seconds);

  const hours =
    Math.floor(
      wholeSeconds / 3600,
    );

  const minutes =
    Math.floor(
      (
        wholeSeconds % 3600
      ) / 60,
    );

  const remaining =
    wholeSeconds % 60;

  if (hours > 0) {
    return (
      `${hours}:` +
      `${minutes
        .toString()
        .padStart(2, "0")}:` +
      `${remaining
        .toString()
        .padStart(2, "0")}`
    );
  }

  return (
    `${minutes}:` +
    remaining
      .toString()
      .padStart(2, "0")
  );
}


function NotesSection({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: typeof Sparkles;
  children: React.ReactNode;
}) {
  return (
    <section className="min-w-0 rounded-2xl border border-white/8 bg-[#0d111b] p-4 sm:p-5 lg:p-6">
      <div className="flex items-center gap-2">
        <Icon
          size={17}
          className="shrink-0 text-indigo-300"
        />

        <h2 className="min-w-0 text-sm font-semibold text-white sm:text-base">
          {title}
        </h2>
      </div>

      <div className="mt-4 min-w-0 sm:mt-5">
        {children}
      </div>
    </section>
  );
}


export function MeetingDetailPage() {
  const {
    meetingId,
  } = useParams();

  const id = Number(
    meetingId,
  );

  const validMeetingId =
    Number.isFinite(id) &&
    id > 0;

  const mediaRef =
    useRef<HTMLMediaElement | null>(
      null,
    );

  const [
    meeting,
    setMeeting,
  ] = useState<MeetingDetail | null>(
    null,
  );

  const [
    transcript,
    setTranscript,
  ] = useState<MeetingTranscriptResponse | null>(
    null,
  );

  const [
    notes,
    setNotes,
  ] = useState<MeetingNotesResponse | null>(
    null,
  );

  const [
    speakers,
    setSpeakers,
  ] = useState<MeetingSpeakersResponse | null>(
    null,
  );

  const [
    activeTab,
    setActiveTab,
  ] = useState<Tab>(
    "overview",
  );

  const [
    loading,
    setLoading,
  ] = useState(
    validMeetingId,
  );

  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );

  const [
    regenerating,
    setRegenerating,
  ] = useState(false);

  const [
    editingSegmentId,
    setEditingSegmentId,
  ] = useState<number | null>(
    null,
  );

  const [
    editingSegmentText,
    setEditingSegmentText,
  ] = useState("");

  const [
    activeSegmentId,
    setActiveSegmentId,
  ] = useState<number | null>(
    null,
  );

  const [
    transcriptSearch,
    setTranscriptSearch,
  ] = useState("");


  useEffect(() => {
    if (!validMeetingId) {
      return;
    }

    let cancelled = false;

    async function loadMeetingData() {
      try {
        const meetingData =
          await getMeeting(id);

        if (cancelled) {
          return;
        }

        setMeeting(
          meetingData,
        );

        const requests: Promise<void>[] =
          [];

        if (
          meetingData.has_transcript
        ) {
          requests.push(
            getTranscript(id)
              .then((result) => {
                if (!cancelled) {
                  setTranscript(
                    result,
                  );
                }
              })
              .catch(() => {
                // Transcript can remain unavailable.
              }),
          );
        }

        if (
          meetingData.has_speakers
        ) {
          requests.push(
            getSpeakers(id)
              .then((result) => {
                if (!cancelled) {
                  setSpeakers(
                    result,
                  );
                }
              })
              .catch(() => {
                // Speaker data is optional.
              }),
          );
        }

        if (
          meetingData.has_notes
        ) {
          requests.push(
            getMeetingNotes(id)
              .then((result) => {
                if (!cancelled) {
                  setNotes(
                    result,
                  );
                }
              })
              .catch(() => {
                // Notes can be regenerated later.
              }),
          );
        }

        await Promise.all(
          requests,
        );

        if (!cancelled) {
          setError(null);
        }
      } catch (caught) {
        if (cancelled) {
          return;
        }

        setError(
          caught instanceof Error
            ? caught.message
            : "Unable to load meeting.",
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadMeetingData();

    return () => {
      cancelled = true;
    };
  }, [
    id,
    validMeetingId,
  ]);


  const filteredTranscriptSegments =
    useMemo(() => {
      if (!transcript) {
        return [];
      }

      const query =
        transcriptSearch
          .trim()
          .toLowerCase();

      if (!query) {
        return transcript.segments;
      }

      return transcript.segments.filter(
        (segment) => {
          const text = (
            segment.edited_text ??
            segment.original_text
          ).toLowerCase();

          const speakerName = (
            segment.speaker_display_name ??
            segment.speaker_label ??
            "Unknown Speaker"
          ).toLowerCase();

          return (
            text.includes(query) ||
            speakerName.includes(query)
          );
        },
      );
    }, [
      transcript,
      transcriptSearch,
    ]);


  async function handleRegenerate() {
    try {
      setRegenerating(true);

      await analyzeMeeting(id);

      const [
        nextNotes,
        nextMeeting,
      ] = await Promise.all([
        getMeetingNotes(id),
        getMeeting(id),
      ]);

      setNotes(
        nextNotes,
      );

      setMeeting(
        nextMeeting,
      );
    } catch (caught) {
      window.alert(
        caught instanceof Error
          ? caught.message
          : "Unable to regenerate meeting notes.",
      );
    } finally {
      setRegenerating(false);
    }
  }


  async function handleRenameSpeaker(
    speaker: Speaker,
  ) {
    const current =
      speaker.display_name ??
      speaker.speaker_label;

    const nextName =
      window.prompt(
        `Rename ${speaker.speaker_label}`,
        current,
      );

    if (
      !nextName ||
      !nextName.trim()
    ) {
      return;
    }

    try {
      await updateSpeaker(
        speaker.id,
        nextName.trim(),
      );

      const nextSpeakers =
        await getSpeakers(id);

      setSpeakers(
        nextSpeakers,
      );

      if (
        meeting?.has_transcript
      ) {
        const nextTranscript =
          await getTranscript(id);

        setTranscript(
          nextTranscript,
        );
      }
    } catch (caught) {
      window.alert(
        caught instanceof Error
          ? caught.message
          : "Unable to rename speaker.",
      );
    }
  }


  function startEditingSegment(
    segment: TranscriptSegment,
  ) {
    setEditingSegmentId(
      segment.id,
    );

    setEditingSegmentText(
      segment.edited_text ??
        segment.original_text,
    );
  }


  async function saveSegment(
    segmentId: number,
  ) {
    if (
      !editingSegmentText.trim()
    ) {
      return;
    }

    try {
      await updateTranscriptSegment(
        segmentId,
        editingSegmentText.trim(),
      );

      const [
        nextTranscript,
        nextMeeting,
      ] = await Promise.all([
        getTranscript(id),
        getMeeting(id),
      ]);

      setEditingSegmentId(
        null,
      );

      setTranscript(
        nextTranscript,
      );

      setMeeting(
        nextMeeting,
      );

      setNotes(null);
    } catch (caught) {
      window.alert(
        caught instanceof Error
          ? caught.message
          : "Unable to update transcript.",
      );
    }
  }


  function seekToSegment(
    segment: TranscriptSegment,
  ) {
    const player =
      mediaRef.current;

    if (!player) {
      return;
    }

    setActiveSegmentId(
      segment.id,
    );

    player.currentTime =
      segment.start_time;

    void player
      .play()
      .catch(() => {
        // Seeking still succeeds if autoplay is blocked.
      });
  }


  if (!validMeetingId) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6 sm:py-20">
        <AlertCircle
          size={30}
          className="mx-auto text-red-300"
        />

        <h1 className="mt-4 text-lg font-semibold text-white">
          Invalid meeting
        </h1>

        <p className="mt-2 text-sm text-slate-500">
          The meeting ID in the URL is
          invalid.
        </p>

        <Link
          to="/meetings"
          className="mt-6 inline-flex text-sm font-medium text-indigo-300"
        >
          Return to meetings
        </Link>
      </div>
    );
  }


  if (loading) {
    return (
      <div className="flex min-h-[70vh] items-center justify-center px-4 text-sm text-slate-500">
        <LoaderCircle
          className="mr-2 animate-spin"
          size={18}
        />

        Loading meeting...
      </div>
    );
  }


  if (
    error ||
    !meeting
  ) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6 sm:py-20">
        <AlertCircle
          size={30}
          className="mx-auto text-red-300"
        />

        <h1 className="mt-4 text-lg font-semibold text-white">
          Unable to load meeting
        </h1>

        <p className="mt-2 text-sm text-slate-500">
          {error ??
            "Meeting not found."}
        </p>

        <Link
          to="/meetings"
          className="mt-6 inline-flex text-sm font-medium text-indigo-300"
        >
          Return to meetings
        </Link>
      </div>
    );
  }


  const tabs: {
    key: Tab;
    label: string;
  }[] = [
    {
      key: "overview",
      label: "Overview",
    },
    {
      key: "transcript",
      label: `Transcript (${meeting.transcript_segment_count})`,
    },
    {
      key: "speakers",
      label: `Speakers (${meeting.speaker_count})`,
    },
  ];


  const mediaUrl =
    getMeetingMediaUrl(
      meeting.id,
    );


  return (
    <div className="mx-auto w-full min-w-0 max-w-[1500px] overflow-x-hidden px-3 py-5 sm:px-5 sm:py-7 lg:px-8 lg:py-8">
      <Link
        to="/meetings"
        className="inline-flex items-center gap-2 text-xs text-slate-500 transition hover:text-slate-300 sm:text-sm"
      >
        <ArrowLeft size={15} />

        Meetings
      </Link>

      <div className="mt-4 flex min-w-0 flex-col gap-4 sm:mt-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex min-w-0 flex-col items-start gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-3">
            <h1 className="max-w-full break-words text-xl font-semibold tracking-tight text-white sm:text-2xl">
              {meeting.title}
            </h1>

            <StatusBadge
              status={
                meeting.status
              }
            />
          </div>

          <div className="mt-3 flex min-w-0 flex-col gap-1.5 text-[11px] text-slate-500 sm:flex-row sm:flex-wrap sm:gap-x-5 sm:gap-y-2 sm:text-xs">
            <span className="max-w-full truncate">
              {meeting.original_filename}
            </span>

            {meeting.language && (
              <span>
                Language:{" "}
                {meeting.language.toUpperCase()}
              </span>
            )}

            {meeting.duration && (
              <span>
                Duration:{" "}
                {formatTimestamp(
                  meeting.duration,
                )}
              </span>
            )}
          </div>
        </div>

        <div className="grid w-full min-w-0 grid-cols-1 gap-2 sm:flex sm:w-auto sm:flex-wrap sm:items-center sm:gap-3">
          <div className="min-w-0 w-full sm:w-auto">
            <ExportMenu
              meetingId={
                meeting.id
              }
            />
          </div>

          {meeting.has_transcript &&
            !meeting.has_notes && (
              <button
                type="button"
                disabled={
                  regenerating
                }
                onClick={() =>
                  void handleRegenerate()
                }
                className="inline-flex min-w-0 w-full items-center justify-center gap-2 rounded-xl bg-indigo-500 px-3 py-2.5 text-center text-sm font-semibold leading-5 text-white transition hover:bg-indigo-400 disabled:opacity-50 sm:w-auto sm:px-4"
              >
                {regenerating ? (
                  <LoaderCircle
                    size={16}
                    className="shrink-0 animate-spin"
                  />
                ) : (
                  <Sparkles
                    size={16}
                    className="shrink-0"
                  />
                )}

                <span className="min-w-0 whitespace-normal break-words">
                  Generate notes
                </span>
              </button>
            )}

          {meeting.has_notes && (
            <button
              type="button"
              disabled={
                regenerating
              }
              onClick={() =>
                void handleRegenerate()
              }
              className="inline-flex min-w-0 w-full items-center justify-center gap-2 rounded-xl border border-white/8 bg-white/5 px-3 py-2.5 text-center text-sm font-medium leading-5 text-slate-300 transition hover:bg-white/8 hover:text-white disabled:opacity-50 sm:w-auto sm:px-4"
            >
              {regenerating ? (
                <LoaderCircle
                  size={16}
                  className="shrink-0 animate-spin"
                />
              ) : (
                <RefreshCw
                  size={16}
                  className="shrink-0"
                />
              )}

              <span className="min-w-0 whitespace-normal break-words">
                Regenerate notes
              </span>
            </button>
          )}
        </div>
      </div>

      <div className="mt-5 min-w-0 sm:mt-7">
        <MeetingPlayer
          meetingId={
            meeting.id
          }
          filename={
            meeting.original_filename
          }
          mediaUrl={
            mediaUrl
          }
          mediaRef={
            mediaRef
          }
        />
      </div>

      <div className="mt-5 grid grid-cols-3 border-b border-white/8 sm:mt-7">
        {tabs.map(
          (tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() =>
                setActiveTab(
                  tab.key,
                )
              }
              className={[
                "min-w-0 border-b-2 px-1 py-3 text-center text-[11px] font-medium transition sm:px-4 sm:text-sm",
                activeTab ===
                tab.key
                  ? "border-indigo-400 text-white"
                  : "border-transparent text-slate-500 hover:text-slate-300",
              ].join(" ")}
            >
              <span className="block truncate">
                {tab.label}
              </span>
            </button>
          ),
        )}
      </div>

      {activeTab ===
        "overview" && (
        <div className="mt-5 grid min-w-0 gap-4 sm:mt-6 sm:gap-6 xl:grid-cols-2">
          {!notes ? (
            <section className="col-span-full rounded-2xl border border-dashed border-white/10 bg-[#0d111b] px-4 py-10 text-center sm:px-6 sm:py-14">
              <Sparkles
                size={28}
                className="mx-auto text-indigo-300"
              />

              <h2 className="mt-4 font-semibold text-white">
                No current AI notes
              </h2>

              <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">
                Generate structured
                meeting intelligence from
                the current transcript.
              </p>
            </section>
          ) : (
            <>
              <NotesSection
                title="Meeting summary"
                icon={
                  MessageSquareText
                }
              >
                <p className="break-words text-sm leading-7 text-slate-300">
                  {notes.summary}
                </p>
              </NotesSection>

              <NotesSection
                title="Key discussion points"
                icon={
                  FileText
                }
              >
                {notes
                  .key_discussion_points
                  .length === 0 ? (
                  <p className="text-sm text-slate-500">
                    No key discussion
                    points extracted.
                  </p>
                ) : (
                  <ul className="space-y-3">
                    {notes.key_discussion_points.map(
                      (
                        point,
                        index,
                      ) => (
                        <li
                          key={`${index}-${point}`}
                          className="flex min-w-0 gap-3 text-sm leading-6 text-slate-300"
                        >
                          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />

                          <span className="min-w-0 break-words">
                            {point}
                          </span>
                        </li>
                      ),
                    )}
                  </ul>
                )}
              </NotesSection>

              <NotesSection
                title="Action items"
                icon={
                  ClipboardCheck
                }
              >
                {notes.action_items
                  .length === 0 ? (
                  <p className="text-sm text-slate-500">
                    No explicit action
                    items were detected.
                  </p>
                ) : (
                  <div className="space-y-4">
                    {notes.action_items.map(
                      (item) => (
                        <div
                          key={
                            item.id
                          }
                          className="min-w-0 rounded-xl border border-white/8 bg-[#080b12] p-4"
                        >
                          <p className="break-words text-sm font-medium leading-6 text-slate-200">
                            {item.task}
                          </p>

                          <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                            <span className="max-w-full break-words rounded-lg bg-white/5 px-2.5 py-1">
                              Owner:{" "}
                              {item.responsible_person ??
                                "Not specified"}
                            </span>

                            <span className="max-w-full break-words rounded-lg bg-white/5 px-2.5 py-1">
                              Deadline:{" "}
                              {item.deadline ??
                                "Not mentioned"}
                            </span>

                            <span className="rounded-lg bg-white/5 px-2.5 py-1">
                              {
                                item.priority
                              }
                            </span>
                          </div>

                          <p className="mt-3 break-words border-l-2 border-indigo-500/30 pl-3 text-xs italic leading-5 text-slate-600">
                            “
                            {
                              item.evidence
                            }
                            ”
                          </p>
                        </div>
                      ),
                    )}
                  </div>
                )}
              </NotesSection>

              <NotesSection
                title="Decisions"
                icon={
                  CheckCircle2
                }
              >
                {notes.decisions
                  .length === 0 ? (
                  <p className="text-sm text-slate-500">
                    No confirmed decisions
                    were detected.
                  </p>
                ) : (
                  <div className="space-y-4">
                    {notes.decisions.map(
                      (decision) => (
                        <div
                          key={
                            decision.id
                          }
                          className="min-w-0 rounded-xl border border-white/8 bg-[#080b12] p-4"
                        >
                          <p className="break-words text-sm leading-6 text-slate-300">
                            {
                              decision.decision
                            }
                          </p>

                          <p className="mt-3 break-words border-l-2 border-emerald-500/30 pl-3 text-xs italic leading-5 text-slate-600">
                            “
                            {
                              decision.evidence
                            }
                            ”
                          </p>
                        </div>
                      ),
                    )}
                  </div>
                )}
              </NotesSection>

              <NotesSection
                title="Open issues"
                icon={
                  AlertCircle
                }
              >
                {notes.open_issues
                  .length === 0 ? (
                  <p className="text-sm text-slate-500">
                    No open issues detected.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {notes.open_issues.map(
                      (issue) => (
                        <div
                          key={
                            issue.id
                          }
                          className="min-w-0 rounded-xl border border-white/8 bg-[#080b12] p-4"
                        >
                          <p className="break-words text-sm leading-6 text-slate-300">
                            {issue.issue}
                          </p>
                        </div>
                      ),
                    )}
                  </div>
                )}
              </NotesSection>

              <NotesSection
                title="Important dates"
                icon={
                  CalendarDays
                }
              >
                {notes.important_dates
                  .length === 0 ? (
                  <p className="text-sm text-slate-500">
                    No important dates
                    explicitly mentioned.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {notes.important_dates.map(
                      (
                        item,
                        index,
                      ) => (
                        <div
                          key={`${index}-${item.date_or_time}`}
                          className="min-w-0 rounded-xl border border-white/8 bg-[#080b12] p-4"
                        >
                          <p className="break-words text-xs font-medium text-indigo-300">
                            {
                              item.date_or_time
                            }
                          </p>

                          <p className="mt-2 break-words text-sm leading-6 text-slate-300">
                            {
                              item.description
                            }
                          </p>
                        </div>
                      ),
                    )}
                  </div>
                )}
              </NotesSection>

              <NotesSection
                title="Questions"
                icon={
                  CircleHelp
                }
              >
                {notes
                  .unanswered_questions
                  .length === 0 ? (
                  <p className="text-sm text-slate-500">
                    No unanswered questions
                    detected.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {notes.unanswered_questions.map(
                      (
                        item,
                        index,
                      ) => (
                        <p
                          key={`${index}-${item.question}`}
                          className="break-words text-sm leading-6 text-slate-300"
                        >
                          {item.question}
                        </p>
                      ),
                    )}
                  </div>
                )}
              </NotesSection>

              <NotesSection
                title="Topics"
                icon={
                  Tag
                }
              >
                <div className="flex flex-wrap gap-2">
                  {notes.topics.length ===
                  0 ? (
                    <span className="text-sm text-slate-500">
                      No topics extracted.
                    </span>
                  ) : (
                    notes.topics.map(
                      (topic) => (
                        <span
                          key={
                            topic
                          }
                          className="max-w-full break-words rounded-lg border border-indigo-500/15 bg-indigo-500/8 px-3 py-1.5 text-xs text-indigo-300"
                        >
                          {topic}
                        </span>
                      ),
                    )
                  )}
                </div>
              </NotesSection>
            </>
          )}
        </div>
      )}

      {activeTab ===
        "transcript" && (
        <section className="mt-5 min-w-0 overflow-hidden rounded-2xl border border-white/8 bg-[#0d111b] sm:mt-6">
          <div className="border-b border-white/8 px-4 py-4 sm:px-5 lg:px-6">
            <div className="flex min-w-0 flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="min-w-0">
                <h2 className="font-semibold text-white">
                  Transcript
                </h2>

                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Click a timestamp to jump
                  to that moment in the
                  recording. Search by
                  speaker or transcript text.
                </p>
              </div>

              <div className="w-full min-w-0 lg:w-[360px]">
                <div className="relative min-w-0">
                  <Search
                    size={16}
                    className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-600"
                  />

                  <input
                    value={
                      transcriptSearch
                    }
                    onChange={(event) =>
                      setTranscriptSearch(
                        event
                          .target
                          .value,
                      )
                    }
                    placeholder="Search transcript or speaker..."
                    className="w-full min-w-0 rounded-xl border border-white/8 bg-[#080b12] py-2.5 pl-10 pr-10 text-sm text-slate-200 outline-none transition placeholder:text-slate-600 focus:border-indigo-500/50"
                  />

                  {transcriptSearch && (
                    <button
                      type="button"
                      onClick={() =>
                        setTranscriptSearch(
                          "",
                        )
                      }
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-600 transition hover:bg-white/5 hover:text-slate-300"
                      title="Clear search"
                    >
                      <X
                        size={15}
                      />
                    </button>
                  )}
                </div>

                {transcriptSearch.trim() && (
                  <p className="mt-2 text-left text-[11px] text-slate-600 sm:text-right">
                    {
                      filteredTranscriptSegments.length
                    }{" "}
                    matching{" "}
                    {filteredTranscriptSegments.length ===
                    1
                      ? "segment"
                      : "segments"}
                  </p>
                )}
              </div>
            </div>
          </div>

          {!transcript ? (
            <div className="p-10 text-center text-sm text-slate-500">
              No transcript available.
            </div>
          ) : filteredTranscriptSegments.length ===
            0 ? (
            <div className="flex flex-col items-center justify-center px-4 py-12 text-center sm:px-6 sm:py-16">
              <Search
                size={24}
                className="text-slate-700"
              />

              <h3 className="mt-4 text-sm font-medium text-slate-300">
                No transcript matches
              </h3>

              <p className="mt-2 text-xs text-slate-600">
                Try another word or
                speaker name.
              </p>

              <button
                type="button"
                onClick={() =>
                  setTranscriptSearch(
                    "",
                  )
                }
                className="mt-5 rounded-lg border border-white/8 bg-white/5 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-white/8"
              >
                Clear search
              </button>
            </div>
          ) : (
            <div className="divide-y divide-white/6">
              {filteredTranscriptSegments.map(
                (segment) => {
                  const isEditing =
                    editingSegmentId ===
                    segment.id;

                  const isActive =
                    activeSegmentId ===
                    segment.id;

                  const speakerName =
                    segment.speaker_display_name ??
                    segment.speaker_label ??
                    "Unknown Speaker";

                  return (
                    <div
                      key={
                        segment.id
                      }
                      className={[
                        "group min-w-0 px-4 py-4 transition sm:px-5 sm:py-5 lg:grid lg:grid-cols-[80px_150px_minmax(0,1fr)_auto] lg:gap-5 lg:px-6",
                        isActive
                          ? "bg-indigo-500/[0.055]"
                          : "hover:bg-white/[0.015]",
                      ].join(
                        " ",
                      )}
                    >
                      <div className="flex min-w-0 items-center justify-between gap-3 lg:block">
                        <button
                          type="button"
                          onClick={() =>
                            seekToSegment(
                              segment,
                            )
                          }
                          className="shrink-0 rounded-lg border border-indigo-500/15 bg-indigo-500/8 px-2 py-1 text-xs font-semibold text-indigo-300 transition hover:border-indigo-400/30 hover:bg-indigo-500/15 hover:text-indigo-200"
                          title="Jump to this timestamp"
                        >
                          {formatTimestamp(
                            segment.start_time,
                          )}
                        </button>

                        <div className="min-w-0 truncate text-right text-xs font-medium text-slate-400 lg:hidden">
                          {speakerName}
                        </div>
                      </div>

                      <div className="hidden min-w-0 pt-1 text-xs font-medium text-slate-400 lg:block">
                        <span className="block truncate">
                          {speakerName}
                        </span>
                      </div>

                      <div className="mt-3 min-w-0 lg:mt-0">
                        {isEditing ? (
                          <textarea
                            autoFocus
                            value={
                              editingSegmentText
                            }
                            onChange={(
                              event,
                            ) =>
                              setEditingSegmentText(
                                event
                                  .target
                                  .value,
                              )
                            }
                            rows={4}
                            className="w-full min-w-0 resize-y rounded-xl border border-indigo-500/30 bg-[#080b12] px-3 py-2.5 text-sm leading-6 text-slate-200 outline-none"
                          />
                        ) : (
                          <p className="min-w-0 break-words text-sm leading-6 text-slate-300">
                            {segment.edited_text ??
                              segment.original_text}
                          </p>
                        )}
                      </div>

                      <div className="mt-3 flex items-center justify-end gap-1 lg:mt-0 lg:items-start">
                        {isEditing ? (
                          <>
                            <button
                              type="button"
                              onClick={() =>
                                void saveSegment(
                                  segment.id,
                                )
                              }
                              className="rounded-lg p-2 text-emerald-300 hover:bg-emerald-500/10"
                              title="Save"
                            >
                              <Save
                                size={
                                  15
                                }
                              />
                            </button>

                            <button
                              type="button"
                              onClick={() =>
                                setEditingSegmentId(
                                  null,
                                )
                              }
                              className="rounded-lg p-2 text-slate-500 hover:bg-white/5 hover:text-slate-300"
                              title="Cancel"
                            >
                              <X
                                size={
                                  15
                                }
                              />
                            </button>
                          </>
                        ) : (
                          <button
                            type="button"
                            onClick={() =>
                              startEditingSegment(
                                segment,
                              )
                            }
                            className="rounded-lg p-2 text-slate-600 transition hover:bg-white/5 hover:text-slate-300 lg:opacity-0 lg:group-hover:opacity-100"
                            title="Edit transcript"
                          >
                            <Edit3
                              size={
                                15
                              }
                            />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                },
              )}
            </div>
          )}
        </section>
      )}

      {activeTab ===
        "speakers" && (
        <section className="mt-5 min-w-0 rounded-2xl border border-white/8 bg-[#0d111b] sm:mt-6">
          <div className="border-b border-white/8 px-4 py-4 sm:px-5 lg:px-6">
            <h2 className="font-semibold text-white">
              Speakers
            </h2>

            <p className="mt-1 text-xs leading-5 text-slate-500">
              Rename generic speaker
              labels when you know the
              participant&apos;s identity.
            </p>
          </div>

          {!speakers ? (
            <div className="p-10 text-center text-sm text-slate-500">
              No speakers available.
            </div>
          ) : (
            <div className="divide-y divide-white/6">
              {speakers.speakers.map(
                (speaker) => (
                  <div
                    key={
                      speaker.id
                    }
                    className="flex min-w-0 items-center justify-between gap-3 px-4 py-4 sm:gap-4 sm:px-5 lg:px-6"
                  >
                    <div className="flex min-w-0 items-center gap-3 sm:gap-4">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/8 bg-white/5 text-indigo-300 sm:h-10 sm:w-10">
                        <UserRound
                          size={17}
                        />
                      </div>

                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-slate-200">
                          {speaker.display_name ??
                            speaker.speaker_label}
                        </div>

                        {speaker.display_name && (
                          <div className="mt-1 truncate text-xs text-slate-600">
                            {
                              speaker.speaker_label
                            }
                          </div>
                        )}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() =>
                        void handleRenameSpeaker(
                          speaker,
                        )
                      }
                      className="shrink-0 rounded-lg border border-white/8 bg-white/5 px-3 py-2 text-xs font-medium text-slate-300 transition hover:bg-white/8 hover:text-white"
                    >
                      Rename
                    </button>
                  </div>
                ),
              )}
            </div>
          )}
        </section>
      )}

      <div className="mt-5 grid min-w-0 grid-cols-1 gap-3 rounded-2xl border border-white/8 bg-[#0d111b] p-4 text-xs text-slate-500 sm:mt-6 sm:flex sm:flex-wrap sm:items-center sm:gap-4 sm:p-5">
        <div className="flex items-center gap-2">
          <Clock3
            size={14}
            className="shrink-0"
          />

          {
            meeting.transcript_segment_count
          }{" "}
          transcript segments
        </div>

        <div className="flex items-center gap-2">
          <Users
            size={14}
            className="shrink-0"
          />

          {
            meeting.speaker_count
          }{" "}
          detected speakers
        </div>

        {notes && (
          <div className="flex min-w-0 items-center gap-2">
            <Sparkles
              size={14}
              className="shrink-0"
            />

            <span className="truncate">
              {notes.model_name}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}