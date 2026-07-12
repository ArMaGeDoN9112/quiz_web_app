import { motion } from 'motion/react'
import { Link } from 'react-router-dom'

import { AppShell } from '../components/AppShell'
import { GlassPanel } from '../components/GlassPanel'
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

        <div className="mt-20 grid gap-6 sm:grid-cols-3">
          {[
            {
              step: '01',
              title: 'Build',
              text: 'Draft quizzes with timed questions and scoring rules.',
              glow: 'aurora' as const,
            },
            {
              step: '02',
              title: 'Launch',
              text: 'Generate a unique room code and open the live session.',
              glow: 'violet' as const,
            },
            {
              step: '03',
              title: 'Compete',
              text: 'Participants answer in sync. Scores update instantly.',
              glow: 'plasma' as const,
            },
          ].map((item, index) => (
            <motion.div
              key={item.step}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + index * 0.1, duration: 0.5 }}
            >
              <GlassPanel glow={item.glow} className="h-full">
                <p className="font-display text-xs text-muted">{item.step}</p>
                <h2 className="mt-2 font-display text-lg text-foreground">{item.title}</h2>
                <p className="mt-2 font-body text-sm leading-relaxed text-muted">
                  {item.text}
                </p>
              </GlassPanel>
            </motion.div>
          ))}
        </div>
      </section>
    </AppShell>
  )
}
