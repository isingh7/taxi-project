"""Relational model for the local analytics store.

Star-schema style layout:
    * ``Zone`` and ``PaymentType`` are reference (dimension) tables loaded from
      CSV files.
    * ``Trip`` is the fact table, filled by the ETL pipeline from BigQuery, a
      CSV extract or the synthetic generator.
    * ``IngestionRun`` is an audit log. Each load records row counts and its
      data-quality report, so data lineage can be traced.
"""

from django.db import models


class Zone(models.Model):
    zone_id = models.PositiveIntegerField(primary_key=True)
    zone_name = models.CharField(max_length=64, unique=True)
    borough = models.CharField(max_length=32, db_index=True)
    min_lat = models.FloatField()
    max_lat = models.FloatField()
    min_lon = models.FloatField()
    max_lon = models.FloatField()
    priority = models.PositiveSmallIntegerField(
        help_text="Lower number wins when bounding boxes overlap."
    )

    class Meta:
        ordering = ["priority"]

    def __str__(self):
        return f"{self.zone_name} ({self.borough})"


class PaymentType(models.Model):
    payment_code = models.PositiveSmallIntegerField(primary_key=True)
    payment_label = models.CharField(max_length=32)
    is_electronic = models.BooleanField(default=False)

    def __str__(self):
        return self.payment_label


class IngestionRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running"
        SUCCESS = "success"
        FAILED = "failed"

    source = models.CharField(max_length=32)
    source_table = models.CharField(max_length=64)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING)
    rows_extracted = models.PositiveIntegerField(default=0)
    rows_loaded = models.PositiveIntegerField(default=0)
    rows_rejected = models.PositiveIntegerField(default=0)
    quality_report = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.source}:{self.source_table} @ {self.started_at:%Y-%m-%d %H:%M} ({self.status})"


class Trip(models.Model):
    ingestion_run = models.ForeignKey(IngestionRun, on_delete=models.CASCADE, related_name="trips")
    source_table = models.CharField(max_length=64, db_index=True)
    pickup_datetime = models.DateTimeField(db_index=True)
    dropoff_datetime = models.DateTimeField()
    passenger_count = models.PositiveSmallIntegerField(null=True)
    trip_distance = models.FloatField(help_text="Miles")
    duration_minutes = models.FloatField()
    fare_amount = models.DecimalField(max_digits=10, decimal_places=2)
    tip_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.ForeignKey(PaymentType, on_delete=models.PROTECT, related_name="trips")
    pickup_zone = models.ForeignKey(
        Zone, null=True, on_delete=models.SET_NULL, related_name="pickups"
    )
    dropoff_zone = models.ForeignKey(
        Zone, null=True, on_delete=models.SET_NULL, related_name="dropoffs"
    )
    pickup_latitude = models.FloatField(null=True)
    pickup_longitude = models.FloatField(null=True)
    dropoff_latitude = models.FloatField(null=True)
    dropoff_longitude = models.FloatField(null=True)
    is_outlier = models.BooleanField(
        default=False, help_text="Flagged by the robust z-score fare check; kept, not deleted."
    )

    class Meta:
        indexes = [models.Index(fields=["source_table", "pickup_datetime"])]
