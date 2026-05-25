"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/button";
import { Alert } from "@/components/alert";
import { apiClient, ApiClientError } from "@/lib/api-client";
import type { AuthToken, PaginatedResponse } from "@/lib/types";

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

function parseUserAgent(ua: string | null): string {
  if (!ua) return "Unknown device";
  if (ua.includes("Chrome")) return "Chrome browser";
  if (ua.includes("Firefox")) return "Firefox browser";
  if (ua.includes("Safari")) return "Safari browser";
  if (ua.includes("Edge")) return "Edge browser";
  return "Web browser";
}

export default function SessionsPage() {
  const [sessions, setSessions] = useState<AuthToken[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await apiClient.get<PaginatedResponse<AuthToken>>("/auth/sessions");
      setSessions(data.items);
      setError(null);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 404) {
        setSessions([]);
        setError(null);
      } else {
        setError("Could not load sessions. The sessions endpoint may not be available yet.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const revokeSession = async (id: string) => {
    setRevokingId(id);
    try {
      await apiClient.post(`/auth/sessions/${id}/revoke`);
      setSessions((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      }
    } finally {
      setRevokingId(null);
    }
  };

  return (
    <div>
      <p className="text-sm text-text-secondary mb-6">
        Manage your active login sessions across devices
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
      ) : sessions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center bg-surface-strong rounded-xl border border-border-light shadow-sm">
          <div className="w-10 h-10 rounded-full bg-surface-sunken text-text-tertiary flex items-center justify-center mb-3 text-lg font-semibold">
            –
          </div>
          <p className="text-sm font-medium text-text-primary mb-1">No active sessions found</p>
          <p className="text-sm text-text-secondary max-w-sm">
            Session data will appear here once the backend endpoint is available.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`flex items-center gap-4 p-4 bg-surface-strong rounded-xl border shadow-sm ${
                session.token_type === "ACCESS"
                  ? "border-accent/30 bg-accent-subtle/30"
                  : "border-border-light"
              }`}
            >
              <div className="w-10 h-10 rounded-lg bg-surface-sunken text-text-secondary flex items-center justify-center text-sm font-semibold flex-shrink-0 font-display">
                {parseUserAgent(session.user_agent).charAt(0)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-text-primary">
                    {session.device_name || parseUserAgent(session.user_agent)}
                  </span>
                  {session.token_type === "ACCESS" && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-accent-subtle text-accent">
                      Current
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 flex-wrap mt-0.5">
                  {session.ip_address && (
                    <span className="text-xs text-text-tertiary">{session.ip_address}</span>
                  )}
                  <span className="text-xs text-text-tertiary">
                    Last active {formatRelativeTime(session.last_used_at)}
                  </span>
                  <span className="text-xs text-text-tertiary">
                    Created {formatRelativeTime(session.created_at)}
                  </span>
                </div>
              </div>
              <div className="flex-shrink-0">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => revokeSession(session.id)}
                  loading={revokingId === session.id}
                  disabled={session.token_type === "ACCESS"}
                >
                  Revoke
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
