import { useEffect, useState } from "react";
import { GraduationRecord } from "@/components/GraduationGates";
import { Button } from "@/components/ui/button";
import { graduationError, graduationStatus } from "@/lib/graduation";
import { graduationService } from "@/services/graduation.service";
import type { GraduationResult } from "@/types/graduation";

function SavedRecord({ id }: { id: number }) {
  const [result, setResult] = useState<GraduationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const request = new AbortController();
    graduationService.getResult(id, request.signal).then((data) => {
      if (!request.signal.aborted) setResult(data);
    }).catch((reason: unknown) => {
      if (!request.signal.aborted) setError(graduationError(reason));
    });
    return () => request.abort();
  }, [id]);
  if (error) return <p role="alert" className="text-sm text-red-700">{error} Close and reopen this record to retry.</p>;
  return result ? <GraduationRecord result={result} /> : <p role="status">Loading saved record...</p>;
}

function RecordPage({ trackId, page, onSelect, onPage }: {
  trackId: number; page: number; onSelect: (studentId: number) => void; onPage: (page: number) => void;
}) {
  const [records, setRecords] = useState<GraduationResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  useEffect(() => {
    const request = new AbortController();
    graduationService.getResults(trackId, page * 25, request.signal).then((data) => {
      if (!request.signal.aborted) setRecords(data);
    }).catch((reason: unknown) => {
      if (!request.signal.aborted) setError(graduationError(reason));
    });
    return () => request.abort();
  }, [trackId, page]);
  return <div className="space-y-4">
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {!records && !error && <p role="status" className="text-sm text-slate-600">Loading track graduation records...</p>}
    {records?.length === 0 && <p className="text-sm text-slate-600">No saved records on this page. Use the student ID lookup to view eligibility before finalization.</p>}
    {records && records.length > 0 && <ul className="divide-y divide-slate-200">
      {records.map((result) => <li key={result.id} className="flex flex-wrap items-center justify-between gap-3 py-4">
        <div className="text-sm">
          <p className="font-semibold text-slate-900">Student #{result.student_id}</p>
          <p className="mt-1 text-slate-600">Record #{result.id}: {graduationStatus[result.status]} / {result.overall_score === null ? "Score not recorded" : `${result.overall_score}%`}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => onSelect(result.student_id)}>View eligibility<span className="sr-only"> for student #{result.student_id}</span></Button>
          <Button type="button" variant="ghost" size="sm" aria-expanded={selected === result.id} onClick={() => setSelected(selected === result.id ? null : result.id)}>{selected === result.id ? "Close record" : "View record"}<span className="sr-only"> #{result.id}</span></Button>
        </div>
      </li>)}
    </ul>}
    <div className="flex items-center gap-3">
      <Button type="button" variant="outline" size="sm" disabled={page === 0} onClick={() => onPage(page - 1)}>Previous</Button>
      <span className="text-sm text-slate-500">Page {page + 1}</span>
      <Button type="button" variant="outline" size="sm" disabled={!records || records.length < 25} onClick={() => onPage(page + 1)}>Next</Button>
    </div>
    {selected !== null && <SavedRecord key={selected} id={selected} />}
  </div>;
}

export default function GraduationRecords({ trackId, onSelect }: { trackId: number; onSelect: (studentId: number) => void }) {
  const [page, setPage] = useState(0);
  const [revision, setRevision] = useState(0);
  return <section aria-label="Track graduation records" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div><h2 className="text-xl font-semibold text-slate-900">Track graduation records</h2><p className="mt-1 text-sm text-slate-600">Saved decisions for this track, newest first.</p></div>
      <Button type="button" variant="outline" onClick={() => { setPage(0); setRevision((value) => value + 1); }}>Refresh records</Button>
    </div>
    <RecordPage key={`${page}:${revision}`} trackId={trackId} page={page} onSelect={onSelect} onPage={setPage} />
  </section>;
}
