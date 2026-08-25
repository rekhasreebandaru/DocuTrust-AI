import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { ShieldAlert } from 'lucide-react';
import { getAuditLog } from '../services/api';
import type { AuditLogItem } from '../types';
import { useAuth } from '../hooks/useAuth';

export function AuditLog() {
  const { isAdmin } = useAuth();
  const [entries, setEntries] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAdmin) {
      setLoading(false);
      return;
    }
    getAuditLog()
      .then(setEntries)
      .catch(() => toast.error('Could not load audit log'))
      .finally(() => setLoading(false));
  }, [isAdmin]);

  if (!isAdmin) {
    return (
      <div className="panel flex flex-col items-center gap-3 p-10 text-center">
        <ShieldAlert size={32} className="text-amber-500" />
        <h2 className="text-lg font-semibold">Admins only</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">The audit log is restricted to admin accounts.</p>
      </div>
    );
  }

  return (
    <div className="panel p-6">
      <h1 className="mb-1 text-2xl font-bold">Audit log</h1>
      <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">Recent account activity across the workspace.</p>
      {loading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : entries.length === 0 ? (
        <p className="text-sm text-slate-500">No activity recorded yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800">
                <th className="py-2 pr-4 font-medium">Time</th>
                <th className="py-2 pr-4 font-medium">User</th>
                <th className="py-2 pr-4 font-medium">Action</th>
                <th className="py-2 pr-4 font-medium">Target</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} className="border-b border-slate-100 dark:border-slate-900">
                  <td className="py-2 pr-4 text-slate-500">{new Date(entry.created_at).toLocaleString()}</td>
                  <td className="py-2 pr-4 font-medium">{entry.username}</td>
                  <td className="py-2 pr-4"><span className="rounded-full bg-teal-50 px-2 py-0.5 text-xs font-semibold text-trust dark:bg-teal-950">{entry.action}</span></td>
                  <td className="py-2 pr-4 text-slate-500">{entry.target ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
