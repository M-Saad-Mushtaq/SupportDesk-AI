import type { ReactNode } from 'react'

export function PageHeading({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <header className="page-heading"><div><p className="section-label">Support workspace</p><h1>{title}</h1><p>{description}</p></div>{action}</header>
}
