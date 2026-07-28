import { useCallback, useEffect, useRef } from 'react'

import { api } from '../api/client.js'
import type { SessionLiveUpdate } from '../types/api.js'
import { parseCommandResult, parseSessionUpdate } from './liveScoreboard.js'

const RECONNECT_DELAY_MS = 2_000

export type LiveSessionCommand =
  | { type: 'question.start'; question_id: string; duration_seconds?: number }
  | { type: 'answer.submit'; question_id: string; selected_answer_ids: string[]; text_answer?: string }
  | { type: 'session.end' }

export function useLiveScoreboard(
  sessionId: string | undefined,
  roomCode: string | undefined,
  onSessionUpdate: (update: SessionLiveUpdate) => void,
) {
  const socketRef = useRef<WebSocket | null>(null)
  const pendingCommandsRef = useRef(new Map<string, { resolve: () => void; reject: (reason: Error) => void }>())

  const sendCommand = useCallback((command: LiveSessionCommand): Promise<void> => {
    const socket = socketRef.current
    if (socket === null || socket.readyState !== WebSocket.OPEN) {
      return Promise.reject(new Error('Live connection is unavailable'))
    }
    const requestId = crypto.randomUUID()
    return new Promise((resolve, reject) => {
      pendingCommandsRef.current.set(requestId, { resolve, reject })
      socket.send(JSON.stringify({ ...command, request_id: requestId }))
    })
  }, [])

  useEffect(() => {
    if (!sessionId || !roomCode) return
    const pendingCommands = pendingCommandsRef.current
    let disposed = false
    let reconnectTimer: number | undefined
    let socket: WebSocket | null = null

    const scheduleReconnect = () => {
      if (!disposed) reconnectTimer = window.setTimeout(connect, RECONNECT_DELAY_MS)
    }

    const connect = () => {
      const nextSocket = api.openSessionScoreboardSocket(roomCode)
      socket = nextSocket
      socketRef.current = nextSocket
      if (nextSocket === null) {
        scheduleReconnect()
        return
      }
      nextSocket.onmessage = (event) => {
        const update = parseSessionUpdate(event.data)
        if (update !== null) onSessionUpdate(update)
        const result = parseCommandResult(event.data)
        if (result !== null) {
          const pending = pendingCommandsRef.current.get(result.request_id)
          if (pending !== undefined) {
            pendingCommandsRef.current.delete(result.request_id)
            if (result.detail === null) pending.resolve()
            else pending.reject(new Error(result.detail))
          }
        }
      }
      nextSocket.onerror = () => nextSocket.close()
      nextSocket.onclose = scheduleReconnect
    }

    connect()
    return () => {
      disposed = true
      socketRef.current = null
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer)
      socket?.close()
      for (const pending of pendingCommands.values()) pending.reject(new Error('Live connection closed'))
      pendingCommands.clear()
    }
  }, [onSessionUpdate, roomCode, sessionId])

  return { sendCommand }
}
