import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/nav";

export const metadata: Metadata = {
  title: "可研报告生成 Agent",
  description: "氢能可研报告 AI 写作工具",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-abyss text-platinum antialiased">
        <Nav />
        <main className="mx-auto w-full max-w-[1440px] px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
