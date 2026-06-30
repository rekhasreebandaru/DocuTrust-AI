import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
export function ProtectedRoute() { return useAuth().isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />; }
