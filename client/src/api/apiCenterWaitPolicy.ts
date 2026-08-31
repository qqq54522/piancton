const MILLISECONDS_PER_SECOND = 1000;
const REQUEST_GRACE_SECONDS = 15;

export const NEW_API_PROBE_LIMIT_SECONDS = 60;
export const HEALTH_PROBE_LIMIT_SECONDS = 60;
export const HEALTH_PROBE_ATTEMPTS = 2;
export const HEALTH_CHECK_PARALLELISM = 4;

export function apiCenterRequestWaitMs(
  perCallLimitSeconds: number,
  operationCount = 1,
  parallelism = 1,
): number {
  const safeLimit = Math.max(0.5, perCallLimitSeconds);
  const safeCount = Math.max(1, Math.ceil(operationCount));
  const safeParallelism = Math.max(1, Math.floor(parallelism));
  const rounds = Math.ceil(safeCount / safeParallelism);
  return Math.ceil(
    (safeLimit * rounds + REQUEST_GRACE_SECONDS) * MILLISECONDS_PER_SECOND,
  );
}

export function recommendedApiCallLimitSeconds(probeDurationsMs: number[]): number {
  const slowestProbeSeconds = Math.max(0, ...probeDurationsMs) / MILLISECONDS_PER_SECOND;
  const recommended = Math.ceil(slowestProbeSeconds * 2 + 10);
  return Math.min(NEW_API_PROBE_LIMIT_SECONDS, Math.max(20, recommended));
}
