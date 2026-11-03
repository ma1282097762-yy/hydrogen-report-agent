"use client";

import { useEffect, useState } from "react";

import { ReportCard } from "@/components/report-card";
import { api } from "@/lib/api";
import type { Report } from "@/lib/types";

export default function Home() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<{ reports: Report[] }>("/api/v1/reports")
      .then((data) => {
        if (!cancelled) setReports(data.reports || []);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function retry() {
    setLoading(true);
    setError(null);
    try {
      const data = await api<{ reports: Report[] }>("/api/v1/reports");
      setReports(data.reports || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="mb-10">
        <p className="mb-3 text-xs uppercase tracking-[0.12em] text-silver">
          Feasibility Studies
        </p>
        <h1 className="text-4xl font-medium leading-none tracking-tight text-platinum md:text-6xl">
          我的可研报告
        </h1>
        <p className="mt-4 text-base text-silver">数字不能错，全文小于 2 万字。</p>
      </div>

      {loading && (
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="surface-card h-40 animate-pulse" />
          ))}
        </div>
      )}

      {!loading && error && (
        <div className="surface-card p-10">
          <p className="text-lg font-medium text-platinum">后端连接失败</p>
          <p className="mt-2 text-silver">{error}</p>
          <button
            onClick={retry}
            className="btn-aurora mt-6 px-5 py-2.5 text-xs uppercase tracking-[0.08em]"
          >
            重试
          </button>
        </div>
      )}

      {!loading && !error && reports.length === 0 && (
        <div className="surface-card p-16 text-center">
          <p className="text-xl font-medium text-mist">还没有报告</p>
          <p className="mt-2 text-silver">先创建一份可研报告，开始写作。</p>
        </div>
      )}

      {!loading && !error && reports.length > 0 && (
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {reports.map((r) => (
            <ReportCard key={r.id} report={r} />
          ))}
        </div>
      )}
    </div>
  );
}
