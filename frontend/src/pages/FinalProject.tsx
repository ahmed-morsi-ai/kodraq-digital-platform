import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Loader2, RefreshCw, ShieldCheck } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import FinalProjectSubmissionForm from "@/components/FinalProjectSubmissionForm";
import InstructorReviewPanel from "@/components/InstructorReviewPanel";
import ProjectSubmissionDetails from "@/components/ProjectSubmissionDetails";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/context/AuthContext";
import { canEditProject, projectError, projectRole } from "@/lib/finalProjects";
import { finalProjectService } from "@/services/finalProject.service";
import type { User } from "@/types/auth";
import type { ProjectSubmission, TrainingProject } from "@/types/finalProject";

export function StudentProjectWorkspace({ user, project, submission, onSaved }: {
  user: User | null;
  project: TrainingProject;
  submission: ProjectSubmission | null;
  onSaved: (submission: ProjectSubmission) => void;
}) {
  if (projectRole(user) !== "student" || (submission && String(submission.student_id) !== String(user?.id))) return null;
  return <div className="space-y-6">
    {project.is_active && canEditProject(submission) && <FinalProjectSubmissionForm projectId={project.id} submission={submission} onSaved={onSaved} />}
    {submission && <Card className="border-slate-200 shadow-sm"><CardContent className="pt-6"><ProjectSubmissionDetails submission={submission} /></CardContent></Card>}
  </div>;
}

function ProjectWorkspace({ trackId, user }: { trackId: number; user: User }) {
  const role = projectRole(user);
  const [project, setProject] = useState<TrainingProject | null>(null);
  const [submission, setSubmission] = useState<ProjectSubmission | null>(null);
  const [submissions, setSubmissions] = useState<ProjectSubmission[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const nextOffset = useRef(0);
  const loadingPage = useRef(false);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    const request = new AbortController();
    controller.current = request;
    async function load() {
      try {
        const data = await finalProjectService.getByTrack(trackId, request.signal);
        if (role === "manager") {
          const items = await finalProjectService.getByProject(data.id, 0, request.signal);
          if (request.signal.aborted) return;
          setSubmissions(items);
          nextOffset.current = items.length;
          setHasMore(items.length === 50);
        } else {
          const items = await finalProjectService.getMySubmissions({ project_id: data.id, limit: 1 }, request.signal);
          if (request.signal.aborted) return;
          setSubmission(items[0] ?? null);
        }
        setProject(data);
      } catch (requestError) {
        if (!request.signal.aborted) setError(projectError(requestError));
      }
    }
    void load();
    return () => request.abort();
  }, [trackId, role]);

  async function loadMore() {
    const request = controller.current;
    if (!project || loadingPage.current || !hasMore || !request || request.signal.aborted) return;
    loadingPage.current = true;
    setLoadingMore(true);
    setListError(null);
    try {
      const items = await finalProjectService.getByProject(project.id, nextOffset.current, request.signal);
      if (request.signal.aborted) return;
      nextOffset.current += items.length;
      setSubmissions((current) => [...current, ...items.filter((item) => !current.some((existing) => existing.id === item.id))]);
      setHasMore(items.length === 50);
    } catch (requestError) {
      if (!request.signal.aborted) setListError(projectError(requestError));
    } finally {
      loadingPage.current = false;
      if (!request.signal.aborted) setLoadingMore(false);
    }
  }

  if (error) return <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-700">{error}</p>;
  if (!project) return <p role="status" className="flex items-center justify-center gap-3 py-16 text-slate-600"><Loader2 className="h-5 w-5 animate-spin" />Loading final project...</p>;
  return <div className="space-y-6">
    <section className="rounded-2xl border border-slate-200 bg-gradient-to-br from-blue-50 to-white p-6 shadow-sm md:p-8">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div className="max-w-3xl">
          <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-blue-700"><ShieldCheck className="h-4 w-4" />Final project</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">{project.title}</h1>
          <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-600">{project.description || "Complete the requirements and submit your work for instructor review."}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Passing score</p>
          <p className="mt-2 text-3xl font-bold text-slate-900">{project.passing_score}/100</p>
        </div>
      </div>
      {!project.is_active && <p className="mt-4 text-sm font-medium text-amber-800">This project is inactive. New student submissions and edits are disabled.</p>}
    </section>
    <Card className="border-slate-200 shadow-sm">
      <CardHeader><CardTitle className="text-xl">Project requirements</CardTitle><CardDescription>Complete the mandatory requirements before submission.</CardDescription></CardHeader>
      <CardContent>
        {project.requirements.length === 0 ? <p className="text-sm text-slate-500">No detailed requirements published yet.</p> : <ol className="space-y-3">
          {[...project.requirements].sort((a, b) => a.order - b.order || a.id - b.id).map((requirement, index) => <li key={requirement.id} className="flex gap-3 rounded-xl bg-slate-50 p-4">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white text-xs font-bold text-blue-700">{index + 1}</span>
            <div><p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{requirement.description}</p><p className={`mt-1 text-xs font-semibold ${requirement.is_mandatory ? "text-red-700" : "text-slate-500"}`}>{requirement.is_mandatory ? "Mandatory" : "Recommended"}</p></div>
          </li>)}
        </ol>}
      </CardContent>
    </Card>
    {role === "student" ? <StudentProjectWorkspace user={user} project={project} submission={submission} onSaved={setSubmission} /> : (
      <InstructorReviewPanel user={user} project={project} submissions={submissions} hasMore={hasMore} loadingMore={loadingMore} listError={listError} onLoadMore={() => void loadMore()} onUpdated={(updated) => setSubmissions((current) => current.map((item) => item.id === updated.id ? updated : item))} />
    )}
  </div>;
}

export default function FinalProject() {
  const { trackId } = useParams<{ trackId: string }>();
  const { user } = useAuth();
  const [revision, setRevision] = useState(0);
  const numericTrackId = Number(trackId);
  const role = projectRole(user);
  if (!Number.isSafeInteger(numericTrackId) || numericTrackId <= 0) return <p role="alert" className="p-8 text-red-700">Invalid track ID.</p>;
  if (!user || !role) return <p role="alert" className="p-8 text-red-700">You do not have access to final projects.</p>;
  return <main className="mx-auto w-full max-w-6xl space-y-6 px-6 py-8">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <Button asChild variant="ghost"><Link to={`/tracks/${numericTrackId}`}><ArrowLeft className="h-4 w-4" />Back to track</Link></Button>
      <Button type="button" variant="outline" title="Reload project and discard unsaved edits" onClick={() => setRevision((value) => value + 1)}><RefreshCw className="h-4 w-4" />Refresh</Button>
    </div>
    <ProjectWorkspace key={`${numericTrackId}:${user.id}:${role}:${revision}`} trackId={numericTrackId} user={user} />
  </main>;
}
