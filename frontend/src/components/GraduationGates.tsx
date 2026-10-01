import { CheckCircle2, CircleX } from "lucide-react";
import { graduationGates, graduationStatus } from "@/lib/graduation";
import type { GraduationCheck, GraduationEligibility, GraduationGate, GraduationResult } from "@/types/graduation";

function Gate({ gate }: { gate: GraduationGate | GraduationCheck }) {
  const definition = graduationGates[gate.gate_key];
  const title = definition?.title ?? `Additional requirement: ${gate.gate_key}`;
  const score = "actual_value" in gate ? gate.actual_value : gate.score;
  const details = gate.details;
  const countKeys = gate.gate_key === "curriculum_completion" ? ["completed_lessons", "lessons"]
    : gate.gate_key === "mandatory_assignments" ? ["approved", "total"]
      : gate.gate_key === "quiz_average" ? ["completed_quizzes", "quizzes"] : null;
  const completed = countKeys && details?.[countKeys[0]];
  const total = countKeys && details?.[countKeys[1]];
  return <li className={`rounded-xl border p-5 ${gate.passed ? "border-emerald-200 bg-emerald-50/40" : "border-amber-200 bg-amber-50/40"}`}>
    <div className="flex items-start justify-between gap-3">
      <h3 className="font-semibold text-slate-900">{title}</h3>
      <span className={`flex shrink-0 items-center gap-1.5 text-sm font-semibold ${gate.passed ? "text-emerald-800" : "text-amber-900"}`}>
        {gate.passed ? <CheckCircle2 aria-hidden="true" className="h-4 w-4" /> : <CircleX aria-hidden="true" className="h-4 w-4" />}
        {gate.passed ? "Pass" : "Fail"}
      </span>
    </div>
    {definition && <p className="mt-2 text-sm leading-6 text-slate-600">{definition.description}</p>}
    <div className="mt-4 flex flex-wrap justify-between gap-2 text-sm">
      <span>Current: <strong>{score === null ? "Not recorded" : `${score}%`}</strong></span>
      <span>Required: <strong>{gate.required_value === null ? "Not recorded" : `${gate.required_value}%`}</strong></span>
    </div>
    {score !== null && <progress aria-label={`${title} recorded progress`} max={100} value={score} className={`mt-3 h-2 w-full ${gate.passed ? "accent-emerald-600" : "accent-amber-600"}`} />}
    {typeof completed === "number" && typeof total === "number" && <p className="mt-2 text-xs text-slate-600">{completed} of {total} {gate.gate_key === "mandatory_assignments" ? "approved" : "completed"}</p>}
    {!gate.passed && <p className="mt-3 text-sm font-medium text-amber-900">{gate.failure_reason || "This requirement has not been met."}</p>}
  </li>;
}

export function GraduationGates({ eligibility }: { eligibility: GraduationEligibility }) {
  return <section aria-label="Current graduation eligibility" className="space-y-5">
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm text-slate-500">Student #{eligibility.user_id} / Track #{eligibility.track_id}</p>
          <h2 className="mt-2 text-2xl font-bold text-slate-900">{graduationStatus[eligibility.status]}</h2>
          <p className="mt-2 text-sm text-slate-600">{eligibility.is_eligible ? "All mandatory graduation gates passed." : "Every mandatory gate must pass. A high overall score cannot make up for a failed gate."}</p>
        </div>
        <div className="rounded-xl bg-slate-50 px-6 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Overall score</p>
          <p className="mt-1 text-3xl font-bold text-slate-900">{eligibility.overall_score}%</p>
        </div>
      </div>
      <p className="mt-4 text-xs text-slate-500">Evaluated <time dateTime={eligibility.evaluated_at}>{new Date(eligibility.evaluated_at).toLocaleString()}</time></p>
    </div>
    <div>
      <h2 className="text-xl font-semibold text-slate-900">Graduation gates</h2>
      <p className="mt-1 mb-4 text-sm text-slate-600">Minimums: 100% curriculum, all mandatory assignments approved, 70% quiz average, 75% final project, and 75% overall. Track requirements may be higher.</p>
      <ul className="grid gap-4 md:grid-cols-2">
        {eligibility.gate_checks.map((gate) => <Gate key={gate.gate_key} gate={gate} />)}
      </ul>
      {eligibility.gate_checks.length === 0 && <p role="alert">No gate details were returned. Refresh or contact your instructor.</p>}
    </div>
  </section>;
}

export function GraduationRecord({ result }: { result: GraduationResult }) {
  return <section aria-label="Historical graduation record" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <h2 className="text-xl font-semibold text-slate-900">Saved graduation record #{result.id}</h2>
    <p className="mt-2 text-sm text-slate-600">Historical snapshot for student #{result.student_id}, track #{result.track_id}. Current eligibility is evaluated separately.</p>
    <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
      <div><dt className="text-slate-500">Saved status</dt><dd className="font-semibold">{graduationStatus[result.status]}</dd></div>
      <div><dt className="text-slate-500">Saved overall score</dt><dd className="font-semibold">{result.overall_score === null ? "Not recorded" : `${result.overall_score}%`}</dd></div>
      <div><dt className="text-slate-500">Evaluated</dt><dd>{result.evaluated_at ? new Date(result.evaluated_at).toLocaleString() : "Not recorded"}</dd></div>
      <div><dt className="text-slate-500">Finalized</dt><dd>{result.finalized_at ? new Date(result.finalized_at).toLocaleString() : "Not finalized"}{result.finalized_by !== null ? ` by staff #${result.finalized_by}` : ""}</dd></div>
    </dl>
    <details className="mt-5">
      <summary className="cursor-pointer font-medium text-blue-700">View saved gate checks ({result.checks.length})</summary>
      <ul className="mt-4 grid gap-4 md:grid-cols-2">{result.checks.map((check) => <Gate key={check.id} gate={check} />)}</ul>
      {!result.checks.length && <p className="mt-2 text-sm text-slate-500">No gate checks were saved with this record.</p>}
    </details>
  </section>;
}
