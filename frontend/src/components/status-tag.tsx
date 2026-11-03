import { REPORT_STATUS_META } from "@/lib/status";
import type { ReportStatus } from "@/lib/types";

export function StatusTag({ status }: { status: ReportStatus }) {
  const meta = REPORT_STATUS_META[status];
  return (
    <span className={`inline-flex rounded-full border px-3 py-1 text-xs ${meta.className}`}>
      {meta.label}
    </span>
  );
}
