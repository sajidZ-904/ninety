const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

export interface User {
  id: string;
  name: string;
  email: string;
  role: "admin" | "team_member" | "observer";
}

export interface Team {
  id: string;
  name: string;
}

export interface MeasurableWeekStatus {
  week_start: string;
  value: number | null;
  status: "on_track" | "off_track" | "pending";
  version?: number | null;
}

export interface Measurable {
  id: string;
  team_id: string;
  name: string;
  owner_id: string;
  owner_name: string | null;
  unit: string;
  goal: {
    type: string;
    value?: number;
    min?: number;
    max?: number;
  };
  weeks: MeasurableWeekStatus[];
}

export interface Issue {
  id: string;
  team_id: string;
  title: string;
  owner_id: string;
  owner_name: string | null;
  priority: number | null;
  created_at: string;
  solved_at: string | null;
  resolution_note: string | null;
  source: {
    measurable_id: string;
    week_start: string;
  } | null;
}

export interface ToDo {
  id: string;
  team_id: string;
  title: string;
  owner_id: string;
  owner_name: string | null;
  due_date: string;
  done_at: string | null;
  source_issue_id: string | null;
  created_at: string;
  is_overdue: boolean;
}

export interface RockMilestone {
  id: string;
  rock_id: string;
  title: string;
  due_date: string;
  done: boolean;
}

export interface Rock {
  id: string;
  team_id: string;
  title: string;
  owner_id: string;
  owner_name: string | null;
  quarter: string;
  status: "on_track" | "off_track" | "complete";
  progress_percent: number;
  milestones: RockMilestone[];
}

export interface MeetingState {
  id: string;
  team_id: string;
  facilitator_id: string;
  facilitator_name: string | null;
  status: "active" | "ended";
  current_section: "scorecard" | "ids" | "conclude" | "ended";
  section_started_at: string;
  started_at: string;
  ended_at: string | null;
  server_now: string;
  section_elapsed_seconds: number;
  section_allocated_seconds: number;
  is_overtime: boolean;
  attendees: string[];
  ratings: { user_id: string; rating: number }[];
  new_todos: ToDo[];
  solved_issues: Issue[];
  scorecard_week: string;
}

export interface MeetingSummary {
  meeting_id: string;
  team_id: string;
  scorecard_week: string;
  measurable_status: Record<string, string>;
  issues_solved: string[];
  todos_created: string[];
  attendee_ids: string[];
  rating: number | null;
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  userId: string = "u1"
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  headers.set("x-user-id", userId);

  const res = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorMsg = `API Error: ${res.status}`;
    try {
      const data = await res.json();
      if (data.detail) {
        errorMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

