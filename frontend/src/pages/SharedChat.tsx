import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import { CitationList } from '../components/CitationList';
import { api } from '../services/api';
import type { ChatResponse } from '../types';

export function SharedChat() {
  const { token } = useParams();
  const [chat, setChat] = useState<ChatResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!token) return;
    api
      .get<ChatResponse>('/public/share/' + token)
      .then((res) => setChat(res.data))
      .catch(() => setError(true));
  }, [token]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4 py-10 dark:bg-slate-950">
      <div className="panel w-full max-w-2xl p-8">
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-md bg-teal-50 p-3 text-trust dark:bg-teal-950">
            <ShieldCheck size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">DocuTrust — shared answer</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Read-only view, no login required</p>
          </div>
        </div>
        {error && <p className="text-sm text-red-500">This share link is invalid or has been disabled.</p>}
        {!error && !chat && <p className="text-sm text-slate-500">Loading...</p>}
        {chat && (
          <div>
            <p className="mb-2 font-semibold text-slate-900 dark:text-white">{chat.question}</p>
            <p className="mb-6 whitespace-pre-wrap leading-7 text-slate-700 dark:text-slate-200">{chat.answer}</p>
            <CitationList citations={chat.citations} />
          </div>
        )}
      </div>
    </div>
  );
}
