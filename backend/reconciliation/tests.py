from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from reconciliation.comparison import (
    DATA_ISSUE,
    DUPLICATE_B_ENTRIES,
    MISSING_IN_B,
    UNKNOWN_B_REFERENCE,
    VALUE_MISMATCH,
    find_disagreements,
)
from reconciliation.models import Location, Organization, SystemARecord, SystemBEntry


class ImportReconciliationDataTests(TestCase):
    def test_import_keeps_dirty_rows_and_stores_warnings_on_rows(self):
        with TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "locations.csv").write_text(
                "location_id,org_id,location_name\n"
                "LOC-1,ORG-A,Location One\n",
                encoding="utf-8",
            )
            (data_dir / "system_a.csv").write_text(
                "record_id,location_id,event_date,category_code,actor_id,base_value,adjustment,total_value,state\n"
                "REC-1001,LOC-1,2026-04-03,CAT-02,USR-22,1.00,2.00,3.00,CONFIRMED\n"
                "REC-1002,LOC-1,2026-04-04,CAT-03,USR-22,1.00,2.00,bad,CONFIRMED\n",
                encoding="utf-8",
            )
            (data_dir / "system_b.csv").write_text(
                "entry_id,record_ref,location_id,recorded_on,value,label\n"
                "ENT-1,rec1001,LOC-1,2026-04-03,3.00,Entry one\n"
                "ENT-2, REC - 1002 ,LOC-1,2026-04-04,,Entry two\n"
                "ENT-3,1003,LOC-1,2026-04-05,1,Entry three\n",
                encoding="utf-8",
            )

            output = StringIO()
            call_command("import_reconciliation_data", "--data-dir", str(data_dir), "--reset", stdout=output)

        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(Location.objects.count(), 1)
        self.assertEqual(SystemARecord.objects.count(), 2)
        self.assertEqual(SystemBEntry.objects.count(), 3)

        dirty_a = SystemARecord.objects.get(record_id="REC-1002")
        self.assertIsNone(dirty_a.total_value)
        self.assertIn("Invalid total_value", dirty_a.import_warnings)

        blank_b = SystemBEntry.objects.get(entry_id="ENT-2")
        self.assertEqual(blank_b.normalized_record_ref, "REC-1002")
        self.assertIsNone(blank_b.value)
        self.assertIn("Blank value", blank_b.import_warnings)

        numeric_ref = SystemBEntry.objects.get(entry_id="ENT-3")
        self.assertEqual(numeric_ref.normalized_record_ref, "REC-1003")
        self.assertEqual(numeric_ref.value, Decimal("1"))

        self.assertIn("Imported 1 locations, 2 System A records, 3 System B entries, 2 row warnings", output.getvalue())


class ComparisonLogicTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(org_id="ORG-A", name="Org A")
        self.org_b = Organization.objects.create(org_id="ORG-B", name="Org B")
        self.loc_a = Location.objects.create(
            location_id="LOC-A",
            organization=self.org_a,
            location_name="Location A",
        )
        self.loc_b = Location.objects.create(
            location_id="LOC-B",
            organization=self.org_b,
            location_name="Location B",
        )

    def test_missing_system_b_entry_is_reported(self):
        self.make_a("REC-1001", "10.00", self.loc_a)

        disagreements = find_disagreements()

        self.assertEqual([item.reason for item in disagreements], [MISSING_IN_B])
        self.assertEqual(disagreements[0].record_id, "REC-1001")
        self.assertEqual(disagreements[0].org_id, "ORG-A")

    def test_system_b_reference_is_unknown_when_record_exists_only_in_another_org(self):
        self.make_a("REC-1001", "10.00", self.loc_a)
        self.make_b("ENT-1", "REC-1001", "10.00", self.loc_b)

        reasons = sorted(item.reason for item in find_disagreements())

        self.assertEqual(reasons, [MISSING_IN_B, UNKNOWN_B_REFERENCE])

    def test_duplicate_system_b_entries_are_reported(self):
        self.make_a("REC-1001", "10.00", self.loc_a)
        self.make_b("ENT-1", "REC-1001", "10.00", self.loc_a)
        self.make_b("ENT-2", "REC-1001", "10.00", self.loc_a)

        disagreements = find_disagreements()

        self.assertEqual([item.reason for item in disagreements], [DUPLICATE_B_ENTRIES])
        self.assertEqual(disagreements[0].b_entry_ids, ("ENT-1", "ENT-2"))

    def test_different_amounts_are_reported(self):
        self.make_a("REC-1001", "10.00", self.loc_a)
        self.make_b("ENT-1", "REC-1001", "12.00", self.loc_a)

        disagreements = find_disagreements()

        self.assertEqual([item.reason for item in disagreements], [VALUE_MISMATCH])
        self.assertEqual(disagreements[0].a_value, Decimal("10.00"))
        self.assertEqual(disagreements[0].b_values, (Decimal("12.00"),))

    def test_blank_or_invalid_amounts_are_data_issues_not_zero(self):
        self.make_a("REC-1001", None, self.loc_a, warnings=["Invalid total_value"])
        self.make_b("ENT-1", "REC-1001", None, self.loc_a, warnings=["Blank value"])

        reasons = [item.reason for item in find_disagreements()]

        self.assertEqual(reasons, [DATA_ISSUE, DATA_ISSUE])

    def test_rec_1055_with_split_label_and_matching_sum_is_not_a_duplicate(self):
        self.make_a("REC-1055", "100.00", self.loc_a)
        self.make_b("ENT-1", "REC-1055", "40.00", self.loc_a, label="Entry for CAT-08")
        self.make_b("ENT-2", "REC-1055", "60.00", self.loc_a, label="Entry part 2 of 2")

        self.assertEqual(find_disagreements(), [])

    def test_rec_1055_equal_sum_without_split_label_is_still_duplicate(self):
        self.make_a("REC-1055", "100.00", self.loc_a)
        self.make_b("ENT-1", "REC-1055", "40.00", self.loc_a, label="Entry for CAT-08")
        self.make_b("ENT-2", "REC-1055", "60.00", self.loc_a, label="Entry for CAT-08")

        disagreements = find_disagreements()

        self.assertEqual([item.reason for item in disagreements], [DUPLICATE_B_ENTRIES])

    def make_a(self, record_id, amount, location, warnings=None):
        return SystemARecord.objects.create(
            record_id=record_id,
            location=location,
            raw_location_id=location.location_id,
            total_value=Decimal(amount) if amount is not None else None,
            source_row_number=1,
            import_warnings=warnings or [],
            raw_data={"record_id": record_id, "total_value": amount or ""},
        )

    def make_b(self, entry_id, record_ref, amount, location, label="Entry", warnings=None):
        return SystemBEntry.objects.create(
            entry_id=entry_id,
            record_ref=record_ref,
            normalized_record_ref=record_ref,
            location=location,
            raw_location_id=location.location_id,
            value=Decimal(amount) if amount is not None else None,
            label=label,
            source_row_number=1,
            import_warnings=warnings or [],
            raw_data={"entry_id": entry_id, "record_ref": record_ref, "value": amount or ""},
        )

class DisagreementApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org_a = Organization.objects.create(org_id="ORG-A", name="Org A")
        self.org_b = Organization.objects.create(org_id="ORG-B", name="Org B")
        self.loc_a = Location.objects.create(
            location_id="LOC-A",
            organization=self.org_a,
            location_name="Location A",
        )
        self.loc_b = Location.objects.create(
            location_id="LOC-B",
            organization=self.org_b,
            location_name="Location B",
        )

    def test_api_returns_all_disagreements_by_default(self):
        self.make_a("REC-1001", "10.00", self.loc_a)
        self.make_b("ENT-1", "REC-1001", "12.00", self.loc_a)
        self.make_a("REC-2001", "20.00", self.loc_b)

        response = self.client.get("/api/disagreements/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        reasons = sorted(item["reason"] for item in data["results"])
        self.assertEqual(reasons, [MISSING_IN_B, VALUE_MISMATCH])

    def test_api_can_still_filter_by_org_for_backend_safety(self):
        self.make_a("REC-1001", "10.00", self.loc_a)
        self.make_b("ENT-1", "REC-1001", "12.00", self.loc_a)
        self.make_a("REC-2001", "20.00", self.loc_b)

        response = self.client.get("/api/disagreements/?org_id=ORG-A")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["org_id"], "ORG-A")
        self.assertEqual(data["results"][0]["reason"], VALUE_MISMATCH)

    def test_api_filters_by_reason(self):
        self.make_a("REC-1001", "10.00", self.loc_a)
        self.make_b("ENT-1", "REC-1001", "12.00", self.loc_a)
        self.make_a("REC-1002", "15.00", self.loc_a)

        response = self.client.get(f"/api/disagreements/?reason={MISSING_IN_B}")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["record_id"], "REC-1002")
        self.assertEqual(data["results"][0]["reason"], MISSING_IN_B)

    def test_api_sorts_by_value(self):
        self.make_a("REC-1001", "30.00", self.loc_a)
        self.make_b("ENT-1", "REC-1001", "31.00", self.loc_a)
        self.make_a("REC-1002", "10.00", self.loc_a)
        self.make_b("ENT-2", "REC-1002", "11.00", self.loc_a)

        response = self.client.get("/api/disagreements/?sort=value")

        self.assertEqual(response.status_code, 200)
        records = [item["record_id"] for item in response.json()["results"]]
        self.assertEqual(records, ["REC-1002", "REC-1001"])

    def test_api_paginates_results(self):
        for index in range(1, 4):
            record_id = f"REC-100{index}"
            self.make_a(record_id, str(index), self.loc_a)

        response = self.client.get("/api/disagreements/?page=2&page_size=2")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["page_size"], 2)
        self.assertEqual(data["total_pages"], 2)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["record_id"], "REC-1003")

    def make_a(self, record_id, amount, location, warnings=None):
        return SystemARecord.objects.create(
            record_id=record_id,
            location=location,
            raw_location_id=location.location_id,
            total_value=Decimal(amount) if amount is not None else None,
            source_row_number=1,
            import_warnings=warnings or [],
            raw_data={"record_id": record_id, "total_value": amount or ""},
        )

    def make_b(self, entry_id, record_ref, amount, location, label="Entry", warnings=None):
        return SystemBEntry.objects.create(
            entry_id=entry_id,
            record_ref=record_ref,
            normalized_record_ref=record_ref,
            location=location,
            raw_location_id=location.location_id,
            value=Decimal(amount) if amount is not None else None,
            label=label,
            source_row_number=1,
            import_warnings=warnings or [],
            raw_data={"entry_id": entry_id, "record_ref": record_ref, "value": amount or ""},
        )



