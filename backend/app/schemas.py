"""Request schemas. Patch models never allow null for non-nullable fields."""
from __future__ import annotations

from typing import Literal

from .money import Currency
from .validation import (
    Cents,
    DateStr,
    Email,
    IdList,
    Int,
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
    type: EventType = None  # type: ignore[assignment]
    title: Text(120, min_len=1) = None  # type: ignore[assignment]
    eventDate: DateStr = None  # type: ignore[assignment]
    attendance: Int(1, 100000) = None  # type: ignore[assignment]
    location: Text(120) = None  # type: ignore[assignment]
    budgetCents: Cents = None  # type: ignore[assignment]
    currency: Currency = None  # type: ignore[assignment]
    notes: Text(2000, multiline=True) = None  # type: ignore[assignment]


class CategoryIn(StrictModel):
    name: Text(80, min_len=1)
    plannedCents: Cents = 0


class CategoryPatch(StrictModel):
    name: Text(80, min_len=1) = None  # type: ignore[assignment]
    plannedCents: Cents = None  # type: ignore[assignment]


class ExpenseIn(StrictModel):
    categoryId: RecordId
    vendorId: RecordId | None = None
    description: Text(200, min_len=1)
    amountCents: PositiveCents
    spentOn: DateStr


class ExpensePatch(StrictModel):
    categoryId: RecordId = None  # type: ignore[assignment]
    vendorId: RecordId | None = None
    description: Text(200, min_len=1) = None  # type: ignore[assignment]
    amountCents: PositiveCents = None  # type: ignore[assignment]
    spentOn: DateStr = None  # type: ignore[assignment]


class TaskIn(StrictModel):
    title: Text(120, min_len=1)
    description: Text(1000, multiline=True) = ""
    dueDate: DateStr | None = None
    status: TaskStatus = "todo"
    category: Text(80) = ""
    vendorId: RecordId | None = None
    dependsOn: IdList | None = None


class TaskPatch(StrictModel):
    title: Text(120, min_len=1) = None  # type: ignore[assignment]
    description: Text(1000, multiline=True) = None  # type: ignore[assignment]
    dueDate: DateStr | None = None
    status: TaskStatus = None  # type: ignore[assignment]
    category: Text(80) = None  # type: ignore[assignment]
    vendorId: RecordId | None = None
    dependsOn: IdList = None  # type: ignore[assignment]


class VendorIn(StrictModel):
    name: Text(80, min_len=1)
    category: Text(80) = ""
    status: VendorStatus = "researching"
    quoteCents: Cents | None = None
    contact: Text(1000, multiline=True) = ""


class VendorPatch(StrictModel):
    name: Text(80, min_len=1) = None  # type: ignore[assignment]
    category: Text(80) = None  # type: ignore[assignment]
    status: VendorStatus = None  # type: ignore[assignment]
    quoteCents: Cents | None = None
    contact: Text(1000, multiline=True) = None  # type: ignore[assignment]


class PlanRequest(StrictModel):
    preferences: Text(1000, multiline=True) = ""
    instruction: Text(1000, multiline=True) = ""
    parentId: RecordId | None = None
