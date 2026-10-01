import { useEffect, useState } from "react";
import { ClipboardCheck, Loader2, Plus } from "lucide-react";
import AssignmentDetail from "@/components/AssignmentDetail";
import AssignmentForm from "@/components/AssignmentForm";
import AssignmentList from "@/components/AssignmentList";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { assignmentError, assignmentModuleId } from "@/lib/assignments";
import { assignmentService } from "@/services/assignment.service";
import type { Assignment } from "@/types/assignment";
import type { TrackCurriculum } from "@/types/track";

export default function TrackAssignments({ track, hasEnrollment }: { track: TrackCurriculum; hasEnrollment: boolean }) {
  const { user } = useAuth();
  const role = user?.role_name?.toLowerCase();
  const canManage = Boolean(user?.is_active && (user.is_superuser || role === "admin" || role === "instructor"));
  const isStudent = Boolean(user?.is_active && !canManage && (!role || role === "student"));
  return (
    <section dir="ltr" aria-label="Track assignments" className="space-y-5">
      {user?.is_active && (canManage || hasEnrollment) ? (
        <AssignmentWorkspace key={`${track.id}:${user.id}:${canManage}`} track={track} canManage={canManage} isStudent={isStudent} />
      ) : <div className="rounded-xl border border-blue-200 bg-blue-50 p-5 text-sm text-blue-800">Assignments are available with an active enrollment.</div>}
    </section>
  );
}

function AssignmentWorkspace({ track, canManage, isStudent }: { track: TrackCurriculum; canManage: boolean; isStudent: boolean }) {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [moduleFilter, setModuleFilter] = useState("all");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [editor, setEditor] = useState<Assignment | "create" | null>(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const result: Assignment[] = [];
        const limit = 100;
        let page: Assignment[];
        do {
          page = await assignmentService.list({ track_id: track.id, skip: result.length, limit }, controller.signal);
          result.push(...page);
        } while (page.length === limit && !controller.signal.aborted);
        if (!controller.signal.aborted) setAssignments(result);
      } catch (requestError) {
        if (!controller.signal.aborted) setError(assignmentError(requestError));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [track.id, attempt]);

  const visible = assignments.filter((assignment) => {
    if (!canManage && !assignment.is_active) return false;
    const moduleId = assignmentModuleId(assignment, track.modules);
    return moduleFilter === "all" || (moduleFilter === "track" ? moduleId === null : moduleId === Number(moduleFilter));
  }).sort((a, b) => a.ordering - b.ordering || a.id - b.id);

  function saved(assignment: Assignment) {
    setAssignments((items) => [...items.filter((item) => item.id !== assignment.id), assignment]);
    setEditor(null);
    setSelectedId(assignment.id);
    setNotice("Assignment saved.");
  }

  return <>
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div><h2 className="flex items-center gap-2 text-2xl font-bold text-slate-900"><ClipboardCheck className="size-6 text-violet-600" /> Assignments</h2><p className="mt-1 text-sm text-slate-500">Review requirements and prepare your work.</p></div>
      {canManage && <Button disabled={loading || Boolean(error)} onClick={() => { setSelectedId(null); setEditor("create"); }} className="bg-blue-600 text-white hover:bg-blue-700"><Plus /> Create assignment</Button>}
    </div>
    {notice && <p role="status" className="text-sm text-emerald-700">{notice}</p>}
    {loading ? <p role="status" className="flex items-center gap-2 text-sm text-slate-500"><Loader2 className="size-4 animate-spin" /> Loading assignments…</p> : error ? <div role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}<Button variant="outline" className="ml-3" onClick={() => { setError(null); setLoading(true); setAttempt((value) => value + 1); }}>Retry</Button></div> : <>
      <label className="flex flex-wrap items-center gap-3 text-sm text-slate-600">Filter by module
        <select value={moduleFilter} onChange={(event) => setModuleFilter(event.target.value)} className="max-w-full rounded-lg border bg-white px-3 py-2">
          <option value="all">All assignments</option><option value="track">Track-wide assignments</option>
          {track.modules.map((module) => <option key={module.id} value={module.id}>{module.title}</option>)}
        </select><span>{visible.length} {visible.length === 1 ? "assignment" : "assignments"}</span>
      </label>
      <AssignmentList assignments={visible} modules={track.modules} onSelect={(id) => { setNotice(""); setSelectedId(id); }} />
    </>}
    {selectedId !== null && <AssignmentDetail key={selectedId} id={selectedId} modules={track.modules} canManage={canManage} isStudent={isStudent} onClose={() => setSelectedId(null)} onEdit={(assignment) => { if (canManage) { setSelectedId(null); setEditor(assignment); } }} onDeleted={(id) => { setAssignments((items) => items.filter((item) => item.id !== id)); setSelectedId(null); setNotice("Assignment deleted."); }} />}
    {canManage && editor !== null && <AssignmentForm key={editor === "create" ? "create" : editor.id} assignment={editor === "create" ? undefined : editor} track={track} onClose={() => setEditor(null)} onSaved={saved} />}
  </>;
}
