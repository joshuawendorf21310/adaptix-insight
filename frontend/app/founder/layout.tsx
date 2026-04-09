"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { PlatformShell } from '@/components/PlatformShell';

const LINKS = [
  { href: '/founder/infra', label: 'Infra' },
  { href: '/founder/roi', label: 'ROI' },
  { href: '/founder/studio/analytics', label: 'Studio Analytics' },
];

export default function FounderLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const breadcrumbs = <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center' }}><div><div style={{ color: 'var(--q-orange)', fontSize: '.75rem', textTransform: 'uppercase' }}>Adaptix Insight</div><h1 style={{ margin: '.35rem 0' }}>Founder Intelligence</h1></div><nav style={{ display: 'flex', gap: '.75rem' }}>{LINKS.map((link) => <Link key={link.href} href={link.href} style={{ textDecoration: pathname.startsWith(link.href) ? 'underline' : 'none' }}>{link.label}</Link>)}</nav></div>;
  return <PlatformShell breadcrumbs={breadcrumbs}>{children}</PlatformShell>;
}
