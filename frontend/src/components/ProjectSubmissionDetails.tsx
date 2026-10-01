import { ExternalLink } from "lucide-react";
import { isProjectUrl, projectStatus } from "@/lib/finalProjects";
import type { ProjectSubmission, ProjectSubmissionStatus } from "@/types/finalProject";

export function ProjectStatusBadge({ status }: { status: ProjectSubmissionStatus }) {
  const value = projectStatus[status];
  return <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${value.style}`}>{value.label}</span>;
}

export default function ProjectSubmissionDetails({ submission }: { submission: ProjectSubmission }) {
  const links = [
    { label: "GitHub repository", url: submission.github_url },
    { label: "Live project", url: submission.live_url },
    { label: "Project files", url: submission.file_url },
  ];
  const reviews = [...submission.reviews].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at) || b.id - a.id);
  return <section className="space-y-5" aria-label="Submission details">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h3 className="font-semibold text-slate-900">Submission #{submission.id}</h3>
      <ProjectStatusBadge status={submission.status} />
    </div>
    <p className="text-sm text-slate-600">{projectStatus[submission.status].message}</p>
    <p className="text-xs text-slate-500">
      Created {new Date(submission.created_at).toLocaleString()}
      {submission.submitted_at && <> / Last submitted {new Date(submission.submitted_at).toLocaleString()}</>}
    </p>
    <div className="flex flex-wrap gap-3">
      {links.filter((link) => link.url).map(({ label, url }) => isProjectUrl(url!) ? (
        <a key={label} href={url!} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50">
          <ExternalLink className="h-4 w-4" />{label}
        </a>
      ) : <p key={label} className="text-sm text-red-700">{label}: invalid saved link</p>)}
      {!links.some((link) => link.url) && <p className="text-sm text-slate-500">No project links saved yet.</p>}
    </div>
    {submission.student_notes && <div className="rounded-lg bg-slate-50 p-4">
      <h4 className="text-sm font-semibold text-slate-700">Student notes</h4>
      <p className="mt-2 whitespace-pre-wrap break-words text-sm text-slate-600">{submission.student_notes}</p>
    </div>}
    <div>
      <h4 className="mb-3 font-semibold text-slate-900">Instructor feedback and review history</h4>
      {reviews.length === 0 ? <p className="text-sm text-slate-500">No reviews yet.</p> : (
        <ol className="space-y-3">
          {reviews.map((review) => <li key={review.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <ProjectStatusBadge status={review.status_decision} />
              <span className="text-sm font-semibold text-slate-900">{review.score === null ? "Not graded" : `${review.score}/100`}</span>
            </div>
            <p className="mt-2 text-xs text-slate-500">Reviewer #{review.reviewer_id} / {new Date(review.created_at).toLocaleString()}</p>
            <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-slate-700">{review.feedback || "No written feedback."}</p>
          </li>)}
        </ol>
      )}
    </div>
  </section>;
}
