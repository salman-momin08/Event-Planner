"""Request schemas. Patch models never allow null for non-nullable fields."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from .money import Currency
from .validation import (
    Cents,
    DateStr,
    Email,
    IdList,
    Int,
    NonNull,
    PositiveCents,
    RecordId,
    Secret,
    StrictModel,
    Text,
)

EventType = Literal["wedding", "birthday", "community"]
TaskStatus = Literal["todo", "in_progress", "done"]
VendorStatus = Literal["researching", "contacted", "quoted", "booked", "declined"]


class RegisterIn(StrictModel):
    email: Email
    displayName: Text(80, min_len=1)
    password: Secret(12, 128)


class LoginIn(StrictModel):
    email: Email
    password: Secret(1, 128)


class ChangePasswordIn(StrictModel):
    currentPassword: Secret(1, 128)
    newPassword: Secret(12, 128)


class DeleteAccountIn(StrictModel):
    password: Secret(1, 128)


class EventIn(StrictModel):
    type: EventType
    title: Text(120, min_len=1)
    eventDate: DateStr
    attendance: Int(1, 100000)
    location: Text(120) = ""
    budgetCents: Cents = 0
    currency: Currency = "USD"
    notes: Text(2000, multiline=True) = ""


class EventPatch(StrictModel):
    type: NonNull(EventType) = None
    title: NonNull(Text(120, min_len=1)) = None
    eventDate: NonNull(DateStr) = None
    attendance: NonNull(Int(1, 100000)) = None
    location: NonNull(Text(120)) = None
    budgetCents: NonNull(Cents) = None
    currency: NonNull(Currency) = None
    notes: NonNull(Text(2000, multiline=True)) = None
    shiftTaskDates: NonNull(Annotated[bool, Field(strict=True)]) = None


class CategoryIn(StrictModel):
    name: Text(80, min_len=1)
    plannedCents: Cents = 0


class CategoryPatch(StrictModel):
    name: NonNull(Text(80, min_len=1)) = None
    plannedCents: NonNull(Cents) = None


class ExpenseIn(StrictModel):
    categoryId: RecordId
    vendorId: RecordId | None = None
    description: Text(200, min_len=1)
    amountCents: PositiveCents
    spentOn: DateStr


class ExpensePatch(StrictModel):
    categoryId: NonNull(RecordId) = None
    vendorId: RecordId | None = None
    description: NonNull(Text(200, min_len=1)) = None
    amountCents: NonNull(PositiveCents) = None
    spentOn: NonNull(DateStr) = None


class TaskIn(StrictModel):
    title: Text(120, min_len=1)
    description: Text(1000, multiline=True) = ""
    dueDate: DateStr | None = None
    status: TaskStatus = "todo"
    category: Text(80) = ""
    vendorId: RecordId | None = None
    dependsOn: IdList | None = None


class TaskPatch(StrictModel):
    title: NonNull(Text(120, min_len=1)) = None
    description: NonNull(Text(1000, multiline=True)) = None
    dueDate: DateStr | None = None
    status: NonNull(TaskStatus) = None
    category: NonNull(Text(80)) = None
    vendorId: RecordId | None = None
    dependsOn: NonNull(IdList) = None


class VendorIn(StrictModel):
    name: Text(80, min_len=1)
    category: Text(80) = ""
    status: VendorStatus = "researching"
    quoteCents: Cents | None = None
    contact: Text(1000, multiline=True) = ""


class VendorPatch(StrictModel):
    name: NonNull(Text(80, min_len=1)) = None
    category: NonNull(Text(80)) = None
    status: NonNull(VendorStatus) = None
    quoteCents: Cents | None = None
    contact: NonNull(Text(1000, multiline=True)) = None


class PlanRequest(StrictModel):
    preferences: Text(1000, multiline=True) = ""
    instruction: Text(1000, multiline=True) = ""
    parentId: RecordId | None = None


class PlanApplyIn(StrictModel):
    categories: Annotated[list[Text(80, min_len=1)], Field(max_length=12)] | None = None
    tasks: Annotated[list[Text(120, min_len=1)], Field(max_length=40)] | None = None
    includeVendors: Annotated[bool, Field(strict=True)] = False
