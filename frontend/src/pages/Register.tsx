import { FormEvent, useState } from 'react';
import toast from 'react-hot-toast';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { UserPlus } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export function Register() {
  const { register, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) return <Navigate to="/" replace />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (password !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    if (password.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }
    setLoading(true);
    try {
      await register(username, password);
      toast.success('Account created — welcome to DocuTrust');
      navigate('/');
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Could not create account';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4 dark:bg-slate-950">
      <form onSubmit={handleSubmit} className="panel w-full max-w-md p-8">
        <div className="mb-8 flex items-center gap-3">
          <div className="rounded-md bg-teal-50 p-3 text-trust dark:bg-teal-950">
            <UserPlus size={28} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Create account</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Join your team's DocuTrust workspace</p>
          </div>
        </div>
        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-medium">Username</span>
          <input className="input" value={username} onChange={(event) => setUsername(event.target.value)} minLength={3} required />
        </label>
        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-medium">Password</span>
          <input className="input" type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={6} required />
        </label>
        <label className="mb-6 block">
          <span className="mb-1 block text-sm font-medium">Confirm password</span>
          <input className="input" type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} minLength={6} required />
        </label>
        <button className="btn-primary w-full" disabled={loading}>{loading ? 'Creating account...' : 'Create account'}</button>
        <p className="mt-4 text-center text-sm text-slate-500 dark:text-slate-400">
          Already have an account? <Link to="/login" className="font-semibold text-trust">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
