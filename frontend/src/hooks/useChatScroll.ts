import { useLayoutEffect, useRef, useState } from 'react'

export function useChatScroll(count: number) {
  const thread = useRef<HTMLDivElement>(null)
  const nearBottom = useRef(true)
  const previous = useRef(0)
  const [unread, setUnread] = useState(0)
  function jump() {
    const element = thread.current
    if (element) element.scrollTop = element.scrollHeight
    nearBottom.current = true
    setUnread(0)
  }
  function onScroll() {
    const element = thread.current
    if (!element) return
    nearBottom.current = element.scrollHeight - element.scrollTop - element.clientHeight < 90
    if (nearBottom.current) setUnread(0)
  }
  useLayoutEffect(() => {
    const element = thread.current
    const added = count - previous.current
    if (element && added > 0) {
      if (nearBottom.current || previous.current === 0) element.scrollTop = element.scrollHeight
      // Incoming messages must not interrupt someone reading earlier history.
      // oxlint-disable-next-line react/set-state-in-effect
      else setUnread((value) => value + added)
    }
    previous.current = count
  }, [count])
  return { thread, unread, jump, onScroll }
}
