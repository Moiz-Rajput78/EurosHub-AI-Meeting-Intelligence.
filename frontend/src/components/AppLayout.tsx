import {
  AudioLines,
  History,
  LayoutDashboard,
  Menu,
  Plus,
  Sparkles,
  X,
} from "lucide-react";

import {
  useState,
} from "react";

import {
  NavLink,
  Outlet,
} from "react-router-dom";


const navigation = [
  {
    to: "/",
    label: "Dashboard",
    icon: LayoutDashboard,
    end: true,
  },
  {
    to: "/meetings",
    label: "Meetings",
    icon: History,
    end: false,
  },
  {
    to: "/upload",
    label: "New meeting",
    icon: Plus,
    end: false,
  },
];


export function AppLayout() {
  const [
    mobileOpen,
    setMobileOpen,
  ] = useState(false);

  return (
    <div className="min-h-screen bg-[#080b12] text-slate-100">
      <aside
        className={[
          "fixed inset-y-0 left-0 z-50",
          "w-72 border-r border-white/8",
          "bg-[#0b0f18]/95 backdrop-blur-xl",
          "transition-transform duration-200",
          "lg:translate-x-0",
          mobileOpen
            ? "translate-x-0"
            : "-translate-x-full",
        ].join(" ")}
      >
        <div className="flex h-full flex-col">
          <div className="flex h-20 items-center justify-between px-6">
            <NavLink
              to="/"
              className="flex items-center gap-3"
              onClick={() =>
                setMobileOpen(false)
              }
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-950/50">
                <AudioLines
                  size={21}
                />
              </div>

              <div>
                <div className="font-semibold tracking-tight text-white">
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
              className="rounded-lg p-2 text-slate-400 hover:bg-white/5 lg:hidden"
            >
              <X size={20} />
            </button>
          </div>

          <div className="px-4">
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

          <nav className="mt-7 flex-1 space-y-1 px-4">
            {navigation.map(
              ({
                to,
                label,
                icon: Icon,
                end,
              }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
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
                  <Icon size={18} />

                  {label}
                </NavLink>
              ),
            )}
          </nav>

          <div className="m-4 rounded-2xl border border-indigo-500/15 bg-gradient-to-br from-indigo-500/10 to-violet-500/5 p-4">
            <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/15 text-indigo-300">
              <Sparkles size={16} />
            </div>

            <p className="text-sm font-medium text-slate-200">
              AI-powered notes
            </p>

            <p className="mt-1 text-xs leading-5 text-slate-500">
              Transcribe, identify
              speakers, and extract
              grounded meeting insights.
            </p>
          </div>
        </div>
      </aside>

      {mobileOpen && (
        <button
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={() =>
            setMobileOpen(false)
          }
        />
      )}

      <div className="lg:pl-72">
        <header className="sticky top-0 z-30 flex h-16 items-center border-b border-white/8 bg-[#080b12]/85 px-4 backdrop-blur-xl sm:px-6 lg:px-8">
          <button
            type="button"
            onClick={() =>
              setMobileOpen(true)
            }
            className="mr-4 rounded-lg p-2 text-slate-300 hover:bg-white/5 lg:hidden"
          >
            <Menu size={20} />
          </button>

          <div className="ml-auto flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <div className="text-xs font-medium text-slate-300">
                Local workspace
              </div>

              <div className="text-[11px] text-slate-600">
                FastAPI + Ollama Cloud
              </div>
            </div>

            <div className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-sm font-semibold text-indigo-300">
              MI
            </div>
          </div>
        </header>

        <main className="min-h-[calc(100vh-4rem)]">
          <Outlet />
        </main>
      </div>
    </div>
  );
}