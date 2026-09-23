import { useEffect, useState } from "react";
import { isAxiosError } from "axios";
import {
  ArrowRight,
  Clock3,
  ClipboardCheck,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { quizService } from "@/services/quiz.service";
import type { StudentQuiz } from "@/types/quiz";

interface QuizListProps {
  trackId: number;
}

function getErrorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }
  }

  return "Unable to load quizzes right now.";
}

function formatDuration(minutes: number | null) {
  if (!minutes || minutes <= 0) {
    return "No time limit";
  }

  if (minutes < 60) {
    return `${minutes} min`;
  }

  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;

  return remaining > 0
    ? `${hours}h ${remaining}m`
    : `${hours}h`;
}

export default function QuizList({ trackId }: QuizListProps) {
  const navigate = useNavigate();
  const [quizzes, setQuizzes] = useState<StudentQuiz[]>([]);
  const [loading, setLoading] = useState(true);
  const [startingQuizId, setStartingQuizId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadQuizzes() {
    setLoading(true);
    setError(null);

    try {
      const data = await quizService.getAvailableQuizzes({ trackId });
      setQuizzes(data);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadQuizzes();
  }, [trackId]);

  async function handleStartQuiz(quiz: StudentQuiz) {
    setStartingQuizId(quiz.id);
    setError(null);

    try {
      const attempt = await quizService.startAttempt(quiz.id);
      navigate(`/quizzes/${quiz.id}/attempts/${attempt.id}`);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setStartingQuizId(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <ClipboardCheck className="h-5 w-5 text-blue-600" />
              Quizzes
            </CardTitle>
            <CardDescription>
              Complete available assessments to check your understanding.
            </CardDescription>
          </div>

          <div className="text-sm text-slate-500">
            {quizzes.length} available
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-10 text-sm text-slate-500">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Loading quizzes...
          </div>
        ) : error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <span>{error}</span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void loadQuizzes()}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry
              </Button>
            </div>
          </div>
        ) : quizzes.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-6 text-center text-sm text-slate-500">
            No quizzes are available for this track yet.
          </div>
        ) : (
          <div className="space-y-3">
            {quizzes.map((quiz) => (
              <div
                key={quiz.id}
                className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-4 transition hover:border-blue-200 hover:bg-blue-50/30 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <h3 className="font-semibold text-slate-900">
                    {quiz.title}
                  </h3>

                  {quiz.description ? (
                    <p className="mt-1 text-sm text-slate-500">
                      {quiz.description}
                    </p>
                  ) : null}

                  <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
                    <span>{quiz.questions.length} questions</span>
                    <span>Passing: {quiz.passing_score}%</span>
                    <span className="inline-flex items-center gap-1">
                      <Clock3 className="h-3.5 w-3.5" />
                      {formatDuration(quiz.time_limit_minutes)}
                    </span>
                  </div>
                </div>

                <Button
                  type="button"
                  className="shrink-0"
                  disabled={startingQuizId !== null}
                  onClick={() => void handleStartQuiz(quiz)}
                >
                  {startingQuizId === quiz.id ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Starting...
                    </>
                  ) : (
                    <>
                      Start Quiz
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </>
                  )}
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
