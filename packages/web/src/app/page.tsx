export default function Home() {
  return (
    <div className="flex h-full flex-col p-6">
      {/* Header */}
      <header className="mb-8">
        <h1 className="gradient-primary-text text-3xl font-bold">Dashboard</h1>
        <p className="mt-2 text-muted-foreground">CEO Voice Agent Overview</p>
      </header>

      {/* Stats cards */}
      <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-3">
        <div className="rounded-xl border border-border bg-card p-6">
          <h3 className="mb-2 text-sm font-medium text-muted-foreground">
            Voice Profiles
          </h3>
          <p className="text-3xl font-bold text-foreground">3</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-6">
          <h3 className="mb-2 text-sm font-medium text-muted-foreground">
            Content Generated
          </h3>
          <p className="text-3xl font-bold text-foreground">127</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-6">
          <h3 className="mb-2 text-sm font-medium text-muted-foreground">
            Scraped Sources
          </h3>
          <p className="text-3xl font-bold text-foreground">45</p>
        </div>
      </div>

      {/* Recent activity */}
      <div className="flex-1 rounded-xl border border-border bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold text-foreground">
          Recent Activity
        </h2>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex items-center gap-4 rounded-lg border border-border bg-background p-4"
            >
              <div className="gradient-primary h-10 w-10 rounded-full opacity-80" />
              <div className="flex-1">
                <p className="font-medium text-foreground">
                  Generated LinkedIn post
                </p>
                <p className="text-sm text-muted-foreground">
                  Using Ali Ghodsi voice profile
                </p>
              </div>
              <span className="text-sm text-muted-foreground">2h ago</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
