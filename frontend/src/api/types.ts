export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export type UserRole = "analyst" | "compliance_officer" | "admin";

export interface AuthMeResponse {
  sub: string;
  role: UserRole;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RagAskRequest {
  question: string;
  top_k?: number;
}

export interface RagSource {
  id: string;
  document_id: string;
  content: string;
  position: number;
  title: string;
  source: string;
}

export interface RagCitation {
  reference: number;
  document_id: string;
  chunk_id: string;
}

export interface RagAskResponse {
  question: string;
  answer: string;
  sources: RagSource[];
  citations: RagCitation[];
  abstained: boolean;
}

export type ConfigurationValue = string | number | boolean | null;

export interface EvaluationParameterChange {
  name: string;
  previous_value: ConfigurationValue;
  new_value: ConfigurationValue;
}

export interface EvaluationMetrics {
  source_hit_at_1: number;
  source_hit_at_3: number;
  evidence_hit_at_1: number;
  evidence_hit_at_3: number;
  mean_latency_seconds: number;
  precision_at_1?: number;
  precision_at_3?: number;
  recall_at_1?: number;
  recall_at_3?: number;
  f1_at_1?: number;
  f1_at_3?: number;
  map_at_3?: number;
  success_at_1?: number;
  success_at_3?: number;
  mrr_at_3?: number;
  ndcg_at_3?: number;
  latency_p50_seconds?: number;
  latency_p95_seconds?: number;
  error_rate?: number;
  mean_returned_chunks?: number;
  distinct_documents_at_3?: number;
  source_diversity_at_3?: number;
}

export interface EvaluationRun {
  run_id: string;
  created_at: string;
  rag_configuration: Record<string, ConfigurationValue>;
  parameter_change: EvaluationParameterChange | null;
  measured_metrics: Record<string, EvaluationMetrics>;
}

export interface EvaluationConfigurationChange {
  name: string;
  previous_value: ConfigurationValue;
  new_value: ConfigurationValue;
}

export interface EvaluationMetricDelta {
  engine: string;
  metric: keyof EvaluationMetrics;
  previous_value: number | null;
  new_value: number | null;
  delta: number | null;
}

export interface EvaluationComparison {
  previous_run_id: string;
  new_run_id: string;
  configuration_changes: EvaluationConfigurationChange[];
  metric_deltas: EvaluationMetricDelta[];
}
