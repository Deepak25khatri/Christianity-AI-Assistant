import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, Denomination } from '../api'
import { useAuth } from '../store'

export default function Settings() {
  const { user, setUser, logout } = useAuth()
  const navigate = useNavigate()
  const [denom, setDenom] = useState<Denomination>(user?.denomination_pref || 'none')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    try {
      const res = await api.updateDenom(denom)
      if (user) setUser({ ...user, denomination_pref: res.denomination_pref })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen p-6 max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl">Settings</h1>
        <Link to="/chat" className="btn-ghost">Back to chat</Link>
      </div>
      <div className="card p-6 mb-6">
        <h2 className="text-xl mb-3">Account</h2>
        <p className="text-sm text-ink-500">Signed in as <span className="font-medium text-ink-800">{user?.email}</span></p>
        <button className="btn-ghost mt-3 text-red-600 hover:bg-red-50" onClick={() => { logout(); navigate('/login') }}>Sign out</button>
      </div>
      <div className="card p-6">
        <h2 className="text-xl mb-3">Tradition preference</h2>
        <p className="text-sm text-ink-500 mb-3">
          We highlight commentary from your tradition and clearly label alternate views when relevant.
          You can change this anytime.
        </p>
        <select className="input mb-4" value={denom} onChange={(e) => setDenom(e.target.value as Denomination)}>
          <option value="none">Prefer not to say</option>
          <option value="catholic">Catholic</option>
          <option value="protestant">Protestant</option>
          <option value="orthodox">Orthodox</option>
        </select>
        <button className="btn-primary" disabled={saving} onClick={save}>{saving ? 'Saving...' : 'Save'}</button>
      </div>
    </div>
  )
}
