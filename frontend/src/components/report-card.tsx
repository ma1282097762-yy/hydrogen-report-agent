import { StatusTag } from "@/components/status-tag";
import type { Report } from "@/lib/types";

export function ReportCard({ report }: { report: Report }) {
  return (
    <article className="surface-card flex flex-col justify-between p-6">
      <div>
        <h2 className="text-lg font-medium leading-snug text-platinum">{report.title}</h2>
        <p className="mt-3 text-sm text-silver">目标 {report.target_words} 字</p>
      </div>
      <div className="mt-8 flex items-center justify-between">
        <StatusTag status={report.status} />
        <span className="text-xs text-slate-deep">{report.created_at}</span>
      </div>
    </article>
  );
}
