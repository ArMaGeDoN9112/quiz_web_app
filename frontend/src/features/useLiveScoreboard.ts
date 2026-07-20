import { useEffect } from 'react'

import { api } from '../api/client.js'
import type { SessionScoreboard } from '../types/api.js'
import { parseScoreboardUpdate } from './liveScoreboard.js'

const RECONNECT_DELAY_MS = 2_000

export function useLiveScoreboard(
  sessionId: string | undefined,
  roomCode: string | undefined,
  onScoreboard: (scoreboard: SessionScoreboard) => void,
) {
  useEffect(() => {
    if (!sessionId || !roomCode) return
    let disposed = false
    let reconnectTimer: number | undefined
    let socket: WebSocket | null = null

    const loadFallback = async () => {
      try {
        const scoreboard = await api.getSessionScoreboard(sessionId)
        if (!disposed) onScoreboard(scoreboard)
      } catch {
        // Reconnection continues while API or WebSocket is unavailable.
      }
    }

    const scheduleReconnect = () => {
      if (!disposed) reconnectTimer = window.setTimeout(connect, RECONNECT_DELAY_MS)
    }

    const connect = () => {
      void loadFallback()
      const nextSocket = api.openSessionScoreboardSocket(roomCode)
      socket = nextSocket
      if (nextSocket === null) {
        scheduleReconnect()
        return
      }
      nextSocket.onmessage = (event) => {
        const scoreboard = parseScoreboardUpdate(event.data)
        if (scoreboard !== null) onScoreboard(scoreboard)
      }
      nextSocket.onerror = () => nextSocket.close()
      nextSocket.onclose = scheduleReconnect
    }

    connect()
    return () => {
      disposed = true
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer)
      socket?.close()
    }
  }, [onScoreboard, roomCode, sessionId])
}
