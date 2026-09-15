type IconName = 'inbox' | 'grid' | 'book' | 'activity' | 'settings' | 'search' | 'back' | 'close' | 'menu' | 'user' | 'send' | 'lock' | 'chevron' | 'box' | 'check' | 'hand'

const paths: Record<IconName, string> = {
  inbox: 'M4 4h16v16H4z M4 13h5l2 3h2l2-3h5',
  grid: 'M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h6v6h-6z',
  book: 'M12 6v15 M12 6C9 3 5 3 2 4v15c4-1 7-1 10 2 3-3 6-3 10-2V4c-3-1-7-1-10 2Z',
  activity: 'M3 12h4l3-8 4 16 3-8h4',
  settings: 'm9 3-1 3-3 1-2 4 2 2v4l4 3 3-1 3 1 4-3v-4l2-2-2-4-3-1-1-3Z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  search: 'M16 16l5 5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  back: 'm14 5-7 7 7 7 M7 12h14',
  close: 'm6 6 12 12 M6 18 18 6',
  menu: 'M4 6h16 M4 12h16 M4 18h16',
  user: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M4 21v-2a8 8 0 0 1 16 0v2Z',
  send: 'm3 3 18 9-18 9 4-9-4-9Z M7 12h14',
  lock: 'M5 10h14v11H5z M8 10V6a4 4 0 0 1 8 0v4 M12 14v3',
  chevron: 'm8 5 7 7-7 7',
  box: 'm3 7 9-4 9 4v10l-9 4-9-4V7Z M3 7l9 4 9-4 M12 11v10 M7 5l10 4',
  check: 'm5 12 4 4L19 6',
  hand: 'M8 12V5a2 2 0 0 1 4 0v7 M12 6a2 2 0 0 1 4 0v6 M16 9a2 2 0 0 1 4 0v6a7 7 0 0 1-12 5l-5-6a2 2 0 0 1 3-2l2 2',
}

export function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>
}
