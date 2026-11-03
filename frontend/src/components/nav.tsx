export function Nav() {
  return (
    <header className="border-b border-white/10">
      <div className="mx-auto flex h-20 w-full max-w-[1440px] items-center justify-between px-6">
        <div className="text-sm font-medium uppercase tracking-[0.12em] text-mist">
          可研报告生成 <span className="text-phosphor">Agent</span>
        </div>
        <div className="flex items-center gap-6">
          <span className="text-xs uppercase tracking-[0.12em] text-platinum">报告</span>
          <span className="text-xs uppercase tracking-[0.12em] text-silver">资料库</span>
          <button className="btn-aurora px-5 py-2.5 text-xs uppercase tracking-[0.08em]">
            新建报告
          </button>
        </div>
      </div>
    </header>
  );
}
