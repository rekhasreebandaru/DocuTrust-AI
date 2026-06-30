import { useEffect, useState } from 'react';
export function useDarkMode() {
  const [enabled, setEnabled] = useState(() => localStorage.getItem('docutrust_dark') === 'true');
  useEffect(() => { document.documentElement.classList.toggle('dark', enabled); localStorage.setItem('docutrust_dark', String(enabled)); }, [enabled]);
  return { darkMode: enabled, setDarkMode: setEnabled };
}
