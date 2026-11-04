from django.contrib import admin

from taxi_api.models import IngestionRun, PaymentType, Trip, Zone


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "source_table", "status", "started_at",
                    "rows_extracted", "rows_loaded", "rows_rejected")
    list_filter = ("status", "source", "source_table")
    readonly_fields = [f.name for f in IngestionRun._meta.fields]


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("id", "source_table", "pickup_datetime", "trip_distance",
                    "fare_amount", "total_amount", "payment_type", "pickup_zone", "is_outlier")
    list_filter = ("source_table", "is_outlier", "payment_type", "pickup_zone__borough")
    list_select_related = ("payment_type", "pickup_zone")


admin.site.register(Zone)
admin.site.register(PaymentType)
