import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { isAxiosError } from "axios";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Loader2,
  ShieldAlert,
} from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { quizService } from "@/services/quiz.service";
import type {
  QuizAttempt,
  QuizAttemptSubmit,
  StudentQuiz,
} from "@/types/quiz";

function getErrorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }
  }

  return "Something went wrong while loading the quiz.";
}

function formatTime(seconds: number) {
  const safeSeconds = Math.max(seconds, 0);
  const minutes = Math.floor(safeSeconds / 60);
  const remainingSeconds = safeSeconds % 60;

  return `${String(minutes).padStart(2, "0")}:${String(
    remainingSeconds,
  ).padStart(2, "0")}`;
}

export default function QuizTaker() {
  const { quizId: quizIdParam, attemptId: attemptIdParam } =
    useParams<{
      quizId: string;
      attemptId: string;
    }>();
  const navigate = useNavigate();

  const quizId = Number(quizIdParam);
  const attemptId = Number(attemptIdParam);

  const [quiz, setQuiz] = useState<StudentQuiz | null>(null);
  const [attempt, setAttempt] = useState<QuizAttempt | null>(null);
  const [answers, setAnswers] = useState<Record<number, number | null>>({});
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submittedRef = useRef(false);

  const orderedQuestions = useMemo(() => {
    return [...(quiz?.questions ?? [])].sort(
      (left, right) => left.ordering - right.ordering,
    );
  }, [quiz]);

  const navigateToResults = useCallback(() => {
    navigate(`/quiz-attempts/${attemptId}/results`, { replace: true });
  }, [attemptId, navigate]);

  const submitQuiz = useCallback(
    async (flagged: boolean, flagReason: string | null) => {
      if (!attempt || submittedRef.current) {
        return;
      }

      submittedRef.current = true;
      setSubmitting(true);
      setError(null);

      const payload: QuizAttemptSubmit = {
        answers: orderedQuestions.map(({ question }) => ({
          question_id: question.id,
          selected_option_id: answers[question.id] ?? null,
        })),
        is_flagged: flagged,
        flag_reason: flagReason,
      };

      try {
        await quizService.submitAttempt(attempt.id, payload);
        navigateToResults();
      } catch (requestError) {
        if (flagged) {
          navigateToResults();
          return;
        }

        submittedRef.current = false;
        setSubmitting(false);
        setError(getErrorMessage(requestError));
      }
    },
    [
      answers,
      attempt,
      navigateToResults,
      orderedQuestions,
    ],
  );

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (
        !Number.isInteger(quizId) ||
        !Number.isInteger(attemptId) ||
        quizId <= 0 ||
        attemptId <= 0
      ) {
        setError("Invalid quiz attempt.");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const [quizData, attemptData] = await Promise.all([
          quizService.getQuiz(quizId),
          quizService.getAttempt(attemptId),
        ]);

        if (cancelled) {
          return;
        }

        if (attemptData.quiz_id !== quizData.id) {
          setError("This quiz attempt does not belong to the selected quiz.");
          return;
        }

        if (attemptData.status === "COMPLETED") {
          navigateToResults();
          return;
        }

        setQuiz(quizData);
        setAttempt(attemptData);

        const initialAnswers: Record<number, number | null> = {};

        for (const questionLink of quizData.questions) {
          initialAnswers[questionLink.question.id] = null;
        }

        for (const answer of attemptData.answers) {
          initialAnswers[answer.question_id] =
            answer.selected_option_id ?? null;
        }

        setAnswers(initialAnswers);
      } catch (requestError) {
        if (!cancelled) {
          setError(getErrorMessage(requestError));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [attemptId, navigateToResults, quizId]);

  useEffect(() => {
    if (!attempt || !quiz?.time_limit_minutes) {
      setRemainingSeconds(null);
      return;
    }

    const durationSeconds = quiz.time_limit_minutes * 60;
    const startedAt = new Date(attempt.started_at).getTime();

    function updateRemaining() {
      const elapsedSeconds = Math.floor(
        (Date.now() - startedAt) / 1000,
      );
      const nextRemaining = Math.max(
        durationSeconds - elapsedSeconds,
        0,
      );

      setRemainingSeconds(nextRemaining);
    }

    updateRemaining();

    const timerId = window.setInterval(updateRemaining, 1000);

    return () => {
      window.clearInterval(timerId);
    };
  }, [attempt, quiz]);

  useEffect(() => {
    if (remainingSeconds !== 0 || !attempt || submittedRef.current) {
      return;
    }

    void submitQuiz(true, "TIME_LIMIT_EXCEEDED");
  }, [attempt, remainingSeconds, submitQuiz]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        void submitQuiz(true, "VISIBILITY_HIDDEN");
      }
    };

    const handleWindowBlur = () => {
      void submitQuiz(true, "WINDOW_BLUR");
    };

    document.addEventListener(
      "visibilitychange",
      handleVisibilityChange,
    );
    window.addEventListener("blur", handleWindowBlur);

    return () => {
      document.removeEventListener(
        "visibilitychange",
        handleVisibilityChange,
      );
      window.removeEventListener("blur", handleWindowBlur);
    };
  }, [submitQuiz]);

  if (loading) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-4xl items-center justify-center px-4">
        <div className="flex items-center text-sm text-slate-500">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          Loading quiz...
        </div>
      </div>
    );
  }

  if (error || !quiz || !attempt) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <Card className="border-red-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-700">
              <AlertTriangle className="h-5 w-5" />
              Quiz unavailable
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-600">
              {error ?? "Unable to load this quiz attempt."}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl">
        <div className="mb-6 rounded-2xl border border-blue-100 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-600">
                Assessment
              </p>
              <h1 className="mt-1 text-2xl font-bold text-slate-900">
                {quiz.title}
              </h1>
              {quiz.description ? (
                <p className="mt-2 text-sm text-slate-500">
                  {quiz.description}
                </p>
              ) : null}
            </div>

            <div className="flex shrink-0 flex-col items-start gap-2 sm:items-end">
              {remainingSeconds !== null ? (
                <div
                  className={[
                    "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold",
                    remainingSeconds <= 60
                      ? "bg-red-50 text-red-700"
                      : "bg-blue-50 text-blue-700",
                  ].join(" ")}
                >
                  <Clock3 className="h-4 w-4" />
                  {formatTime(remainingSeconds)}
                </div>
              ) : (
                <span className="text-sm text-slate-500">
                  No time limit
                </span>
              )}

              <div className="text-xs text-slate-500">
                Passing score: {quiz.passing_score}%
              </div>
            </div>
          </div>
        </div>

        <div className="mb-5 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-semibold">Assessment integrity is enabled.</p>
            <p className="mt-1">
              Leaving the quiz window or switching away from this page
              will automatically submit and flag the attempt.
            </p>
          </div>
        </div>

        <div className="space-y-5">
          {orderedQuestions.map(({ question }, index) => (
            <Card key={question.id}>
              <CardHeader>
                <CardTitle className="text-base">
                  Question {index + 1}
                </CardTitle>
                <CardDescription>
                  {question.points} point{question.points === 1 ? "" : "s"}
                </CardDescription>
              </CardHeader>

              <CardContent>
                <p className="mb-5 whitespace-pre-wrap text-sm leading-6 text-slate-900 sm:text-base">
                  {question.text}
                </p>

                <div className="space-y-3">
                  {question.options.map((option) => {
                    const selected =
                      answers[question.id] === option.id;

                    return (
                      <label
                        key={option.id}
                        className={[
                          "flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition",
                          selected
                            ? "border-blue-500 bg-blue-50"
                            : "border-slate-200 hover:border-blue-200 hover:bg-slate-50",
                        ].join(" ")}
                      >
                        <input
                          type="radio"
                          name={`question-${question.id}`}
                          value={option.id}
                          checked={selected}
                          disabled={submitting}
                          onChange={() =>
                            setAnswers((current) => ({
                              ...current,
                              [question.id]: option.id,
                            }))
                          }
                          className="mt-1 h-4 w-4 accent-blue-600"
                        />
                        <span className="text-sm leading-6 text-slate-800">
                          {option.text}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {error ? (
          <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <div className="sticky bottom-0 mt-6 border-t border-slate-200 bg-slate-50/95 py-4 backdrop-blur">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-slate-500">
              Review your answers before submitting.
            </p>

            <Button
              type="button"
              size="lg"
              disabled={submitting}
              onClick={() =>
                void submitQuiz(false, null)
              }
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Submit Quiz
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
