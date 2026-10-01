import { submissionTimeline } from "@/lib/submissions";
import type { SubmissionDetail } from "@/types/submission";

export default function SubmissionHistory({ submission }: { submission: SubmissionDetail }) {
  return <section className="space-y-3">
    <h4 className="font-semibold">Submission history</h4>
    <ol className="ml-2 space-y-4 border-l-2 border-slate-200 pl-4">
      {submissionTimeline(submission).map((event) => <li key={event.id} className="space-y-1 text-sm">
        <p className="font-medium capitalize">{event.label}{event.grade !== null && <span className="ml-2 text-blue-700">Grade: {event.grade}</span>}</p>
        <time dateTime={event.date} className="text-xs text-slate-500">{new Date(event.date).toLocaleString()}</time>
        {event.feedback && <p className="whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-3 text-slate-700">{event.feedback}</p>}
      </li>)}
    </ol>
  </section>;
}
