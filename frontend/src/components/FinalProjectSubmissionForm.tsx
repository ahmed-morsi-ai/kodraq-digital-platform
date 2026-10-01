import { useId, useRef, useState } from "react";
import { Loader2, Save, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { canEditProject, projectError, validateProjectLinks } from "@/lib/finalProjects";
import { saveProjectSubmission } from "@/services/finalProject.service";
import type { ProjectSubmission, ProjectSubmissionCreate } from "@/types/finalProject";

export default function FinalProjectSubmissionForm({ projectId, submission, onSaved }: {
  projectId: number;
  submission: ProjectSubmission | null;
  onSaved: (submission: ProjectSubmission) => void;
}) {
  const id = useId();
  const pending = useRef(false);
  const [githubUrl, setGithubUrl] = useState(submission?.github_url ?? "");
  const [liveUrl, setLiveUrl] = useState(submission?.live_url ?? "");
  const [fileUrl, setFileUrl] = useState(submission?.file_url ?? "");
  const [notes, setNotes] = useState(submission?.student_notes ?? "");
  const [action, setAction] = useState<"save" | "submit" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const rework = submission?.status === "CHANGES_REQUIRED";

  async function save(submit: boolean) {
    if (pending.current || !canEditProject(submission)) return;
    const payload: ProjectSubmissionCreate = {
      github_url: githubUrl.trim() || null,
      live_url: liveUrl.trim() || null,
      file_url: fileUrl.trim() || null,
      student_notes: notes.trim() || null,
    };
    setSuccess(null);
    const validation = validateProjectLinks(payload, submit);
    setError(validation);
    if (validation) return;
    pending.current = true;
    setAction(submit ? "submit" : "save");
    try {
      await saveProjectSubmission(projectId, submission, payload, submit, onSaved);
      setSuccess(submit ? "Project submitted for review." : "Changes saved. Submit when you are ready for review.");
    } catch (requestError) {
      setError(projectError(requestError));
    } finally {
      pending.current = false;
      setAction(null);
    }
  }

  if (!canEditProject(submission)) return null;
  return <Card className="border-slate-200 shadow-sm">
    <CardHeader>
      <CardTitle className="text-xl">{rework ? "Revise and resubmit" : "Project submission"}</CardTitle>
      <CardDescription>
        {rework ? "Address the instructor feedback below, save your changes, then resubmit." : "Add your work below. You can save a draft before submitting for review."}
      </CardDescription>
    </CardHeader>
    <CardContent>
      <form noValidate onSubmit={(event) => { event.preventDefault(); void save(true); }} className="space-y-5" aria-label="Final project submission" aria-busy={action !== null}>
        <fieldset disabled={action !== null} className="grid gap-5 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor={`${id}-github`}>GitHub repository URL</Label>
            <Input id={`${id}-github`} type="url" maxLength={512} value={githubUrl} onChange={(event) => setGithubUrl(event.target.value)} placeholder="https://github.com/owner/repository" />
          </div>
          <div className="space-y-2">
            <Label htmlFor={`${id}-live`}>Live project URL</Label>
            <Input id={`${id}-live`} type="url" maxLength={512} value={liveUrl} onChange={(event) => setLiveUrl(event.target.value)} placeholder="https://your-project.example" />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor={`${id}-file`}>Project files URL</Label>
            <Input id={`${id}-file`} type="url" maxLength={512} aria-describedby={`${id}-file-help`} value={fileUrl} onChange={(event) => setFileUrl(event.target.value)} placeholder="https://your-storage.example/final-project.zip" />
            <p id={`${id}-file-help`} className="text-xs leading-5 text-slate-500">Paste a link to your hosted project files or archive. Make sure your instructor can open it.</p>
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor={`${id}-notes`}>Notes for your instructor</Label>
            <textarea id={`${id}-notes`} value={notes} onChange={(event) => setNotes(event.target.value)} rows={5} className="w-full rounded-md border border-input bg-white px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-blue-500" />
          </div>
        </fieldset>
        <p className="text-sm text-slate-500">At least one project link is required to submit.</p>
        {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {success && <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{success}</p>}
        <div className="flex flex-wrap justify-end gap-3">
          <Button type="button" variant="outline" disabled={action !== null} onClick={() => void save(false)}>
            {action === "save" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {rework ? "Save changes" : "Save draft"}
          </Button>
          <Button type="submit" disabled={action !== null}>
            {action === "submit" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            {rework ? "Resubmit for review" : "Submit for review"}
          </Button>
        </div>
      </form>
    </CardContent>
  </Card>;
}
