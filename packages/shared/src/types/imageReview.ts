export type ImageCurationStatus =
  | 'CURATED_VALID'
  | 'HUMAN_REVIEW'
  | 'APPROVED_INTERNAL_STUDY'
  | 'APPROVED_INTERNAL_QUESTION_CANDIDATE'
  | 'REJECTED_NON_EDUCATIONAL'
  | 'REJECTED_UNUSABLE_QUALITY'
  | 'PROVENANCE_UNRESOLVED';

export interface ImageReviewSummary {
  total_assets: number;
  status_counts: Record<string, number>;
  human_verified_links: number;
  eligible_question_assets: number;
  pilot_target: number;
  pilot_gate_open: boolean;
}

export interface ImageReviewAssetListItem {
  id: string;
  filename: string;
  width: number;
  height: number;
  triage_class: string;
  reviewed_utility_class?: string | null;
  curation_status: ImageCurationStatus;
  metadata_verification_status: string;
  storage_access_status: string;
  review_revision: number;
  source_short_name?: string | null;
  pdf_page?: number | null;
  verified_link_count: number;
  automated_rank_score?: number | null;
  automated_suggested_utility_class?: string | null;
  automated_tags: string[];
  pilot_shortlisted: boolean;
}

export interface ImageOccurrenceReview {
  id: string;
  source_document_id: string;
  source_short_name: string;
  source_title: string;
  pdf_page?: number | null;
  textbook_page?: number | null;
  figure_label?: string | null;
  is_canonical: boolean;
}

export interface ImageTextLinkReview {
  id: string;
  occurrence_id?: string | null;
  document_chunk_id: string;
  source_short_name: string;
  pdf_page?: number | null;
  textbook_page?: number | null;
  section_heading?: string | null;
  content: string;
  confidence: number;
  verification_status: string;
}

export interface ImageReviewAsset extends ImageReviewAssetListItem {
  sha256: string;
  format: string;
  rights_status: string;
  has_resolvable_object: boolean;
  reviewed_diagnosis?: string | null;
  reviewed_stain?: string | null;
  reviewed_magnification?: string | null;
  reviewed_caption?: string | null;
  occurrences: ImageOccurrenceReview[];
  links: ImageTextLinkReview[];
  history: Array<{
    id: string;
    action: string;
    reviewer_id: string;
    notes: string;
    created_at: string;
  }>;
}

export interface ImageReviewAssetPage {
  items: ImageReviewAssetListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface SaveImageReview {
  expected_revision: number;
  utility_class: string;
  diagnosis?: string | null;
  stain?: string | null;
  magnification?: string | null;
  caption?: string | null;
  occurrence_id?: string | null;
  link_id?: string | null;
  notes: string;
  attested: boolean;
}

export interface MultimodalPilotReadiness {
  target: number;
  eligible: number;
  gate_open: boolean;
  distribution: Record<string, number>;
  required_distribution: Record<string, number>;
  generation_allowed: boolean;
  message: string;
}
