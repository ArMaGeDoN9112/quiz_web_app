import { motion } from 'motion/react'
import { Link } from 'react-router-dom'

import { AppShell } from '../components/AppShell'
import { ParticleField } from '../components/ParticleField'

export function HomePage() {
  return (
    <AppShell>
      <ParticleField />

      <section className="relative mx-auto flex min-h-[calc(100vh-73px)] max-w-6xl flex-col justify-center px-6 py-16">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="max-w-3xl"
        >
          <p className="mb-4 font-body text-xs uppercase tracking-[0.4em] text-plasma">
            Live intelligence platform
          </p>
          <h1 className="font-display text-4xl leading-tight text-foreground sm:text-6xl">
            Quiz rooms that feel
            <span className="block bg-gradient-to-r from-aurora via-violet to-plasma bg-clip-text text-transparent">
              broadcast from the future
            </span>
          </h1>
          <p className="mt-6 max-w-xl font-body text-lg text-muted">
            Organizers launch holographic room codes. Participants join in seconds.
            Answers sync in real time across every screen.
          </p>

          <div className="mt-10 flex flex-wrap gap-4">
            <Link to="/register?role=organizer" className="btn-primary">
              Host a quiz
            </Link>
            <Link to="/join" className="btn-secondary">
              Enter room code
            </Link>
          </div>
        </motion.div>
      </section>
    </AppShell>
  )
}
