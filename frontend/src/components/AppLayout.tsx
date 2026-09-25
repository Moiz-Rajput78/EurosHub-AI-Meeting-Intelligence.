import {
  LayoutDashboard,
  Menu,
  Moon,
  Plus,
  Sun,
  Trash2,
  X,
} from "lucide-react";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";

import {
  deleteMeeting,
  getMeetings,
} from "../lib/api";

import type {
  MeetingListItem,
} from "../types";

import {
  AppDialogProvider,
} from "./AppDialogProvider";

import {
  useAppDialog,
} from "./appDialog";


type Theme =
  | "light"
  | "dark";


const THEME_STORAGE_KEY =
  "meeting-intelligence-theme";


function getInitialTheme(): Theme {
  if (
    typeof window ===
    "undefined"
  ) {
    return "dark";
  }

  const stored =
    window.localStorage.getItem(
      THEME_STORAGE_KEY,
    );

  if (
    stored === "light" ||
    stored === "dark"
  ) {
    return stored;
  }

  const currentTheme =
    document.documentElement
      .dataset.theme;

  if (
    currentTheme === "light" ||
    currentTheme === "dark"
  ) {
    return currentTheme;
  }

  return window.matchMedia(
    "(prefers-color-scheme: light)",
  ).matches
    ? "light"
    : "dark";
}


function formatShortDate(
  value: string,
) {
  return new Intl.DateTimeFormat(
    undefined,
    {
      month: "short",
      day: "numeric",
    },
  ).format(
    new Date(value),
  );
}


function formatDuration(
  seconds: number | null,
) {
  if (!seconds) {
    return "";
  }

  const totalMinutes =
    Math.floor(seconds / 60);

  return `${totalMinutes}m`;
}


function AppLayoutContent() {
  const location =
    useLocation();

  const navigate =
    useNavigate();

  const {
    confirm,
    alert,
  } = useAppDialog();

  const workspaceMode =
    /^\/meetings\/\d+\/?$/.test(
      location.pathname,
    );

  const dashboardMode =
    location.pathname === "/";

  const uploadMode =
    location.pathname === "/upload";

  const fixedShellMode =
    workspaceMode ||
    dashboardMode ||
    uploadMode;

  const [
    mobileOpen,
    setMobileOpen,
  ] = useState(false);

  const [
    theme,
    setTheme,
  ] = useState<Theme>(
    getInitialTheme,
  );

  const [
    meetings,
    setMeetings,
  ] = useState<MeetingListItem[]>([]);

  const [
    deletingId,
    setDeletingId,
  ] = useState<number | null>(
    null,
  );


  useEffect(() => {
    document.documentElement
      .setAttribute(
        "data-theme",
        theme,
      );

    window.localStorage.setItem(
      THEME_STORAGE_KEY,
      theme,
    );

    const metaThemeColor =
      document.querySelector(
        'meta[name="theme-color"]',
      );

    if (metaThemeColor) {
      metaThemeColor.setAttribute(
        "content",
        theme === "light"
          ? "#f8faf9"
          : "#070908",
      );
    }
  }, [
    theme,
  ]);


  useEffect(() => {
    let cancelled = false;

    async function loadMeetings() {
      try {
        const result =
          await getMeetings();

        if (!cancelled) {
          setMeetings(
            result.meetings,
          );
        }
      } catch {
        // Keep navigation usable if the API is temporarily unavailable.
      }
    }

    void loadMeetings();

    const intervalId =
      window.setInterval(
        () => {
          void loadMeetings();
        },
        15000,
      );

    return () => {
      cancelled = true;

      window.clearInterval(
        intervalId,
      );
    };
  }, [
    location.pathname,
  ]);


  const recentMeetings =
    useMemo(
      () =>
        meetings
          .slice()
          .sort(
            (a, b) =>
              new Date(
                b.created_at,
              ).getTime() -
              new Date(
                a.created_at,
              ).getTime(),
          )
          .slice(
            0,
            8,
          ),
      [
        meetings,
      ],
    );


  function toggleTheme() {
    setTheme(
      (current) =>
        current === "dark"
          ? "light"
          : "dark",
    );
  }


  async function handleDeleteMeeting(
    meeting: MeetingListItem,
  ) {
    if (
      deletingId !== null
    ) {
      return;
    }

    const confirmed =
      await confirm({
        title: "Delete meeting?",
        description:
          `“${meeting.title}” will be permanently deleted together with its transcript, speakers, AI notes, exports, and stored recording files. This action cannot be undone.`,
        confirmLabel:
          "Delete meeting",
        cancelLabel:
          "Keep meeting",
        tone:
          "danger",
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

      if (
        location.pathname ===
        `/meetings/${meeting.id}`
      ) {
        navigate(
          "/",
          {
            replace: true,
          },
        );
      }
    } catch (caught) {
      await alert({
        title:
          "Unable to delete meeting",
        description:
          caught instanceof Error
            ? caught.message
            : "The meeting could not be deleted. Please try again.",
        actionLabel:
          "Close",
        tone:
          "danger",
      });
    } finally {
      setDeletingId(null);
    }
  }


  return (
    <div
      className={[
        "app-shell bg-[#080b12] text-slate-100",
        fixedShellMode
          ? "h-screen overflow-hidden"
          : "min-h-screen",
      ].join(" ")}
    >
      <aside
        className={[
          "app-sidebar",
          "fixed inset-y-0 left-0 z-50",
          "w-[248px] border-r border-white/8",
          "bg-[#0b0f18]/95 backdrop-blur-xl",
          "transition-transform duration-200",
          "lg:translate-x-0",
          mobileOpen
            ? "translate-x-0"
            : "-translate-x-full",
        ].join(" ")}
      >
        <div className="flex h-full min-h-0 flex-col overflow-hidden">
          <div className="flex h-[68px] shrink-0 items-center justify-between px-5">
            <NavLink
              to="/"
              className="flex min-w-0 items-center gap-3"
              onClick={() =>
                setMobileOpen(false)
              }
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-white/8 bg-white shadow-sm">
                <img
                  src="/favicon.ico"
                  alt="EurosHub"
                  className="h-9 w-9 object-contain"
                />
              </div>

              <div className="min-w-0">
                <div className="truncate font-semibold tracking-tight text-white">
                  Meeting Intelligence
                </div>

                <div className="text-xs text-slate-500">
                  AI meeting workspace
                </div>
              </div>
            </NavLink>

            <button
              type="button"
              onClick={() =>
                setMobileOpen(false)
              }
              className="rounded-lg p-2 text-slate-400 transition hover:bg-white/5 lg:hidden"
              aria-label="Close navigation"
            >
              <X size={20} />
            </button>
          </div>

          <div className="shrink-0 px-3.5">
            <NavLink
              to="/upload"
              onClick={() =>
                setMobileOpen(false)
              }
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-500 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-950/30 transition hover:bg-indigo-400"
            >
              <Plus size={17} />

              Upload meeting
            </NavLink>
          </div>

          <div className="mt-5 flex min-h-0 flex-1 flex-col px-3.5 pb-4">
            <nav className="shrink-0">
              <NavLink
                to="/"
                end
                onClick={() =>
                  setMobileOpen(false)
                }
                className={({
                  isActive,
                }) =>
                  [
                    "flex items-center gap-3",
                    "rounded-xl px-4 py-3",
                    "text-sm font-medium transition",
                    isActive
                      ? "bg-white/8 text-white"
                      : "text-slate-400 hover:bg-white/5 hover:text-slate-100",
                  ].join(" ")
                }
              >
                <LayoutDashboard
                  size={18}
                  className="shrink-0"
                />

                Dashboard
              </NavLink>
            </nav>

            <div className="mt-5 flex min-h-0 flex-1 flex-col">
              <div className="flex shrink-0 items-center justify-between px-3">
                <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                  Meetings
                </span>

                <span className="text-[10px] tabular-nums text-slate-600">
                  {meetings.length}
                </span>
              </div>

              <div className="mt-2 min-h-0 flex-1 overflow-y-auto pr-1">
                {recentMeetings.length ===
                0 ? (
                  <div className="rounded-xl border border-white/6 px-3 py-4 text-center text-xs leading-5 text-slate-600">
                    No meetings yet.
                  </div>
                ) : (
                  <div className="space-y-1">
                    {recentMeetings.map(
                      (meeting) => (
                        <div
                          key={
                            meeting.id
                          }
                          className="group relative min-w-0"
                        >
                          <NavLink
                            to={`/meetings/${meeting.id}`}
                            onClick={() =>
                              setMobileOpen(
                                false,
                              )
                            }
                            className={({
                              isActive,
                            }) =>
                              [
                                "block min-w-0 rounded-xl px-3 py-2.5 pr-10 transition",
                                isActive
                                  ? "bg-white/8"
                                  : "hover:bg-white/5",
                              ].join(
                                " ",
                              )
                            }
                          >
                            <div className="truncate text-xs font-medium text-slate-300">
                              {
                                meeting.title
                              }
                            </div>

                            <div className="mt-1 flex items-center gap-2 text-[10px] text-slate-600">
                              <span>
                                {formatShortDate(
                                  meeting.created_at,
                                )}
                              </span>

                              {meeting.duration && (
                                <>
                                  <span>
                                    •
                                  </span>

                                  <span>
                                    {formatDuration(
                                      meeting.duration,
                                    )}
                                  </span>
                                </>
                              )}
                            </div>
                          </NavLink>

                          <button
                            type="button"
                            disabled={
                              deletingId ===
                              meeting.id
                            }
                            onClick={(event) => {
                              event.preventDefault();
                              event.stopPropagation();

                              void handleDeleteMeeting(
                                meeting,
                              );
                            }}
                            className={[
                              "absolute right-2 top-1/2 -translate-y-1/2",
                              "flex h-7 w-7 items-center justify-center rounded-lg",
                              "text-slate-600 transition",
                              "hover:bg-red-500/10 hover:text-red-400",
                              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/30",
                              "disabled:cursor-not-allowed disabled:opacity-40",
                              "lg:opacity-0 lg:group-hover:opacity-100 lg:focus-within:opacity-100",
                            ].join(" ")}
                            aria-label={`Delete ${meeting.title}`}
                            title="Delete meeting"
                          >
                            <Trash2
                              size={14}
                            />
                          </button>
                        </div>
                      ),
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="shrink-0 border-t border-white/8 px-3.5 py-3">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="text-xs font-medium text-slate-300">
                  Appearance
                </div>

                <div className="mt-0.5 text-[11px] text-slate-600">
                  Light / dark
                </div>
              </div>

              <button
                type="button"
                onClick={toggleTheme}
                className="theme-toggle shrink-0"
                aria-label={
                  theme === "dark"
                    ? "Switch to light mode"
                    : "Switch to dark mode"
                }
                title={
                  theme === "dark"
                    ? "Switch to light mode"
                    : "Switch to dark mode"
                }
              >
                <span className="theme-toggle-indicator" />

                <span className="theme-toggle-icon theme-toggle-sun">
                  <Sun size={14} />
                </span>

                <span className="theme-toggle-icon theme-toggle-moon">
                  <Moon size={14} />
                </span>
              </button>
            </div>

            <div className="mt-3 flex items-center gap-3 border-t border-white/6 pt-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-sm font-semibold text-indigo-300">
                MI
              </div>

              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-semibold text-slate-300">
                  Meeting Intelligence
                </div>

                <div className="mt-0.5 text-[11px] text-slate-600">
                  Workspace profile
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={() =>
            setMobileOpen(false)
          }
        />
      )}

      <div
        className={[
          "lg:pl-[248px]",
          fixedShellMode
            ? "h-screen overflow-hidden"
            : "",
        ].join(" ")}
      >
        {!workspaceMode && (
          <button
            type="button"
            onClick={() =>
              setMobileOpen(true)
            }
            className="fixed left-4 top-4 z-30 flex h-10 w-10 items-center justify-center rounded-xl border border-white/8 bg-[#0d111b]/95 text-slate-300 shadow-lg backdrop-blur-xl transition hover:bg-white/5 lg:hidden"
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>
        )}

        <main
          className={
            workspaceMode ||
            dashboardMode ||
            uploadMode
              ? "h-screen min-h-0 overflow-hidden"
              : "min-h-screen"
          }
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}


export function AppLayout() {
  return (
    <AppDialogProvider>
      <AppLayoutContent />
    </AppDialogProvider>
  );
}
