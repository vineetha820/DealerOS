from django.db import models


class Organization(models.Model):
    org_id = models.CharField(max_length=50, unique=True, primary_key=True)
    name = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "organization"

    def __str__(self):
        return self.org_id


class Location(models.Model):
    location_id = models.CharField(max_length=50, unique=True, primary_key=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="locations",
        db_column="org_id",
    )
    location_name = models.CharField(max_length=255)

    class Meta:
        db_table = "location"

    def __str__(self):
        return self.location_name


class SystemARecord(models.Model):
    record_id = models.CharField(max_length=50, db_index=True)
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        related_name="system_a_records",
        null=True,
        blank=True,
    )
    raw_location_id = models.CharField(max_length=50, blank=True, default="")
    total_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    source_row_number = models.PositiveIntegerField(default=0)
    import_warnings = models.JSONField(default=list, blank=True)
    raw_data = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["raw_location_id", "record_id"],
                name="unique_a_record_per_raw_location",
            )
        ]

    def __str__(self):
        return self.record_id


class SystemBEntry(models.Model):
    entry_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    record_ref = models.CharField(max_length=100, blank=True)
    normalized_record_ref = models.CharField(max_length=50, blank=True, db_index=True)
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        related_name="system_b_entries",
        null=True,
        blank=True,
    )
    raw_location_id = models.CharField(max_length=50, blank=True, default="")
    value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    label = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    source_row_number = models.PositiveIntegerField(default=0)
    import_warnings = models.JSONField(default=list, blank=True)
    raw_data = models.JSONField(default=dict)

    def __str__(self):
        return self.entry_id or self.record_ref
