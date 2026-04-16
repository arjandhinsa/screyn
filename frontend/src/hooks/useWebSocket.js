import { useEffect, useRef, useState } from 'react'

/**
 * Subscribes to the backend live-metric WebSocket.
 * Returns the most recent LiveFrame payload (or null before first message)
 * plus a connection status.
 */
export default function useWebSocket(path = '/ws/live') {
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('connecting')
  const wsRef = useRef(null)
  const reconnectTimerRef = useRef(null)

  useEffect(() => {
    let cancelled = false

    const connect = () => {
      if (cancelled) return
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      // In dev, Vite proxies /ws to the backend
      const url = `${proto}//${window.location.host}${path}`
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => setStatus('connected')
      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data)
          setData(parsed)
        } catch (err) {
          console.error('Bad WS message:', err)
        }
      }
      ws.onerror = () => setStatus('error')
      ws.onclose = () => {
        setStatus('disconnected')
        if (!cancelled) {
          // Reconnect after 2s
          reconnectTimerRef.current = setTimeout(connect, 2000)
        }
      }
    }

    connect()

    return () => {
      cancelled = true
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [path])

  return { data, status }
}
