import { useState } from "react";
import { Button } from "@/components/ui/button";
import { submissionService } from "@/services/submission.service";
import { submissionError } from "@/lib/submissions";
import type { SubmissionDetail } from "@/types/submission";

export default function SubmissionFiles({ submission, editable, busy, onBusy, onRemoved }: {
  submission: SubmissionDetail;
  editable: boolean;
  busy: boolean;
  onBusy: (value: boolean) => void;
  onRemoved: (id: string) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  async function download(id: string, name: string) {
    onBusy(true);
    setError(null);
    try {
      const blob = await submissionService.download(submission.id, id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = name;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (requestError) {
      setError(submissionError(requestError));
    } finally { onBusy(false); }
  }
  async function remove(id: string) {
    onBusy(true);
    setError(null);
    try {
      await submissionService.removeFile(submission.id, id);
      onRemoved(id);
      setConfirmId(null);
    } catch (requestError) {
      setError(submissionError(requestError));
    } finally { onBusy(false); }
  }
  return <section className="space-y-2">
    <h4 className="font-medium">Files</h4>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {submission.files.length === 0 ? <p className="text-sm text-slate-500">No files attached.</p> : <ul className="space-y-2">
      {submission.files.map((file) => <li key={file.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3 text-sm">
        <span className="min-w-0 break-all">{file.file_name}{file.file_size_bytes !== null && <span className="ml-2 text-xs text-slate-500">{Math.ceil(file.file_size_bytes / 1024)} KB</span>}</span>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" disabled={busy} onClick={() => void download(file.id, file.file_name)}>Download</Button>
          {editable && (confirmId === file.id ? <>
            <Button size="sm" variant="destructive" disabled={busy} onClick={() => void remove(file.id)}>Confirm removal</Button>
            <Button size="sm" variant="outline" disabled={busy} onClick={() => setConfirmId(null)}>Cancel</Button>
          </> : <Button size="sm" variant="outline" disabled={busy} onClick={() => setConfirmId(file.id)}>Remove</Button>)}
        </div>
      </li>)}
    </ul>}
  </section>;
}
