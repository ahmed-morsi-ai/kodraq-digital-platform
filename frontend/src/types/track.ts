export interface Resource {
  id: number;
  module_id: number;
  title: string;
  file_url: string;
  resource_type: string;
}

export interface ResourceCreate {
  title: string;
  file_url: string;
  resource_type: string;
}

export interface LessonQuizQuestion {
  id: number;
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
}

export interface Lesson {
  id: number;
  module_id: number;
  title: string;
  description: string | null;
  content: string | null;
  video_url: string | null;
  ordering: number;
  quiz_data: LessonQuizQuestion[] | string | null;
}

export interface LessonCreate {
  title: string;
  description?: string | null;
  content?: string | null;
  video_url?: string | null;
  quiz_data?: LessonQuizQuestion[] | null;
  ordering?: number;
}

export interface TrackModule {
  id: number;
  track_id: number;
  title: string;
  description: string | null;
  ordering: number;
  is_active: boolean;
  lessons: Lesson[];
  resources: Resource[];
}

export interface TrackModuleCreate {
  title: string;
  description?: string | null;
  ordering?: number;
  is_active?: boolean;
}

export interface Track {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  ordering: number;
  price: number;
  currency: string;
  is_premium: boolean;
  modules?: TrackModule[];
}

export interface TrackCreate {
  name: string;
  slug: string;
  description?: string | null;
  is_active?: boolean;
  ordering?: number;
}

export interface TrackSummary {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  ordering: number;
  price: number;
  currency: string;
  is_premium: boolean;
}

export interface TrackCurriculum extends Track {
  modules: TrackModule[];
}
