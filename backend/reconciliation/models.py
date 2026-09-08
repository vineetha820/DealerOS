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
    record_id = models.CharField(max_length=50)
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="system_a_records",
    )
    total_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Original CSV row
    raw_data = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["location", "record_id"],
                name="unique_a_record_per_location",
            )
        ]

    def __str__(self):
        return self.record_id


class SystemBEntry(models.Model):
    # Exactly what appeared in the CSV
    record_ref = models.CharField(max_length=100)

    # Cleaned value used for matching
    normalized_record_ref = models.CharField(
        max_length=50,
        db_index=True,
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="system_b_entries",
    )

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

    # Original CSV row
    raw_data = models.JSONField(default=dict)

    def __str__(self):
        return self.record_ref
