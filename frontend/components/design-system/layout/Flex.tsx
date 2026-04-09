import React from 'react';

export function Flex({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={className} style={{ display: 'flex' }}>{children}</div>;
}
