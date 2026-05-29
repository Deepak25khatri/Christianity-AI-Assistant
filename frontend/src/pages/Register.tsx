import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, Denomination } from '../api'
import { useAuth } from '../store'

export default function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [denom, setDenom] = useState<Denomination>('none')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const setUser = useAuth((s) => s.setUser)
  const navigate = useNavigate()

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await api.register(email, password, denom === 'none' ? undefined : denom)
      setUser({ user_id: res.user_id, email: res.email, denomination_pref: res.denomination_pref, token: res.access_token })
      navigate('/chat')
    } catch (err: any) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form onSubmit={submit} className="card w-full max-w-sm p-8">
        <h1 className="text-3xl text-ink-800 mb-1">Create your account</h1>
        <p className="text-sm text-ink-400 mb-6">A space to ask, study, and reflect.</p>
        <div className="mb-4">
          <label className="label">Email</label>
          <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
        </div>
        <div className="mb-4">
          <label className="label">Password</label>
          <input className="input" value={password} onChange={(e) => setPassword(e.target.value)} type="password" minLength={6} required />
        </div>
        <div className="mb-6">
          <label className="label">Tradition (optional)</label>
          <select className="input" value={denom} onChange={(e) => setDenom(e.target.value as Denomination)}>
            <option value="none">Prefer not to say</option>
            <option value="catholic">Catholic</option>
            <option value="protestant">Protestant</option>
            <option value="orthodox">Orthodox</option>
          </select>
          <p className="mt-1 text-xs text-ink-400">We tailor commentary to your tradition while still showing other views.</p>
        </div>
        {error && <div className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        <button className="btn-primary w-full" disabled={loading}>{loading ? 'Creating...' : 'Create account'}</button>
        <p className="mt-4 text-center text-sm text-ink-500">
          Already have one? <Link className="text-gold-600 hover:underline" to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  )
}
