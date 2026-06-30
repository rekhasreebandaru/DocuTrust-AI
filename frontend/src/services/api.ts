import axios from 'axios';
import type { ChatHistoryItem, ChatResponse, DashboardStats, DocumentMetadata, LoginResponse, SearchResult, UserSettings } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';
export const api = axios.create({ baseURL: API_BASE_URL, timeout: 180000 });
api.interceptors.request.use((config) => { const token = localStorage.getItem('docutrust_token'); if (token) config.headers.Authorization = 'Bearer ' + token; return config; });
function downloadBlob(blob: Blob, filename: string) { const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = filename; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url); }
export async function login(username: string, password: string): Promise<LoginResponse> { const { data } = await api.post<LoginResponse>('/auth/login', { username, password }); return data; }
export async function getDashboardStats(): Promise<DashboardStats> { const { data } = await api.get<DashboardStats>('/dashboard/stats'); return data; }
export async function uploadDocuments(files: File[]): Promise<DocumentMetadata[]> { const formData = new FormData(); files.forEach((file) => formData.append('files', file)); const { data } = await api.post<DocumentMetadata[]>('/documents/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }); return data; }
export async function listDocuments(): Promise<DocumentMetadata[]> { const { data } = await api.get<DocumentMetadata[]>('/documents'); return data; }
export async function deleteDocument(id: string): Promise<void> { await api.delete('/documents/' + id); }
export async function renameDocument(id: string, name: string): Promise<void> { await api.patch('/documents/' + id + '/rename', { name }); }
export async function reindexDocument(id: string): Promise<DocumentMetadata> { const { data } = await api.post<DocumentMetadata>('/documents/' + id + '/reindex'); return data; }
export async function fetchDocumentBlob(id: string): Promise<Blob> { const response = await api.get('/documents/' + id + '/file', { responseType: 'blob' }); return response.data; }
export async function searchDocuments(q: string): Promise<SearchResult[]> { const { data } = await api.get<SearchResult[]>('/search', { params: { q } }); return data; }
export async function askQuestion(payload: { question: string; top_k: number; document_ids?: string[] }): Promise<ChatResponse> { const { data } = await api.post<ChatResponse>('/chat/query', payload); return data; }
export async function getChatHistory(): Promise<ChatHistoryItem[]> { const { data } = await api.get<ChatHistoryItem[]>('/chat/history'); return data; }
export async function getChat(id: string): Promise<ChatHistoryItem> { const { data } = await api.get<ChatHistoryItem>('/chat/' + id); return data; }
export async function renameChat(id: string, name: string): Promise<void> { await api.patch('/chat/' + id + '/rename', { name }); }
export async function deleteChat(id: string): Promise<void> { await api.delete('/chat/' + id); }
export async function sendFeedback(id: string, feedback: 'like' | 'dislike'): Promise<void> { await api.post('/chat/' + id + '/feedback', { feedback }); }
export async function exportChat(id: string, format: 'pdf' | 'word' | 'markdown' | 'text'): Promise<void> { const response = await api.get('/chat/' + id + '/export/' + format, { responseType: 'blob' }); const ext = format === 'markdown' ? 'md' : format === 'word' ? 'doc' : format === 'text' ? 'txt' : 'pdf'; downloadBlob(response.data, 'docutrust-chat-' + id + '.' + ext); }
export async function downloadChatPdf(chatId: string): Promise<void> { await exportChat(chatId, 'pdf'); }
export async function getSettings(): Promise<UserSettings> { const { data } = await api.get<UserSettings>('/settings'); return data; }
export async function updateSettings(settings: UserSettings): Promise<UserSettings> { const { data } = await api.put<UserSettings>('/settings', settings); return data; }