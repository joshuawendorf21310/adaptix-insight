'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useApi } from '@/hooks/useApi';
import { PlateCard } from '@/components/ui/PlateCard';
import { Stack } from '@/components/design-system/layout/Stack';
import { Flex as _Flex } from '@/components/design-system/layout/Flex';
import { Badge } from '@/components/design-system/data-display/Badge';
import { Stat as _Stat } from '@/components/design-system/data-display/Stat';
import { Button } from '@/components/ui/Button';

interface HealthCheckResult {
  overall_status: string;
  timestamp: string;
  checks: Record<string, any>;
}

interface ReadinessResult {
  ready_for_production: boolean;
  completeness_percent: number;
  checks: Record<string, string>;
}

export default function DeploymentHealthView() {
  const { get } = useApi();
  const [health, setHealth] = useState<HealthCheckResult | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResult | null>(null);
  const [_loading, _setLoading] = useState(false);

  const loadHealthStatus = useCallback(async () => {
    try {
      const [healthRes, readinessRes] = await Promise.all([
        get('/api/v1/system-health/dashboard'),
        get('/api/v1/founder/deployment'),
      ]);
      setHealth({
        overall_status: (healthRes.data as Record<string, unknown>).overall_status as string,
        timestamp: ((healthRes.data as Record<string, unknown>).as_of as string) ?? new Date().toISOString(),
        checks: healthRes.data as Record<string, unknown>,
      });
      setReadiness({
        ready_for_production: Boolean((readinessRes.data as Record<string, unknown>).deployment_ready_for_aws),
        completeness_percent: Number((readinessRes.data as Record<string, unknown>).completion_percent ?? 0),
        checks: ((readinessRes.data as Record<string, unknown>).checks as Record<string, string>) ?? {},
      });
    } catch (err) {
      console.error('Failed to load health status:', err);
    }
  }, [get]);

  useEffect(() => {
    loadHealthStatus();
    const interval = setInterval(loadHealthStatus, 30000);
    return () => clearInterval(interval);
  }, [loadHealthStatus]);


  return (
    <div className="p-8 space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Deployment Health</h1>
        <Button onClick={loadHealthStatus} variant="secondary" size="sm">
          Refresh
        </Button>
      </div>

      <PlateCard>
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Readiness Status</h2>
            {readiness && (
              <Badge color={readiness.ready_for_production ? 'green' : 'yellow'}>
                {readiness.ready_for_production ? 'Production Ready' : 'Degraded'}
              </Badge>
            )}
          </div>

          {readiness && (
            <div className="space-y-4">
              <div className="w-full bg-gray-200 rounded-full h-8">
                <div
                  className="bg-green-500 h-8 rounded-full flex items-center justify-center text-white font-semibold text-sm"
                  style={{ width: `${readiness.completeness_percent}%` }}
                >
                  {Math.round(readiness.completeness_percent)}%
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {Object.entries(readiness.checks).map(([check, status]) => (
                  <PlateCard key={check}>
                    <div className="flex items-center space-x-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{
                          backgroundColor:
                            status === 'healthy'
                              ? '#10b981'
                              : status === 'degraded'
                                ? '#f59e0b'
                                : '#ef4444',
                        }}
                      />
                      <div>
                        <p className="text-sm font-medium capitalize">{check.replace(/_/g, ' ')}</p>
                        <p className="text-xs text-gray-500">{status}</p>
                      </div>
                    </div>
                  </PlateCard>
                ))}
              </div>
            </div>
          )}
        </div>
      </PlateCard>

      {health && (
        <PlateCard>
          <h2 className="text-xl font-semibold mb-6">Full System Health</h2>
          <Stack spacing={3}>
            {Object.entries(health.checks).map(([service, result]) => (
              <ServiceHealthRow key={service} service={service} result={result} />
            ))}
          </Stack>
          <p className="text-xs text-gray-500 mt-6">
            Last updated: {new Date(health.timestamp).toLocaleString()}
          </p>
        </PlateCard>
      )}
    </div>
  );
}

function ServiceHealthRow({
  service,
  result,
}: {
  service: string;
  result: any;
}) {
  const statusColors: Record<string, string> = {
    healthy: '#10b981',
    degraded: '#f59e0b',
    unhealthy: '#ef4444',
  };

  const status = result.status || 'unknown';
  const color = statusColors[status] || '#6b7280';

  return (
    <div className="flex items-center justify-between p-4 border rounded-lg bg-gray-50">
      <div className="flex items-center space-x-3">
        <div
          className="w-3 h-3 rounded-full"
          style={{ backgroundColor: color }}
        />
        <div>
          <p className="font-semibold capitalize">{service.replace(/_/g, ' ')}</p>
          {result.service && (
            <p className="text-sm text-gray-600">{result.service}</p>
          )}
          {result.error && (
            <p className="text-sm text-red-600">{result.error}</p>
          )}
        </div>
      </div>
      <Badge color={status === 'healthy' ? 'green' : status === 'degraded' ? 'yellow' : 'red'}>
        {status}
      </Badge>
    </div>
  );
}
