export type Profile = Record<string, string | number | boolean | null>;
export type Citation = {
  scheme_id: string;
  scheme_name: string;
  source_name: string | null;
  source_url: string | null;
  retrieved_from: string;
  original_record_key?: string;
};
export type Trace = {
  field: string;
  status: string;
  source_path: string;
  description: string;
  explanation: string;
  actual_value: unknown;
  required_value: unknown;
};
export type Result = {
  scheme_id: string;
  scheme_name: string;
  status: "ELIGIBLE" | "NOT_ELIGIBLE" | "NEEDS_VERIFICATION";
  matched_rules: Trace[];
  failed_rules: Trace[];
  missing_information: string[];
  verification_required: string[];
  rule_trace: Trace[];
};
export type Scheme = {
  scheme_id: string;
  name: string;
  provider: string;
  objective?: string;
  benefits: unknown;
  eligibility: unknown;
  documents_required: string[];
  application: unknown;
  important_notes: string[];
  citation?: Citation;
};
export type Answer = {
  answer: string;
  scheme_ids: string[];
  citations: Citation[];
  eligibility: Result[];
  explanation_state: string;
  warnings: { code: string; message: string }[];
  evidence: {
    chunk_id: string;
    scheme_id: string;
    section: string;
    text: string;
  }[];
};
