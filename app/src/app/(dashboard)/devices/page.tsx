"use client";

import { useCallback, useEffect, useState } from "react";

import { Alert } from "@/components/alert";
import { apiClient, ApiClientError } from "@/lib/api-client";
import type { AuthToken, PaginatedResponse } from "@/lib/types";

type DeviceGroup = {
  deviceName: string;
  sessionCount: number;
  lastActive: string;
  ipAddresses: string[];
  userAgent: string | null;
};

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHrs = Math.floor(diffMin / 60);
  const diffDays = Math.floor(diffHrs / 24);

  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHrs < 24) return `${diffHrs}h ago`;
  if (diffDays < 30) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function groupByDevice(sessions: AuthToken[]): DeviceGroup[] {
  const groups = new Map<string, DeviceGroup>();

  for (const session of sessions) {
    const key = session.device_name || session.user_agent || "Unknown device";
    const existing = groups.get(key);

    if (existing) {
      existing.sessionCount++;
      if (new Date(session.last_used_at) > new Date(existing.lastActive)) {
        existing.lastActive = session.last_used_at;
      }
      if (session.ip_address && !existing.ipAddresses.includes(session.ip_address)) {
        existing.ipAddresses.push(session.ip_address);
      }
    } else {
      groups.set(key, {
        deviceName: session.device_name || "Web browser",
        sessionCount: 1,
        lastActive: session.last_used_at,
        ipAddresses: session.ip_address ? [session.ip_address] : [],
        userAgent: session.user_agent,
      });
    }
  }

  return Array.from(groups.values()).sort(
    (a, b) => new Date(b.lastActive).getTime() - new Date(a.lastActive).getTime()
  );
}

export default function DevicesPage() {
  const [devices, setDevices] = useState<DeviceGroup[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDevices = useCallback(async () => {
    try {
      const data = await apiClient.get<PaginatedResponse<AuthToken>>("/auth/sessions");
      setDevices(groupByDevice(data.items));
      setError(null);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 404) {
        setDevices([]);
        setError(null);
      } else {
        setError("Could not load devices. The sessions endpoint may not be available yet.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();
  }, [fetchDevices]);

  return (
    <div>
      <p className="text-sm text-text-secondary mb-6">
        Devices that have been used to access your account
      </p>

      {error && (
        <div className="mb-4">
          <Alert variant="info" dismissible onDismiss={() => setError(null)}>
            <p>{error}</p>
          </Alert>
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="w-6 h-6 border-2 border-border-default border-t-accent rounded-full animate-spin" />
        </div>
      ) : devices.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center bg-surface-strong rounded-xl border border-border-light shadow-sm">
          <div className="w-10 h-10 rounded-full bg-surface-sunken text-text-tertiary flex items-center justify-center mb-3 text-lg font-semibold">
            –
          </div>
          <p className="text-sm font-medium text-text-primary mb-1">No devices found</p>
          <p className="text-sm text-text-secondary max-w-sm">
            Device information will appear here once the backend endpoint is available.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {devices.map((device) => (
            <div
              key={device.deviceName}
              className="flex flex-col gap-3 p-5 bg-surface-strong rounded-xl border border-border-light shadow-sm"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-surface-sunken text-text-secondary flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="5" y="2" width="14" height="20" rx="2" ry="2" />
                    <line x1="12" y1="18" x2="12.01" y2="18" />
                  </svg>
                </div>
                <span className="text-sm font-semibold text-text-primary truncate">
                  {device.deviceName}
                </span>
              </div>
              <div className="flex flex-col gap-1.5 text-xs text-text-secondary">
                <span>
                  Sessions:{" "}
                  <strong className="text-text-primary">{device.sessionCount}</strong>
                </span>
                <span>
                  Last active:{" "}
                  <strong className="text-text-primary">{formatRelativeTime(device.lastActive)}</strong>
                </span>
                {device.ipAddresses.length > 0 && (
                  <span>
                    IP:{" "}
                    <strong className="text-text-primary">{device.ipAddresses.join(", ")}</strong>
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
