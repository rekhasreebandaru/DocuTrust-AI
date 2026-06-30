import { useEffect, useState } from 'react';
export function AnimatedCounter({ value, suffix = '' }: { value: number; suffix?: string }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => { const start = performance.now(); const duration = 700; const from = display; const frame = (now: number) => { const progress = Math.min(1, (now - start) / duration); const eased = 1 - Math.pow(1 - progress, 3); setDisplay(Math.round(from + (value - from) * eased)); if (progress < 1) requestAnimationFrame(frame); }; requestAnimationFrame(frame); }, [value]);
  return <>{display.toLocaleString()}{suffix}</>;
}