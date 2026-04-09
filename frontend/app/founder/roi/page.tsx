'use client';
import Link from 'next/link';

const LINKS = [
  { href: '/founder/roi/analytics', label: 'ROI Analytics', desc: 'MRR, ARR, agency breakdown, payer mix, churn risk', color: 'var(--q-yellow)' },
  { href: '/founder/roi/funnel', label: 'Funnel Dashboard', desc: 'Lead pipeline, conversion rates, deal velocity', color: 'var(--q-yellow)' },
  { href: '/founder/roi/pricing-simulator', label: 'Pricing Simulator', desc: 'Compare Adaptix vs % billing model ROI', color: 'var(--q-yellow)' },
  { href: '/founder/roi/proposals', label: 'Proposal Tracker', desc: 'Track sent proposals, follow-ups, acceptance rate', color: 'var(--q-yellow)' },
];

export default function ROIPage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">DOMAIN 8 · ROI & SALES</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">ROI & Sales</h1>
        <p className="text-xs text-text-muted mt-0.5">Pipeline · simulator · proposals · analytics</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {LINKS.map((l) => (
          <div key={l.href}>
            <Link href={l.href} className="block bg-bg-panel border border-border-DEFAULT p-5 hover:border-[rgba(255,255,255,0.18)] transition-colors" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div className="text-sm font-bold mb-1" style={{ color: l.color }}>{l.label}</div>
              <div className="text-xs text-[rgba(255,255,255,0.45)]">{l.desc}</div>
            </Link>
          </div>
        ))}
      </div>
      <Link href="/founder" className="text-xs text-orange-dim hover:text-orange">← Back to Platform Command</Link>
    </div>
  );
}

