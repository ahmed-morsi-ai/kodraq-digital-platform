import { ArrowUpRight, ClipboardCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { assignmentContext } from "@/lib/assignments";
import type { Assignment } from "@/types/assignment";
import type { TrackModule } from "@/types/track";

export default function AssignmentList({ assignments, modules, onSelect }: {
  assignments: Assignment[];
  modules: TrackModule[];
  onSelect: (id: number) => void;
}) {
  if (!assignments.length) return <p className="rounded-xl border border-dashed p-6 text-sm text-slate-500">No assignments available for this selection.</p>;
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {assignments.map((assignment) => (
        <article key={assignment.id} className="flex min-w-0 flex-col rounded-xl border border-violet-100 bg-violet-50/30 p-5">
          <div className="flex items-start gap-3">
            <ClipboardCheck className="mt-1 size-5 shrink-0 text-violet-600" />
            <div className="min-w-0">
              <p className="text-xs text-slate-500">{assignmentContext(assignment, modules)}</p>
              <h3 className="mt-1 font-semibold break-words text-slate-900">{assignment.title}</h3>
            </div>
          </div>
          <div className="my-3 flex flex-wrap gap-2 text-xs">
            <span className="rounded-full bg-white px-2 py-1 capitalize text-violet-700">{assignment.difficulty}</span>
            <span className="rounded-full bg-white px-2 py-1 text-slate-600">{assignment.is_mandatory ? "Mandatory" : "Optional"}</span>
            {!assignment.is_active && <span className="rounded-full bg-amber-100 px-2 py-1 text-amber-800">Inactive</span>}
          </div>
          <p className="mb-4 line-clamp-3 break-words text-sm leading-6 text-slate-600">{assignment.description}</p>
          <div className="mt-auto flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-slate-500">{assignment.estimated_minutes !== null ? `${assignment.estimated_minutes} min` : "Self-paced"}</span>
            <Button variant="outline" onClick={() => onSelect(assignment.id)} aria-label={`View assignment: ${assignment.title}`}>View assignment <ArrowUpRight /></Button>
          </div>
        </article>
      ))}
    </div>
  );
}
