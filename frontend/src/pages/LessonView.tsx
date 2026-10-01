import { useEffect, useMemo, useState } from "react";
import { isAxiosError } from "axios";
import { ArrowLeft, Languages, Loader2, Send, Sparkles, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { Link, Navigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/context/AuthContext";
import { getEmbedUrl } from "@/lib/youtube";
import { enrollmentService } from "@/services/enrollment.service";
import { lessonChatService } from "@/services/lessonChat.service";
import { trackService } from "@/services/track.service";
import type { Enrollment } from "@/types/enrollment";
import type { Lesson, LessonQuizQuestion, TrackCurriculum } from "@/types/track";
import type {
  LessonChatMessage,
  LessonTranslation,
} from "@/services/lessonChat.service";

const lessonMarkdownSchema = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames ?? []), "iframe"],
  attributes: {
    ...defaultSchema.attributes,
    iframe: [
      ["src", /^https:\/\/www\.youtube\.com\/embed\/[\w-]+$/],
      "width",
      "height",
      "title",
      "frameBorder",
      "allow",
      "allowFullScreen",
    ],
  },
};

function getRequestError(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return "Unable to load this lesson. Please return to the track and try again.";
}

function getTranslationError(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  if (error instanceof Error && error.message) return error.message;
  return "Arabic translation is unavailable right now. Please try again.";
}

function isLessonQuizQuestion(value: unknown): value is LessonQuizQuestion {
  if (!value || typeof value !== "object") return false;
  const question = value as Partial<LessonQuizQuestion>;
  return typeof question.id === "number"
    && typeof question.question === "string"
    && Array.isArray(question.options)
    && question.options.length > 0
    && question.options.every((option) => typeof option === "string")
    && typeof question.correct_index === "number"
    && Number.isInteger(question.correct_index)
    && question.correct_index >= 0
    && question.correct_index < question.options.length
    && typeof question.explanation === "string";
}

function parseLessonQuiz(
  rawQuiz: Lesson["quiz_data"] | undefined,
): LessonQuizQuestion[] {
  let parsedQuiz: unknown = rawQuiz;
  if (typeof rawQuiz === "string") {
    try {
      parsedQuiz = JSON.parse(rawQuiz);
    } catch (parseError) {
      console.error("Unable to parse lesson quiz data", parseError);
      return [];
    }
  }

  return Array.isArray(parsedQuiz)
    ? parsedQuiz.filter(isLessonQuizQuestion)
    : [];
}

export default function LessonView() {
  const { trackId: trackIdParam, lessonId: lessonIdParam } = useParams();
  const { user } = useAuth();
  const trackId = Number(trackIdParam);
  const lessonId = Number(lessonIdParam);
  const hasValidRoute = Number.isInteger(trackId) && trackId > 0
    && Number.isInteger(lessonId) && lessonId > 0;
  const [track, setTrack] = useState<TrackCurriculum | null>(null);
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<LessonChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [progressWarning, setProgressWarning] = useState<string | null>(null);
  const [isArabic, setIsArabic] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [translatedLesson, setTranslatedLesson] = useState<LessonTranslation | null>(null);
  const [translationError, setTranslationError] = useState<string | null>(null);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, number>>({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);

  const enrollment = enrollments.find((item) => item.track_id === trackId);
  const hasAccess = Boolean(
    user?.is_superuser || enrollment?.status === "active",
  );
  const rawQuiz = lesson?.quiz_data;
  const quizList = useMemo(() => parseLessonQuiz(rawQuiz), [rawQuiz]);
  const displayQuizList = isArabic && translatedLesson
    ? translatedLesson.quiz_data
    : quizList;
  const displayTitle = isArabic && translatedLesson
    ? translatedLesson.title
    : lesson?.title ?? "";
  const displayContent = isArabic && translatedLesson
    ? translatedLesson.content
    : lesson?.content ?? "";
  const quizScore = displayQuizList.reduce(
    (score, quizQuestion) => score + (
      selectedAnswers[quizQuestion.id] === quizQuestion.correct_index ? 1 : 0
    ),
    0,
  );
  const quizPercentage = displayQuizList.length
    ? Math.round((quizScore / displayQuizList.length) * 100)
    : 0;
  const allQuestionsAnswered = displayQuizList.length > 0
    && displayQuizList.every((quizQuestion) => selectedAnswers[quizQuestion.id] !== undefined);

  useEffect(() => {
    console.log("Lesson Quiz Data:", quizList);
  }, [lesson?.id, quizList]);

  useEffect(() => {
    setSelectedAnswers({});
    setQuizSubmitted(false);
    setIsArabic(false);
    setTranslatedLesson(null);
    setTranslationError(null);
  }, [lessonId]);

  useEffect(() => {
    let active = true;
    if (!hasValidRoute) return;

    void Promise.all([
      trackService.getCurriculum(trackId),
      enrollmentService.getMyEnrollments(),
    ]).then(([curriculum, userEnrollments]) => {
      if (!active) return;
      const selectedLesson = curriculum.modules
        .flatMap((module) => module.lessons)
        .find((item) => item.id === lessonId);
      setTrack(curriculum);
      setLesson(selectedLesson ?? null);
      setEnrollments(userEnrollments);
      if (!selectedLesson) setError("This lesson was not found in the track.");
      else setError(null);
    }).catch((requestError: unknown) => {
      if (active) setError(getRequestError(requestError));
    }).finally(() => {
      if (active) setIsLoading(false);
    });

    return () => {
      active = false;
    };
  }, [hasValidRoute, lessonId, trackId]);

  useEffect(() => {
    if (!lesson || !hasAccess || !enrollment) return;
    let active = true;
    void enrollmentService.getProgress(enrollment.id)
      .then((existingProgress) => {
        if (existingProgress.some((item) => item.lesson_id === lesson.id)) return;
        return enrollmentService.createProgress(enrollment.id, {
          lesson_id: lesson.id,
          status: "in_progress",
          progress_percentage: 0,
        });
      })
      .then(() => {
        if (active) setProgressWarning(null);
      })
      .catch((requestError: unknown) => {
        console.error("Lesson opened, but progress sync failed", requestError);
        if (active) {
          setProgressWarning("Lesson is open, but progress could not be synced.");
        }
      });
    return () => {
      active = false;
    };
  }, [enrollment, hasAccess, lesson]);

  const sendQuestion = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const prompt = question.trim();
    if (!lesson || !track || !prompt || isSending) return;

    const nextHistory: LessonChatMessage[] = [
      ...messages,
      { role: "user", content: prompt },
    ];
    setMessages(nextHistory);
    setQuestion("");
    setIsSending(true);
    setChatError(null);
    try {
      const answer = await lessonChatService.ask(lesson, track.name, nextHistory);
      setMessages([...nextHistory, { role: "assistant", content: answer }]);
    } catch (requestError) {
      setChatError(getRequestError(requestError));
    } finally {
      setIsSending(false);
    }
  };

  const toggleArabic = async () => {
    if (isArabic) {
      setIsArabic(false);
      return;
    }
    if (translatedLesson) {
      setIsArabic(true);
      return;
    }
    if (!lesson) return;

    setIsTranslating(true);
    setTranslationError(null);
    try {
      const translation = await lessonChatService.translateToArabic(lesson, quizList);
      setTranslatedLesson(translation);
      setIsArabic(true);
    } catch (requestError) {
      setTranslationError(getTranslationError(requestError));
    } finally {
      setIsTranslating(false);
    }
  };

  const selectQuizAnswer = (quizQuestion: LessonQuizQuestion, optionIndex: number) => {
    setSelectedAnswers((currentAnswers) => ({
      ...currentAnswers,
      [quizQuestion.id]: optionIndex,
    }));
  };

  const resetQuiz = () => {
    setSelectedAnswers({});
    setQuizSubmitted(false);
  };

  if (!hasValidRoute) {
    return (
      <main className="mx-auto max-w-3xl px-5 py-10">
        <Card><CardContent className="space-y-4 p-6">
          <p role="alert" className="text-sm text-red-700">Invalid lesson address.</p>
        </CardContent></Card>
      </main>
    );
  }

  if (isLoading) {
    return (
      <div role="status" className="flex min-h-[60vh] items-center justify-center gap-2 text-sm text-slate-600">
        <Loader2 aria-hidden="true" className="size-4 animate-spin" /> Loading lesson...
      </div>
    );
  }

  if (error || !track || !lesson) {
    return (
      <main className="mx-auto max-w-3xl px-5 py-10">
        <Card><CardContent className="space-y-4 p-6">
          <p role="alert" className="text-sm text-red-700">{error ?? "Lesson unavailable."}</p>
          <Button asChild variant="outline"><Link to={`/tracks/${trackId}`}>Back to track</Link></Button>
        </CardContent></Card>
      </main>
    );
  }

  if (!hasAccess) return <Navigate to={`/tracks/${trackId}`} replace />;
  const videoEmbedUrl = getEmbedUrl(lesson.video_url ?? "");

  return (
    <main className="mx-auto grid max-w-7xl gap-6 px-5 py-8 sm:px-8 lg:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.8fr)]">
      <section className="space-y-5">
        <Button asChild variant="ghost" className="px-0 text-slate-600">
          <Link to={`/tracks/${trackId}`}><ArrowLeft aria-hidden="true" className="size-4" /> Back to track</Link>
        </Button>
        <Card className="border-slate-200">
          <CardHeader className="gap-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold uppercase text-sky-700">{track.name}</p>
                <CardTitle className="mt-2 text-2xl">{displayTitle}</CardTitle>
              </div>
              <Button
                type="button"
                variant="outline"
                className="h-auto max-w-full whitespace-normal"
                onClick={() => void toggleArabic()}
                disabled={isTranslating}
              >
                {isTranslating ? (
                  <Loader2 aria-hidden="true" className="size-4 animate-spin" />
                ) : (
                  <Languages aria-hidden="true" className="size-4" />
                )}
                {isTranslating
                  ? "Translating..."
                  : isArabic
                    ? "Show English / عرض الإنجليزية"
                    : "Translate to Arabic / ترجم للعربية 🌐"}
              </Button>
            </div>
            {isTranslating && (
              <p role="status" className="flex items-center gap-2 text-sm text-sky-800">
                <Loader2 aria-hidden="true" className="size-4 animate-spin" />
                Translating lesson and quiz...
              </p>
            )}
            {translationError && (
              <div role="alert" className="flex items-start justify-between gap-3 rounded-md bg-rose-50 p-3 text-sm text-rose-800">
                <p className="min-w-0 flex-1">{translationError}</p>
                <button
                  type="button"
                  aria-label="Dismiss translation error"
                  onClick={() => setTranslationError(null)}
                  className="shrink-0 rounded p-1 hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600"
                >
                  <X aria-hidden="true" className="size-4" />
                </button>
              </div>
            )}
          </CardHeader>
          <CardContent className="space-y-5">
            {videoEmbedUrl && (
              <div className="aspect-video w-full overflow-hidden rounded-md bg-slate-950">
                <iframe
                  className="h-full w-full border-0"
                  src={videoEmbedUrl}
                  title={`${lesson.title} video`}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  referrerPolicy="strict-origin-when-cross-origin"
                  allowFullScreen
                  loading="lazy"
                />
              </div>
            )}
            {progressWarning && (
              <p role="status" className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                {progressWarning}
              </p>
            )}
            <article dir={isArabic ? "rtl" : "ltr"} className={`min-w-0 break-words ${isArabic ? "text-right" : "text-left"} font-sans text-sm leading-7 text-slate-700 transition-opacity duration-300 [overflow-wrap:anywhere] [&_blockquote]:my-5 [&_blockquote]:border-l-4 [&_blockquote]:border-slate-300 [&_blockquote]:pl-4 [&_h1]:mb-4 [&_h1]:mt-2 [&_h1]:text-3xl [&_h1]:font-bold [&_h2]:mb-3 [&_h2]:mt-8 [&_h2]:text-xl [&_h2]:font-semibold [&_h3]:mb-2 [&_h3]:mt-6 [&_h3]:text-lg [&_h3]:font-semibold [&_li]:ml-6 [&_ol]:my-4 [&_ol]:list-decimal [&_p]:my-4 [&_pre]:my-5 [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-slate-950 [&_pre]:p-4 [&_pre]:text-slate-100 [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_ul]:my-4 [&_ul]:list-disc`}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[
                  rehypeRaw,
                  [rehypeSanitize, lessonMarkdownSchema],
                ]}
                components={{
                  iframe: ({ src, title }) => {
                    if (
                      typeof src !== "string"
                      || !/^https:\/\/www\.youtube\.com\/embed\/[\w-]+$/.test(src)
                    ) {
                      return null;
                    }
                    return (
                      <div className="my-5 aspect-video w-full overflow-hidden rounded-md bg-slate-950">
                        <iframe
                          className="h-full w-full border-0"
                          src={src}
                          title={title ?? "Lesson video resource"}
                          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                          referrerPolicy="strict-origin-when-cross-origin"
                          allowFullScreen
                          loading="lazy"
                        />
                      </div>
                    );
                  },
                  pre: ({ children }) => (
                    <pre dir="ltr" className="my-5 overflow-x-auto rounded-md bg-slate-950 p-4 text-left text-slate-100">
                      {children}
                    </pre>
                  ),
                  table: ({ children }) => (
                    <div className="my-5 overflow-x-auto">
                      <table className="w-full border-collapse text-left text-sm">
                        {children}
                      </table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th className="border border-slate-300 bg-slate-100 px-3 py-2 font-semibold">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="border border-slate-300 px-3 py-2 align-top">
                      {children}
                    </td>
                  ),
                  code: ({ children, className }) => (
                    <code dir="ltr" className={`${className ?? ""} rounded bg-slate-100 px-1 py-0.5 font-mono text-[0.9em]`}>
                      {children}
                    </code>
                  ),
                }}
              >
                {displayContent || "No lesson content has been published yet."}
              </ReactMarkdown>
            </article>
            {quizList.length > 0 && (
              <section
                dir={isArabic ? "rtl" : "ltr"}
                className={`mt-12 rounded-xl border-t border-slate-200 bg-slate-50 p-6 pt-8 ${isArabic ? "text-right" : "text-left"}`}
                aria-labelledby="lesson-quiz-title"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 id="lesson-quiz-title" className="text-2xl font-bold text-slate-900">
                    {isArabic
                      ? "🧪 اختبار تفاعلي لتأكيد الفهم"
                      : "Lesson Comprehension Quiz"}
                  </h2>
                  {quizSubmitted && (
                    <span
                      role="status"
                      dir="ltr"
                      className="rounded-full bg-sky-100 px-3 py-1 text-sm font-semibold text-sky-900"
                    >
                      {isArabic ? "النتيجة" : "Score"}: {quizScore}/{displayQuizList.length} - {quizPercentage}%
                    </span>
                  )}
                </div>

                <div dir={isArabic ? "rtl" : "ltr"} className={`mt-6 space-y-5 ${isArabic ? "text-right" : "text-left"}`}>
                  <div className="space-y-4">
                  {displayQuizList.map((quizQuestion, questionIndex) => (
                    <fieldset key={quizQuestion.id} className="min-w-0 rounded-md border border-slate-200 p-4">
                      <legend className="max-w-full px-1 font-semibold leading-6 text-slate-900">
                        {questionIndex + 1}. {quizQuestion.question}
                      </legend>
                      <div className="mt-2 space-y-2">
                        {quizQuestion.options.map((option, optionIndex) => {
                          const isCorrect = quizSubmitted
                            && optionIndex === quizQuestion.correct_index;
                          const isChosenWrong = quizSubmitted
                            && selectedAnswers[quizQuestion.id] === optionIndex
                            && optionIndex !== quizQuestion.correct_index;
                          const optionStyle = isCorrect
                            ? "border-emerald-300 bg-emerald-50 text-emerald-950"
                            : isChosenWrong
                              ? "border-red-300 bg-red-50 text-red-950"
                              : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50";

                          return (
                            <label
                              key={`${quizQuestion.id}-${optionIndex}`}
                              className={`flex min-w-0 cursor-pointer items-start gap-3 rounded-md border p-3 text-sm leading-6 [overflow-wrap:anywhere] ${optionStyle}`}
                            >
                              <input
                                type="radio"
                                name={`lesson-${lesson.id}-quiz-${quizQuestion.id}`}
                                value={optionIndex}
                                checked={selectedAnswers[quizQuestion.id] === optionIndex}
                                onChange={() => selectQuizAnswer(quizQuestion, optionIndex)}
                                disabled={quizSubmitted}
                                className="mt-1 size-4 shrink-0 accent-sky-700"
                              />
                              <span className="min-w-0 flex-1">{option}</span>
                              {isCorrect && <span className="shrink-0 font-semibold">{isArabic ? "إجابة صحيحة" : "Correct"}</span>}
                              {isChosenWrong && <span className="shrink-0 font-semibold">{isArabic ? "إجابتك" : "Your answer"}</span>}
                            </label>
                          );
                        })}
                      </div>
                      {quizSubmitted && (
                        <div className="mt-4 rounded-md border border-sky-200 bg-sky-50 p-3 text-sm leading-6 text-sky-950">
                          <p className="font-semibold">{isArabic ? "التفسير" : "Explanation"}</p>
                          <p className="mt-1">{quizQuestion.explanation}</p>
                        </div>
                      )}
                    </fieldset>
                  ))}
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    {!quizSubmitted ? (
                      <>
                        <Button
                          type="button"
                          onClick={() => setQuizSubmitted(true)}
                          disabled={!allQuestionsAnswered}
                        >
                          {isArabic ? "تسليم الإجابات" : "Submit Answers"}
                        </Button>
                        {!allQuestionsAnswered && (
                          <p className="text-sm text-slate-500">
                            {isArabic ? "أجب عن جميع الأسئلة قبل التسليم." : "Answer every question to submit."}
                          </p>
                        )}
                      </>
                    ) : (
                      <Button type="button" variant="outline" onClick={resetQuiz}>
                        {isArabic ? "إعادة المحاولة" : "Try Again"}
                      </Button>
                    )}
                  </div>
                </div>
              </section>
            )}
          </CardContent>
        </Card>
      </section>

      <Card className="flex max-h-[78vh] min-h-[480px] flex-col border-slate-200">
        <CardHeader className="border-b border-slate-100">
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles aria-hidden="true" className="size-4 text-sky-700" /> Lesson tutor
          </CardTitle>
          <p className="text-xs leading-5 text-slate-500">Answers are grounded in this lesson’s content.</p>
        </CardHeader>
        <CardContent className="flex min-h-0 flex-1 flex-col gap-4 p-4">
          <div className="flex-1 space-y-3 overflow-y-auto" aria-live="polite">
            {messages.length === 0 && (
              <p className="rounded-md bg-slate-50 p-3 text-sm leading-6 text-slate-600">
                Ask a question about “{lesson.title}”.
              </p>
            )}
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`max-w-[92%] whitespace-pre-wrap rounded-md p-3 text-sm leading-6 ${message.role === "user" ? "ml-auto bg-sky-700 text-white" : "bg-slate-100 text-slate-800"}`}>
                {message.content}
              </div>
            ))}
            {isSending && <p role="status" className="text-xs text-slate-500">Tutor is thinking...</p>}
          </div>
          {chatError && (
            <div role="alert" className="flex items-start justify-between gap-2 rounded-md bg-rose-50 p-2 text-xs text-rose-800">
              <p className="min-w-0 flex-1">{chatError}</p>
              <button
                type="button"
                aria-label="Dismiss tutor error"
                onClick={() => setChatError(null)}
                className="shrink-0 rounded p-1 hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600"
              >
                <X aria-hidden="true" className="size-3.5" />
              </button>
            </div>
          )}
          <form onSubmit={sendQuestion} className="flex items-end gap-2 border-t border-slate-100 pt-3">
            <label className="sr-only" htmlFor="lesson-question">Ask about this lesson</label>
            <textarea
              id="lesson-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              maxLength={4000}
              rows={2}
              placeholder="Ask about this lesson..."
              className="min-h-10 flex-1 resize-y rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-sky-600"
            />
            <Button type="submit" size="icon" aria-label="Send question" disabled={isSending || !question.trim()}>
              <Send aria-hidden="true" className="size-4" />
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}