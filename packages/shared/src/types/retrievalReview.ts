export type RetrievalVerificationStatus =
  | 'AUTO_BOOTSTRAP_UNVERIFIED'
  | 'HUMAN_REVIEW'
  | 'HUMAN_VERIFIED'
  | 'REJECTED';

export interface RetrievalReviewSummary {
  id: string;
  slug: string;
  title: string;
  version: number;
  status: string;
  source_hash: string;
  total_cases: number;
  verified_cases: number;
  progress_percent: number;
  status_counts: Record<string, number>;
  domain_counts: Record<string, number>;
  out_of_corpus_cases: number;
}

export interface RetrievalReviewCaseListItem {
  id: string;
  case_key: string;
  domain: string;
  query: string;
  expected_chunk_count: number;
  out_of_corpus: boolean;
  verification_status: RetrievalVerificationStatus;
  reviewer_id?: string | null;
  reviewed_at?: string | null;
  revision: number;
}

export interface RetrievalEvidenceChunk {
  id: string;
  content: string;
  content_hash: string;
  source_short_name: string;
  source_title: string;
  edition?: string | null;
  pdf_page?: number | null;
  textbook_page?: number | null;
  chapter_name?: string | null;
  section_heading?: string | null;
  word_count: number;
}

export interface RetrievalReviewHistory {
  id: string;
  reviewer_id: string;
  action: string;
  notes: string;
  created_at: string;
  previous_snapshot: Record<string, unknown>;
  new_snapshot: Record<string, unknown>;
}

export interface RetrievalReviewCase {
  id: string;
  case_key: string;
  domain: string;
  query: string;
  expected_chunk_ids: string[];
  out_of_corpus: boolean;
  verification_status: RetrievalVerificationStatus;
  reviewer_id?: string | null;
  reviewed_at?: string | null;
  review_notes?: string | null;
  revision: number;
  evidence: RetrievalEvidenceChunk[];
  history: RetrievalReviewHistory[];
}

export interface RetrievalReviewCasePage {
  items: RetrievalReviewCaseListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface UpdateRetrievalReviewCase {
  expected_revision: number;
  domain: string;
  query: string;
  expected_chunk_ids: string[];
  out_of_corpus: boolean;
  notes: string;
}
