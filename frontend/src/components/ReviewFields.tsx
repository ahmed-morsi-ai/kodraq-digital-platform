import { useId } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/** Shared by assignment and final-project instructor reviews. */
export default function ReviewFields({ grade, feedback, onGradeChange, onFeedbackChange, disabled, min = -2147483648, max = 2147483647, hint }: {
  grade: string;
  feedback: string;
  onGradeChange: (value: string) => void;
  onFeedbackChange: (value: string) => void;
  disabled: boolean;
  min?: number;
  max?: number;
  hint?: string;
}) {
  const id = useId();
  return <div className="grid gap-4 sm:grid-cols-[140px_1fr]">
    <div className="space-y-2">
      <Label htmlFor={`${id}-grade`}>Grade</Label>
      <Input id={`${id}-grade`} type="number" step={1} min={min} max={max} value={grade} onChange={(event) => onGradeChange(event.target.value)} disabled={disabled} />
      <p className="text-xs text-slate-500">{hint ?? "Optional whole number"}</p>
    </div>
    <div className="space-y-2">
      <Label htmlFor={`${id}-feedback`}>Feedback</Label>
      <textarea id={`${id}-feedback`} required value={feedback} onChange={(event) => onFeedbackChange(event.target.value)} disabled={disabled} rows={4} placeholder="Explain the decision and required improvements." className="w-full rounded-md border border-input bg-white px-3 py-2 text-sm text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-60" />
    </div>
  </div>;
}
