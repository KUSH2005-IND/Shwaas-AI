export interface Clinical {
  version: number;
  status: string;
  notes: string;
  next_action: string;
  reviewer: string | null;
  updated_at: string | null;
}
export interface SourceField {
  name: string;
  value: string;
  page: number;
}
export interface Document {
  id: string;
  filename: string;
  media_type: string;
  sha256: string;
  size: number;
  fields: SourceField[];
  verification: string;
  confirmed_by: string | null;
  version: number;
}
export interface Order {
  id: string;
  kind: string;
  status: string;
  notes: string;
  version: number;
}
export interface Imaging {
  id: string;
  order_id: string;
  study_uid: string;
  series_uid: string;
  sop_uid: string;
  patient_id: string;
  identity_check: string;
}
export interface Case {
  id: string;
  patient_code: string;
  age: number;
  sex: string;
  village: string;
  created_at: string;
  tier: string;
  clinical_score: number;
  red_flag: boolean;
  clinical: Clinical;
  document_count: number;
  image_count: number;
  answers?: Record<string, number>;
  uncertain_symptoms?: string[];
  questionnaire_max?: number;
  audio_model?: { raw_score: number; calibrated_score: number; target: string };
  recommended_pathway?: string;
  consent_given?: boolean;
  documents?: Document[];
  investigations?: Order[];
  images?: Imaging[];
  timeline?: {
    id: number;
    kind: string;
    actor: string;
    created_at: string;
    detail: unknown;
  }[];
  reports?: { id: string; version: number; created_at: string }[];
}
export interface User {
  username: string;
  full_name: string;
  facility: string;
}
export interface Mutation {
  id: string;
  owner: string;
  caseId: string;
  label: string;
  path: string;
  body: Record<string, unknown>;
  created: string;
  blocked?: string;
}
