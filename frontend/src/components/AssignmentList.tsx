import {
  AlertCircle,
  ClipboardCheck,
  Clock3,
  FileCheck2,
  Gauge,
  Loader2,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import type { Assignment } from "@/types/assignment";
import type { Lesson } from "@/types/track";

interface AssignmentListProps {
  assignments: Assignment[];
  lessons: Lesson[];
  isLoading: boolean;
  error: string | null;
}

function getDifficultyLabel(
  difficulty: Assignment["difficulty"],
) {
  switch (difficulty) {
    case "beginner":
      return "Beginner";
    case "intermediate":
      return "Intermediate";
    case "advanced":
      return "Advanced";
  }
}

function getDifficultyClasses(
  difficulty: Assignment["difficulty"],
) {
  switch (difficulty) {
    case "beginner":
      return "bg-emerald-50 text-emerald-700 ring-emerald-600/20";
    case "intermediate":
      return "bg-amber-50 text-amber-700 ring-amber-600/20";
    case "advanced":
      return "bg-red-50 text-red-700 ring-red-600/20";
  }
}

export default function AssignmentList({
  assignments,
  lessons,
  isLoading,
  error,
}: AssignmentListProps) {
  const lessonMap = new Map(
    lessons.map((lesson) => [lesson.id, lesson.title]),
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
        <ClipboardCheck className="h-4 w-4 text-violet-600" />
        Assignments
        <span className="text-xs font-normal text-gray-400">
          ({assignments.length})
        </span>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 rounded-lg border border-dashed border-gray-200 px-4 py-6 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading assignments...
        </div>
      ) : error ? (
        <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-4 text-sm text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : assignments.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-200 px-4 py-6 text-sm text-gray-500">
          No active assignments are available for this module yet.
        </div>
      ) : (
        <div className="space-y-3">
          {assignments.map((assignment) => {
            const lessonTitle =
              assignment.lesson_id !== null
                ? lessonMap.get(assignment.lesson_id)
                : undefined;

            return (
              <Card
                key={assignment.id}
                className="border-violet-100 bg-violet-50/20 shadow-none"
              >
                <div className="p-4 md:p-5">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="font-semibold text-slate-900">
                          {assignment.title}
                        </h4>

                        <span
                          className={`rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${getDifficultyClasses(
                            assignment.difficulty,
                          )}`}
                        >
                          {getDifficultyLabel(assignment.difficulty)}
                        </span>

                        <span
                          className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                            assignment.is_mandatory
                              ? "bg-blue-50 text-blue-700"
                              : "bg-slate-100 text-slate-600"
                          }`}
                        >
                          {assignment.is_mandatory
                            ? "Mandatory"
                            : "Optional"}
                        </span>
                      </div>

                      <p className="mt-2 text-sm leading-6 text-gray-600">
                        {assignment.description}
                      </p>

                      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-gray-500">
                        {lessonTitle && (
                          <span className="inline-flex items-center gap-1.5">
                            <FileCheck2 className="h-3.5 w-3.5 text-violet-600" />
                            {lessonTitle}
                          </span>
                        )}

                        {assignment.estimated_minutes !== null && (
                          <span className="inline-flex items-center gap-1.5">
                            <Clock3 className="h-3.5 w-3.5 text-blue-600" />
                            {assignment.estimated_minutes} min
                          </span>
                        )}

                        {assignment.due_days !== null && (
                          <span className="inline-flex items-center gap-1.5">
                            <Gauge className="h-3.5 w-3.5 text-amber-600" />
                            Due {assignment.due_days} days after release
                          </span>
                        )}
                      </div>

                      {assignment.instructions && (
                        <div className="mt-4 rounded-lg border border-gray-200 bg-white px-3.5 py-3">
                          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                            Instructions
                          </p>

                          <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                            {assignment.instructions}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
