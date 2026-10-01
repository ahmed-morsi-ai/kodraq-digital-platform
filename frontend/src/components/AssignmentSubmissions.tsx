import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import AssignmentReviewPanel from "@/components/AssignmentReviewPanel";
import SubmissionFiles from "@/components/SubmissionFiles";
import SubmissionForm from "@/components/SubmissionForm";
import SubmissionHistory from "@/components/SubmissionHistory";
import { Button } from "@/components/ui/button";
import { isRepositoryUrl, statusLabel, submissionError } from "@/lib/submissions";
import { submissionService } from "@/services/submission.service";
import type { Assignment } from "@/types/assignment";
import type { Submission, SubmissionDetail } from "@/types/submission";

export default function AssignmentSubmissions({ assignment, onBusy }: { assignment: Assignment; onBusy: (value: boolean) => void }) {
  const { user } = useAuth();
  const role = user?.role_name?.toLowerCase() ?? "student";
  const manager = Boolean(user?.is_superuser || role === "admin" || role === "instructor");
  const student = Boolean(user && !manager && role === "student");
  const [rows, setRows] = useState<Submission[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<SubmissionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    if (!manager && !student) return;
    const controller = new AbortController();
    async function load() {
      const items: Submission[] = [];
      for (let skip = 0; !controller.signal.aborted; skip += 100) {
        const page = await (manager ? submissionService.listForAssignment : submissionService.listMine)(assignment.id, skip, controller.signal);
        items.push(...page);
        if (page.length < 100) break;
      }
      const selected = items.find((row) => row.id === selectedId) ?? items[0];
      const record = selected ? await submissionService.get(selected.id, controller.signal) : null;
      if (!controller.signal.aborted) { setRows(items); setDetail(record); setLoading(false); }
    }
    void load().catch((requestError: unknown) => {
      if (!controller.signal.aborted) { setError(submissionError(requestError)); setLoading(false); }
    });
    return () => controller.abort();
  }, [assignment.id, user?.id, manager, student, selectedId, revision]);

  function changeBusy(value: boolean) { setBusy(value); onBusy(value); }
  function refresh(id: number | null = selectedId, message: string | null = null) {
    setSelectedId(id); setNotice(message); setError(null); setLoading(true); setDetail(null); setRevision((value) => value + 1);
  }
  if (!manager && !student) return null;
  const editable = student && assignment.is_active && (!detail || detail.status === "DRAFT" || detail.status === "CHANGES_REQUIRED");
  const reviewable = manager && detail && (detail.status === "SUBMITTED" || detail.status === "UNDER_REVIEW");

  return <section className="space-y-5 border-t pt-5" aria-label={manager ? "Assignment submissions" : "Your assignment submission"}>
    <div className="flex items-center justify-between gap-3">
      <h3 className="font-semibold">{manager ? "Student submissions" : "Your work"}</h3>
      <Button size="sm" variant="outline" disabled={busy || loading} onClick={() => refresh()}>Refresh</Button>
    </div>
    {notice && <p role="status" className="rounded-lg bg-green-50 p-3 text-sm text-green-800">{notice}</p>}
    {error && <div role="alert" className="space-y-2 text-sm text-red-700"><p>{error}</p><Button variant="outline" disabled={busy} onClick={() => refresh()}>Retry</Button></div>}
    {loading && <p role="status" className="text-sm text-slate-500">Loading submissions…</p>}
    {!loading && !error && <>
      {rows.length > 0 && <label className="block space-y-2 text-sm font-medium">
        <span>{manager ? "Select a student submission" : "Select a submission"}</span>
        <select value={detail?.id ?? ""} disabled={busy} onChange={(event) => refresh(Number(event.target.value))} className="w-full rounded-lg border bg-white p-2 text-sm">
          {rows.map((row) => <option key={row.id} value={row.id}>{manager ? `Student #${row.user_id} · ` : ""}Submission #{row.id} · {statusLabel(row.status)}</option>)}
        </select>
      </label>}
      {detail && <>
        <div className="flex flex-wrap items-center gap-3 text-sm"><span className="rounded-full bg-blue-50 px-3 py-1 font-medium capitalize text-blue-800">{statusLabel(detail.status)}</span>{detail.grade !== null && <strong>Grade: {detail.grade}</strong>}</div>
        {!editable && <>
          {detail.github_url && (isRepositoryUrl(detail.github_url) ? <a className="block break-all text-sm text-blue-700 underline" href={detail.github_url} target="_blank" rel="noopener noreferrer">{detail.github_url}</a> : <p className="break-all text-sm">Repository: {detail.github_url}</p>)}
          {detail.content && <p className="whitespace-pre-wrap break-words text-sm text-slate-700">{detail.content}</p>}
        </>}
        <SubmissionFiles submission={detail} editable={editable} busy={busy} onBusy={changeBusy} onRemoved={(fileId) => setDetail({ ...detail, files: detail.files.filter((file) => file.id !== fileId) })} />
      </>}
      {editable && <SubmissionForm key={detail?.id ?? "new"} assignmentId={assignment.id} submission={detail} busy={busy} onBusy={changeBusy} onSaved={refresh} />}
      {manager && !detail && <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600">No submissions yet.</p>}
      {student && !editable && <p className="text-sm text-slate-500">{assignment.is_active ? "Your work is read-only while under review or after a final decision." : "This assignment is inactive."}</p>}
      {reviewable && <AssignmentReviewPanel key={`${detail.id}-${detail.status}`} submission={detail} busy={busy} onBusy={changeBusy} onReviewed={refresh} />}
      {detail && <SubmissionHistory submission={detail} />}
    </>}
  </section>;
}
