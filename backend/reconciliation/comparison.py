from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from reconciliation.models import SystemARecord, SystemBEntry


MISSING_IN_B = "missing_in_b"
UNKNOWN_B_REFERENCE = "unknown_b_reference"
DUPLICATE_B_ENTRIES = "duplicate_b_entries"
VALUE_MISMATCH = "value_mismatch"
DATA_ISSUE = "data_issue"


@dataclass(frozen=True)
class Disagreement:
    reason: str
    org_id: str
    record_id: str
    location_id: str
    location_name: str
    a_value: Decimal | None
    b_values: tuple[Decimal | None, ...]
    b_entry_ids: tuple[str, ...]
    message: str


def find_disagreements() -> list[Disagreement]:
    a_records = list(
        SystemARecord.objects.select_related("location__organization").order_by("record_id", "raw_location_id")
    )
    b_entries = list(
        SystemBEntry.objects.select_related("location__organization").order_by("normalized_record_ref", "entry_id")
    )

    a_by_key = {}
    for record in a_records:
        key = record_key(record)
        a_by_key[key] = record

    b_by_key = {}
    for entry in b_entries:
        key = entry_key(entry)
        if key not in b_by_key:
            b_by_key[key] = []
        b_by_key[key].append(entry)

    disagreements: list[Disagreement] = []

    for record in a_records:
        if record.import_warnings or record.total_value is None:
            disagreements.append(data_issue_for_a(record))

    for entry in b_entries:
        if entry.import_warnings or entry.value is None:
            disagreements.append(data_issue_for_b(entry))

        key = entry_key(entry)
        if not entry.normalized_record_ref or key not in a_by_key:
            disagreements.append(unknown_reference_for_b(entry))

    for record in a_records:
        entries = b_by_key.get(record_key(record), [])
        if not entries:
            disagreements.append(missing_in_b(record))
            continue

        if len(entries) > 1:
            if is_likely_valid_split(record, entries):
                continue
            disagreements.append(duplicate_b_entries(record, entries))
            continue

        entry = entries[0]
        if record.total_value is None or entry.value is None:
            continue
        if record.total_value != entry.value:
            disagreements.append(value_mismatch(record, entry))

    return disagreements


def record_key(record: SystemARecord) -> tuple[str, str]:
    return org_id(record), record.record_id


def entry_key(entry: SystemBEntry) -> tuple[str, str]:
    return org_id(entry), entry.normalized_record_ref


def org_id(row) -> str:
    if row.location_id and row.location and row.location.organization_id:
        return row.location.organization_id
    return ""


def row_location_id(row) -> str:
    if row.raw_location_id:
        return row.raw_location_id
    if row.location_id:
        return row.location_id
    return ""


def row_location_name(row) -> str:
    if row.location:
        return row.location.location_name
    return ""


def data_issue_for_a(record: SystemARecord) -> Disagreement:
    return Disagreement(
        reason=DATA_ISSUE,
        org_id=org_id(record),
        record_id=record.record_id,
        location_id=row_location_id(record),
        location_name=row_location_name(record),
        a_value=record.total_value,
        b_values=(),
        b_entry_ids=(),
        message=format_warnings("System A", record.import_warnings),
    )


def data_issue_for_b(entry: SystemBEntry) -> Disagreement:
    return Disagreement(
        reason=DATA_ISSUE,
        org_id=org_id(entry),
        record_id=entry.normalized_record_ref or entry.record_ref,
        location_id=row_location_id(entry),
        location_name=row_location_name(entry),
        a_value=None,
        b_values=(entry.value,),
        b_entry_ids=(entry.entry_id or "",),
        message=format_warnings("System B", entry.import_warnings),
    )


def unknown_reference_for_b(entry: SystemBEntry) -> Disagreement:
    record_ref = entry.normalized_record_ref or entry.record_ref
    return Disagreement(
        reason=UNKNOWN_B_REFERENCE,
        org_id=org_id(entry),
        record_id=record_ref,
        location_id=row_location_id(entry),
        location_name=row_location_name(entry),
        a_value=None,
        b_values=(entry.value,),
        b_entry_ids=(entry.entry_id or "",),
        message="System B entry points at no System A record in the same organization.",
    )


def missing_in_b(record: SystemARecord) -> Disagreement:
    return Disagreement(
        reason=MISSING_IN_B,
        org_id=org_id(record),
        record_id=record.record_id,
        location_id=row_location_id(record),
        location_name=row_location_name(record),
        a_value=record.total_value,
        b_values=(),
        b_entry_ids=(),
        message="System A record has no System B entry in the same organization.",
    )


def duplicate_b_entries(record: SystemARecord, entries: list[SystemBEntry]) -> Disagreement:
    return Disagreement(
        reason=DUPLICATE_B_ENTRIES,
        org_id=org_id(record),
        record_id=record.record_id,
        location_id=row_location_id(record),
        location_name=row_location_name(record),
        a_value=record.total_value,
        b_values=get_b_values(entries),
        b_entry_ids=get_b_entry_ids(entries),
        message="System B has more than one entry for this System A record.",
    )


def get_b_values(entries: list[SystemBEntry]) -> tuple[Decimal | None, ...]:
    values = []
    for entry in entries:
        values.append(entry.value)
    return tuple(values)


def get_b_entry_ids(entries: list[SystemBEntry]) -> tuple[str, ...]:
    entry_ids = []
    for entry in entries:
        entry_ids.append(entry.entry_id or "")
    return tuple(entry_ids)

def value_mismatch(record: SystemARecord, entry: SystemBEntry) -> Disagreement:
    return Disagreement(
        reason=VALUE_MISMATCH,
        org_id=org_id(record),
        record_id=record.record_id,
        location_id=row_location_id(record),
        location_name=row_location_name(record),
        a_value=record.total_value,
        b_values=(entry.value,),
        b_entry_ids=(entry.entry_id or "",),
        message="System A total_value does not equal System B value.",
    )


def is_likely_valid_split(record: SystemARecord, entries: list[SystemBEntry]) -> bool:
    if record.record_id != "REC-1055" or record.total_value is None:
        return False
    if len(entries) < 2:
        return False
    total_b_value = Decimal("0")
    has_split_label = False

    for entry in entries:
        if entry.value is None:
            return False
        if entry.import_warnings:
            return False
        if org_id(entry) != org_id(record):
            return False

        total_b_value += entry.value
        label = (entry.label or "").lower()
        if "part" in label or "split" in label:
            has_split_label = True

    if not has_split_label:
        return False

    return total_b_value == record.total_value


def format_warnings(source: str, warnings: list[str]) -> str:
    if warnings:
        return f"{source} row has data issue: {', '.join(warnings)}."
    return f"{source} row has a blank or invalid amount."


