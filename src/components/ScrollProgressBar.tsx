import React, { useEffect, useState } from 'react';

export const ScrollProgressBar: React.FC = () => {
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const totalScroll = document.documentElement.scrollTop;
      const windowHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      if (windowHeight > 0) {
        const progress = Number((totalScroll / windowHeight).toFixed(3));
        setScrollProgress(Math.min(1, Math.max(0, progress)));
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  if (scrollProgress <= 0) return null;

  return (
    <div
      className="fixed top-0 left-0 right-0 h-1 z-[9999] pointer-events-none transition-opacity duration-300"
      role="progressbar"
      aria-valuenow={Math.round(scrollProgress * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full bg-gradient-to-r from-primary via-[#4D91FF] to-[#A9CBFF] shadow-xs shadow-primary/30 transition-all duration-75 ease-out"
        style={{ width: `${scrollProgress * 100}%` }}
      />
    </div>
  );
};
