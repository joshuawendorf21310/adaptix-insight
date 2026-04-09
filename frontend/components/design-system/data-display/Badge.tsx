import React from 'react';

export function Badge({ children, color = 'gray' }: { children: React.ReactNode; color?: 'green' | 'yellow' | 'red' | 'gray' }) {
  return <span className={`badge badge-${color}`}>{children}</span>;
}
