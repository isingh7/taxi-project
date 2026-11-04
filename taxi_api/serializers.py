from rest_framework import serializers

from taxi_api.models import IngestionRun


class TaxiTripSerializer(serializers.Serializer):
    """Response contract for ``/api/data/<table>/``. The React app depends on this shape."""

    avg_journey_time = serializers.FloatField(allow_null=True)
    min_journey_time = serializers.FloatField(allow_null=True)
    max_journey_time = serializers.FloatField(allow_null=True)
    avg_total_cost = serializers.FloatField(allow_null=True)
    min_total_cost = serializers.FloatField(allow_null=True)
    max_total_cost = serializers.FloatField(allow_null=True)
    most_popular_pickup_location = serializers.DictField()
    most_popular_dropoff_location = serializers.DictField()
    most_popular_time_of_day = serializers.DictField()
    avg_tip_amount = serializers.FloatField(allow_null=True)
    data_source = serializers.ChoiceField(choices=["bigquery", "local"])


class IngestionRunSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = IngestionRun
        fields = [
            "id", "source", "source_table", "status", "started_at", "finished_at",
            "duration_seconds", "rows_extracted", "rows_loaded", "rows_rejected",
            "quality_report", "error_message",
        ]

    def get_duration_seconds(self, obj):
        if obj.finished_at and obj.started_at:
            return round((obj.finished_at - obj.started_at).total_seconds(), 2)
        return None
