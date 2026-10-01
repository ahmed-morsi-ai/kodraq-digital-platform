import type { Lesson, LessonQuizQuestion, TrackCurriculum, TrackModule } from "@/types/track";

export interface AdminStats {
  total_users: number;
  total_students: number;
  active_tracks: number;
  total_lessons: number;
  completion_rate: number;
  daily_active_users: number;
  active_sessions: number;
  completion_velocity: number;
  average_response_ms: number | null;
  system_health: "online" | "degraded";
  engagement: { month: string; active_users: number }[];
  track_completion: {
    track_id: number;
    track_name: string;
    ordering: number;
    completion_rate: number;
  }[];
}

export interface AdminStudent {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_superuser: boolean;
  subscription_active: boolean;
  joined_at: string;
  progress_percentage: number;
}

export interface AdminActivity {
  kind: "enrollment" | "quiz_submission" | "ai_request";
  created_at: string;
  summary: string;
  status: string;
  score?: number | null;
  latency_ms?: number | null;
  total_tokens?: number | null;
}

export interface AdminLogs {
  activities: AdminActivity[];
  ai_usage: {
    requests: number;
    failed_requests: number;
    average_latency_ms: number | null;
    total_tokens: number;
  };
}

export interface AdminTrackPayload {
  name: string;
  slug: string;
  description: string | null;
  ordering: number;
  is_active: boolean;
  is_premium: boolean;
  price: number;
  currency: string;
}

export interface AdminModulePayload {
  title: string;
  description: string | null;
  ordering: number;
  is_active: boolean;
}

export interface AdminLessonPayload {
  title: string;
  description: string | null;
  content: string | null;
  video_url: string | null;
  ordering: number;
  quiz_data: LessonQuizQuestion[] | null;
}

export type AdminTrack = TrackCurriculum;
export type AdminModule = TrackModule;
export type AdminLesson = Lesson;