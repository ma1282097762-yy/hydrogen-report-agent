export type ReportStatus = "draft" | "writing" | "paused" | "done";

export interface Report {
  id: number;
  title: string;
  target_words: number;
  status: ReportStatus;
  status_label: string;
  created_at: string;
  updated_at: string;
}
