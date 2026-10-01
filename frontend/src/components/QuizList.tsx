import { useEffect, useRef, useState } from "react";
import { ClipboardCheck, Loader2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/context/AuthContext";
import { canTakeQuiz, formatQuizScore, quizError } from "@/lib/quizzes";
import { quizService } from "@/services/quiz.service";
import type { QuizAttempt, StudentQuiz } from "@/types/quiz";

export default function QuizList({ trackId }: { trackId: number }) {
  const { user } = useAuth();
  return <TrackQuizzes key={`${trackId}-${user?.id}`} trackId={trackId} student={canTakeQuiz(user)} />;
}

function TrackQuizzes({ trackId, student }: { trackId: number; student: boolean }) {
  const [quizzes, setQuizzes] = useState<StudentQuiz[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const all: StudentQuiz[] = [];
        let page: StudentQuiz[];
        do {
          page = await quizService.getAvailableQuizzes({ trackId, skip: all.length }, controller.signal);
          all.push(...page);
        } while (page.length === 100);
        if (!controller.signal.aborted) setQuizzes(all);
      } catch (error) {
        if (!controller.signal.aborted) setError(quizError(error));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [trackId, revision]);
  return <Card>
    <CardHeader>
      <CardTitle className="flex items-center gap-2"><ClipboardCheck className="h-5 w-5 text-blue-600" />Quizzes</CardTitle>
      <CardDescription>Complete available assessments to check your understanding.</CardDescription>
    </CardHeader>
    <CardContent className="space-y-4">
      {loading && <p role="status" className="flex items-center gap-2 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" />Loading quizzes...</p>}
      {error && <div role="alert" className="space-y-3 rounded-lg bg-red-50 p-4 text-sm text-red-700"><p>{error}</p><Button variant="outline" onClick={() => { setError(null); setLoading(true); setRevision((v) => v + 1); }}>Retry</Button></div>}
      {!loading && !error && quizzes.length === 0 && <p className="text-sm text-slate-500">No quizzes are available for this track yet.</p>}
      {!loading && !error && quizzes.map((quiz) => <QuizCard key={quiz.id} quiz={quiz} student={student} />)}
    </CardContent>
  </Card>;
}

function QuizCard({ quiz, student }: { quiz: StudentQuiz; student: boolean }) {
  const navigate = useNavigate();
  const [latest, setLatest] = useState<QuizAttempt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const busy = useRef(false);
  const mounted = useRef(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    if (student) {
      void quizService.listAttempts(quiz.id, controller.signal, 0, 1)
        .then((items) => { if (!controller.signal.aborted) setLatest(items[0] ?? null); })
        .catch((error: unknown) => { if (!controller.signal.aborted) setError(quizError(error)); });
    }
    return () => { mounted.current = false; controller.abort(); };
  }, [quiz.id, student, revision]);
  async function start() {
    if (busy.current) return;
    busy.current = true;
    setStarting(true);
    setError(null);
    try {
      const attempt = await quizService.startAttempt(quiz.id);
      if (mounted.current) navigate(`/quizzes/${quiz.id}/attempts/${attempt.id}`);
    } catch (error) {
      if (mounted.current) setError(quizError(error));
    } finally {
      busy.current = false;
      if (mounted.current) setStarting(false);
    }
  }
  return <article className="rounded-xl border border-slate-200 p-4">
    <h3 className="font-semibold text-slate-900">{quiz.title}</h3>
    {quiz.description && <p className="mt-1 text-sm text-slate-600">{quiz.description}</p>}
    <p className="my-3 text-sm text-slate-500">{quiz.questions.length} questions | Passing: {quiz.passing_score}% | {quiz.time_limit_minutes === null ? "No time limit" : `${quiz.time_limit_minutes} min`}</p>
    {student && <div className="flex flex-wrap items-center gap-3">
      <Button disabled={starting || quiz.questions.length === 0} onClick={() => void start()}>{starting ? "Starting..." : latest?.status === "IN_PROGRESS" ? "Resume Quiz" : latest ? "Retake Quiz" : "Start Quiz"}</Button>
      {latest?.status === "COMPLETED" && <Button variant="outline" asChild><Link to={`/quiz-attempts/${latest.id}/results`}>View result {latest.score !== null && `(${formatQuizScore(latest.score)})`}</Link></Button>}
    </div>}
    {error && <div role="alert" className="mt-3 text-sm text-red-700"><p>{error}</p><Button variant="outline" size="sm" onClick={() => { setError(null); setRevision((v) => v + 1); }}>Reload attempt</Button></div>}
  </article>;
}
