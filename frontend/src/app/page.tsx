export default function HomePage() {
  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">仪表盘</h1>
        <p className="text-muted-foreground">欢迎回来，这是你的视频生成概览</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="p-6 rounded-lg border border-border bg-card">
          <p className="text-sm text-muted-foreground mb-1">监控频道</p>
          <p className="text-3xl font-bold">3</p>
        </div>
        <div className="p-6 rounded-lg border border-border bg-card">
          <p className="text-sm text-muted-foreground mb-1">任务中</p>
          <p className="text-3xl font-bold text-primary">1</p>
        </div>
        <div className="p-6 rounded-lg border border-border bg-card">
          <p className="text-sm text-muted-foreground mb-1">已完成</p>
          <p className="text-3xl font-bold text-success">12</p>
        </div>
        <div className="p-6 rounded-lg border border-border bg-card">
          <p className="text-sm text-muted-foreground mb-1">失败</p>
          <p className="text-3xl font-bold text-error">2</p>
        </div>
      </div>

      {/* Recent Tasks */}
      <div className="border border-border rounded-lg bg-card overflow-hidden">
        <div className="px-6 py-4 border-b border-border bg-secondary/50 flex items-center justify-between">
          <h3 className="font-semibold">最近任务</h3>
          <button className="px-4 py-2 rounded-md bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition">
            + 新建任务
          </button>
        </div>
        <div className="divide-y divide-border">
          <div className="px-6 py-4 flex items-center justify-between hover:bg-secondary/30 transition">
            <div className="flex-1">
              <p className="font-medium">TED Talk - AI 的未来</p>
              <p className="text-sm text-muted-foreground">Dramatic · 2分钟前</p>
            </div>
            <div className="flex items-center gap-4">
              <span className="px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                处理中
              </span>
              <span className="text-sm text-muted-foreground">60%</span>
            </div>
          </div>
          <div className="px-6 py-4 flex items-center justify-between hover:bg-secondary/30 transition">
            <div className="flex-1">
              <p className="font-medium">量子力学入门</p>
              <p className="text-sm text-muted-foreground">Educational · 1小时前</p>
            </div>
            <div className="flex items-center gap-4">
              <span className="px-2 py-1 rounded-full text-xs font-medium bg-success/10 text-success">
                已完成
              </span>
              <span className="text-sm text-muted-foreground">100%</span>
            </div>
          </div>
          <div className="px-6 py-4 flex items-center justify-between hover:bg-secondary/30 transition">
            <div className="flex-1">
              <p className="font-medium">Python 教程 - 第1集</p>
              <p className="text-sm text-muted-foreground">Humorous · 昨天</p>
            </div>
            <div className="flex items-center gap-4">
              <span className="px-2 py-1 rounded-full text-xs font-medium bg-error/10 text-error">
                失败
              </span>
              <span className="text-sm text-muted-foreground">-</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
