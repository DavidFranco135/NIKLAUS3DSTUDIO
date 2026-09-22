export type Role = "OWNER" | "ADMIN" | "MANAGER" | "OPERATOR" | "VIEWER";

export type Organization = {
  id: string;
  name: string;
  slug: string;
  plan: string;
};

export type Membership = {
  organization: Organization;
  role: Role;
};

export type User = {
  id: string;
  email: string;
  full_name: string | null;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type MeResponse = {
  user: User;
  organizations: Membership[];
};

export type Project = {
  id: string;
  name: string;
  description: string | null;
  status: string;
  active_version_id: string | null;
  created_at: string;
};

export type ProjectVersion = {
  id: string;
  version_number: number;
  label: string | null;
  source_type: string;
  status: string;
  created_at: string;
};

export type FileAsset = {
  id: string;
  kind: string;
  mime_type: string;
  size_bytes: number | null;
  status: string;
};

export type RequestUploadResponse = {
  file_id: string;
  upload_url: string;
  storage_key: string;
};

export type AIJobAttempt = {
  provider_name: string;
  attempt_number: number;
  status: string;
  error_detail: string | null;
  duration_ms: number | null;
};

export type Plan = {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
  trial_period_days: number | null;
};

export type Subscription = {
  id: string;
  plan: Plan;
  status: string;
  current_period_start: string;
  current_period_end: string;
  trial_start: string | null;
  trial_end: string | null;
  cancel_at_period_end: boolean;
  canceled_at: string | null;
};

export type UsageItem = {
  key: string;
  limit_type: "boolean" | "numeric" | "unlimited";
  current_usage: number | null;
  limit: number | null;
  enabled: boolean | null;
};

export type AIJob = {
  id: string;
  project_id: string | null;
  source_image_file_id: string | null;
  task_type: string;
  status: string;
  error_message: string | null;
  result_file_id: string | null;
  result_project_version_id: string | null;
  result_metadata: { development_only?: boolean; placeholder?: boolean; note?: string } | null;
  attempts: AIJobAttempt[];
};
