import { useId, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { isRepositoryUrl, submissionError } from "@/lib/submissions";
import { submissionService } from "@/services/submission.service";
import type { SubmissionDetail } from "@/types/submission";

export default function SubmissionForm({ assignmentId, submission, busy, onBusy, onSaved }: {
  assignmentId: number;
  submission: SubmissionDetail | null;
  busy: boolean;
  onBusy: (value: boolean) => void;
  onSaved: (id: number, message: string) => void;
}) {
  const id = useId();
  const draftId = useRef(submission?.id ?? null);
  const pending = useRef(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const [github, setGithub] = useState(submission?.github_url ?? "");
  const [content, setContent] = useState(submission?.content ?? "");
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const rework = submission?.status === "CHANGES_REQUIRED";

  async function save(submit: boolean) {
    if (pending.current || busy) return;
    if (github.trim() && !isRepositoryUrl(github.trim())) {
      setError("Use a repository URL such as https://github.com/owner/repository.");
      return;
    }
    pending.current = true;
    onBusy(true);
    setError(null);
    try {
      const data = { github_url: github.trim() || null, content: content.trim() || null };
      if (draftId.current === null) {
        draftId.current = (await submissionService.create(assignmentId, data)).id;
      } else {
        await submissionService.update(draftId.current, data);
      }
      if (files.length > 0) {
        await submissionService.upload(draftId.current, files);
        setFiles([]);
        if (fileInput.current) fileInput.current.value = "";
      }
      if (submit) await submissionService.update(draftId.current, { status: "SUBMITTED" });
      onSaved(draftId.current, submit ? (rework ? "Work resubmitted for review." : "Work submitted for review.") : "Draft saved.");
    } catch (requestError) {
      setError(`${submissionError(requestError)}${draftId.current !== null ? " Your saved draft is retained. Refresh to check its latest status before retrying." : ""}`);
    } finally {
      pending.current = false;
      onBusy(false);
    }
  }

  return <form className="space-y-4 rounded-xl border border-blue-100 bg-blue-50/40 p-4" onSubmit={(event) => { event.preventDefault(); void save(true); }}>
    <h4 className="font-semibold">{rework ? "Update your work" : "Your submission"}</h4>
    {rework && <p className="text-sm text-blue-800">Review the feedback below, update your work, then resubmit.</p>}
    <div className="space-y-2">
      <Label htmlFor={`${id}-github`}>GitHub repository</Label>
      <Input id={`${id}-github`} type="url" maxLength={512} value={github} onChange={(event) => setGithub(event.target.value)} placeholder="https://github.com/owner/repository" disabled={busy} />
    </div>
    <div className="space-y-2">
      <Label htmlFor={`${id}-notes`}>Notes for your instructor</Label>
      <textarea id={`${id}-notes`} value={content} onChange={(event) => setContent(event.target.value)} disabled={busy} rows={3} className="w-full rounded-lg border bg-white p-3 text-sm focus-visible:ring-2 focus-visible:ring-blue-500" />
    </div>
    <div className="space-y-2">
      <Label htmlFor={`${id}-files`}>Attach files</Label>
      <Input ref={fileInput} id={`${id}-files`} type="file" multiple disabled={busy} onChange={(event) => setFiles(Array.from(event.target.files ?? []))} />
      {files.length > 0 && <p className="break-words text-xs text-slate-600">Ready to upload: {files.map((file) => file.name).join(", ")}</p>}
    </div>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    <div className="flex flex-wrap gap-2">
      <Button type="button" variant="outline" disabled={busy} onClick={() => void save(false)}>Save draft</Button>
      <Button type="submit" disabled={busy} className="bg-blue-600 text-white">{busy ? "Saving…" : rework ? "Resubmit for review" : "Submit for review"}</Button>
    </div>
  </form>;
}
