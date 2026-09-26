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

export type Customer = {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  document: string | null;
  address: Record<string, unknown> | null;
  notes: string | null;
  created_at: string;
};

export type CustomerHistory = {
  quotes: Quote[];
  projects: Project[];
  orders: Order[];
};

export type Machine = {
  id: string;
  name: string;
  brand: string | null;
  model: string | null;
  technology: string;
  build_volume_x_mm: number | null;
  build_volume_y_mm: number | null;
  build_volume_z_mm: number | null;
  power_watts: number | null;
  cost_per_hour: number | null;
  speed_profile: Record<string, unknown> | null;
  compatible_materials: string[] | null;
  status: string;
  created_at: string;
};

export type Material = {
  id: string;
  name: string;
  type: string;
  color: string | null;
  density_g_cm3: number | null;
  cost_per_kg: number | null;
  supplier: string | null;
  created_at: string;
};

export const ORDER_STATUSES = [
  "quote",
  "order",
  "paid",
  "production",
  "printing",
  "finishing",
  "packaging",
  "delivered",
  "completed",
  "cancelled",
] as const;

export type OrderStatus = (typeof ORDER_STATUSES)[number];

export type Order = {
  id: string;
  customer_id: string;
  quote_id: string | null;
  status: OrderStatus;
  total_amount: number;
  notes: string | null;
  created_at: string;
};

export type OrderItem = {
  id: string;
  order_id: string;
  project_version_id: string | null;
  product_id: string | null;
  machine_id: string | null;
  material_id: string | null;
  quantity: number;
  unit_cost: number | null;
  unit_price: number | null;
  status: string;
  created_at: string;
};

export const INVENTORY_CATEGORIES = [
  "filament",
  "resin",
  "component",
  "packaging",
  "spare_part",
] as const;

export type InventoryItem = {
  id: string;
  material_id: string | null;
  name: string;
  category: string;
  quantity_on_hand: number;
  unit: string;
  minimum_stock: number;
  unit_cost: number | null;
  supplier: string | null;
  created_at: string;
  is_low_stock: boolean;
};

export const INVENTORY_MOVEMENT_TYPES = ["entrada", "saida", "ajuste", "consumo", "perda"] as const;

export type InventoryMovement = {
  id: string;
  inventory_item_id: string;
  type: string;
  quantity: number;
  unit_cost: number | null;
  notes: string | null;
  reference_order_id: string | null;
  created_at: string;
};

export const FINANCE_TRANSACTION_TYPES = ["receita", "custo", "despesa"] as const;

export type FinancialTransaction = {
  id: string;
  type: string;
  category: string;
  cost_center: string | null;
  amount: number;
  reference_order_id: string | null;
  due_date: string | null;
  paid_at: string | null;
  created_at: string;
};

export type FinancialSummary = {
  total_revenue: number;
  total_cost: number;
  total_expense: number;
  profit: number;
  pending_receivables: number;
  pending_payables: number;
};

export type CostProfile = {
  id: string;
  name: string;
  energy_cost_per_kwh: number;
  labor_cost_per_hour: number;
  packaging_cost_flat: number;
  waste_percentage: number;
  fees_percentage: number;
  profit_margin_percentage: number;
  tax_percentage: number | null;
  is_default: boolean;
  created_at: string;
};

export type Quote = {
  id: string;
  cost_profile_id: string;
  project_version_id: string | null;
  customer_id: string | null;
  piece_name: string | null;
  printer_name: string | null;
  weight_g: number | null;
  quantity: number;
  cost_breakdown_snapshot: Record<string, unknown>;
  production_cost: number;
  suggested_price: number;
  final_price: number | null;
  status: string;
  created_at: string;
};

export type ProductMaterialLine = {
  material_id: string;
  quantity_g: number;
};

export type Product = {
  id: string;
  name: string;
  description: string | null;
  print_time_hours: number | null;
  machine_id: string | null;
  is_active: boolean;
  created_at: string;
  materials: ProductMaterialLine[];
};

export type ProductCost = {
  material_cost: number;
  waste_cost: number;
  energy_cost: number;
  machine_cost: number;
  labor_cost: number;
  packaging_cost: number;
  fees: number;
  production_cost: number;
  tax_amount: number;
  suggested_price: number;
};

export type DashboardData = {
  orders_by_status: Record<string, number>;
  low_stock_items_count: number;
  customers_count: number;
  projects_count: number;
  financial: FinancialSummary;
};
