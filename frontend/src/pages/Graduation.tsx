import { useEffect, useRef, useState } from "react";
import { ArrowLeft, GraduationCap, Loader2, RefreshCw } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { GraduationGates, GraduationRecord } from "@/components/GraduationGates";
import GraduationRecords from "@/components/GraduationRecords";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { canFinalizeGraduation, graduationError, graduationRole, studentIdInput } from "@/lib/graduation";
import { graduationService } from "@/services/graduation.service";
import type { User } from "@/types/auth";
import type { GraduationEligibility, GraduationResult } from "@/types/graduation";

export function GraduationActions({ user, eligibility, busy, onFinalize }: {
  user: User; eligibility: GraduationEligibility; busy: boolean; onFinalize: () => void;
}) {
  if (graduationRole(user) !== "manager") return <p className="text-sm text-slate-600">Your instructor or administrator finalizes graduation after all gates pass.</p>;
  const self = String(user.id) === String(eligibility.user_id);
  return <div className="rounded-xl border border-blue-200 bg-blue-50 p-5">
    <h2 className="font-semibold text-slate-900">Staff finalization</h2>
    <p className="mt-2 mb-4 text-sm text-slate-700">{self ? "You cannot finalize your own graduation." : eligibility.status === "GRADUATED" ? "Graduation has already been finalized." : !eligibility.is_eligible ? "Resolve the failed gates and refresh eligibility before finalizing." : `Finalize graduation for student #${eligibility.user_id} in track #${eligibility.track_id}. All gates will be checked again before the decision is saved.`}</p>
    <Button type="button" disabled={busy || !canFinalizeGraduation(user, eligibility)} onClick={onFinalize}>
      {busy && <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />}{busy ? "Finalizing..." : "Finalize Graduation"}
    </Button>
  </div>;
}

function EligibilityWorkspace({ user, trackId, studentId, onFinalized }: {
  user: User; trackId: number; studentId?: number; onFinalized: () => void;
}) {
  const [eligibility, setEligibility] = useState<GraduationEligibility | null>(null);
  const [record, setRecord] = useState<GraduationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const writing = useRef(false);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    const request = new AbortController();
    controller.current = request;
    graduationService.getEligibility(trackId, studentId, request.signal).then((data) => {
      if (request.signal.aborted) return;
      setEligibility(data);
      setRecord(data.finalized_result);
    }).catch((reason: unknown) => {
      if (!request.signal.aborted) setError(graduationError(reason));
    }).finally(() => {
      if (!request.signal.aborted) setLoading(false);
    });
    return () => request.abort();
  }, [trackId, studentId, revision]);

  function refresh() {
    if (writing.current) return;
    setEligibility(null);
    setError(null);
    setLoading(true);
    setRevision((value) => value + 1);
  }

  async function finalize() {
    const request = controller.current;
    if (!eligibility || writing.current || loading || !request || request.signal.aborted || !canFinalizeGraduation(user, eligibility)) return;
    writing.current = true;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const saved = await graduationService.finalize(trackId, eligibility.user_id);
      if (request.signal.aborted) return;
      setRecord(saved);
      setNotice(saved.status === "GRADUATED" ? "Graduation finalized. The saved record is shown below." : "The latest evaluation did not pass all gates. A not-graduated decision was saved.");
      setEligibility(null);
      setLoading(true);
      setRevision((value) => value + 1);
      onFinalized();
    } catch (reason) {
      if (request.signal.aborted) return;
      setEligibility(null);
      setError(`Finalization could not be confirmed. ${graduationError(reason)} Refresh current eligibility before trying again.`);
    } finally {
      writing.current = false;
      if (!request.signal.aborted) setBusy(false);
    }
  }

  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-lg font-semibold text-slate-900">{studentId ? `Student #${studentId}` : "Your graduation progress"}</h2>
      <Button type="button" variant="outline" disabled={busy || loading} onClick={refresh}><RefreshCw aria-hidden="true" className="h-4 w-4" />Refresh eligibility</Button>
    </div>
    {notice && <p role="status" className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">{notice}</p>}
    {loading && <p role="status" className="flex items-center gap-2 py-8 text-slate-600"><Loader2 aria-hidden="true" className="h-5 w-5 animate-spin" />Checking graduation gates...</p>}
    {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p>}
    {eligibility && <>
      <GraduationGates eligibility={eligibility} />
      <GraduationActions user={user} eligibility={eligibility} busy={busy} onFinalize={() => void finalize()} />
      {graduationRole(user) === "student" && <div className="flex flex-wrap gap-3">
        <Button asChild variant="outline"><Link to={`/tracks/${trackId}`}>Continue track work</Link></Button>
        <Button asChild variant="outline"><Link to={`/tracks/${trackId}/final-project`}>View final project and feedback</Link></Button>
      </div>}
    </>}
    {record && <GraduationRecord result={record} />}
    {eligibility && !record && <p className="text-sm text-slate-500">No graduation decision has been saved yet.</p>}
  </div>;
}

function StaffGraduation({ trackId, user }: { trackId: number; user: User }) {
  const [input, setInput] = useState("");
  const [studentId, setStudentId] = useState<number | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [selection, setSelection] = useState(0);
  const [recordsRevision, setRecordsRevision] = useState(0);
  function selectStudent(id: number) {
    setInput(String(id));
    setStudentId(id);
    setLookupError(null);
    setSelection((value) => value + 1);
  }
  return <div className="space-y-8">
    <form aria-label="Student graduation lookup" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm" onSubmit={(event) => {
      event.preventDefault();
      const id = studentIdInput(input);
      if (id === null) { setLookupError("Enter a positive whole-number student ID."); return; }
      selectStudent(id);
    }}>
      <Label htmlFor="graduation-student-id">Student ID</Label>
      <p id="graduation-lookup-help" className="mt-2 text-sm text-slate-600">Check a student enrolled in this track. Instructors can access only their assigned tracks.</p>
      <div className="mt-3 flex flex-wrap gap-3">
        <Input id="graduation-student-id" inputMode="numeric" autoComplete="off" required value={input} onChange={(event) => setInput(event.target.value)} aria-invalid={Boolean(lookupError)} aria-describedby={`graduation-lookup-help${lookupError ? " graduation-lookup-error" : ""}`} className="max-w-xs" />
        <Button type="submit">View eligibility</Button>
      </div>
      {lookupError && <p id="graduation-lookup-error" role="alert" className="mt-2 text-sm text-red-700">{lookupError}</p>}
    </form>
    {studentId !== null && <EligibilityWorkspace key={`${studentId}:${selection}`} user={user} trackId={trackId} studentId={studentId} onFinalized={() => setRecordsRevision((value) => value + 1)} />}
    <GraduationRecords key={recordsRevision} trackId={trackId} onSelect={selectStudent} />
  </div>;
}

export default function Graduation() {
  const { trackId } = useParams<{ trackId: string }>();
  const { user } = useAuth();
  const id = studentIdInput(trackId ?? "");
  const role = graduationRole(user);
  if (id === null) return <p role="alert" className="p-8 text-red-700">Invalid track ID.</p>;
  if (!user || !role) return <p role="alert" className="p-8 text-red-700">You do not have access to graduation.</p>;
  return <main className="mx-auto w-full max-w-6xl space-y-8 px-6 py-8">
    <Button asChild variant="ghost"><Link to={`/tracks/${id}`}><ArrowLeft aria-hidden="true" className="h-4 w-4" />Back to track</Link></Button>
    <header>
      <p className="flex items-center gap-2 text-sm font-semibold text-blue-700"><GraduationCap aria-hidden="true" className="h-5 w-5" />Track #{id}</p>
      <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">Graduation</h1>
      <p className="mt-3 max-w-3xl text-slate-600">{role === "manager" ? "Review current eligibility, inspect saved decisions, and finalize graduation when every requirement passes." : "Follow your progress through each requirement. Graduation is finalized by your instructor or administrator."}</p>
    </header>
    {role === "manager" ? <StaffGraduation key={`${id}:${user.id}:${role}`} trackId={id} user={user} /> : <EligibilityWorkspace key={`${id}:${user.id}:${role}`} user={user} trackId={id} onFinalized={() => {}} />}
  </main>;
}
