from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

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
