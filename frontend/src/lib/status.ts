import type { ReportStatus } from "@/lib/types";

export const REPORT_STATUS_META: Record<
  ReportStatus,
  { label: string; className: string }
> = {
  draft: { label: "待确认大纲", className: "border-white/20 text-silver" },
  writing: { label: "写作中", className: "border-phosphor/40 text-phosphor" },
  paused: { label: "已暂停", className: "border-white/20 text-ash" },
  done: { label: "已完成", className: "border-mist/40 text-mist" },
};
