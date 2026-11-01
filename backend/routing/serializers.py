from rest_framework import serializers


def _has_timezone_offset(value: str) -> bool:
    return value.endswith('Z') or len(value) >= 6 and value[-6] in ('+', '-') and value[-3] == ':'


class RouteAnalysisRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=256, trim_whitespace=True)
    destination = serializers.CharField(max_length=256, trim_whitespace=True)
    departureTime = serializers.DateTimeField()
    loadWeightLbs = serializers.FloatField(min_value=0)
    checkpointIntervalMiles = serializers.ChoiceField(choices=(10, 25, 50), default=25, required=False)

    def validate(self, attrs):
        raw_departure_time = self.initial_data.get('departureTime')
        if isinstance(raw_departure_time, str) and not _has_timezone_offset(raw_departure_time):
            raise serializers.ValidationError({'departureTime': 'Departure time must include a timezone offset.'})
        return attrs

    def validate_departureTime(self, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise serializers.ValidationError('Departure time must include a timezone offset.')
        return value
