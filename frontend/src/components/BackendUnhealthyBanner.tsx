import { BackendStatus } from '../types';

interface BackendUnhealthyBannerProps {
  status: BackendStatus;
}

export default function BackendUnhealthyBanner({ status }: BackendUnhealthyBannerProps) {
  console.log("BackendUnhealthyBanner status: ", status);
  if (status.status !== 'healthy') {
    return (
    <div className="border border-red-500 rounded-lg overflow-hidden bg-red-50">
      <p>Backend {status.service} is {status.status}</p>
    </div>
  );
  }
  return null;
}

