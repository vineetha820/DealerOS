import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from reconciliation.models import Location, Organization, SystemARecord, SystemBEntry


DEFAULT_DATA_DIR = settings.BASE_DIR.parent / "data"
REFERENCE_DIGITS_RE = re.compile(r"(\d+)")


class Command(BaseCommand):
    help = "Import DealerOS reconciliation CSV files without dropping dirty rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            default=str(DEFAULT_DATA_DIR),
            help="Directory containing locations.csv, system_a.csv, and system_b.csv.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Clear imported reconciliation data before loading the CSV files.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])
        if not data_dir.exists():
            raise CommandError(f"Data directory does not exist: {data_dir}")

        for name in ("locations.csv", "system_a.csv", "system_b.csv"):
            if not (data_dir / name).exists():
                raise CommandError(f"Missing required CSV: {data_dir / name}")

        if options["reset"]:
            SystemBEntry.objects.all().delete()
            SystemARecord.objects.all().delete()
            Location.objects.all().delete()
            Organization.objects.all().delete()

        locations = self.import_locations(data_dir / "locations.csv")
        a_count = self.import_system_a(data_dir / "system_a.csv", locations)
        b_count = self.import_system_b(data_dir / "system_b.csv", locations)
        warning_count = self.warning_count()

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(locations)} locations, {a_count} System A records, "
                f"{b_count} System B entries, {warning_count} row warnings."
            )
        )

    def import_locations(self, path):
        locations = {}
        for row_number, row in read_csv(path):
            org_id = clean(row.get("org_id"))
            location_id = clean(row.get("location_id"))
            location_name = clean(row.get("location_name"))
            if not org_id or not location_id:
                continue

            org, _ = Organization.objects.update_or_create(
                org_id=org_id,
                defaults={"name": org_id},
            )
            location, _ = Location.objects.update_or_create(
                location_id=location_id,
                defaults={"organization": org, "location_name": location_name or location_id},
            )
            locations[location_id] = location
        return locations

    def import_system_a(self, path, locations):
        count = 0
        for row_number, row in read_csv(path):
            warnings = []
            raw_location_id = clean(row.get("location_id"))
            location = locations.get(raw_location_id)
            if location is None:
                warnings.append("Unknown location_id")

            total_value = self.parse_decimal("total_value", row.get("total_value"), warnings)
            record_id = clean(row.get("record_id"))
            if not record_id:
                warnings.append("Missing record_id")

            SystemARecord.objects.update_or_create(
                raw_location_id=raw_location_id,
                record_id=record_id,
                defaults={
                    "location": location,
                    "total_value": total_value,
                    "source_row_number": row_number,
                    "import_warnings": warnings,
                    "raw_data": row,
                },
            )
            count += 1
        return count

    def import_system_b(self, path, locations):
        count = 0
        for row_number, row in read_csv(path):
            warnings = []
            raw_location_id = clean(row.get("location_id"))
            location = locations.get(raw_location_id)
            if location is None:
                warnings.append("Unknown location_id")

            value = self.parse_decimal("value", row.get("value"), warnings)
            record_ref = clean(row.get("record_ref"))
            normalized_ref = normalize_record_ref(record_ref)
            if not normalized_ref:
                warnings.append("Could not normalize record_ref")

            entry_id = clean(row.get("entry_id")) or f"missing-entry-id-row-{row_number}"
            if not clean(row.get("entry_id")):
                warnings.append("Missing entry_id")

            SystemBEntry.objects.update_or_create(
                entry_id=entry_id,
                defaults={
                    "record_ref": record_ref,
                    "normalized_record_ref": normalized_ref,
                    "location": location,
                    "raw_location_id": raw_location_id,
                    "value": value,
                    "label": clean(row.get("label")),
                    "source_row_number": row_number,
                    "import_warnings": warnings,
                    "raw_data": row,
                },
            )
            count += 1
        return count

    def parse_decimal(self, field_name, raw_value, warnings):
        value = clean(raw_value)
        if not value:
            warnings.append(f"Blank {field_name}")
            return None

        normalized = value.replace(",", "")
        try:
            return Decimal(normalized)
        except InvalidOperation:
            warnings.append(f"Invalid {field_name}")
            return None

    def warning_count(self):
        a_warnings = sum(1 for record in SystemARecord.objects.all() if record.import_warnings)
        b_warnings = sum(1 for entry in SystemBEntry.objects.all() if entry.import_warnings)
        return a_warnings + b_warnings


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row_number, row in enumerate(reader, start=2):
            yield row_number, {key: value for key, value in row.items()}


def clean(value):
    return "" if value is None else str(value).strip()


def normalize_record_ref(value):
    cleaned = clean(value).upper().replace(" ", "")
    if cleaned.startswith("REC-"):
        return cleaned
    if cleaned.startswith("REC"):
        digits = "".join(REFERENCE_DIGITS_RE.findall(cleaned))
        return f"REC-{digits}" if digits else ""
    if cleaned.isdigit():
        return f"REC-{cleaned}"
    return ""
