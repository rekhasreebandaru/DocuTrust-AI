import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AuthProvider } from './hooks/useAuth';
import { AuditLog } from './pages/AuditLog';
import { Chat } from './pages/Chat';
import { Dashboard } from './pages/Dashboard';
import { History } from './pages/History';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Settings } from './pages/Settings';
import { SharedChat } from './pages/SharedChat';
import { Upload } from './pages/Upload';
export default function App() { return <AuthProvider><Routes><Route path="/login" element={<Login />} /><Route path="/register" element={<Register />} /><Route path="/share/:token" element={<SharedChat />} /><Route element={<ProtectedRoute />}><Route element={<Layout />}><Route index element={<Dashboard />} /><Route path="/upload" element={<Upload />} /><Route path="/chat" element={<Chat />} /><Route path="/history" element={<History />} /><Route path="/settings" element={<Settings />} /><Route path="/audit" element={<AuditLog />} /></Route></Route><Route path="*" element={<Navigate to="/" replace />} /></Routes></AuthProvider>; }
