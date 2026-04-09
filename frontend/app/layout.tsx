import './globals.css';

import type { Metadata } from 'next';

import { AuthProvider } from '@/components/AuthProvider';

export const metadata: Metadata = { title: 'Adaptix Insight', description: 'Standalone founder insight shell for Adaptix' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body><AuthProvider>{children}</AuthProvider></body></html>;
}
