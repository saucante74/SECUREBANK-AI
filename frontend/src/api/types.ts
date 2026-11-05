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
  source_hit_at_1: number | null;
  source_hit_at_3: number | null;
  evidence_hit_at_1: number | null;
  evidence_hit_at_3: number | null;
  mean_latency_seconds: number;
  latency_p50_seconds: number | null;
  latency_p95_seconds: number | null;
  error_rate: number | null;
  mean_returned_chunk_count: number | null;
  mean_distinct_document_count_at_3: number | null;
  mean_source_diversity_at_3: number | null;
}

export interface EvaluationIRMetricAggregate {
  value: number | null;
  evaluated_question_count: number;
  unavailable_question_count: number;
}

export interface EvaluationIRMetrics {
  judgment_source: "qwen";
  precision_at_1: EvaluationIRMetricAggregate;
  precision_at_3: EvaluationIRMetricAggregate;
  recall_at_1: EvaluationIRMetricAggregate;
  recall_at_3: EvaluationIRMetricAggregate;
  f1_at_1: EvaluationIRMetricAggregate;
  f1_at_3: EvaluationIRMetricAggregate;
  map_at_3: EvaluationIRMetricAggregate;
  success_at_1: EvaluationIRMetricAggregate;
  success_at_3: EvaluationIRMetricAggregate;
  mrr_at_3: EvaluationIRMetricAggregate;
  ndcg_at_3: EvaluationIRMetricAggregate;
}

export type EvaluationIRMetricName = Exclude<keyof EvaluationIRMetrics, "judgment_source">;

export interface EvaluationRun {
  run_id: string;
  created_at: string;
  rag_configuration: Record<string, ConfigurationValue>;
  parameter_change: EvaluationParameterChange | null;
  measured_metrics: Record<string, EvaluationMetrics>;
  ir_metrics: Record<string, EvaluationIRMetrics>;
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
