import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { defaultSettings, timezones, toneExamples, tones, validateSettings, weekDays } from '../data/workspace'
import type { DemoSettings } from '../data/workspace'
import { PageHeading } from '../components/PageHeading'
import { Icon } from '../components/Icon'

export function Settings() {
  const [saved, setSaved] = useState(defaultSettings)
  const [draft, setDraft] = useState(defaultSettings)
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(true)
  const [ready, setReady] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const version = useRef(0)
  const writing = useRef(false)
  const load = useCallback(async () => {
    const request = ++version.current
    try {
      const settings = await api.settings()
      if (request !== version.current) return
      setSaved(settings)
      setDraft(settings)
      setReady(true)
      setError('')
    } catch (error) {
      if (request === version.current) setError(error instanceof Error ? error.message : 'Could not load settings.')
    } finally { if (request === version.current) setLoading(false) }
  }, [])
  const invalidateLoad = useCallback(() => { version.current++ }, [])
  // The read callback updates state only after awaited API I/O.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void load(); return invalidateLoad }, [load, invalidateLoad])
  const dirty = JSON.stringify(saved) !== JSON.stringify(draft)

  function update<K extends keyof DemoSettings>(key: K, value: DemoSettings[K]) {
    setDraft((current) => ({ ...current, [key]: value }))
    setNotice('')
  }
  async function save() {
    if (writing.current || !ready) return
    const cleaned = { ...draft, company: draft.company.trim(), email: draft.email.trim() }
    if (!validateSettings(cleaned)) {
      setNotice('Check the company and email, select at least one support day, and set a closing time after opening time.')
      return
    }
    writing.current = true
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const result = await api.saveSettings(cleaned)
      setSaved(result)
      setDraft(result)
      setNotice('Settings saved to SQLite. They will remain after refresh or backend restart.')
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Settings could not be saved. Your edits are kept; retry Save.')
    } finally { writing.current = false; setSaving(false) }
  }

  return <main className="content-page settings-page">
    <PageHeading title="Settings" description="Set up your demo company and support preferences." action={<span className="page-period">Local demo configuration</span>} />
    {error && <div className="storage-error" role="alert"><span>{error}</span><button type="button" className="secondary-button" disabled={loading || saving} onClick={() => { setLoading(true); void load() }}>Reload settings</button></div>}
    {loading && <p role="status" className="page-notice">Loading settings from SQLite...</p>}
    <form onSubmit={(event) => { event.preventDefault(); void save() }}><fieldset className="settings-form-fields" disabled={loading || saving || !ready}>
      <section className="settings-section"><div className="settings-description"><span className="settings-section-icon"><Icon name="box" /></span><h2>Company details</h2><p>Use sample business information for this workspace.</p></div><div className="panel settings-fields two-fields"><label>Company name<input name="company" required maxLength={80} value={draft.company} onChange={(event) => update('company', event.target.value)} /></label><label>Support email<input name="supportEmail" required type="email" maxLength={120} value={draft.email} onChange={(event) => update('email', event.target.value)} /></label><p className="field-hint full-field">No credentials are needed. These non-sensitive details are saved in the local database.</p></div></section>
      <section className="settings-section"><div className="settings-description"><span className="settings-section-icon"><Icon name="activity" /></span><h2>Support hours</h2><p>Choose the team's regular working days and hours.</p></div><div className="panel settings-fields"><label>Time zone<select name="timezone" value={draft.timezone} onChange={(event) => update('timezone', event.target.value)}>{timezones.map((zone) => <option key={zone}>{zone}</option>)}</select></label><fieldset className="day-picker"><legend>Working days</legend>{weekDays.map((day) => <label key={day}><input type="checkbox" checked={draft.days.includes(day)} onChange={(event) => update('days', weekDays.filter((item) => item === day ? event.target.checked : draft.days.includes(item)))} /><span>{day}</span></label>)}</fieldset><div className="two-fields"><label>Opens at<input name="start" type="time" required value={draft.start} onChange={(event) => update('start', event.target.value)} /></label><label>Closes at<input name="end" type="time" required value={draft.end} onChange={(event) => update('end', event.target.value)} /></label></div><p className="field-hint">Hours use the selected time zone. This demo supports same-day shifts.</p></div></section>
      <section className="settings-section"><div className="settings-description"><span className="settings-section-icon"><Icon name="inbox" /></span><h2>Response tone</h2><p>Choose how sample support responses should sound.</p></div><div className="panel settings-fields"><label>Preferred tone<select name="tone" value={draft.tone} onChange={(event) => update('tone', event.target.value as DemoSettings['tone'])}>{tones.map((tone) => <option key={tone}>{tone}</option>)}</select></label><div className="tone-preview"><span className="section-label">Sample wording · Not generated</span><p>{toneExamples[draft.tone]}</p></div></div></section>
      <section className="settings-section"><div className="settings-description"><span className="settings-section-icon"><Icon name="hand" /></span><h2>Escalation rules</h2><p>Choose when a support specialist should review a request.</p></div><div className="panel settings-fields escalation-fields">
        <label><span><strong>Customer asks for a person</strong><small>Route direct requests for human help to the team.</small></span><input type="checkbox" checked={draft.escalateOnRequest} onChange={(event) => update('escalateOnRequest', event.target.checked)} /></label>
        <label><span><strong>Damaged or faulty item</strong><small>Review replacement and refund options with a person.</small></span><input type="checkbox" checked={draft.escalateDamage} onChange={(event) => update('escalateDamage', event.target.checked)} /></label>
        <label><span><strong>Time-sensitive delivery issue</strong><small>Review delays when the customer has a deadline.</small></span><input type="checkbox" checked={draft.escalateDelivery} onChange={(event) => update('escalateDelivery', event.target.checked)} /></label>
        <p className="field-hint">Demo preferences only. Saving does not reroute existing tickets, schedule replies, or change the fixed inbox simulations.</p>
      </div></section>
      <div className="settings-save-bar"><div role="status"><strong>{dirty ? 'Unsaved changes' : 'Demo preferences'}</strong><p>{notice || 'Settings and messages persist in the local SQLite database.'}</p></div><div className="settings-save-actions"><button type="button" className="secondary-button" onClick={() => { setDraft(defaultSettings); setNotice('Demo defaults applied to the form. Save to keep them.') }}>Use demo defaults</button><button type="submit" className="primary-button"><Icon name="check" size={17} />{saving ? 'Saving...' : 'Save demo settings'}</button></div></div>
    </fieldset></form>
  </main>
}
