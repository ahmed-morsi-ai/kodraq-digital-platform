import { api } from "@/services/api";
import type { Lesson, LessonQuizPrompt } from "@/types/track";

export interface LessonChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface AICompletionResponse {
  content: string;
}

export interface LessonTranslation {
  title: string;
  content: string;
  quiz_data: LessonQuizPrompt[];
}

function parseLessonTranslation(
  content: string,
  sourceQuiz: LessonQuizPrompt[],
): LessonTranslation {
  const start = content.indexOf("{");
  const end = content.lastIndexOf("}");
  if (start < 0 || end <= start) {
    throw new Error("Translation response was not valid JSON.");
  }

  const parsed: unknown = JSON.parse(content.slice(start, end + 1));
  if (!parsed || typeof parsed !== "object") {
    throw new Error("Translation response was not a JSON object.");
  }

  const result = parsed as Record<string, unknown>;
  if (
    typeof result.title !== "string"
    || typeof result.content !== "string"
    || !Array.isArray(result.quiz_data)
    || result.quiz_data.length !== sourceQuiz.length
  ) {
    throw new Error("Translation response is missing required lesson fields.");
  }

  const quizData = result.quiz_data.map((item, index) => {
    if (!item || typeof item !== "object") {
      throw new Error("Translation response contains an invalid quiz question.");
    }
    const question = item as Record<string, unknown>;
    const sourceQuestion = sourceQuiz[index];
    if (
      typeof question.id !== "number"
      || question.id !== sourceQuestion.id
      || typeof question.question !== "string"
      || !Array.isArray(question.options)
      || question.options.length !== sourceQuestion.options.length
      || !question.options.every((option) => typeof option === "string")
      || (sourceQuestion.explanation !== undefined && typeof question.explanation !== "string")
    ) {
      throw new Error("Translation response changed the quiz answer structure.");
    }
    return {
      id: sourceQuestion.id,
      question: question.question,
      options: question.options as string[],
      ...(sourceQuestion.explanation !== undefined
        ? { explanation: question.explanation as string }
        : {}),
    };
  });

  return {
    title: result.title,
    content: result.content,
    quiz_data: quizData,
  };
}

export const lessonChatService = {
  async ask(
    lesson: Lesson,
    trackName: string,
    history: LessonChatMessage[],
  ): Promise<string> {
    const response = await api.post<AICompletionResponse>(
      "/api/v1/ai/completions",
      {
        request_type: "lesson_rag_chat",
        messages: [
          {
            role: "system",
            content: [
              "You are a helpful tutor for the Kodraq Digital learning platform.",
              "Answer using the supplied lesson context. If it does not contain the answer, say so and explain what additional source is needed.",
              `Track: ${trackName}`,
              `Lesson: ${lesson.title}`,
              "Lesson context:",
              lesson.content,
            ].join("\n\n"),
          },
          ...history,
        ],
        temperature: 0.2,
        max_tokens: 800,
      },
    );
    return response.data.content;
  },

  async translateToArabic(
    lesson: Lesson,
    quizData: LessonQuizPrompt[],
  ): Promise<LessonTranslation> {
    const response = await api.post<AICompletionResponse>(
      "/api/v1/ai/completions",
      {
        request_type: "lesson_translation",
        messages: [
          {
            role: "system",
            content: [
              "Translate the supplied English lesson into clear Modern Standard Arabic.",
              "Return only one valid JSON object with exactly these fields: title, content, quiz_data.",
              "Translate the title, Markdown prose and headings, quiz questions, options, and explanations into Arabic.",
              "Preserve all Markdown structure, tables, code fences, inline code, URLs, HTTP methods, identifiers, JSON field names, and code examples exactly.",
              "Keep quiz question IDs and option order unchanged. Do not add, remove, or reorder quiz questions or options. Do not infer or add answer keys or explanations that are not supplied.",
              "Do not wrap the JSON in Markdown fences or include commentary outside the JSON object.",
            ].join(" "),
          },
          {
            role: "user",
            content: JSON.stringify({
              title: lesson.title,
              content: lesson.content ?? "",
              quiz_data: quizData,
            }),
          },
        ],
        temperature: 0.1,
        max_tokens: 12_000,
      },
    );
    return parseLessonTranslation(response.data.content, quizData);
  },
};
