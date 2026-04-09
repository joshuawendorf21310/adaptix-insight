'use client';

import { useApi } from '@/hooks/useApi';
import Link from 'next/link';
import type { AnalyticsOverview } from '@/services/founderStudio';

function StatCard({ label, value, accent, subtext }: { label: string; value: number | string; accent?: string; subtext?: string }) {
  return (
    <div
      className="bg-bg-panel border border-border-DEFAULT p-5"
      style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}
    >
      <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-text-muted">{label}</div>
      <div className="text-3xl font-black mt-1" style={{ color: accent || 'var(--color-text-primary)' }}>{value}</div>
      {subtext && <div className="text-[10px] text-text-muted mt-1">{subtext}</div>}
    </div>
  );
}

export default function AnalyticsPage() {
  const { data, loading, error } = useApi<AnalyticsOverview>('/api/v1/founder/module-status');

  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">FOUNDER STUDIO · ANALYTICS</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">Analytics</h1>
        <p className="text-xs text-text-muted mt-0.5">Studio performance metrics & engagement overview</p>
      </div>

      {loading && <p className="text-sm text-text-muted">Loading analytics…</p>}
      {error && <p className="text-red-400 text-sm">Error: {error}</p>}

      {data && (
        <div className="space-y-6">
          {/* Primary Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Total Views" value={0} accent="var(--q-cyan)" />
            <StatCard label="Total Clicks" value={0} accent="var(--q-green)" subtext="Traffic generated" />
            <StatCard label="Conversions" value={0} accent="var(--q-yellow)" />
            <StatCard label="Active Campaigns" value={0} accent="var(--q-orange)" subtext="Currently running" />
          </div>

          {/* Secondary Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Avg Engagement" value={0} accent="var(--q-orange)" subtext="Average score" />
            <StatCard label="Videos This Week" value={0} accent="var(--q-cyan)" subtext="Generated media" />
            <StatCard label="Posts This Week" value={0} accent="var(--q-green)" subtext="Published output" />
            <StatCard label="Demos Sent" value={0} accent="var(--color-text-primary)" subtext="Outbound demos" />
          </div>

          {/* Quick Actions */}
          <div>
            <h2 className="text-xs font-bold uppercase tracking-[0.15em] text-text-muted mb-3">Quick Actions</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { href: '/founder/studio/social', label: 'Create Post', icon: '📱' },
                { href: '/founder/studio/campaigns', label: 'New Campaign', icon: '📣' },
                { href: '/founder/studio/review', label: 'Review Queue', icon: '✅' },
                { href: '/founder/studio/render', label: 'Render Queue', icon: '🎞️' },
              ].map((action) => (
                <Link
                  key={action.href}
                  href={action.href}
                  className="flex items-center gap-2 bg-bg-panel border border-border-DEFAULT p-3 hover:border-[rgba(255,255,255,0.18)] transition-colors"
                >
                  <span>{action.icon}</span>
                  <span className="text-xs font-bold text-text-primary">{action.label}</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      <Link href="/founder/studio" className="text-xs text-orange-dim hover:text-orange">← Back to Studio</Link>
    </div>
  );
}
