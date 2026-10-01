import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  BookOpen,
  Check,
  ChevronDown,
  CircleHelp,
  Database,
  FileText,
  Gauge,
  LayoutDashboard,
  Loader2,
  LogOut,
  Plus,
  RefreshCw,
  Save,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Trash2,
  Users,
  Video,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { adminDashboardService } from "@/services/adminDashboard.service";
import type {
  AdminActivity,
  AdminLessonPayload,
  AdminLogs,
  AdminModulePayload,
  AdminStats,
  AdminStudent,
  AdminTrack,
  AdminTrackPayload,
} from "@/types/adminDashboard";
import type { Lesson, LessonQuizQuestion } from "@/types/track";

type DashboardTab = "Overview" | "Content CMS" | "Students" | "Analytics" | "Settings";

const tabs: { label: DashboardTab; icon: typeof LayoutDashboard }[] = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Content CMS", icon: BookOpen },
  { label: "Students", icon: Users },
  { label: "Analytics", icon: BarChart3 },
  { label: "Settings", icon: Settings2 },
];

const inputClass = "w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-100";
const labelClass = "mb-1.5 block text-xs font-semibold text-slate-600";

function getErrorMessage(error: unknown): string {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response;
    if (typeof response?.data?.detail === "string") return response.data.detail;
  }
  return error instanceof Error ? error.message : "The request could not be completed.";
}

function quizFromLesson(lesson: Lesson): LessonQuizQuestion[] {
  if (Array.isArray(lesson.quiz_data)) return lesson.quiz_data;
  if (typeof lesson.quiz_data === "string") {
    try {
      const parsed: unknown = JSON.parse(lesson.quiz_data);
      return Array.isArray(parsed) ? parsed as LessonQuizQuestion[] : [];
    } catch {
      return [];
    }
  }
  return [];
}

function ActivityChart({ data }: { data: AdminStats["engagement"] }) {
  const values = data.map((item) => item.active_users);
  const maxValue = Math.max(...values, 1);
  const points = values.map((value, index) => {
    const x = data.length <= 1 ? 24 : 24 + (index * 592) / (data.length - 1);
    const y = 174 - (value / maxValue) * 132;
    return `${x},${y}`;
  });
  const polygon = points.length ? `24,188 ${points.join(" ")} 616,188` : "24,188 616,188";

  return (
    <div className="mt-5 min-w-0">
      <svg className="h-56 w-full overflow-visible" viewBox="0 0 640 220" role="img" aria-label="Monthly active student engagement">
        <defs>
          <linearGradient id="engagement-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.01" />
          </linearGradient>
        </defs>
        {[50, 95, 140, 185].map((y) => (
          <line key={y} x1="20" x2="620" y1={y} y2={y} stroke="#e2e8f0" strokeDasharray="4 6" />
        ))}
        {points.length > 1 && <polygon points={polygon} fill="url(#engagement-fill)" />}
        {points.length > 1 && (
          <polyline points={points.join(" ")} fill="none" stroke="#0284c7" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
        )}
        {points.map((point, index) => {
          const [cx, cy] = point.split(",");
          return <circle key={`${data[index]?.month}-${point}`} cx={cx} cy={cy} r="4" fill="#fff" stroke="#0284c7" strokeWidth="3"><title>{`${data[index]?.month}: ${values[index]} active students`}</title></circle>;
        })}
      </svg>
      <div className="-mt-2 flex justify-between px-1 text-[11px] font-medium text-slate-400">
        {data.map((item) => <span key={item.month}>{item.month}</span>)}
      </div>
    </div>
  );
}

function EngagementBars({ data }: { data: AdminStats["engagement"] }) {
  const maxValue = Math.max(1, ...data.map((item) => item.active_users));
  return (
    <div className="mt-5 flex h-52 items-end gap-2 border-b border-slate-200 px-1 pb-0 sm:gap-4">
      {data.map((item, index) => (
        <div key={item.month} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-2">
          <span className="text-[10px] tabular-nums text-slate-500">{item.active_users}</span>
          <div
            className={`w-full max-w-11 rounded-t-md transition-all ${index === data.length - 1 ? "bg-sky-500" : "bg-sky-200 hover:bg-sky-300"}`}
            style={{ height: `${Math.max(5, (item.active_users / maxValue) * 75)}%` }}
            title={`${item.month}: ${item.active_users} active students`}
          />
          <span className="text-[10px] font-medium text-slate-400">{item.month}</span>
        </div>
      ))}
    </div>
  );
}

function MetricCard({
  label,
  value,
  note,
  icon: Icon,
  tone = "sky",
}: {
  label: string;
  value: string | number;
  note: string;
  icon: typeof Users;
  tone?: "sky" | "emerald" | "amber" | "violet";
}) {
  const tones = {
    sky: "bg-sky-50 text-sky-700",
    emerald: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    violet: "bg-violet-50 text-violet-700",
  };
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <span className={`flex size-9 items-center justify-center rounded-lg ${tones[tone]}`}>
          <Icon aria-hidden="true" className="size-[18px]" />
        </span>
      </div>
      <p className="mt-4 text-3xl font-bold tracking-tight text-slate-950">{value}</p>
      <p className="mt-1.5 text-xs text-slate-500">{note}</p>
    </article>
  );
}

function ActivityList({ activities }: { activities: AdminActivity[] }) {
  if (!activities.length) {
    return <p className="py-8 text-center text-sm text-slate-500">No recent activity recorded.</p>;
  }
  return (
    <div className="divide-y divide-slate-100">
      {activities.slice(0, 8).map((activity, index) => (
        <div key={`${activity.kind}-${activity.created_at}-${index}`} className="flex items-start gap-3 py-3.5">
          <span className={`mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full ${activity.status === "failed" ? "bg-rose-50 text-rose-600" : "bg-sky-50 text-sky-700"}`}>
            {activity.kind === "quiz_submission" ? <CircleHelp className="size-4" /> : activity.kind === "ai_request" ? <Sparkles className="size-4" /> : <Users className="size-4" />}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-slate-800">{activity.summary}</p>
            <p className="mt-1 text-xs text-slate-400">{new Date(activity.created_at).toLocaleString()}</p>
          </div>
          {activity.kind === "ai_request" && activity.latency_ms != null && (
            <span className="shrink-0 text-xs tabular-nums text-slate-500">{activity.latency_ms} ms</span>
          )}
        </div>
      ))}
    </div>
  );
}

export default function AdvancedAdminDashboard() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<DashboardTab>("Overview");
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [students, setStudents] = useState<AdminStudent[]>([]);
  const [logs, setLogs] = useState<AdminLogs | null>(null);
  const [tracks, setTracks] = useState<AdminTrack[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedTrackId, setSelectedTrackId] = useState<number | null>(null);
  const [selectedModuleId, setSelectedModuleId] = useState<number | null>(null);
  const [selectedLessonId, setSelectedLessonId] = useState<number | null>(null);
  const [trackDraft, setTrackDraft] = useState<AdminTrackPayload | null>(null);
  const [moduleDraft, setModuleDraft] = useState<AdminModulePayload | null>(null);
  const [lessonDraft, setLessonDraft] = useState<AdminLessonPayload | null>(null);
  const [newTrackName, setNewTrackName] = useState("");
  const [newTrackDescription, setNewTrackDescription] = useState("");
  const [newModuleTitle, setNewModuleTitle] = useState("");
  const [newLessonTitle, setNewLessonTitle] = useState("");

  const loadDashboard = async (quiet = false) => {
    if (quiet) setIsRefreshing(true);
    else setIsLoading(true);
    setError(null);
    try {
      const [nextStats, nextStudents, nextLogs, nextTracks] = await Promise.all([
        adminDashboardService.getStats(),
        adminDashboardService.getStudents(),
        adminDashboardService.getLogs(),
        adminDashboardService.getTracks(),
      ]);
      setStats(nextStats);
      setStudents(nextStudents);
      setLogs(nextLogs);
      setTracks(nextTracks);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    void loadDashboard();
  }, []);

  const selectedTrack = tracks.find((track) => track.id === selectedTrackId) ?? null;
  const modules = selectedTrack?.modules ?? [];
  const selectedModule = modules.find((module) => module.id === selectedModuleId) ?? null;
  const lessons = selectedModule?.lessons ?? [];
  const selectedLesson = lessons.find((lesson) => lesson.id === selectedLessonId) ?? null;
  const filteredStudents = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return students;
    return students.filter((student) =>
      `${student.full_name} ${student.email}`.toLowerCase().includes(needle),
    );
  }, [search, students]);

  useEffect(() => {
    if (!tracks.length) {
      setSelectedTrackId(null);
      return;
    }
    if (!selectedTrackId || !tracks.some((track) => track.id === selectedTrackId)) {
      setSelectedTrackId(tracks[0].id);
    }
  }, [selectedTrackId, tracks]);

  useEffect(() => {
    if (!modules.length) {
      setSelectedModuleId(null);
      return;
    }
    if (!selectedModuleId || !modules.some((module) => module.id === selectedModuleId)) {
      setSelectedModuleId(modules[0].id);
    }
  }, [modules, selectedModuleId]);

  useEffect(() => {
    if (!lessons.length) {
      setSelectedLessonId(null);
      return;
    }
    if (!selectedLessonId || !lessons.some((lesson) => lesson.id === selectedLessonId)) {
      setSelectedLessonId(lessons[0].id);
    }
  }, [lessons, selectedLessonId]);

  useEffect(() => {
    if (selectedTrack) {
      setTrackDraft({
        name: selectedTrack.name,
        slug: selectedTrack.slug,
        description: selectedTrack.description,
        ordering: selectedTrack.ordering,
        is_active: selectedTrack.is_active,
        is_premium: selectedTrack.is_premium,
        price: selectedTrack.price,
        currency: selectedTrack.currency,
      });
    } else setTrackDraft(null);
  }, [selectedTrack]);

  useEffect(() => {
    if (selectedModule) {
      setModuleDraft({
        title: selectedModule.title,
        description: selectedModule.description,
        ordering: selectedModule.ordering,
        is_active: selectedModule.is_active,
      });
    } else setModuleDraft(null);
  }, [selectedModule]);

  useEffect(() => {
    if (selectedLesson) {
      setLessonDraft({
        title: selectedLesson.title,
        description: selectedLesson.description,
        content: selectedLesson.content,
        video_url: selectedLesson.video_url,
        ordering: selectedLesson.ordering,
        quiz_data: quizFromLesson(selectedLesson),
      });
    } else setLessonDraft(null);
  }, [selectedLesson]);

  const withSaving = async (action: () => Promise<void>) => {
    setIsSaving(true);
    setError(null);
    setNotice(null);
    try {
      await action();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsSaving(false);
    }
  };

  const refreshContent = async () => {
    const refreshed = await adminDashboardService.getTracks();
    setTracks(refreshed);
  };

  const saveTrack = () => {
    if (!selectedTrack || !trackDraft) return;
    void withSaving(async () => {
      await adminDashboardService.updateTrack(selectedTrack.id, trackDraft);
      await refreshContent();
      setNotice("Track settings saved.");
    });
  };

  const saveModule = () => {
    if (!selectedModule || !moduleDraft) return;
    void withSaving(async () => {
      await adminDashboardService.updateModule(selectedModule.id, moduleDraft);
      await refreshContent();
      setNotice("Module settings saved.");
    });
  };

  const saveLesson = () => {
    if (!selectedLesson || !lessonDraft) return;
    void withSaving(async () => {
      await adminDashboardService.updateLesson(selectedLesson.id, lessonDraft);
      await refreshContent();
      setNotice("Lesson content and quiz saved.");
    });
  };

  const createTrack = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const name = newTrackName.trim();
    if (!name) return;
    void withSaving(async () => {
      const slug = name.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      const created = await adminDashboardService.createTrack({
        name,
        slug,
        description: newTrackDescription || null,
        ordering: tracks.length + 1,
        is_active: true,
        is_premium: false,
        price: 0,
        currency: "EGP",
      });
      await refreshContent();
      setSelectedTrackId(created.id);
      setNewTrackName("");
      setNewTrackDescription("");
      setNotice("Track created.");
    });
  };

  const createModule = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedTrack || !newModuleTitle.trim()) return;
    void withSaving(async () => {
      const created = await adminDashboardService.createModule(selectedTrack.id, {
        title: newModuleTitle.trim(),
        description: null,
        ordering: modules.length + 1,
        is_active: true,
      });
      await refreshContent();
      setSelectedModuleId(created.id);
      setNewModuleTitle("");
      setNotice("Module created.");
    });
  };

  const createLesson = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedModule || !newLessonTitle.trim()) return;
    void withSaving(async () => {
      const created = await adminDashboardService.createLesson(selectedModule.id, {
        title: newLessonTitle.trim(),
        description: null,
        content: "",
        video_url: null,
        ordering: lessons.length + 1,
        quiz_data: [],
      });
      await refreshContent();
      setSelectedLessonId(created.id);
      setNewLessonTitle("");
      setNotice("Lesson created.");
    });
  };

  const deleteSelected = (kind: "track" | "module" | "lesson") => {
    const target = kind === "track" ? selectedTrack : kind === "module" ? selectedModule : selectedLesson;
    if (!target || !window.confirm(`Delete this ${kind}?`)) return;
    void withSaving(async () => {
      if (kind === "track") await adminDashboardService.deleteTrack(target.id);
      else if (kind === "module") await adminDashboardService.deleteModule(target.id);
      else await adminDashboardService.deleteLesson(target.id);
      await refreshContent();
      setNotice(kind === "track" ? "Track archived." : `${kind[0].toUpperCase()}${kind.slice(1)} deleted.`);
    });
  };

  const updateStudent = (student: AdminStudent, update: { is_active: boolean }) => {
    void withSaving(async () => {
      const updated = await adminDashboardService.updateStudent(student.id, update);
      setStudents((current) => current.map((item) => item.id === updated.id ? updated : item));
      setNotice(`${student.full_name}'s account was updated.`);
    });
  };

  const activateSubscription = (student: AdminStudent) => {
    void withSaving(async () => {
      const result = await adminDashboardService.activateSubscription(student.id);
      setStudents((current) => current.map((item) => item.id === student.id
        ? {
          ...item,
          is_active: result.is_active,
          subscription_active: result.subscription_active,
        }
        : item));
      setNotice(result.activated_enrollments
        ? `Activated ${result.activated_enrollments} subscription(s) for ${student.full_name}.`
        : `${student.full_name}'s account is active; no track enrollments were found to activate.`);
    });
  };

  const addQuizQuestion = () => {
    if (!lessonDraft) return;
    const current = lessonDraft.quiz_data ?? [];
    const nextId = Math.max(0, ...current.map((item) => item.id)) + 1;
    setLessonDraft({
      ...lessonDraft,
      quiz_data: [...current, {
        id: nextId,
        question: "",
        options: ["", "", "", ""],
        correct_index: 0,
        explanation: "",
      }],
    });
  };

  const updateQuizQuestion = (questionId: number, changes: Partial<LessonQuizQuestion>) => {
    if (!lessonDraft) return;
    setLessonDraft({
      ...lessonDraft,
      quiz_data: (lessonDraft.quiz_data ?? []).map((item) =>
        item.id === questionId ? { ...item, ...changes } : item,
      ),
    });
  };

  const removeQuizQuestion = (questionId: number) => {
    if (!lessonDraft) return;
    setLessonDraft({
      ...lessonDraft,
      quiz_data: (lessonDraft.quiz_data ?? []).filter((item) => item.id !== questionId),
    });
  };

  const heading = activeTab === "Overview" ? "Platform overview" : activeTab;

  return (
    <div className="min-h-[calc(100vh-64px)] bg-slate-950 p-3 text-slate-900 sm:p-5 lg:p-6">
      <div className="mx-auto grid min-h-[calc(100vh-112px)] max-w-[1680px] overflow-hidden rounded-2xl border border-slate-800 bg-slate-50 shadow-2xl shadow-black/20 lg:grid-cols-[244px_minmax(0,1fr)]">
        <aside className="flex flex-col border-b border-slate-800 bg-slate-950 p-4 text-slate-200 lg:border-b-0 lg:border-r lg:p-5">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="flex size-10 items-center justify-center rounded-xl bg-sky-500 text-white shadow-lg shadow-sky-950/30">
              <ShieldCheck aria-hidden="true" className="size-5" />
            </div>
            <div>
              <p className="text-sm font-bold text-white">Kodraq Control</p>
              <p className="mt-0.5 text-[10px] uppercase tracking-[0.18em] text-slate-500">Administration</p>
            </div>
          </div>

          <div className="mt-7 hidden px-2 lg:block">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-600">Workspace</p>
          </div>
          <nav aria-label="Admin navigation" className="mt-3 flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible">
            {tabs.map(({ label, icon: Icon }) => (
              <button
                key={label}
                type="button"
                onClick={() => setActiveTab(label)}
                aria-current={activeTab === label ? "page" : undefined}
                className={`flex min-h-10 shrink-0 items-center gap-3 rounded-lg px-3 text-left text-sm font-medium transition ${activeTab === label ? "bg-sky-500/15 text-sky-200 ring-1 ring-inset ring-sky-400/20" : "text-slate-400 hover:bg-white/5 hover:text-white"}`}
              >
                <Icon aria-hidden="true" className="size-[17px]" />
                {label}
                {activeTab === label && <span className="ml-auto hidden size-1.5 rounded-full bg-sky-400 lg:block" />}
              </button>
            ))}
          </nav>

          <div className="mt-auto hidden rounded-xl border border-slate-800 bg-slate-900/80 p-3 lg:block">
            <div className="flex items-center gap-2">
              <span className={`size-2 rounded-full ${stats?.system_health === "degraded" ? "bg-amber-400" : "bg-emerald-400 shadow-[0_0_12px_#34d399]"}`} />
              <span className="text-xs font-semibold text-slate-200">System {stats?.system_health === "degraded" ? "Degraded" : "Online"}</span>
            </div>
            <p className="mt-2 truncate text-[11px] text-slate-500">{user?.email}</p>
          </div>
          <button type="button" onClick={logout} className="mt-3 hidden items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-slate-500 transition hover:bg-white/5 hover:text-slate-200 lg:flex">
            <LogOut aria-hidden="true" className="size-4" /> Sign out
          </button>
        </aside>

        <main className="min-w-0 bg-[#f4f7fb]">
          <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200/80 bg-white/90 px-4 py-3 backdrop-blur-md sm:px-6 lg:px-8">
            <div>
              <p className="text-[11px] font-semibold text-slate-400">Admin workspace <span className="px-1">/</span> {heading}</p>
              <h1 className="mt-1 text-xl font-bold tracking-tight text-slate-950 sm:text-2xl">{heading}</h1>
            </div>
            <div className="flex items-center gap-2">
              <label className="relative hidden md:block">
                <Search aria-hidden="true" className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
                <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search students" className="h-9 w-52 rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-3 text-xs outline-none focus:border-sky-400 focus:bg-white" />
              </label>
              <span className="hidden items-center gap-2 rounded-full border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800 sm:inline-flex">
                <span className="size-1.5 rounded-full bg-emerald-500" /> System {stats?.system_health === "degraded" ? "Degraded" : "Online"}
              </span>
              <Button type="button" variant="outline" size="icon" aria-label="Refresh dashboard" onClick={() => void loadDashboard(true)} disabled={isRefreshing} className="border-slate-200 bg-white">
                <RefreshCw aria-hidden="true" className={`size-4 ${isRefreshing ? "animate-spin" : ""}`} />
              </Button>
            </div>
          </header>

          <div className="space-y-5 p-4 sm:p-6 lg:p-8">
            {error && <div role="alert" className="flex items-start justify-between gap-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><span>{error}</span><button type="button" onClick={() => setError(null)} aria-label="Dismiss error"><X className="size-4" /></button></div>}
            {notice && <div role="status" className="flex items-start justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"><span>{notice}</span><button type="button" onClick={() => setNotice(null)} aria-label="Dismiss notice"><X className="size-4" /></button></div>}
            {isLoading ? (
              <div role="status" className="flex min-h-72 items-center justify-center gap-2 text-sm text-slate-500"><Loader2 aria-hidden="true" className="size-4 animate-spin" /> Loading admin workspace…</div>
            ) : (
              <>
                {activeTab === "Overview" && stats && (
                  <div className="space-y-5">
                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                      <MetricCard label="Total students" value={stats.total_users.toLocaleString()} note="Registered student accounts" icon={Users} tone="sky" />
                      <MetricCard label="Active sessions" value={stats.active_sessions.toLocaleString()} note="Students active in the last 24 hours" icon={Activity} tone="emerald" />
                      <MetricCard label="Completion velocity" value={stats.completion_velocity.toLocaleString()} note="Lessons completed in the last 7 days" icon={ArrowUpRight} tone="violet" />
                      <MetricCard label="Avg. response time" value={stats.average_response_ms == null ? "—" : `${Math.round(stats.average_response_ms)} ms`} note="Measured AI service requests" icon={Gauge} tone="amber" />
                    </div>

                    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.6fr)_minmax(320px,0.9fr)]">
                      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div><p className="text-sm font-semibold text-slate-900">Student engagement</p><p className="mt-1 text-xs text-slate-500">Monthly active learners · last 6 months</p></div>
                          <span className="rounded-full bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-sky-800">Live data</span>
                        </div>
                        <ActivityChart data={stats.engagement} />
                      </section>
                      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                        <div className="flex items-center justify-between gap-2"><div><p className="text-sm font-semibold text-slate-900">Track progress</p><p className="mt-1 text-xs text-slate-500">Average lesson completion</p></div><BookOpen className="size-4 text-slate-400" /></div>
                        <div className="mt-6 space-y-5">
                          {stats.track_completion.map((track, index) => (
                            <div key={track.track_id}>
                              <div className="mb-2 flex items-center justify-between gap-2"><span className="truncate text-xs font-medium text-slate-700">Track {track.ordering || index + 1} · {track.track_name}</span><span className="text-xs font-bold tabular-nums text-slate-900">{track.completion_rate}%</span></div>
                              <div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full transition-all ${index === 0 ? "bg-sky-500" : index === 1 ? "bg-emerald-500" : "bg-violet-500"}`} style={{ width: `${Math.min(100, track.completion_rate)}%` }} /></div>
                            </div>
                          ))}
                          {!stats.track_completion.length && <p className="py-6 text-center text-xs text-slate-400">Progress data will appear after learners start lessons.</p>}
                        </div>
                        <div className="mt-7 border-t border-slate-100 pt-4"><div className="flex items-center justify-between text-xs"><span className="text-slate-500">Overall completion</span><span className="font-semibold text-slate-800">{stats.completion_rate}%</span></div></div>
                      </section>
                    </div>

                    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
                      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                        <div className="flex items-center justify-between"><div><p className="text-sm font-semibold text-slate-900">Recent platform activity</p><p className="mt-1 text-xs text-slate-500">Enrollments, quizzes, and tutor requests</p></div><button type="button" onClick={() => setActiveTab("Analytics")} className="text-xs font-semibold text-sky-700 hover:text-sky-900">View logs</button></div>
                        <ActivityList activities={logs?.activities ?? []} />
                      </section>
                      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                        <div className="flex items-center gap-2"><Database className="size-4 text-emerald-600" /><p className="text-sm font-semibold text-slate-900">System health</p></div>
                        <div className="mt-5 flex items-center justify-between rounded-lg bg-slate-50 p-4"><div><p className="text-sm font-semibold text-slate-800">API and database</p><p className="mt-1 text-xs text-slate-500">Last checked just now</p></div><span className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-semibold ${stats.system_health === "online" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}`}><span className={`size-1.5 rounded-full ${stats.system_health === "online" ? "bg-emerald-500" : "bg-amber-500"}`} />{stats.system_health}</span></div>
                        <div className="mt-3 grid grid-cols-2 gap-3"><div className="rounded-lg border border-slate-100 p-3"><p className="text-[11px] text-slate-500">Active tracks</p><p className="mt-1 text-xl font-bold text-slate-900">{stats.active_tracks}</p></div><div className="rounded-lg border border-slate-100 p-3"><p className="text-[11px] text-slate-500">Published lessons</p><p className="mt-1 text-xl font-bold text-slate-900">{stats.total_lessons}</p></div></div>
                      </section>
                    </div>
                  </div>
                )}

                {activeTab === "Students" && (
                    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-5">
                      <div><p className="text-sm font-semibold text-slate-900">Student accounts</p><p className="mt-1 text-xs text-slate-500">Manage access and activate track subscriptions without removing learning history.</p></div>
                      <label className="relative md:hidden"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search students" className={`${inputClass} pl-9`} /></label>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[840px] text-left text-sm">
                        <thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3">Student</th><th className="px-5 py-3">Joined</th><th className="px-5 py-3">Progress</th><th className="px-5 py-3">Role</th><th className="px-5 py-3">Status</th><th className="px-5 py-3 text-right">Actions</th></tr></thead>
                        <tbody className="divide-y divide-slate-100">
                          {filteredStudents.map((student) => (
                            <tr key={student.id} className="hover:bg-slate-50/70">
                              <td className="px-5 py-4"><p className="font-semibold text-slate-900">{student.full_name}</p><p className="mt-1 text-xs text-slate-500">{student.email}</p></td>
                              <td className="px-5 py-4 text-xs text-slate-600">{new Date(student.joined_at).toLocaleDateString()}</td>
                              <td className="px-5 py-4"><div className="flex items-center gap-2"><div className="h-1.5 w-24 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-sky-500" style={{ width: `${Math.min(100, student.progress_percentage)}%` }} /></div><span className="text-xs tabular-nums text-slate-600">{student.progress_percentage}%</span></div></td>
                              <td className="px-5 py-4"><span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${student.role === "admin" ? "bg-violet-50 text-violet-700" : "bg-slate-100 text-slate-600"}`}>{student.role}</span></td>
                              <td className="px-5 py-4"><span className={`inline-flex items-center gap-1.5 text-xs font-medium ${student.is_active ? "text-emerald-700" : "text-rose-700"}`}><span className={`size-1.5 rounded-full ${student.is_active ? "bg-emerald-500" : "bg-rose-500"}`} />{student.is_active ? "Active" : "Blocked"}</span></td>
                              <td className="px-5 py-4 text-right"><div className="inline-flex flex-wrap justify-end gap-2">{student.role === "student" ? <><Button size="sm" variant={student.is_active ? "outline" : "default"} disabled={isSaving} onClick={() => updateStudent(student, { is_active: !student.is_active })}>{student.is_active ? "Block" : "Unblock"}</Button><Button size="sm" disabled={isSaving || student.subscription_active} onClick={() => activateSubscription(student)} className={student.subscription_active ? "bg-emerald-100 text-emerald-800 hover:bg-emerald-100" : "bg-emerald-600 text-white hover:bg-emerald-700"}>{student.subscription_active ? <Check aria-hidden="true" className="size-4" /> : <ShieldCheck aria-hidden="true" className="size-4" />}{student.subscription_active ? "Active Subscription" : "Activate Sub"}</Button></> : <span className="text-xs font-semibold text-violet-700">Platform admin</span>}</div></td>
                            </tr>
                          ))}
                          {!filteredStudents.length && <tr><td colSpan={6} className="px-5 py-12 text-center text-sm text-slate-500">No matching students.</td></tr>}
                        </tbody>
                      </table>
                    </div>
                  </section>
                )}

                {activeTab === "Content CMS" && (
                  <div className="space-y-5">
                    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
                      <div className="grid gap-3 md:grid-cols-3">
                        <label><span className={labelClass}>Track</span><div className="relative"><select className={`${inputClass} appearance-none pr-9`} value={selectedTrackId ?? ""} onChange={(event) => setSelectedTrackId(Number(event.target.value) || null)}><option value="">Select track</option>{tracks.map((track) => <option key={track.id} value={track.id}>{track.name}</option>)}</select><ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /></div></label>
                        <label><span className={labelClass}>Module</span><div className="relative"><select className={`${inputClass} appearance-none pr-9`} value={selectedModuleId ?? ""} onChange={(event) => setSelectedModuleId(Number(event.target.value) || null)} disabled={!modules.length}><option value="">Select module</option>{modules.map((module) => <option key={module.id} value={module.id}>{module.ordering}. {module.title}</option>)}</select><ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /></div></label>
                        <label><span className={labelClass}>Lesson</span><div className="relative"><select className={`${inputClass} appearance-none pr-9`} value={selectedLessonId ?? ""} onChange={(event) => setSelectedLessonId(Number(event.target.value) || null)} disabled={!lessons.length}><option value="">Select lesson</option>{lessons.map((lesson) => <option key={lesson.id} value={lesson.id}>{lesson.ordering}. {lesson.title}</option>)}</select><ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /></div></label>
                      </div>
                      <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
                        <details className="group"><summary className="flex h-8 cursor-pointer list-none items-center gap-1.5 rounded-md border border-slate-200 px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50"><Plus className="size-3.5" />New track</summary><form onSubmit={createTrack} className="mt-3 grid min-w-[min(88vw,600px)] gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 sm:grid-cols-[1fr_1fr_auto]"><input className={inputClass} value={newTrackName} onChange={(event) => setNewTrackName(event.target.value)} placeholder="Track name" required /><input className={inputClass} value={newTrackDescription} onChange={(event) => setNewTrackDescription(event.target.value)} placeholder="Description" /><Button size="sm" disabled={isSaving}><Plus className="size-4" />Create</Button></form></details>
                        <details className="group"><summary className="flex h-8 cursor-pointer list-none items-center gap-1.5 rounded-md border border-slate-200 px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50" aria-disabled={!selectedTrack}><Plus className="size-3.5" />New module</summary><form onSubmit={createModule} className="mt-3 flex min-w-[min(88vw,500px)] gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3"><input className={inputClass} value={newModuleTitle} onChange={(event) => setNewModuleTitle(event.target.value)} placeholder="Module title" required disabled={!selectedTrack} /><Button size="sm" disabled={isSaving || !selectedTrack}><Plus className="size-4" />Create</Button></form></details>
                        <details className="group"><summary className="flex h-8 cursor-pointer list-none items-center gap-1.5 rounded-md border border-slate-200 px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50" aria-disabled={!selectedModule}><Plus className="size-3.5" />New lesson</summary><form onSubmit={createLesson} className="mt-3 flex min-w-[min(88vw,500px)] gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3"><input className={inputClass} value={newLessonTitle} onChange={(event) => setNewLessonTitle(event.target.value)} placeholder="Lesson title" required disabled={!selectedModule} /><Button size="sm" disabled={isSaving || !selectedModule}><Plus className="size-4" />Create</Button></form></details>
                      </div>
                    </section>

                    {selectedTrack && trackDraft && (
                      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                        <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-semibold text-slate-900">Track settings</p><p className="mt-1 text-xs text-slate-500">Edit metadata and publishing state.</p></div><div className="flex gap-2"><Button size="sm" variant="outline" disabled={isSaving} onClick={() => deleteSelected("track")}><Trash2 className="size-3.5" />Archive</Button><Button size="sm" disabled={isSaving} onClick={saveTrack}><Save className="size-3.5" />Save track</Button></div></div>
                        <div className="grid gap-3 md:grid-cols-2"><label><span className={labelClass}>Name</span><input className={inputClass} value={trackDraft.name} onChange={(event) => setTrackDraft({ ...trackDraft, name: event.target.value })} /></label><label><span className={labelClass}>Slug</span><input className={inputClass} value={trackDraft.slug} onChange={(event) => setTrackDraft({ ...trackDraft, slug: event.target.value })} /></label><label className="md:col-span-2"><span className={labelClass}>Description</span><textarea rows={2} className={inputClass} value={trackDraft.description ?? ""} onChange={(event) => setTrackDraft({ ...trackDraft, description: event.target.value || null })} /></label></div>
                        <label className="mt-4 flex w-fit cursor-pointer items-center gap-3"><input type="checkbox" checked={trackDraft.is_active} onChange={(event) => setTrackDraft({ ...trackDraft, is_active: event.target.checked })} className="size-4 accent-sky-600" /><span><span className="block text-xs font-semibold text-slate-800">Track published</span><span className="block text-[11px] text-slate-500">Active tracks appear in student discovery.</span></span></label>
                      </section>
                    )}

                    {selectedModule && moduleDraft && (
                      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                        <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-semibold text-slate-900">Module settings</p><p className="mt-1 text-xs text-slate-500">Ordering {selectedModule.ordering} · {selectedModule.lessons.length} lessons</p></div><div className="flex gap-2"><Button size="sm" variant="outline" disabled={isSaving} onClick={() => deleteSelected("module")}><Trash2 className="size-3.5" />Delete</Button><Button size="sm" disabled={isSaving} onClick={saveModule}><Save className="size-3.5" />Save module</Button></div></div>
                        <div className="grid gap-3 md:grid-cols-2"><label><span className={labelClass}>Title</span><input className={inputClass} value={moduleDraft.title} onChange={(event) => setModuleDraft({ ...moduleDraft, title: event.target.value })} /></label><label><span className={labelClass}>Ordering</span><input type="number" className={inputClass} value={moduleDraft.ordering} onChange={(event) => setModuleDraft({ ...moduleDraft, ordering: Number(event.target.value) })} /></label><label className="md:col-span-2"><span className={labelClass}>Description</span><textarea rows={2} className={inputClass} value={moduleDraft.description ?? ""} onChange={(event) => setModuleDraft({ ...moduleDraft, description: event.target.value || null })} /></label></div>
                      </section>
                    )}

                    {selectedLesson && lessonDraft && (
                      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                        <div className="mb-5 flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-semibold text-slate-900">Lesson editor</p><p className="mt-1 text-xs text-slate-500">Markdown, video embed, and interactive quiz data.</p></div><div className="flex gap-2"><Button size="sm" variant="outline" disabled={isSaving} onClick={() => deleteSelected("lesson")}><Trash2 className="size-3.5" />Delete lesson</Button><Button size="sm" disabled={isSaving} onClick={saveLesson}><Save className="size-3.5" />Save lesson</Button></div></div>
                        <div className="grid gap-3 md:grid-cols-2"><label><span className={labelClass}>Title</span><input className={inputClass} value={lessonDraft.title} onChange={(event) => setLessonDraft({ ...lessonDraft, title: event.target.value })} /></label><label><span className={labelClass}>Ordering</span><input type="number" className={inputClass} value={lessonDraft.ordering} onChange={(event) => setLessonDraft({ ...lessonDraft, ordering: Number(event.target.value) })} /></label><label className="md:col-span-2"><span className={labelClass}>Track-card description</span><textarea rows={2} className={inputClass} value={lessonDraft.description ?? ""} onChange={(event) => setLessonDraft({ ...lessonDraft, description: event.target.value || null })} /></label><label className="md:col-span-2"><span className={labelClass}><Video className="mr-1 inline size-3.5" />YouTube embed URL</span><input className={inputClass} placeholder="https://www.youtube.com/embed/..." value={lessonDraft.video_url ?? ""} onChange={(event) => setLessonDraft({ ...lessonDraft, video_url: event.target.value || null })} /></label><label className="md:col-span-2"><span className={labelClass}><FileText className="mr-1 inline size-3.5" />Markdown content</span><textarea rows={16} className={`${inputClass} min-h-72 resize-y font-mono text-xs leading-6`} value={lessonDraft.content ?? ""} onChange={(event) => setLessonDraft({ ...lessonDraft, content: event.target.value })} /></label></div>

                        <div className="mt-7 border-t border-slate-100 pt-5">
                          <div className="mb-4 flex flex-wrap items-center justify-between gap-2"><div><p className="text-sm font-semibold text-slate-900">Interactive quiz</p><p className="mt-1 text-xs text-slate-500">Each item has four options and one correct answer.</p></div><Button type="button" size="sm" variant="outline" onClick={addQuizQuestion}><Plus className="size-3.5" />Add question</Button></div>
                          <div className="space-y-4">
                            {(lessonDraft.quiz_data ?? []).map((item, questionIndex) => (
                              <fieldset key={item.id} className="rounded-lg border border-slate-200 bg-slate-50/70 p-4">
                                <legend className="px-1 text-xs font-bold text-slate-700">Question {questionIndex + 1}</legend>
                                <div className="flex items-start gap-2"><textarea rows={2} className={`${inputClass} flex-1`} aria-label={`Question ${questionIndex + 1}`} value={item.question} onChange={(event) => updateQuizQuestion(item.id, { question: event.target.value })} placeholder="Question text" /><Button type="button" variant="ghost" size="icon-sm" aria-label={`Delete question ${questionIndex + 1}`} onClick={() => removeQuizQuestion(item.id)}><Trash2 className="size-4 text-rose-600" /></Button></div>
                                <div className="mt-3 grid gap-2 md:grid-cols-2">{item.options.map((option, optionIndex) => <label key={optionIndex} className={`flex items-center gap-2 rounded-md border p-2 ${item.correct_index === optionIndex ? "border-emerald-300 bg-emerald-50" : "border-slate-200 bg-white"}`}><input type="radio" name={`correct-${item.id}`} checked={item.correct_index === optionIndex} onChange={() => updateQuizQuestion(item.id, { correct_index: optionIndex })} aria-label={`Mark option ${optionIndex + 1} correct`} className="size-4 accent-emerald-600" /><input className="min-w-0 flex-1 border-0 bg-transparent text-xs outline-none" value={option} onChange={(event) => { const options = [...item.options]; options[optionIndex] = event.target.value; updateQuizQuestion(item.id, { options }); }} placeholder={`Option ${optionIndex + 1}`} /></label>)}</div>
                                <label className="mt-3 block"><span className={labelClass}>Explanation</span><textarea rows={2} className={inputClass} value={item.explanation} onChange={(event) => updateQuizQuestion(item.id, { explanation: event.target.value })} /></label>
                              </fieldset>
                            ))}
                            {!lessonDraft.quiz_data?.length && <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500">No quiz questions yet. Add one to build a comprehension quiz.</div>}
                          </div>
                        </div>
                      </section>
                    )}
                  </div>
                )}

                {activeTab === "Analytics" && (
                  <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(340px,0.8fr)]">
                    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><div className="flex items-center justify-between"><div><p className="text-sm font-semibold text-slate-900">Engagement analytics</p><p className="mt-1 text-xs text-slate-500">Monthly active students · six-month view</p></div><BarChart3 className="size-4 text-sky-700" /></div>{stats && <EngagementBars data={stats.engagement} />}<div className="mt-7 grid grid-cols-2 gap-3"><div className="rounded-lg bg-slate-50 p-4"><p className="text-xs text-slate-500">Completion rate</p><p className="mt-1 text-2xl font-bold text-slate-900">{stats?.completion_rate ?? 0}%</p></div><div className="rounded-lg bg-slate-50 p-4"><p className="text-xs text-slate-500">Weekly completions</p><p className="mt-1 text-2xl font-bold text-slate-900">{stats?.completion_velocity ?? 0}</p></div></div></section>
                    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><div className="flex items-center justify-between"><div><p className="text-sm font-semibold text-slate-900">AI tutor usage</p><p className="mt-1 text-xs text-slate-500">Recorded provider requests</p></div><Sparkles className="size-4 text-violet-600" /></div><div className="mt-5 grid grid-cols-2 gap-3"><div className="rounded-lg border border-slate-100 p-3"><p className="text-xs text-slate-500">Requests</p><p className="mt-1 text-xl font-bold text-slate-900">{logs?.ai_usage.requests ?? 0}</p></div><div className="rounded-lg border border-slate-100 p-3"><p className="text-xs text-slate-500">Failed</p><p className="mt-1 text-xl font-bold text-rose-700">{logs?.ai_usage.failed_requests ?? 0}</p></div><div className="rounded-lg border border-slate-100 p-3"><p className="text-xs text-slate-500">Avg latency</p><p className="mt-1 text-xl font-bold text-slate-900">{logs?.ai_usage.average_latency_ms == null ? "—" : `${Math.round(logs.ai_usage.average_latency_ms)} ms`}</p></div><div className="rounded-lg border border-slate-100 p-3"><p className="text-xs text-slate-500">Tokens</p><p className="mt-1 text-xl font-bold text-slate-900">{(logs?.ai_usage.total_tokens ?? 0).toLocaleString()}</p></div></div></section>
                    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm xl:col-span-2 sm:p-6"><div className="mb-2 flex items-center justify-between"><div><p className="text-sm font-semibold text-slate-900">Activity log</p><p className="mt-1 text-xs text-slate-500">Latest enrollment, quiz, and AI events</p></div><Activity className="size-4 text-slate-400" /></div><ActivityList activities={logs?.activities ?? []} /></section>
                  </div>
                )}

                {activeTab === "Settings" && (
                  <div className="mx-auto max-w-3xl space-y-5">
                    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><div className="flex items-center gap-3"><span className="flex size-10 items-center justify-center rounded-lg bg-sky-50 text-sky-700"><Settings2 className="size-5" /></span><div><h2 className="text-sm font-semibold text-slate-900">Platform controls</h2><p className="mt-1 text-xs text-slate-500">Changes update the live track record.</p></div></div>
                      <div className="mt-5 divide-y divide-slate-100">{tracks.map((track) => <div key={track.id} className="flex flex-wrap items-center justify-between gap-3 py-4"><div className="min-w-0"><p className="truncate text-sm font-medium text-slate-800">{track.name}</p><p className="mt-1 text-xs text-slate-500">Student track visibility</p></div><button type="button" role="switch" aria-checked={track.is_active} disabled={isSaving} onClick={() => void withSaving(async () => { await adminDashboardService.updateTrack(track.id, { is_active: !track.is_active }); await refreshContent(); setNotice(`${track.name} ${track.is_active ? "archived" : "published"}.`); })} className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition ${track.is_active ? "bg-emerald-500" : "bg-slate-300"}`}><span className={`inline-block size-4 rounded-full bg-white shadow transition-transform ${track.is_active ? "translate-x-6" : "translate-x-1"}`} /></button></div>)}</div>
                    </section>
                    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><div className="flex items-center gap-3"><span className="flex size-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700"><Database className="size-5" /></span><div><h2 className="text-sm font-semibold text-slate-900">System status</h2><p className="mt-1 text-xs text-slate-500">Live health reported by the backend.</p></div></div><div className="mt-5 flex items-center justify-between rounded-lg bg-slate-50 p-4"><div><p className="text-sm font-medium text-slate-800">Application database</p><p className="mt-1 text-xs text-slate-500">Admin API connectivity check</p></div><span className={`rounded-full px-3 py-1 text-xs font-semibold ${stats?.system_health === "online" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}`}>{stats?.system_health ?? "unknown"}</span></div></section>
                  </div>
                )}
              </>
            )}
          </div>
          <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 bg-white px-4 py-3 text-[11px] text-slate-400 sm:px-6 lg:px-8"><span>Kodraq Digital · Admin console</span><span className="inline-flex items-center gap-1.5"><ShieldCheck className="size-3.5" />Signed in as {user?.full_name ?? user?.email}</span></footer>
        </main>
      </div>
    </div>
  );
}