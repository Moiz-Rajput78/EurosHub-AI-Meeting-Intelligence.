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
import {
  useAppDialog,
} from "../components/appDialog";
import type {
  MeetingDetail,
  MeetingNotesResponse,
  MeetingSpeakersResponse,
  MeetingTranscriptResponse,
  Speaker,
  TranscriptSegment,
} from "../types";



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


export function MeetingDetailPage() {
  const {
    alert,
    prompt,
  } = useAppDialog();

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
      await alert({
        title: "Unable to regenerate notes",
        description:
          caught instanceof Error
            ? caught.message
            : "The meeting notes could not be regenerated. Please try again.",
        actionLabel: "Close",
        tone: "danger",
      });
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
      await prompt({
        title: `Rename ${speaker.speaker_label}`,
        description:
          "Enter the participant name you want to display throughout this meeting transcript.",
        defaultValue: current,
        placeholder: "Participant name",
        confirmLabel: "Save name",
        cancelLabel: "Cancel",
      });

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
      await alert({
        title: "Unable to rename speaker",
        description:
          caught instanceof Error
            ? caught.message
            : "The speaker name could not be updated. Please try again.",
        actionLabel: "Close",
        tone: "danger",
      });
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
      await alert({
        title: "Unable to update transcript",
        description:
          caught instanceof Error
            ? caught.message
            : "The transcript segment could not be saved. Please try again.",
        actionLabel: "Close",
        tone: "danger",
      });
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


  const mediaUrl =
    getMeetingMediaUrl(
      meeting.id,
    );

  const meetingDate =
    new Intl.DateTimeFormat(
      undefined,
      {
        dateStyle: "medium",
      },
    ).format(
      new Date(
        meeting.created_at,
      ),
    );

  return (
    <div className="meeting-workspace h-full min-h-0 overflow-hidden">
      <div className="grid h-full min-h-0 grid-cols-1 xl:grid-cols-[minmax(0,1fr)_352px] 2xl:grid-cols-[minmax(0,1fr)_372px]">
        <section className="meeting-workspace-main flex min-h-0 min-w-0 flex-col overflow-hidden">
          <header className="meeting-workspace-header shrink-0 border-b border-white/8 px-4 py-2 sm:px-5 lg:px-6">
            <div className="flex min-w-0 items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2.5">
                <Link
                  to="/meetings"
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/8 bg-white/5 text-slate-300 transition hover:bg-white/8 hover:text-white"
                  title="Back to meetings"
                >
                  <ArrowLeft size={18} />
                </Link>

                <div className="min-w-0">
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <h1 className="min-w-0 truncate text-[17px] font-semibold tracking-tight text-white sm:text-lg">
                      {meeting.title}
                    </h1>

                    <StatusBadge
                      status={meeting.status}
                      progressPercent={
                        meeting.progress_percent
                      }
                    />
                  </div>

                  <div className="mt-1 flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
                    <span className="inline-flex items-center gap-1.5">
                      <CalendarDays size={13} />
                      {meetingDate}
                    </span>

                    {meeting.duration && (
                      <span className="inline-flex items-center gap-1.5">
                        <Clock3 size={13} />
                        {formatTimestamp(
                          meeting.duration,
                        )}
                      </span>
                    )}

                    <span className="inline-flex items-center gap-1.5">
                      <Users size={13} />
                      {meeting.speaker_count} speaker{
                        meeting.speaker_count === 1
                          ? ""
                          : "s"
                      }
                    </span>

                    {meeting.language && (
                      <span className="rounded-full border border-white/8 bg-white/5 px-2 py-0.5">
                        {meeting.language.toUpperCase()}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <ExportMenu
                  meetingId={meeting.id}
                />

                {meeting.has_transcript && (
                  <button
                    type="button"
                    disabled={regenerating}
                    onClick={() =>
                      void handleRegenerate()
                    }
                    className="hidden h-9 items-center gap-1.5 rounded-lg border border-white/8 bg-white/5 px-3 text-[13px] font-medium text-slate-300 transition hover:bg-white/8 hover:text-white disabled:opacity-50 sm:inline-flex"
                  >
                    {regenerating ? (
                      <LoaderCircle
                        size={14}
                        className="animate-spin"
                      />
                    ) : meeting.has_notes ? (
                      <RefreshCw size={14} />
                    ) : (
                      <Sparkles size={14} />
                    )}

                    {meeting.has_notes
                      ? "Regenerate"
                      : "Generate notes"}
                  </button>
                )}
              </div>
            </div>

          </header>

          <div className="meeting-center-scroll min-h-0 flex-1 overflow-y-auto px-4 py-3 sm:px-5 lg:px-6">
            <MeetingPlayer
              meetingId={meeting.id}
              filename={
                meeting.original_filename
              }
              mediaUrl={mediaUrl}
              mediaRef={mediaRef}
            />

            <section className="transcript-workspace mt-2.5 flex min-h-[360px] flex-col overflow-hidden rounded-2xl border border-white/8 bg-[#0d111b]">
              <div className="shrink-0 border-b border-white/8 px-4 py-2 sm:px-5">
                <div className="flex min-w-0 flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <FileText
                        size={17}
                        className="text-indigo-300"
                      />
                      <h2 className="font-semibold text-white">
                        Transcript
                      </h2>
                    </div>

                    <p className="mt-1 text-xs text-slate-500">
                      {meeting.transcript_segment_count} segments · click a timestamp to jump to the recording
                    </p>
                  </div>

                  <div className="w-full min-w-0 lg:w-[310px]">
                    <div className="relative">
                      <Search
                        size={15}
                        className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-600"
                      />

                      <input
                        value={transcriptSearch}
                        onChange={(event) =>
                          setTranscriptSearch(
                            event.target.value,
                          )
                        }
                        placeholder="Search transcript..."
                        className="w-full rounded-xl border border-white/8 bg-[#080b12] py-2 pl-10 pr-10 text-sm text-slate-200 outline-none transition placeholder:text-slate-600 focus:border-indigo-500/50"
                      />

                      {transcriptSearch && (
                        <button
                          type="button"
                          onClick={() =>
                            setTranscriptSearch("")
                          }
                          className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-600 transition hover:bg-white/5 hover:text-slate-300"
                          title="Clear search"
                        >
                          <X size={15} />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {speakers &&
                speakers.speakers.length > 0 && (
                  <div className="shrink-0 border-b border-white/8 px-4 py-2 sm:px-5">
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="flex shrink-0 items-center gap-2 text-xs font-semibold text-slate-400">
                        <Users
                          size={14}
                          className="text-indigo-300"
                        />

                        <span>
                          Speakers
                        </span>
                      </div>

                      <div className="h-5 w-px shrink-0 bg-white/8" />

                      <div className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto pb-0.5">
                        {speakers.speakers.map(
                          (speaker) => (
                            <button
                              key={speaker.id}
                              type="button"
                              onClick={() =>
                                void handleRenameSpeaker(
                                  speaker,
                                )
                              }
                              className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-white/8 bg-white/[0.025] px-2.5 py-1 text-[11px] font-medium text-slate-300 transition hover:border-indigo-500/30 hover:bg-indigo-500/8 hover:text-white"
                              title={`Rename ${speaker.speaker_label}`}
                            >
                              <UserRound
                                size={13}
                              />

                              {speaker.display_name ??
                                speaker.speaker_label}
                            </button>
                          ),
                        )}
                      </div>
                    </div>
                  </div>
                )}

              <div className="transcript-list min-h-0 flex-1 overflow-y-auto">
                {!transcript ? (
                  <div className="flex h-full min-h-[220px] items-center justify-center p-8 text-center text-sm text-slate-500">
                    No transcript available.
                  </div>
                ) : filteredTranscriptSegments.length === 0 ? (
                  <div className="flex h-full min-h-[220px] flex-col items-center justify-center px-6 text-center">
                    <Search
                      size={24}
                      className="text-slate-700"
                    />
                    <h3 className="mt-4 text-sm font-medium text-slate-300">
                      No transcript matches
                    </h3>
                    <button
                      type="button"
                      onClick={() =>
                        setTranscriptSearch("")
                      }
                      className="mt-4 rounded-lg border border-white/8 bg-white/5 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-white/8"
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
                          <article
                            key={segment.id}
                            className={[
                              "group grid min-w-0 grid-cols-[40px_minmax(0,1fr)_auto] gap-2.5 px-4 py-2.5 transition sm:grid-cols-[44px_108px_minmax(0,1fr)_auto] sm:px-5",
                              isActive
                                ? "bg-indigo-500/[0.055]"
                                : "hover:bg-white/[0.015]",
                            ].join(" ")}
                          >
                            <button
                              type="button"
                              onClick={() =>
                                seekToSegment(
                                  segment,
                                )
                              }
                              className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-full border border-indigo-500/20 bg-indigo-500/10 text-[11px] font-bold text-indigo-300 transition hover:bg-indigo-500/15"
                              title="Jump to this timestamp"
                            >
                              {speakerName
                                .replace(
                                  /[^A-Za-z0-9 ]/g,
                                  "",
                                )
                                .split(" ")
                                .filter(Boolean)
                                .map((part) =>
                                  part[0],
                                )
                                .join("")
                                .slice(0, 2)
                                .toUpperCase() || "S"}
                            </button>

                            <div className="hidden min-w-0 sm:block">
                              <div className="truncate text-xs font-semibold text-slate-300">
                                {speakerName}
                              </div>

                              <button
                                type="button"
                                onClick={() =>
                                  seekToSegment(
                                    segment,
                                  )
                                }
                                className="mt-1 text-[11px] font-medium text-indigo-300 transition hover:text-indigo-200"
                              >
                                {formatTimestamp(
                                  segment.start_time,
                                )}
                              </button>
                            </div>

                            <div className="min-w-0">
                              <div className="mb-1 flex items-center gap-2 sm:hidden">
                                <span className="truncate text-xs font-semibold text-slate-300">
                                  {speakerName}
                                </span>
                                <button
                                  type="button"
                                  onClick={() =>
                                    seekToSegment(
                                      segment,
                                    )
                                  }
                                  className="shrink-0 text-[11px] text-indigo-300"
                                >
                                  {formatTimestamp(
                                    segment.start_time,
                                  )}
                                </button>
                              </div>

                              {isEditing ? (
                                <textarea
                                  autoFocus
                                  value={
                                    editingSegmentText
                                  }
                                  onChange={(event) =>
                                    setEditingSegmentText(
                                      event.target.value,
                                    )
                                  }
                                  rows={4}
                                  className="w-full resize-y rounded-xl border border-indigo-500/30 bg-[#080b12] px-3 py-2.5 text-sm leading-6 text-slate-200 outline-none"
                                />
                              ) : (
                                <p className="break-words text-sm leading-5.5 text-slate-300">
                                  {segment.edited_text ??
                                    segment.original_text}
                                </p>
                              )}
                            </div>

                            <div className="flex items-start justify-end gap-1">
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
                                    <Save size={15} />
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
                                    <X size={15} />
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
                                  className="rounded-lg p-2 text-slate-600 transition hover:bg-white/5 hover:text-slate-300 sm:opacity-0 sm:group-hover:opacity-100"
                                  title="Edit transcript"
                                >
                                  <Edit3 size={15} />
                                </button>
                              )}
                            </div>
                          </article>
                        );
                      },
                    )}
                  </div>
                )}
              </div>
            </section>
          </div>
        </section>

        <aside className="meeting-notes-panel flex min-h-0 min-w-0 flex-col overflow-hidden border-t border-white/8 bg-[#0b0f18] xl:border-l xl:border-t-0">
          <div className="shrink-0 border-b border-white/8 px-4 py-3 sm:px-5">
            <div className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2.5">
                <Sparkles
                  size={19}
                  className="shrink-0 text-indigo-300"
                />
                <div className="min-w-0">
                  <h2 className="font-semibold text-white">
                    Meeting Notes
                  </h2>
                  <p className="mt-0.5 text-[11px] text-slate-600">
                    Grounded AI meeting intelligence
                  </p>
                </div>
              </div>

              {notes && (
                <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  AI Generated
                </span>
              )}
            </div>
          </div>

          <div className="meeting-notes-scroll min-h-0 flex-1 overflow-y-auto p-3 sm:p-4">
            {!notes ? (
              <div className="flex min-h-[320px] flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 bg-[#0d111b] px-6 text-center">
                <Sparkles
                  size={28}
                  className="text-indigo-300"
                />
                <h3 className="mt-4 font-semibold text-white">
                  No current AI notes
                </h3>
                <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
                  Generate structured meeting intelligence from the current transcript.
                </p>

                {meeting.has_transcript && (
                  <button
                    type="button"
                    disabled={regenerating}
                    onClick={() =>
                      void handleRegenerate()
                    }
                    className="mt-5 inline-flex items-center gap-2 rounded-xl bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:opacity-50"
                  >
                    {regenerating ? (
                      <LoaderCircle
                        size={16}
                        className="animate-spin"
                      />
                    ) : (
                      <Sparkles size={16} />
                    )}
                    Generate notes
                  </button>
                )}
              </div>
            ) : (
              <div className="notes-summary-card overflow-hidden rounded-2xl border border-white/8 bg-[#0d111b]">
                <section className="p-4 sm:p-5">
                  <div className="flex items-center gap-2">
                    <MessageSquareText
                      size={17}
                      className="text-indigo-300"
                    />
                    <h3 className="text-sm font-semibold text-white">
                      Summary
                    </h3>
                  </div>

                  <p className="mt-2.5 break-words text-sm leading-5.5 text-slate-300">
                    {notes.summary}
                  </p>
                </section>

                <section className="border-t border-white/8 p-3.5 sm:p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <ClipboardCheck
                        size={17}
                        className="text-emerald-300"
                      />
                      <h3 className="text-sm font-semibold text-white">
                        Action Items
                      </h3>
                    </div>
                    <span className="text-[11px] text-slate-600">
                      {notes.action_items.length} items
                    </span>
                  </div>

                  {notes.action_items.length === 0 ? (
                    <p className="mt-3 text-sm text-slate-500">
                      No explicit action items were detected.
                    </p>
                  ) : (
                    <div className="mt-2.5 space-y-2">
                      {notes.action_items.map(
                        (item, index) => (
                          <div
                            key={item.id}
                            className="grid min-w-0 grid-cols-[26px_minmax(0,1fr)] gap-2.5"
                          >
                            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/10 text-[11px] font-semibold text-emerald-300">
                              {index + 1}
                            </span>
                            <div className="min-w-0">
                              <p className="break-words text-sm leading-5 text-slate-300">
                                {item.task}
                              </p>
                              <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-600">
                                <span>
                                  Owner: {item.responsible_person ?? "Not specified"}
                                </span>
                                <span>
                                  Due: {item.deadline ?? "Not mentioned"}
                                </span>
                              </div>
                            </div>
                          </div>
                        ),
                      )}
                    </div>
                  )}
                </section>

                <section className="border-t border-white/8 p-3.5 sm:p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <CheckCircle2
                        size={17}
                        className="text-indigo-300"
                      />
                      <h3 className="text-sm font-semibold text-white">
                        Key Decisions
                      </h3>
                    </div>
                    <span className="text-[11px] text-slate-600">
                      {notes.decisions.length} items
                    </span>
                  </div>

                  {notes.decisions.length === 0 ? (
                    <p className="mt-3 text-sm text-slate-500">
                      No confirmed decisions were detected.
                    </p>
                  ) : (
                    <ul className="mt-2.5 space-y-2">
                      {notes.decisions.map(
                        (decision) => (
                          <li
                            key={decision.id}
                            className="flex min-w-0 gap-2.5 text-sm leading-5 text-slate-300"
                          >
                            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
                            <span className="break-words">
                              {decision.decision}
                            </span>
                          </li>
                        ),
                      )}
                    </ul>
                  )}
                </section>

                <section className="border-t border-white/8 p-3.5 sm:p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <FileText
                        size={17}
                        className="text-indigo-300"
                      />
                      <h3 className="text-sm font-semibold text-white">
                        Agenda / Discussion Points
                      </h3>
                    </div>
                    <span className="text-[11px] text-slate-600">
                      {notes.key_discussion_points.length} items
                    </span>
                  </div>

                  {notes.key_discussion_points.length === 0 ? (
                    <p className="mt-3 text-sm text-slate-500">
                      No discussion points were extracted.
                    </p>
                  ) : (
                    <ol className="mt-2.5 space-y-2">
                      {notes.key_discussion_points.map(
                        (point, index) => (
                          <li
                            key={`${index}-${point}`}
                            className="grid grid-cols-[26px_minmax(0,1fr)] gap-2.5 text-sm leading-5 text-slate-300"
                          >
                            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/5 text-[11px] font-semibold text-slate-400">
                              {index + 1}
                            </span>
                            <span className="break-words">
                              {point}
                            </span>
                          </li>
                        ),
                      )}
                    </ol>
                  )}
                </section>

                {notes.important_dates.length > 0 && (
                  <section className="border-t border-white/8 p-3.5 sm:p-4">
                    <div className="flex items-center gap-2">
                      <CalendarDays
                        size={17}
                        className="text-indigo-300"
                      />
                      <h3 className="text-sm font-semibold text-white">
                        Important Dates
                      </h3>
                    </div>
                    <div className="mt-2.5 space-y-2">
                      {notes.important_dates.map(
                        (item, index) => (
                          <div
                            key={`${index}-${item.date_or_time}`}
                            className="rounded-xl bg-white/[0.025] p-3"
                          >
                            <div className="text-xs font-medium text-indigo-300">
                              {item.date_or_time}
                            </div>
                            <p className="mt-1 break-words text-sm leading-5 text-slate-300">
                              {item.description}
                            </p>
                          </div>
                        ),
                      )}
                    </div>
                  </section>
                )}

                {notes.open_issues.length > 0 && (
                  <section className="border-t border-white/8 p-3.5 sm:p-4">
                    <div className="flex items-center gap-2">
                      <AlertCircle
                        size={17}
                        className="text-amber-300"
                      />
                      <h3 className="text-sm font-semibold text-white">
                        Open Issues
                      </h3>
                    </div>
                    <ul className="mt-2.5 space-y-2">
                      {notes.open_issues.map(
                        (issue) => (
                          <li
                            key={issue.id}
                            className="flex gap-2.5 text-sm leading-5 text-slate-300"
                          >
                            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" />
                            <span className="break-words">
                              {issue.issue}
                            </span>
                          </li>
                        ),
                      )}
                    </ul>
                  </section>
                )}

                {notes.requirements.length > 0 && (
                  <section className="border-t border-white/8 p-3.5 sm:p-4">
                    <div className="flex items-center gap-2">
                      <ClipboardCheck
                        size={17}
                        className="text-indigo-300"
                      />
                      <h3 className="text-sm font-semibold text-white">
                        Requirements
                      </h3>
                    </div>
                    <ul className="mt-2.5 space-y-2">
                      {notes.requirements.map(
                        (item) => (
                          <li
                            key={item.id}
                            className="flex gap-2.5 text-sm leading-5 text-slate-300"
                          >
                            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
                            <span className="break-words">
                              {item.requirement}
                            </span>
                          </li>
                        ),
                      )}
                    </ul>
                  </section>
                )}

                {notes.announcements.length > 0 && (
                  <section className="border-t border-white/8 p-3.5 sm:p-4">
                    <div className="flex items-center gap-2">
                      <MessageSquareText
                        size={17}
                        className="text-indigo-300"
                      />
                      <h3 className="text-sm font-semibold text-white">
                        Announcements
                      </h3>
                    </div>
                    <ul className="mt-2.5 space-y-2">
                      {notes.announcements.map(
                        (item, index) => (
                          <li
                            key={`${index}-${item.announcement}`}
                            className="flex gap-2.5 text-sm leading-5 text-slate-300"
                          >
                            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
                            <span className="break-words">
                              {item.announcement}
                            </span>
                          </li>
                        ),
                      )}
                    </ul>
                  </section>
                )}

                {notes.unanswered_questions.length > 0 && (
                  <section className="border-t border-white/8 p-3.5 sm:p-4">
                    <div className="flex items-center gap-2">
                      <CircleHelp
                        size={17}
                        className="text-indigo-300"
                      />
                      <h3 className="text-sm font-semibold text-white">
                        Unanswered Questions
                      </h3>
                    </div>
                    <ul className="mt-2.5 space-y-2">
                      {notes.unanswered_questions.map(
                        (item, index) => (
                          <li
                            key={`${index}-${item.question}`}
                            className="flex gap-2.5 text-sm leading-5 text-slate-300"
                          >
                            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
                            <span className="break-words">
                              {item.question}
                            </span>
                          </li>
                        ),
                      )}
                    </ul>
                  </section>
                )}

                {notes.topics.length > 0 && (
                  <section className="border-t border-white/8 p-3.5 sm:p-4">
                    <div className="flex items-center gap-2">
                      <Tag
                        size={17}
                        className="text-indigo-300"
                      />
                      <h3 className="text-sm font-semibold text-white">
                        Topics
                      </h3>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {notes.topics.map(
                        (topic) => (
                          <span
                            key={topic}
                            className="rounded-lg border border-indigo-500/15 bg-indigo-500/8 px-2.5 py-1.5 text-xs text-indigo-300"
                          >
                            {topic}
                          </span>
                        ),
                      )}
                    </div>
                  </section>
                )}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
