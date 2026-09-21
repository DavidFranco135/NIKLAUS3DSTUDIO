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

export type AIJob = {
  id: string;
  project_id: string | null;
  task_type: string;
  status: string;
  error_message: string | null;
  result_file_id: string | null;
  result_project_version_id: string | null;
  attempts: AIJobAttempt[];
};
