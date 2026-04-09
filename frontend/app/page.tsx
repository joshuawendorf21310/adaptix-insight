import Link from 'next/link';

export default function HomePage() {
  return <main className="platform-shell"><div className="platform-shell__inner plate-card"><h1>Adaptix Insight</h1><p>Standalone founder insight shell for deployment health, ROI, and studio analytics.</p><div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}><Link href="/access">Developer Access</Link><Link href="/founder/infra">Founder Infra</Link></div></div></main>;
}
