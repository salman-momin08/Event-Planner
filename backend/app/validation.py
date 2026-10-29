"""Reusable, strict Pydantic field types. Used at every untrusted-input boundary."""
from __future__ import annotations

import re
import unicodedata
from typing import Annotated, TypeVar

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field

from .dates import is_valid_date
from .money import MAX_CENTS

T = TypeVar("T")

# Keeps \t and \n; strips other control characters.
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def clean_text(value: str, multiline: bool = False) -> str:
    s = _CONTROL.sub("", unicodedata.normalize("NFC", value))
    if not multiline:
        s = re.sub(r"[\r\n\t]+", " ", s)
    return s.strip()


def Text(max_len: int, *, min_len: int = 0, multiline: bool = False):
    def check(value: str) -> str:
        s = clean_text(value, multiline)
        if len(s) < min_len:
            raise ValueError("Must not be empty" if min_len == 1 else f"Must be at least {min_len} characters")
        if len(s) > max_len:
            raise ValueError(f"Must be at most {max_len} characters")
        return s

    return Annotated[str, Field(strict=True), AfterValidator(check)]


def Secret(min_len: int, max_len: int):
    return Annotated[str, Field(strict=True, min_length=min_len, max_length=max_len)]


def Int(lo: int, hi: int):
    return Annotated[int, Field(strict=True, ge=lo, le=hi)]


def _email(value: str) -> str:
    s = value.strip().lower()
    if len(s) > 254 or not _EMAIL.match(s) or re.search(r"[\x00-\x1f\x7f]", s):
        raise ValueError("Must be a valid email address")
    return s


def _date(value: str) -> str:
    if not is_valid_date(value):
        raise ValueError("Must be a valid date in YYYY-MM-DD format (2000-2100)")
    return value


def _unique_ids(values: list[int]) -> list[int]:
    return list(dict.fromkeys(values))


def _reject_null(value: object) -> object:
    if value is None:
        raise ValueError("Must not be null")
    return value


def NonNull(tp: type[T]) -> type[T | None]:
    """Allows omitting a field on PATCH (default None) while rejecting explicit JSON null."""
    return Annotated[tp | None, BeforeValidator(_reject_null)]  # type: ignore[return-value]


Email = Annotated[str, Field(strict=True), AfterValidator(_email)]
DateStr = Annotated[str, Field(strict=True), AfterValidator(_date)]
Cents = Int(0, MAX_CENTS)
PositiveCents = Int(1, MAX_CENTS)
RecordId = Int(1, 2**62)
IdList = Annotated[list[RecordId], Field(max_length=50), AfterValidator(_unique_ids)]


class StrictModel(BaseModel):
    """Request bodies reject unknown fields (mass-assignment protection, SEC-005)."""

    model_config = ConfigDict(extra="forbid")
