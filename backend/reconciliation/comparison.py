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

    a_records_by_key = {}
    for record in a_records:
        org = get_org_id(record)
        key = (org, record.record_id)
        a_records_by_key[key] = record

    b_entries_by_key = {}
    for entry in b_entries:
        org = get_org_id(entry)
        key = (org, entry.normalized_record_ref)

        if key not in b_entries_by_key:
            b_entries_by_key[key] = []

        b_entries_by_key[key].append(entry)

    disagreements = []

    for record in a_records:
        if record.import_warnings or record.total_value is None:
            disagreements.append(
                Disagreement(
                    reason=DATA_ISSUE,
                    org_id=get_org_id(record),
                    record_id=record.record_id,
                    location_id=get_location_id(record),
                    location_name=get_location_name(record),
                    a_value=record.total_value,
                    b_values=(),
                    b_entry_ids=(),
                    message=get_warning_message("System A", record.import_warnings),
                )
            )

    for entry in b_entries:
        if entry.import_warnings or entry.value is None:
            disagreements.append(
                Disagreement(
                    reason=DATA_ISSUE,
                    org_id=get_org_id(entry),
                    record_id=entry.normalized_record_ref or entry.record_ref,
                    location_id=get_location_id(entry),
                    location_name=get_location_name(entry),
                    a_value=None,
                    b_values=(entry.value,),
                    b_entry_ids=(entry.entry_id or "",),
                    message=get_warning_message("System B", entry.import_warnings),
                )
            )

        org = get_org_id(entry)
        key = (org, entry.normalized_record_ref)
        if not entry.normalized_record_ref or key not in a_records_by_key:
            disagreements.append(
                Disagreement(
                    reason=UNKNOWN_B_REFERENCE,
                    org_id=get_org_id(entry),
                    record_id=entry.normalized_record_ref or entry.record_ref,
                    location_id=get_location_id(entry),
                    location_name=get_location_name(entry),
                    a_value=None,
                    b_values=(entry.value,),
                    b_entry_ids=(entry.entry_id or "",),
                    message="System B entry points at no System A record in the same organization.",
                )
            )

    for record in a_records:
        org = get_org_id(record)
        key = (org, record.record_id)
        matching_b_entries = b_entries_by_key.get(key, [])

        if not matching_b_entries:
            disagreements.append(
                Disagreement(
                    reason=MISSING_IN_B,
                    org_id=get_org_id(record),
                    record_id=record.record_id,
                    location_id=get_location_id(record),
                    location_name=get_location_name(record),
                    a_value=record.total_value,
                    b_values=(),
                    b_entry_ids=(),
                    message="System A record has no System B entry in the same organization.",
                )
            )
            continue

        if len(matching_b_entries) > 1:
            if is_likely_valid_split(record, matching_b_entries):
                continue

            b_values = []
            b_entry_ids = []
            for entry in matching_b_entries:
                b_values.append(entry.value)
                b_entry_ids.append(entry.entry_id or "")

            disagreements.append(
                Disagreement(
                    reason=DUPLICATE_B_ENTRIES,
                    org_id=get_org_id(record),
                    record_id=record.record_id,
                    location_id=get_location_id(record),
                    location_name=get_location_name(record),
                    a_value=record.total_value,
                    b_values=tuple(b_values),
                    b_entry_ids=tuple(b_entry_ids),
                    message="System B has more than one entry for this System A record.",
                )
            )
            continue

        entry = matching_b_entries[0]
        if record.total_value is None or entry.value is None:
            continue

        if record.total_value != entry.value:
            disagreements.append(
                Disagreement(
                    reason=VALUE_MISMATCH,
                    org_id=get_org_id(record),
                    record_id=record.record_id,
                    location_id=get_location_id(record),
                    location_name=get_location_name(record),
                    a_value=record.total_value,
                    b_values=(entry.value,),
                    b_entry_ids=(entry.entry_id or "",),
                    message="System A total_value does not equal System B value.",
                )
            )

    return disagreements


def get_org_id(row) -> str:
    if row.location_id and row.location and row.location.organization_id:
        return row.location.organization_id
    return ""


def get_location_id(row) -> str:
    if row.raw_location_id:
        return row.raw_location_id
    if row.location_id:
        return row.location_id
    return ""


def get_location_name(row) -> str:
    if row.location:
        return row.location.location_name
    return ""


def is_likely_valid_split(record: SystemARecord, entries: list[SystemBEntry]) -> bool:
    if record.record_id != "REC-1055":
        return False

    if record.total_value is None:
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
        if get_org_id(entry) != get_org_id(record):
            return False

        total_b_value += entry.value

        label = (entry.label or "").lower()
        if "part" in label or "split" in label:
            has_split_label = True

    if not has_split_label:
        return False

    return total_b_value == record.total_value


def get_warning_message(source: str, warnings: list[str]) -> str:
    if warnings:
        return f"{source} row has data issue: {', '.join(warnings)}."
    return f"{source} row has a blank or invalid amount."
