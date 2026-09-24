import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock3,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { TrackSummary } from "@/types/track";
import type { Enrollment } from "@/types/enrollment";

interface TrackCardProps {
  track: TrackSummary;
  enrollment?: Enrollment;
  onOpenTrack: (trackId: number) => void;
}

function getEnrollmentLabel(status?: Enrollment["status"]) {
  switch (status) {
    case "active":
      return "Active enrollment";
    case "completed":
      return "Completed";
    case "cancelled":
      return "Cancelled";
    default:
      return "Not enrolled";
  }
}

export default function TrackCard({
  track,
  enrollment,
  onOpenTrack,
}: TrackCardProps) {
  const isEnrolled =
    enrollment !== undefined && enrollment.status !== "cancelled";

  return (
    <Card className="h-full border-gray-200 shadow-sm transition-all duration-200 hover:-translate-y-1 hover:shadow-md">
      <CardHeader className="space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
            <BookOpen className="h-5 w-5" />
          </div>

          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
              isEnrolled
                ? "bg-emerald-50 text-emerald-700"
                : "bg-slate-100 text-slate-600"
            }`}
          >
            {isEnrolled ? (
              <CheckCircle2 className="h-3.5 w-3.5" />
            ) : (
              <Clock3 className="h-3.5 w-3.5" />
            )}
            {getEnrollmentLabel(enrollment?.status)}
          </span>
        </div>

        <div>
          <CardTitle className="text-xl text-slate-900">
            {track.name}
          </CardTitle>

          <CardDescription className="mt-2 leading-6">
            {track.description || "Explore this technical learning track."}
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent>
        <div className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
            Track slug
          </p>
          <p className="mt-1 text-sm font-medium text-slate-700">
            {track.slug}
          </p>
        </div>
      </CardContent>

      <CardFooter>
        <Button
          type="button"
          className="w-full gap-2 bg-blue-600 text-white hover:bg-blue-700"
          onClick={() => onOpenTrack(track.id)}
        >
          {isEnrolled ? "Continue learning" : "View & enroll"}
          <ArrowRight className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  );
}
