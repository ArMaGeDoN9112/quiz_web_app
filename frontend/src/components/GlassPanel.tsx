import type { ReactNode } from 'react'

interface GlassPanelProps {
  children: ReactNode
  className?: string
  glow?: 'aurora' | 'plasma' | 'violet' | 'none'
}

const glowStyles = {
  aurora: 'before:from-aurora/30 before:via-violet/20 before:to-plasma/30',
  plasma: 'before:from-plasma/30 before:via-violet/20 before:to-aurora/20',
  violet: 'before:from-violet/30 before:via-plasma/15 before:to-aurora/25',
  none: 'before:from-white/5 before:to-white/5',
}

export function GlassPanel({
  children,
  className = '',
  glow = 'aurora',
}: GlassPanelProps) {
  return (
    <div
      className={`glass-panel relative overflow-hidden rounded-2xl border border-white/10 bg-surface/70 p-6 backdrop-blur-xl before:pointer-events-none before:absolute before:inset-0 before:rounded-2xl before:bg-gradient-to-br before:opacity-40 ${glowStyles[glow]} ${className}`}
    >
      <div className="relative z-10">{children}</div>
    </div>
  )
}
