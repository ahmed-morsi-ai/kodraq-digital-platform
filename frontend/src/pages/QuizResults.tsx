import { useEffect, useState } from "react";
import { quizError, formatQuizScore } from "@/lib/quizzes";
import { useAuth } from "@/context/AuthContext";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Loader2,
  XCircle,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { quizService } from "@/services/quiz.service";
import type { QuizResult } from "@/types/quiz";

function formatDuration(seconds: number) {
  const safeSeconds = Math.max(Math.round(seconds), 0);
  const minutes = Math.floor(safeSeconds / 60);
  const remainingSeconds = safeSeconds % 60;

  if (minutes === 0) {
    return `${remainingSeconds}s`;
  }

  return `${minutes}m ${remainingSeconds}s`;
}

export default function QuizResults() {
  const { attemptId: attemptIdParam } = useParams<{
    attemptId: string;
  }>();
  const { user } = useAuth();
  return <AttemptResults key={`${attemptIdParam}-${user?.id}`} attemptId={Number(attemptIdParam)} />;
}

function AttemptResults({ attemptId }: { attemptId: number }) {

  const [result, setResult] = useState<QuizResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      if (!Number.isInteger(attemptId) || attemptId <= 0) {
        setError("Invalid quiz attempt.");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const data = await quizService.getResult(attemptId, controller.signal);

        if (!controller.signal.aborted) {
          setResult(data);
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(quizError(requestError));
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      controller.abort();
    };
  }, [attemptId, revision]);

  if (loading) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-4xl items-center justify-center px-4">
        <div className="flex items-center text-sm text-slate-500">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          Loading results...
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <Card className="border-red-200">
          <CardHeader>
            <CardTitle className="text-red-700">
              Results unavailable
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-600">
              {error ?? "Unable to load this result."}
            </p>
            <Button className="mt-4" onClick={() => { setLoading(true); setError(null); setRevision((value) => value + 1); }}>Retry</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <QuizResultView result={result} />;
}

export function QuizResultView({ result }: { result: QuizResult }) {
  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl">
        <Card className="mb-6 overflow-hidden">
          <CardHeader>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-2xl">
                  {result.passed ? (
                    <CheckCircle2 className="h-6 w-6 text-emerald-600" />
                  ) : (
                    <XCircle className="h-6 w-6 text-red-600" />
                  )}
                  Quiz Results
                </CardTitle>
                <CardDescription className="mt-2">
                  Attempt #{result.attempt_id}
                </CardDescription>
              </div>

              <div
                className={[
                  "rounded-xl px-5 py-4 text-center",
                  result.passed
                    ? "bg-emerald-50 text-emerald-800"
                    : "bg-red-50 text-red-800",
                ].join(" ")}
              >
                <div className="text-3xl font-bold">
                  {formatQuizScore(result.percentage)}
                </div>
                <div className="text-xs font-semibold uppercase tracking-wide">
                  {result.passed ? "Passed" : "Not passed"}
                </div>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl bg-slate-50 p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Score
                </p>
                <p className="mt-1 text-xl font-semibold text-slate-900">
                  {formatQuizScore(result.score)}
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Points earned
                </p>
                <p className="mt-1 text-xl font-semibold text-slate-900">
                  {result.earned_points} / {result.max_score}
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Time taken
                </p>
                <p className="mt-1 flex items-center gap-2 text-xl font-semibold text-slate-900">
                  <Clock3 className="h-5 w-5 text-slate-400" />
                  {formatDuration(result.time_taken_seconds)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {result.is_flagged ? (
          <Card className="mb-6 border-amber-200 bg-amber-50">
            <CardContent className="flex gap-3 pt-6 text-sm text-amber-800">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
              <div>
                <p className="font-semibold">Attempt flagged</p>
                <p className="mt-1">
                  {result.flag_reason === "TIME_LIMIT_EXCEEDED" ? "The time limit expired. This attempt received zero." : "This attempt received zero because it was flagged by the assessment integrity system."}
                </p>
              </div>
            </CardContent>
          </Card>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle>Question review</CardTitle>
            <CardDescription>
              Review your submitted answers and the recorded correct
              answer.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <div className="space-y-4">
              {result.questions.map((question, index) => (
                <div
                  key={question.question_id}
                  className="rounded-xl border border-slate-200 p-4"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        Question {index + 1}
                      </p>
                      <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                        {question.question_text}
                      </p>
                    </div>

                    <span
                      className={[
                        "inline-flex shrink-0 items-center rounded-full px-2.5 py-1 text-xs font-semibold",
                        question.is_correct
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-red-50 text-red-700",
                      ].join(" ")}
                    >
                      {question.is_correct ? "Correct" : "Incorrect"}
                    </span>
                  </div>

                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-lg bg-slate-50 p-3">
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                        Your answer
                      </p>
                      <p className="mt-1 text-sm text-slate-800">
                        {question.selected_option_text ??
                          "No answer selected"}
                      </p>
                    </div>

                    <div className="rounded-lg bg-blue-50 p-3">
                      <p className="text-xs font-medium uppercase tracking-wide text-blue-600">
                        Correct answer
                      </p>
                      <p className="mt-1 text-sm text-slate-800">
                        {question.correct_option_texts.length > 0
                          ? question.correct_option_texts.join(", ")
                          : "No correct option recorded"}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="mt-6">
          <Button asChild>
            <Link to="/dashboard">Return to Dashboard</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
