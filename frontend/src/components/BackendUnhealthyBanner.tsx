import { AlertTriangle } from 'lucide-react';
import { BackendStatus } from '../types';

interface BackendUnhealthyBannerProps {
  status: BackendStatus;
}

export default function BackendUnhealthyBanner({ status }: BackendUnhealthyBannerProps) {
  if (status.status === 'healthy') return null;

  return (
    <div className="bg-red-50 border-b border-red-200 px-4 py-2.5 flex items-center justify-center gap-2 animate-fade-in">
      <AlertTriangle size={16} className="text-red-500 flex-shrink-0" />
      <p className="text-sm text-red-700 font-medium">
        Backend service <span className="font-semibold">{status.service}</span> is{' '}
        <span className="font-semibold">{status.status}</span>. Some features may be unavailable.
      </p>
    </div>
  );
}
