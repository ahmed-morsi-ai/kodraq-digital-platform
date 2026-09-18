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

export interface Lesson {
  id: number;
  module_id: number;
  title: string;
  content: string;
  video_url: string | null;
  ordering: number;
}

export interface LessonCreate {
  title: string;
  content: string;
  video_url?: string | null;
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
}

export interface TrackCurriculum extends Track {
  modules: TrackModule[];
}
