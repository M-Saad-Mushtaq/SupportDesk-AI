import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { Icon } from './Icon'

// Native modal dialogs provide focus containment, Escape, and an inert backdrop.
export function Drawer({ open, onClose, title, children, side = 'right' }: {
  open: boolean; onClose: () => void; title: string; children: ReactNode; side?: 'left' | 'right'
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current
    if (!dialog || !open) return
    const previous = document.activeElement as HTMLElement | null
    dialog.showModal()
    return () => {
      dialog.close()
      previous?.focus()
    }
  }, [open])
  return (
    <dialog ref={ref} className={`drawer drawer--${side}`} aria-label={title}
      onCancel={(event) => { event.preventDefault(); onClose() }}
      onClick={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <div className="drawer-surface">
        <div className="drawer-heading"><div><h2>{title}</h2><span className="drawer-demo">Demo — sample data</span></div><button className="icon-button" onClick={onClose} aria-label={`Close ${title.toLowerCase()}`}><Icon name="close" /></button></div>
        {children}
      </div>
    </dialog>
  )
}
