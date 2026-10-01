import { useCallback, useEffect, useRef, useState } from "react";
import { Clock3, Loader2, ShieldAlert } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/context/AuthContext";
import { canTakeQuiz, formatQuizTime, quizError, quizPayload, remainingQuizSeconds } from "@/lib/quizzes";
import { quizService } from "@/services/quiz.service";
import type { QuizAttempt, StudentQuiz } from "@/types/quiz";

export default function QuizTaker() {
  const { quizId, attemptId } = useParams<{ quizId: string; attemptId: string }>();
  const { user } = useAuth();
  if (!canTakeQuiz(user)) return <p role="alert" className="p-6">Only students can take quizzes.</p>;
  return <ActiveQuiz key={`${quizId}-${attemptId}-${user?.id}`} quizId={Number(quizId)} attemptId={Number(attemptId)} userId={Number(user?.id)} />;
}

function ActiveQuiz({ quizId, attemptId, userId }: { quizId: number; attemptId: number; userId: number }) {
  const navigate = useNavigate();
  const [quiz, setQuiz] = useState<StudentQuiz | null>(null);
  const [attempt, setAttempt] = useState<QuizAttempt | null>(null);
  const [answers, setAnswers] = useState<Record<number, number | null>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [now, setNow] = useState(Date.now);
  const busy = useRef(false);
  const mounted = useRef(true);
  const automaticSubmit = useRef(false);
  const integrityReason = useRef<string | null>(null);
  const remaining = remainingQuizSeconds(attempt?.deadline_at ?? null, now);
  const questions = quiz?.questions ?? [];

  const navigateToResults = useCallback(() => {
    navigate(`/quiz-attempts/${attemptId}/results`, { replace: true });
  }, [attemptId, navigate]);

  useEffect(() => {
    const controller = new AbortController();
    mounted.current = true;
    async function load() {
      if (!Number.isSafeInteger(quizId) || !Number.isSafeInteger(attemptId) || quizId <= 0 || attemptId <= 0) {
        setError("Invalid quiz attempt.");
        setLoading(false);
        return;
      }
      try {
        // Read the attempt first so a completed attempt can still show its
        // stored results even when its quiz has since been deactivated.
        const record = await quizService.getAttempt(attemptId, controller.signal);
        if (controller.signal.aborted) return;
        if (record.quiz_id !== quizId || record.user_id !== userId) {
          setError("This attempt does not belong to you or the selected quiz.");
          return;
        }
        if (record.status === "COMPLETED") { navigateToResults(); return; }
        const paper = await quizService.getQuiz(quizId, controller.signal);
        if (controller.signal.aborted) return;
        setQuiz(paper);
        setAttempt(record);
        setAnswers(Object.fromEntries(record.answers.map((answer) => [answer.question_id, answer.selected_option_id])));
        setNow(Date.now());
      } catch (error) {
        if (!controller.signal.aborted) setError(quizError(error));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => { mounted.current = false; controller.abort(); };
  }, [attemptId, quizId, userId, navigateToResults, revision]);

  useEffect(() => {
    if (!attempt?.deadline_at) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [attempt?.deadline_at]);

  const submit = useCallback(async (flagReason: string | null = null) => {
    if (!attempt || !quiz || busy.current) return;
    if (flagReason) integrityReason.current ??= flagReason;
    busy.current = true;
    setSubmitting(true);
    setError(null);
    try {
      const record = await quizService.submitAndConfirm(attempt.id, quizPayload(quiz.questions, answers, integrityReason.current));
      if (mounted.current && record.status === "COMPLETED") navigateToResults();
    } catch (error) {
      if (mounted.current) setError(`${quizError(error)} Your answers are still on this page. Retry submitting.`);
    } finally {
      busy.current = false;
      if (mounted.current) setSubmitting(false);
    }
  }, [answers, attempt, quiz, navigateToResults]);

  useEffect(() => {
    if (remaining !== 0 || !attempt || automaticSubmit.current) return;
    const timer = window.setTimeout(() => {
      automaticSubmit.current = true;
      // Only the server decides whether its deadline has expired.
      void submit();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [remaining, attempt, submit]);

  useEffect(() => {
    if (!attempt || loading) return;
    const flag = (reason: string) => {
      if (automaticSubmit.current || busy.current) return;
      automaticSubmit.current = true;
      void submit(reason);
    };
    const visibility = () => { if (document.visibilityState === "hidden") flag("VISIBILITY_HIDDEN"); };
    const blur = () => flag("WINDOW_BLUR");
    document.addEventListener("visibilitychange", visibility);
    window.addEventListener("blur", blur);
    return () => { document.removeEventListener("visibilitychange", visibility); window.removeEventListener("blur", blur); };
  }, [attempt, loading, submit]);

  if (loading) return <div role="status" className="flex min-h-[60vh] items-center justify-center gap-2 text-slate-500"><Loader2 className="h-5 w-5 animate-spin" />Loading quiz...</div>;
  if (!quiz || !attempt) return <div className="mx-auto max-w-3xl p-6"><Card>
    <CardHeader><CardTitle>Quiz unavailable</CardTitle></CardHeader>
    <CardContent className="space-y-4"><p role="alert">{error ?? "Unable to load this quiz."}</p><Button onClick={() => { setError(null); setLoading(true); setRevision((value) => value + 1); }}>Retry</Button></CardContent>
  </Card></div>;

  const answered = questions.filter(({ question_id }) => answers[question_id] != null).length;
  return <main className="min-h-screen bg-slate-50 px-4 py-6 sm:px-6">
    <div className="mx-auto max-w-4xl space-y-5">
      <header className="rounded-2xl border border-blue-100 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">Assessment</p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">{quiz.title}</h1>
        {quiz.description && <p className="mt-2 text-sm text-slate-600">{quiz.description}</p>}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
          <span>Passing score: {attempt.passing_score ?? quiz.passing_score}%</span>
          <span role="timer" aria-label="Time remaining" className={`flex items-center gap-2 font-semibold ${remaining !== null && remaining <= 60 ? "text-red-700" : "text-blue-700"}`}><Clock3 className="h-4 w-4" />{remaining === null ? "No time limit" : formatQuizTime(remaining)}</span>
        </div>
      </header>
      <div className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"><ShieldAlert className="h-5 w-5 shrink-0" /><p>Leaving this window or switching tabs automatically submits and flags the attempt. A flagged or expired attempt receives zero. Keep this page open until you submit.</p></div>
      {questions.map(({ question }, index) => <fieldset key={question.id} disabled={submitting || remaining === 0} className="rounded-xl border border-slate-200 bg-white p-5">
        <legend className="px-2 font-semibold">Question {index + 1} <span className="font-normal text-slate-500">({question.points} points)</span></legend>
        <p className="mb-4 whitespace-pre-wrap leading-7">{question.text}</p>
        <div className="space-y-3">{question.options.map((option) => <label key={option.id} className={`flex cursor-pointer items-start gap-3 rounded-xl border p-4 ${answers[question.id] === option.id ? "border-blue-500 bg-blue-50" : "border-slate-200 hover:bg-slate-50"}`}>
          <input type="radio" name={`question-${question.id}`} value={option.id} checked={answers[question.id] === option.id} onChange={() => setAnswers((current) => ({ ...current, [question.id]: option.id }))} className="mt-1 h-4 w-4 accent-blue-600" />
          <span className="whitespace-pre-wrap text-sm leading-6">{option.text}</span>
        </label>)}</div>
      </fieldset>)}
      {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      <div className="sticky bottom-0 flex flex-wrap items-center justify-between gap-4 border-t border-slate-200 bg-slate-50/95 py-4 backdrop-blur">
        <p className="text-sm text-slate-600">{answered} of {questions.length} answered. Unanswered questions receive zero.</p>
        <Button size="lg" disabled={submitting} onClick={() => void submit()}>{submitting ? "Submitting..." : "Submit Quiz"}</Button>
      </div>
    </div>
  </main>;
}
