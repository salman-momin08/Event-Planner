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
    ImageDataUrl,
    Int,
    NonNull,
    PositiveCents,
    RecordId,
    Secret,
    StrictModel,
    Text,
    TimeStr,
)

EventType = Literal["wedding", "birthday", "community"]
TaskStatus = Literal["todo", "in_progress", "done"]
VendorStatus = Literal["researching", "contacted", "quoted", "booked", "declined"]
RsvpStatus = Literal["pending", "attending", "declined", "maybe"]
DietaryKind = Literal["none", "vegetarian", "vegan", "halal", "kosher", "gluten_free", "nut_allergy", "other"]
SpaceType = Literal["open_garden", "party_hall", "house_room", "rooftop", "banquet_lawn", "other"]
LightingMood = Literal["warm_ambient", "bright_festive", "candlelight_intimate", "daylight_natural", "neon_party"]
InvitationTheme = Literal[
    "royal_indigo",
    "botanical_sage",
    "sunset_terracotta",
    "midnight_gold",
    "minimal_ivory",
    "rose_velvet",
    "ocean_breeze",
    "lavender_dusk",
]
InvitationLayout = Literal[
    "classic_crest",
    "modern_editorial",
    "garden_arch",
    "royal_mandala",
    "minimal_split",
    "festive_confetti",
]
InvitationTone = Literal["warm_traditional", "modern_minimal", "playful_celebration", "formal_black_tie"]


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
    spentCents: Cents | None = None


class CategoryPatch(StrictModel):
    name: NonNull(Text(80, min_len=1)) = None
    plannedCents: NonNull(Cents) = None
    spentCents: Cents | None = None


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


class GuestIn(StrictModel):
    name: Text(80, min_len=1)
    contact: Text(120) = ""
    rsvpStatus: RsvpStatus = "pending"
    partySize: Int(1, 20) = 1
    dietary: DietaryKind = "none"
    tableGroup: Text(60) = ""
    notes: Text(300, multiline=True) = ""


class GuestPatch(StrictModel):
    name: NonNull(Text(80, min_len=1)) = None
    contact: NonNull(Text(120)) = None
    rsvpStatus: NonNull(RsvpStatus) = None
    partySize: NonNull(Int(1, 20)) = None
    dietary: NonNull(DietaryKind) = None
    tableGroup: NonNull(Text(60)) = None
    notes: NonNull(Text(300, multiline=True)) = None


class ScheduleItemIn(StrictModel):
    startTime: TimeStr
    durationMinutes: Int(5, 720) = 30
    title: Text(120, min_len=1)
    locationZone: Text(80) = ""
    owner: Text(80) = ""
    notes: Text(400, multiline=True) = ""


class ScheduleItemPatch(StrictModel):
    startTime: NonNull(TimeStr) = None
    durationMinutes: NonNull(Int(5, 720)) = None
    title: NonNull(Text(120, min_len=1)) = None
    locationZone: NonNull(Text(80)) = None
    owner: NonNull(Text(80)) = None
    notes: NonNull(Text(400, multiline=True)) = None


class DecorAnalyzeIn(StrictModel):
    spaceType: SpaceType
    customSpaceType: Text(80) = ""
    lightingMood: LightingMood = "warm_ambient"
    stylePreferences: Text(600, multiline=True) = ""
    imageDataUrl: ImageDataUrl = ""


class DecorApplyIn(StrictModel):
    tasks: Annotated[list[Text(120, min_len=1)], Field(max_length=25)] | None = None
    budgetCategoryPercent: Int(0, 60) = 15


class DecorPatchIn(StrictModel):
    themeConcept: NonNull(Text(240, min_len=1)) = None
    venueAssessment: NonNull(Text(500, min_len=1)) = None
    lightingPlan: NonNull(Text(400, min_len=1)) = None
    focalZonesText: NonNull(Text(2000, multiline=True)) = None
    decorTasksText: NonNull(Text(3000, multiline=True)) = None


class InvitationUpdateIn(StrictModel):
    headline: Text(120) = ""
    subheadline: Text(160) = ""
    hostLine: Text(120) = ""
    bodyText: Text(600, multiline=True) = ""
    rsvpContact: Text(120) = ""
    rsvpDeadline: Text(40) = ""
    dressCode: Text(80) = ""
    themeStyle: Text(40) = "royal_indigo"
    layoutStyle: Text(40) = "classic_crest"


class InvitationAiDraftIn(StrictModel):
    includeSelectedTheme: Annotated[bool, Field(strict=True)] = True
    themeStyle: InvitationTheme = "royal_indigo"
    layoutStyle: InvitationLayout = "classic_crest"
    tone: InvitationTone = "warm_traditional"
    changeRequest: Text(500, multiline=True) = ""
    hostLine: Text(120) = ""
    dressCode: Text(80) = ""
    extraNotes: Text(300, multiline=True) = ""
