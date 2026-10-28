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
