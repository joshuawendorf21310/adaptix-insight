'use client';

import {
  CommandPageHeader,
  CommandPanel,
  DataRow,
  MetricTile,
  StatusPill,
} from '@/components/command/CommandPrimitives';
import { AdaptixCardSkeleton } from '@/components/ui';
import { useApi } from '@/hooks/useApi';

interface ConversionKpisResponse {
  total_events: number;
  total_proposals: number;
  active_subscriptions: number;
  proposal_to_paid_conversion_pct: number;
  as_of: string;
}

interface ConversionFunnelStage {
  stage: string;
  count: number;
}

interface ConversionFunnelResponse {
  funnel: ConversionFunnelStage[];
  total_events: number;
}

interface RevenuePipelineResponse {
  pending_pipeline_cents: number;
  active_mrr_cents: number;
  pipeline_to_mrr_ratio: number;
  as_of: string;
}

interface SubscriptionLifecycleResponse {
  lifecycle: Record<string, number>;
  total: number;
  as_of: string;
}

interface PayerMixEntry {
  category: string;
  count: number;
  pct: number;
}

interface PayerMixResponse {
  payer_mix: PayerMixEntry[];
  total_claims: number;
}

interface StripeReconciliationResponse {
  active_subscriptions: number;
  past_due_subscriptions: number;
  mrr_cents: number;
  as_of: string;
}

interface ChurnRiskSubscription {
  subscription_id: string;
  tenant_id?: string | null;
  status: string;
  monthly_amount_cents: number;
}

interface ChurnRiskResponse {
  at_risk_subscriptions: ChurnRiskSubscription[];
  count: number;
}

function formatMoneyFromCents(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '—';
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value / 100);
}

function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) {
    return '—';
  }

  return `${value.toFixed(digits)}%`;
}

function humanizeStage(stage: string): string {
  return stage.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

function churnTone(status: string): 'success' | 'warning' | 'critical' {
  if (status === 'past_due') {
    return 'warning';
  }
  if (status === 'canceled' || status === 'paused') {
    return 'critical';
  }
  return 'success';
}

export default function RoiAnalyticsPage() {
  const conversionKpisState = useApi<ConversionKpisResponse>('/api/v1/roi-funnel/conversion-kpis');
  const conversionFunnelState = useApi<ConversionFunnelResponse>('/api/v1/roi-funnel/conversion-funnel');
  const revenuePipelineState = useApi<RevenuePipelineResponse>('/api/v1/roi-funnel/revenue-pipeline');
  const lifecycleState = useApi<SubscriptionLifecycleResponse>('/api/v1/roi-funnel/subscription-lifecycle');
  const payerMixState = useApi<PayerMixResponse>('/api/v1/billing-command/payer-mix');
  const stripeState = useApi<StripeReconciliationResponse>('/api/v1/billing-command/stripe-reconciliation');
  const churnState = useApi<ChurnRiskResponse>('/api/v1/billing-command/churn-risk');

  const loading = [
    conversionKpisState.loading,
    conversionFunnelState.loading,
    revenuePipelineState.loading,
    lifecycleState.loading,
    payerMixState.loading,
    stripeState.loading,
    churnState.loading,
  ].some(Boolean);

  const errors = [
    conversionKpisState.error,
    conversionFunnelState.error,
    revenuePipelineState.error,
    lifecycleState.error,
    payerMixState.error,
    stripeState.error,
    churnState.error,
  ].filter((value): value is string => Boolean(value));

  const conversionKpis = conversionKpisState.data;
  const conversionFunnel = conversionFunnelState.data?.funnel ?? [];
  const revenuePipeline = revenuePipelineState.data;
  const lifecycle = lifecycleState.data;
  const payerMix = [...(payerMixState.data?.payer_mix ?? [])].sort((left, right) => right.count - left.count);
  const stripe = stripeState.data;
  const churn = churnState.data;

  const arrCents = (stripe?.mrr_cents ?? revenuePipeline?.active_mrr_cents ?? 0) * 12;
  const avgRevenuePerActiveSubscriptionCents = stripe?.active_subscriptions
    ? Math.round((stripe.mrr_cents / Math.max(stripe.active_subscriptions, 1)))
    : null;
  const proposalToPaid = conversionKpis?.proposal_to_paid_conversion_pct ?? null;
  const statusTone = loading
    ? 'neutral'
    : (churn?.count ?? 0) > 0
      ? 'warning'
      : 'success';

  return (
    <div className="space-y-6 md:space-y-7">
      <CommandPageHeader
        eyebrow="ROI and expansion intelligence"
        title="Revenue & ROI Analytics"
        description="This founder commercial surface now uses live conversion, subscription, payer-mix, and pipeline telemetry. Named-account economics, geographic penetration, and synthetic churn scores remain explicit until the backend actually emits them."
        status={<StatusPill label={loading ? 'Refreshing commercial telemetry' : (churn?.count ?? 0) > 0 ? 'Commercial watchlist active' : 'Commercial telemetry healthy'} tone={statusTone} />}
        meta={[
          stripe ? `${stripe.active_subscriptions} active subscriptions` : 'Subscription telemetry loading',
          revenuePipeline ? `${formatMoneyFromCents(revenuePipeline.pending_pipeline_cents)} pending pipeline` : 'Pipeline telemetry loading',
          conversionKpis ? `${conversionKpis.total_proposals} total proposals` : 'Proposal telemetry loading',
        ]}
      />

      {errors.length > 0 ? (
        <div className="command-panel border border-[rgba(255,45,45,0.24)] bg-[rgba(255,45,45,0.08)] px-4 py-3 text-sm text-[var(--color-brand-red)]">
          {errors[0]}
        </div>
      ) : null}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {Array.from({ length: 5 }).map((_, index) => (
            <AdaptixCardSkeleton key={index} />
          ))}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <MetricTile label="MRR" value={formatMoneyFromCents(stripe?.mrr_cents ?? revenuePipeline?.active_mrr_cents)} detail="Active subscription recurring revenue" tone="info" />
            <MetricTile label="ARR" value={formatMoneyFromCents(arrCents)} detail="Annualized recurring revenue from active subscriptions" tone="info" />
            <MetricTile label="Active subscriptions" value={String(stripe?.active_subscriptions ?? conversionKpis?.active_subscriptions ?? '—')} detail="Live paid subscription count" tone="accent" />
            <MetricTile label="Avg revenue / subscription" value={formatMoneyFromCents(avgRevenuePerActiveSubscriptionCents)} detail="MRR divided by active subscriptions" tone="success" />
            <MetricTile label="Proposal → paid" value={formatPercent(proposalToPaid)} detail="Founder conversion from proposals to active subscriptions" tone={(proposalToPaid ?? 0) >= 25 ? 'success' : 'warning'} />
          </div>

          <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
            <CommandPanel
              eyebrow="Funnel performance"
              title="Commercial conversion funnel"
              description="Actual founder conversion events grouped by stage."
            >
              {conversionFunnel.length > 0 ? (
                conversionFunnel.map((stage) => (
                  <DataRow
                    key={stage.stage}
                    label={humanizeStage(stage.stage)}
                    value={`${stage.count}`}
                    tone={stage.count > 0 ? 'info' : 'neutral'}
                    detail={`${stage.count} event(s) recorded in this funnel stage`}
                  />
                ))
              ) : (
                <DataRow label="Conversion funnel" value="No funnel events returned" tone="warning" />
              )}
            </CommandPanel>

            <CommandPanel
              eyebrow="Payer mix"
              title="Revenue composition"
              description="Live payer-category mix from billing claim telemetry."
            >
              {payerMix.length > 0 ? (
                payerMix.map((payer) => (
                  <DataRow
                    key={payer.category}
                    label={payer.category || 'unknown'}
                    value={formatPercent(payer.pct, 2)}
                    tone={payer.pct >= 40 ? 'info' : payer.pct >= 20 ? 'success' : 'warning'}
                    detail={`${payer.count} claim(s)`}
                  />
                ))
              ) : (
                <DataRow label="Payer mix" value="No payer mix rows returned" tone="warning" />
              )}
            </CommandPanel>
          </div>

          <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
            <CommandPanel
              eyebrow="Revenue pipeline"
              title="Commercial pipeline posture"
              description="Pending proposal value and its relationship to live recurring revenue."
            >
              <DataRow
                label="Pending pipeline"
                value={formatMoneyFromCents(revenuePipeline?.pending_pipeline_cents)}
                tone="accent"
              />
              <DataRow
                label="Active MRR"
                value={formatMoneyFromCents(revenuePipeline?.active_mrr_cents)}
                tone="success"
              />
              <DataRow
                label="Pipeline / MRR ratio"
                value={revenuePipeline ? `${revenuePipeline.pipeline_to_mrr_ratio.toFixed(2)}x` : '—'}
                tone={(revenuePipeline?.pipeline_to_mrr_ratio ?? 0) >= 1 ? 'success' : 'warning'}
                detail="Ratio of pending commercial value to current recurring base"
              />
              <DataRow
                label="Past-due subscriptions"
                value={String(stripe?.past_due_subscriptions ?? '—')}
                tone={(stripe?.past_due_subscriptions ?? 0) > 0 ? 'warning' : 'success'}
                detail="From Stripe reconciliation telemetry"
              />
            </CommandPanel>

            <CommandPanel
              eyebrow="Retention posture"
              title="Subscription lifecycle and churn watchlist"
              description="Actual subscription statuses and at-risk subscription rows."
            >
              {Object.entries(lifecycle?.lifecycle ?? {}).length > 0 ? (
                Object.entries(lifecycle?.lifecycle ?? {}).map(([status, count]) => (
                  <DataRow
                    key={status}
                    label={humanizeStage(status)}
                    value={String(count)}
                    tone={status === 'active' ? 'success' : status === 'trial' ? 'info' : churnTone(status)}
                    detail="Subscription lifecycle count"
                  />
                ))
              ) : (
                <DataRow label="Subscription lifecycle" value="No lifecycle rows returned" tone="warning" />
              )}
              {(churn?.at_risk_subscriptions ?? []).slice(0, 5).map((item) => (
                <DataRow
                  key={item.subscription_id}
                  label={`Subscription ${item.subscription_id.slice(0, 8)}`}
                  value={formatMoneyFromCents(item.monthly_amount_cents)}
                  tone={churnTone(item.status)}
                  detail={humanizeStage(item.status)}
                />
              ))}
            </CommandPanel>
          </div>

          <CommandPanel
            eyebrow="Instrumentation honesty"
            title="Still unavailable in backend telemetry"
            description="These views were previously hardcoded. They now stay explicit until real commercial instrumentation exists."
          >
            <DataRow
              label="Named account economics"
              value="Unavailable"
              tone="warning"
              detail="Current founder APIs expose proposal and subscription counts, not per-agency named-account revenue rows with plan labels and transport volumes."
            />
            <DataRow
              label="Regional penetration"
              value="Unavailable"
              tone="warning"
              detail="No founder commercial endpoint currently emits state-by-state market potential or penetration metrics."
            />
            <DataRow
              label="Synthetic churn score"
              value="Unavailable"
              tone="warning"
              detail="The backend exposes at-risk subscription statuses, not per-agency churn scores out of 100."
            />
            <DataRow
              label="Static pricing story"
              value="Unavailable in this dashboard"
              tone="warning"
              detail="Pricing should come from dedicated pricing endpoints or configuration, not a hardcoded founder analytics panel."
            />
          </CommandPanel>
        </>
      )}
    </div>
  );
}
