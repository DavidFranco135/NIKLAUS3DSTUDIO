from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

from src.domain.auth.roles import Role


class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    full_name: str | None = Field(default=None, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None

    model_config = {"from_attributes": True}


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str

    model_config = {"from_attributes": True}


class MembershipResponse(BaseModel):
    organization: OrganizationResponse
    role: Role


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MeResponse(BaseModel):
    user: UserResponse
    organizations: list[MembershipResponse]


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)


class OrgMemberResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    full_name: str | None
    role: Role
    created_at: datetime


class AddMemberRequest(BaseModel):
    email: EmailStr
    role: Role


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    customer_id: UUID | None = None


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(draft|in_progress|completed|archived)$")


class ProjectResponse(BaseModel):
    id: UUID
    customer_id: UUID | None
    name: str
    description: str | None
    status: str
    active_version_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectVersionResponse(BaseModel):
    id: UUID
    version_number: int
    label: str | None
    source_type: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateVersionRequest(BaseModel):
    file_id: UUID
    label: str | None = Field(default=None, max_length=200)


class RequestUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=100)
    kind: str


class RequestUploadResponse(BaseModel):
    file_id: UUID
    upload_url: str
    storage_key: str


class FileAssetResponse(BaseModel):
    id: UUID
    kind: str
    mime_type: str
    size_bytes: int | None
    status: str

    model_config = {"from_attributes": True}


class DownloadUrlResponse(BaseModel):
    download_url: str


class CreateAIJobRequest(BaseModel):
    prompt: str | None = Field(default=None, max_length=2000)
    image_file_id: UUID | None = None
    project_id: UUID | None = None

    @model_validator(mode="after")
    def _require_prompt_or_image(self) -> "CreateAIJobRequest":
        if not self.prompt and self.image_file_id is None:
            raise ValueError("Informe um prompt e/ou uma imagem (image_file_id).")
        if self.prompt is not None and len(self.prompt.strip()) < 3 and self.image_file_id is None:
            raise ValueError("prompt deve ter ao menos 3 caracteres quando não há imagem.")
        return self


class AIJobAttemptResponse(BaseModel):
    provider_name: str
    attempt_number: int
    status: str
    error_detail: str | None
    duration_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateCustomerRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    document: str | None = Field(default=None, max_length=30)
    address: dict | None = None
    notes: str | None = Field(default=None, max_length=2000)


class UpdateCustomerRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    document: str | None = Field(default=None, max_length=30)
    address: dict | None = None
    notes: str | None = Field(default=None, max_length=2000)


class CustomerResponse(BaseModel):
    id: UUID
    name: str
    email: str | None
    phone: str | None
    document: str | None
    address: dict | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateCostProfileRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    energy_cost_per_kwh: float = Field(ge=0)
    labor_cost_per_hour: float = Field(ge=0)
    packaging_cost_flat: float = Field(ge=0)
    waste_percentage: float = Field(ge=0)
    fees_percentage: float = Field(ge=0)
    profit_margin_percentage: float = Field(ge=0)
    tax_percentage: float | None = Field(default=None, ge=0)
    is_default: bool = False


class CostProfileResponse(BaseModel):
    id: UUID
    name: str
    energy_cost_per_kwh: float
    labor_cost_per_hour: float
    packaging_cost_flat: float
    waste_percentage: float
    fees_percentage: float
    profit_margin_percentage: float
    tax_percentage: float | None
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateQuoteRequest(BaseModel):
    cost_profile_id: UUID
    project_id: UUID | None = None
    project_version_id: UUID | None = None
    customer_id: UUID | None = None
    material_cost: float = Field(ge=0)
    print_time_hours: float = Field(ge=0)
    machine_cost_per_hour: float = Field(ge=0)
    energy_kwh: float = Field(ge=0)
    labor_hours: float = Field(ge=0)

    @model_validator(mode="after")
    def _project_fields_go_together(self) -> "CreateQuoteRequest":
        if (self.project_id is None) != (self.project_version_id is None):
            raise ValueError("Informe project_id e project_version_id juntos, ou nenhum dos dois.")
        return self


class QuoteResponse(BaseModel):
    id: UUID
    cost_profile_id: UUID
    project_version_id: UUID | None
    customer_id: UUID | None
    cost_breakdown_snapshot: dict
    production_cost: float
    suggested_price: float
    final_price: float | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateOrderRequest(BaseModel):
    customer_id: UUID
    quote_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class OrderResponse(BaseModel):
    id: UUID
    customer_id: UUID
    quote_id: UUID | None
    status: str
    total_amount: float
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TransitionOrderStatusRequest(BaseModel):
    status: str = Field(
        pattern="^(quote|order|paid|production|printing|finishing|packaging|delivered"
        "|completed|cancelled)$"
    )


class CreateOrderItemRequest(BaseModel):
    project_id: UUID | None = None
    project_version_id: UUID | None = None
    machine_id: UUID | None = None
    material_id: UUID | None = None
    quantity: int = Field(default=1, ge=1)
    unit_cost: float | None = Field(default=None, ge=0)
    unit_price: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _project_fields_go_together(self) -> "CreateOrderItemRequest":
        if (self.project_id is None) != (self.project_version_id is None):
            raise ValueError("Informe project_id e project_version_id juntos, ou nenhum dos dois.")
        return self


class OrderItemResponse(BaseModel):
    id: UUID
    order_id: UUID
    project_version_id: UUID | None
    machine_id: UUID | None
    material_id: UUID | None
    quantity: int
    unit_cost: float | None
    unit_price: float | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerHistoryResponse(BaseModel):
    quotes: list[QuoteResponse]
    projects: list[ProjectResponse]
    orders: list[OrderResponse]


class CreateMaterialRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    type: str = Field(min_length=2, max_length=30)
    color: str | None = Field(default=None, max_length=50)
    density_g_cm3: float | None = Field(default=None, gt=0)
    cost_per_kg: float | None = Field(default=None, ge=0)
    supplier: str | None = Field(default=None, max_length=200)


class MaterialResponse(BaseModel):
    id: UUID
    name: str
    type: str
    color: str | None
    density_g_cm3: float | None
    cost_per_kg: float | None
    supplier: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateInventoryItemRequest(BaseModel):
    material_id: UUID | None = None
    name: str = Field(min_length=2, max_length=200)
    category: str = Field(pattern="^(filament|resin|component|packaging|spare_part)$")
    unit: str = Field(pattern="^(g|kg|un)$")
    minimum_stock: float = Field(default=0, ge=0)
    unit_cost: float | None = Field(default=None, ge=0)
    supplier: str | None = Field(default=None, max_length=200)
    initial_quantity: float = Field(default=0, ge=0)


class InventoryItemResponse(BaseModel):
    id: UUID
    material_id: UUID | None
    name: str
    category: str
    quantity_on_hand: float
    unit: str
    minimum_stock: float
    unit_cost: float | None
    supplier: str | None
    created_at: datetime
    is_low_stock: bool = False

    model_config = {"from_attributes": True}


class CreateInventoryMovementRequest(BaseModel):
    type: str = Field(pattern="^(entrada|saida|ajuste|consumo|perda)$")
    quantity: float
    unit_cost: float | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)
    reference_order_id: UUID | None = None


class InventoryMovementResponse(BaseModel):
    id: UUID
    inventory_item_id: UUID
    type: str
    quantity: float
    unit_cost: float | None
    notes: str | None
    reference_order_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AIJobResponse(BaseModel):
    id: UUID
    project_id: UUID | None
    source_image_file_id: UUID | None
    task_type: str
    status: str
    input_spec: dict
    error_message: str | None
    result_file_id: UUID | None
    result_project_version_id: UUID | None
    result_metadata: dict | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    attempts: list[AIJobAttemptResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CreateFinancialTransactionRequest(BaseModel):
    type: str = Field(pattern="^(receita|custo|despesa)$")
    category: str = Field(min_length=2, max_length=50)
    cost_center: str | None = Field(default=None, max_length=100)
    amount: float = Field(gt=0)
    reference_order_id: UUID | None = None
    due_date: date | None = None
    mark_as_paid: bool = False


class FinancialTransactionResponse(BaseModel):
    id: UUID
    type: str
    category: str
    cost_center: str | None
    amount: float
    reference_order_id: UUID | None
    due_date: date | None
    paid_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FinancialSummaryResponse(BaseModel):
    total_revenue: float
    total_cost: float
    total_expense: float
    profit: float
    pending_receivables: float
    pending_payables: float
