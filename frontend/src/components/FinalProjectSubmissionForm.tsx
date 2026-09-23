import { useState } from "react";
import { isAxiosError } from "axios";
import {
  CheckCircle2,
  GitBranch,
  Globe,
  Loader2,
  Save,
  Send,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type {
  ProjectSubmission,
  ProjectSubmissionCreate,
} from "@/types/finalProject";

interface FinalProjectSubmissionFormProps {
  projectId: number;
  submission: ProjectSubmission | null;
  onCreate: (
    payload: ProjectSubmissionCreate,
  ) => Promise<ProjectSubmission>;
  onUpdate: (
    submissionId: number,
    payload: ProjectSubmissionCreate,
  ) => Promise<ProjectSubmission>;
  onSubmit: (
    submissionId: number,
    payload: ProjectSubmissionCreate,
  ) => Promise<ProjectSubmission>;
}

function getErrorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }

    if (error.response?.status === 403) {
      return "You do not have permission to update this submission.";
    }

    if (error.response?.status === 409) {
      return "A submission already exists for this project.";
    }
  }

  return "Unable to save your project right now. Please try again.";
}

export default function FinalProjectSubmissionForm({
  projectId,
  submission,
  onCreate,
  onUpdate,
  onSubmit,
}: FinalProjectSubmissionFormProps) {
  const [githubUrl, setGithubUrl] = useState(submission?.github_url ?? "");
  const [liveUrl, setLiveUrl] = useState(submission?.live_url ?? "");
  const [fileUrl, setFileUrl] = useState(submission?.file_url ?? "");
  const [studentNotes, setStudentNotes] = useState(
    submission?.student_notes ?? "",
  );
  const [action, setAction] = useState<"save" | "submit" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const payload: ProjectSubmissionCreate = {
    github_url: githubUrl.trim() || null,
    live_url: liveUrl.trim() || null,
    file_url: fileUrl.trim() || null,
    student_notes: studentNotes.trim() || null,
  };

  const handleSave = async () => {
    setAction("save");
    setError(null);
    setSuccess(null);

    try {
      if (submission) {
        await onUpdate(submission.id, payload);
      } else {
        await onCreate(payload);
      }

      setSuccess("Your draft has been saved.");
    } catch (requestError) {
      console.error("Failed to save final project submission", requestError);
      setError(getErrorMessage(requestError));
    } finally {
      setAction(null);
    }
  };

  const handleSubmit = async () => {
    setAction("submit");
    setError(null);
    setSuccess(null);

    try {
      let currentSubmission = submission;

      if (!currentSubmission) {
        currentSubmission = await onCreate(payload);
      }

      await onSubmit(currentSubmission.id, payload);
      setSuccess(
        "Your final project has been submitted for instructor review.",
      );
    } catch (requestError) {
      console.error("Failed to submit final project", requestError);
      setError(getErrorMessage(requestError));
    } finally {
      setAction(null);
    }
  };

  return (
    <Card className="border-gray-200 shadow-sm">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="text-xl text-slate-900">
              {submission?.status === "CHANGES_REQUIRED"
                ? "Revise your project"
                : "Project submission"}
            </CardTitle>
            <CardDescription className="mt-2 leading-6">
              Add your project links and notes. You can save a draft and
              submit when everything is ready.
            </CardDescription>
          </div>

          <span className="inline-flex shrink-0 items-center rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700 ring-1 ring-inset ring-amber-600/20">
            {submission?.status === "CHANGES_REQUIRED"
              ? "Changes requested"
              : "Draft"}
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        <div className="grid gap-5 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="github-url">GitHub URL</Label>
            <div className="relative">
              <GitBranch className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
              <Input
                id="github-url"
                value={githubUrl}
                onChange={(event) => setGithubUrl(event.target.value)}
                placeholder="https://github.com/..."
                className="pl-9"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="live-url">Live project URL</Label>
            <div className="relative">
              <Globe className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
              <Input
                id="live-url"
                value={liveUrl}
                onChange={(event) => setLiveUrl(event.target.value)}
                placeholder="https://..."
                className="pl-9"
              />
            </div>
          </div>

          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="file-url">Project file / archive URL</Label>
            <Input
              id="file-url"
              value={fileUrl}
              onChange={(event) => setFileUrl(event.target.value)}
              placeholder="https://.../final-project.zip"
            />
          </div>

          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="student-notes">Notes for your instructor</Label>
            <textarea
              id="student-notes"
              value={studentNotes}
              onChange={(event) => setStudentNotes(event.target.value)}
              rows={5}
              placeholder="Explain the main implementation choices, known limitations, or anything your instructor should know."
              className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none transition-[color,box-shadow] placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
            />
          </div>
        </div>

        {submission?.status === "CHANGES_REQUIRED" &&
          submission.reviews.length > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4">
              <p className="text-sm font-semibold text-amber-900">
                Latest instructor feedback
              </p>

              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-amber-800">
                {submission.reviews[submission.reviews.length - 1].feedback ||
                  "Please review the requested changes and resubmit."}
              </p>
            </div>
          )}

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {success && (
          <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            {success}
          </div>
        )}

        <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
          <Button
            type="button"
            variant="outline"
            disabled={action !== null}
            onClick={() => void handleSave()}
            className="gap-2"
          >
            {action === "save" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save draft
          </Button>

          <Button
            type="button"
            disabled={action !== null}
            onClick={() => void handleSubmit()}
            className="gap-2 bg-blue-600 text-white hover:bg-blue-700"
          >
            {action === "submit" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            Submit for review
          </Button>
        </div>

        {!submission && (
          <p className="text-xs leading-5 text-gray-400">
            Project {projectId} will receive a draft submission the first time
            you save or submit.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
