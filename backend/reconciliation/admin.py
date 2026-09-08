from django.contrib import admin

from reconciliation.models import Location, Organization, SystemARecord, SystemBEntry


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("org_id", "name")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("location_id", "organization", "location_name")
    list_filter = ("organization",)


@admin.register(SystemARecord)
class SystemARecordAdmin(admin.ModelAdmin):
    list_display = ("record_id", "raw_location_id", "location", "total_value", "source_row_number")
    search_fields = ("record_id", "raw_location_id")
    list_filter = ("location__organization",)


@admin.register(SystemBEntry)
class SystemBEntryAdmin(admin.ModelAdmin):
    list_display = ("entry_id", "record_ref", "normalized_record_ref", "raw_location_id", "value", "source_row_number")
    search_fields = ("entry_id", "record_ref", "normalized_record_ref", "raw_location_id")
    list_filter = ("location__organization",)
