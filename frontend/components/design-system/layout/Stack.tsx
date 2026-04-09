import React from 'react';

export function Stack({ children, spacing = 3 }: { children: React.ReactNode; spacing?: number }) {
  return <div style={{ display: 'grid', gap: `${spacing * 0.25}rem` }}>{children}</div>;
}
