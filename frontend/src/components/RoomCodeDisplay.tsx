import { motion } from 'motion/react'

interface RoomCodeDisplayProps {
  code: string
  label?: string
}

export function RoomCodeDisplay({ code, label = 'Room code' }: RoomCodeDisplayProps) {
  return (
    <div className="flex flex-col items-center gap-3">
      <span className="font-body text-xs uppercase tracking-[0.35em] text-muted">
        {label}
      </span>
      <motion.div
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: 'spring', stiffness: 260, damping: 20 }}
        className="holo-code relative px-8 py-5"
      >
        <div className="scanline pointer-events-none absolute inset-0 overflow-hidden rounded-xl" />
        <p className="font-display relative z-10 text-4xl tracking-[0.45em] text-aurora sm:text-5xl">
          {code}
        </p>
      </motion.div>
      <p className="font-body max-w-xs text-center text-sm text-muted">
        Share this code. Participants enter it to join the live session.
      </p>
    </div>
  )
}
