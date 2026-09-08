from decimal import Decimal

from django.test import TestCase

from reconciliation.comparison import (
    DATA_ISSUE,
    DUPLICATE_B_ENTRIES,
    MISSING_IN_B,
    UNKNOWN_B_REFERENCE,
    VALUE_MISMATCH,
    find_disagreements,
)
from reconciliation.models import Location, Organization, SystemARecord, SystemBEntry


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
        self.assertEqual(disagreements[0].location_id, "LOC-A")

    def test_system_b_entry_pointing_to_missing_record_is_reported(self):
        self.make_b("ENT-1", "REC-9999", "10.00", self.loc_a)

        disagreements = find_disagreements()

        self.assertEqual([item.reason for item in disagreements], [UNKNOWN_B_REFERENCE])
        self.assertEqual(disagreements[0].record_id, "REC-9999")
        self.assertEqual(disagreements[0].b_values, (Decimal("10.00"),))

    def test_same_record_in_different_organization_does_not_match(self):
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
