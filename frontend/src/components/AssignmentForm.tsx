import { useState, type FormEvent } from "react";
import AssignmentDialog from "@/components/AssignmentDialog";
import { Button } from "@/components/ui/button";
import { assignmentError, assignmentModuleId } from "@/lib/assignments";
import { assignmentService } from "@/services/assignment.service";
import type { Assignment, AssignmentCreate, AssignmentDifficulty } from "@/types/assignment";
import type { TrackCurriculum } from "@/types/track";

const fieldClass = "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600";

export default function AssignmentForm({ assignment, track, onClose, onSaved }: {
  assignment?: Assignment;
  track: TrackCurriculum;
  onClose: () => void;
  onSaved: (assignment: Assignment) => void;
}) {
  const [moduleId, setModuleId] = useState(assignment ? assignmentModuleId(assignment, track.modules)?.toString() ?? "" : "");
  const [lessonId, setLessonId] = useState(assignment?.lesson_id?.toString() ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lessons = track.modules.find((module) => module.id === Number(moduleId))?.lessons ?? [];

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const form = new FormData(event.currentTarget);
    const optionalNumber = (name: string) => form.get(name) === "" ? null : Number(form.get(name));
    const data: AssignmentCreate = {
      track_id: track.id,
      module_id: moduleId ? Number(moduleId) : null,
      lesson_id: lessonId ? Number(lessonId) : null,
      title: String(form.get("title")).trim(),
      description: String(form.get("description")).trim(),
      instructions: String(form.get("instructions")).trim(),
      difficulty: form.get("difficulty") as AssignmentDifficulty,
      ordering: Number(form.get("ordering")),
      due_days: optionalNumber("due_days"),
      estimated_minutes: optionalNumber("estimated_minutes"),
      is_mandatory: form.has("is_mandatory"),
      is_active: form.has("is_active"),
    };
    if (!data.title || !data.description || !data.instructions) {
      setError("Title, description, and instructions must contain text.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const saved = assignment
        ? await assignmentService.update(assignment.id, data)
        : await assignmentService.create(data);
      onSaved(saved);
    } catch (requestError) {
      setError(assignmentError(requestError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AssignmentDialog title={assignment ? "Edit assignment" : "Create assignment"} description={`Assignment for ${track.name}. Required fields are marked *.`} onClose={onClose} busy={busy}>
      <form onSubmit={(event) => void save(event)}>
        <fieldset disabled={busy} className="space-y-4">
          <label className="block text-sm font-medium">Title *
            <input name="title" required maxLength={255} defaultValue={assignment?.title ?? ""} className={fieldClass} />
          </label>
          <label className="block text-sm font-medium">Description *
            <textarea name="description" required rows={3} defaultValue={assignment?.description ?? ""} className={fieldClass} />
          </label>
          <label className="block text-sm font-medium">Instructions *
            <textarea name="instructions" required rows={5} defaultValue={assignment?.instructions ?? ""} className={fieldClass} />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm font-medium">Module
              <select value={moduleId} onChange={(event) => { setModuleId(event.target.value); setLessonId(""); }} className={fieldClass}>
                <option value="">Track-wide</option>
                {track.modules.map((module) => <option key={module.id} value={module.id}>{module.title}</option>)}
              </select>
            </label>
            <label className="block text-sm font-medium">Lesson
              <select value={lessonId} onChange={(event) => setLessonId(event.target.value)} disabled={busy || !moduleId} className={fieldClass}>
                <option value="">All lessons / no specific lesson</option>
                {lessons.map((lesson) => <option key={lesson.id} value={lesson.id}>{lesson.title}</option>)}
              </select>
            </label>
            <label className="block text-sm font-medium">Difficulty *
              <select name="difficulty" defaultValue={assignment?.difficulty ?? "beginner"} className={fieldClass}>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </label>
            <label className="block text-sm font-medium">Display order *
              <input name="ordering" type="number" required step={1} defaultValue={assignment?.ordering ?? 0} className={fieldClass} />
            </label>
            <label className="block text-sm font-medium">Due after (days)
              <input name="due_days" type="number" step={1} defaultValue={assignment?.due_days ?? ""} className={fieldClass} />
            </label>
            <label className="block text-sm font-medium">Estimated time (minutes)
              <input name="estimated_minutes" type="number" step={1} defaultValue={assignment?.estimated_minutes ?? ""} className={fieldClass} />
            </label>
          </div>
          <p className="text-xs text-slate-500">Leave due days or estimated time blank to leave them unspecified.</p>
          <div className="flex flex-wrap gap-6 text-sm">
            <label className="flex items-center gap-2"><input type="checkbox" name="is_mandatory" defaultChecked={assignment?.is_mandatory ?? true} /> Mandatory</label>
            <label className="flex items-center gap-2"><input type="checkbox" name="is_active" defaultChecked={assignment?.is_active ?? true} /> Active</label>
          </div>
          {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          <div className="flex justify-end gap-3 border-t pt-4">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" className="bg-blue-600 text-white hover:bg-blue-700">{busy ? "Saving…" : "Save assignment"}</Button>
          </div>
        </fieldset>
      </form>
    </AssignmentDialog>
  );
}
