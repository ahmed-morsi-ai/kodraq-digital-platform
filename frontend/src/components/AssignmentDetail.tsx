import { lazy, Suspense, useEffect, useState } from "react";
import { Loader2, Pencil, Trash2, Upload } from "lucide-react";
import AssignmentDialog from "@/components/AssignmentDialog";
import { Button } from "@/components/ui/button";
import { assignmentContext, assignmentError } from "@/lib/assignments";
import { assignmentService } from "@/services/assignment.service";
import type { Assignment } from "@/types/assignment";
import type { TrackModule } from "@/types/track";

const AssignmentSubmissions = lazy(() => import("@/components/AssignmentSubmissions"));

export default function AssignmentDetail({ id, modules, canManage, isStudent, onClose, onEdit, onDeleted }: {
  id: number;
  modules: TrackModule[];
  canManage: boolean;
  isStudent: boolean;
  onClose: () => void;
  onEdit: (assignment: Assignment) => void;
  onDeleted: (id: number) => void;
}) {
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);
  const [submissionBusy, setSubmissionBusy] = useState(false);
  const [showSubmissions, setShowSubmissions] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    assignmentService.get(id, controller.signal).then((data) => {
      if (!controller.signal.aborted) setAssignment(data);
    }).catch((requestError: unknown) => {
      if (!controller.signal.aborted) setError(assignmentError(requestError));
    });
    return () => controller.abort();
  }, [id, attempt]);

  async function remove() {
    if (!canManage || busy) return;
    setBusy(true);
    setError(null);
    try {
      await assignmentService.remove(id);
      onDeleted(id);
    } catch (requestError) {
      setError(assignmentError(requestError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AssignmentDialog title={assignment?.title ?? "Assignment details"} description={assignment ? assignmentContext(assignment, modules) : "Review the assignment requirements."} onClose={onClose} busy={busy || submissionBusy}>
      {error && <div role="alert" className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}
        {!assignment && <Button variant="outline" className="ml-3" onClick={() => { setError(null); setAttempt((value) => value + 1); }}>Retry</Button>}
      </div>}
      {!assignment && !error && <p role="status" className="flex items-center gap-2 text-sm"><Loader2 className="size-4 animate-spin" /> Loading assignment…</p>}
      {assignment && <div className="space-y-5">
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-violet-50 px-3 py-1 capitalize text-violet-700">{assignment.difficulty}</span>
          <span className="rounded-full bg-blue-50 px-3 py-1 text-blue-700">{assignment.is_mandatory ? "Mandatory" : "Optional"}</span>
          <span className="rounded-full bg-slate-100 px-3 py-1">{assignment.is_active ? "Active" : "Inactive"}</span>
        </div>
        <section><h3 className="mb-2 font-semibold">Description</h3><p className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-600">{assignment.description}</p></section>
        <section className="rounded-xl border bg-slate-50 p-4"><h3 className="mb-2 font-semibold">Instructions</h3><p className="whitespace-pre-wrap break-words text-sm leading-6">{assignment.instructions}</p></section>
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div><dt className="text-slate-500">Estimated time</dt><dd>{assignment.estimated_minutes === null ? "Not specified" : `${assignment.estimated_minutes} minutes`}</dd></div>
          <div><dt className="text-slate-500">Due after release</dt><dd>{assignment.due_days === null ? "Not specified" : `${assignment.due_days} days`}</dd></div>
          <div><dt className="text-slate-500">Created</dt><dd>{new Date(assignment.created_at).toLocaleDateString()}</dd></div>
          <div><dt className="text-slate-500">Updated</dt><dd>{new Date(assignment.updated_at).toLocaleDateString()}</dd></div>
        </dl>
        {(isStudent || canManage) && (showSubmissions ? <Suspense fallback={<p role="status">Loading submission workspace...</p>}>
          <AssignmentSubmissions assignment={assignment} onBusy={setSubmissionBusy} />
        </Suspense> : <Button variant="outline" onClick={() => setShowSubmissions(true)}><Upload />{canManage ? "Review submissions" : "View / submit your work"}</Button>)}
        {canManage && (confirmDelete ? <div className="space-y-3 rounded-xl border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-800">Delete “{assignment.title}”? This cannot be undone.</p>
          <div className="flex flex-wrap gap-3">
            <Button disabled={busy || submissionBusy} variant="destructive" onClick={() => void remove()}>{busy ? "Deleting…" : "Confirm delete"}</Button>
            <Button disabled={busy || submissionBusy} variant="outline" onClick={() => { setConfirmDelete(false); setError(null); }}>Cancel deletion</Button>
          </div>
        </div> : <div className="flex gap-3 border-t pt-4">
          <Button disabled={submissionBusy} variant="outline" onClick={() => onEdit(assignment)}><Pencil /> Edit assignment</Button>
          <Button disabled={submissionBusy} variant="destructive" onClick={() => setConfirmDelete(true)}><Trash2 /> Delete assignment</Button>
        </div>)}
      </div>}
    </AssignmentDialog>
  );
}
