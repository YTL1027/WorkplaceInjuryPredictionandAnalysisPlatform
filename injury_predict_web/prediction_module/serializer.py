from rest_framework import serializers

from prediction_module.models import PredictionTask


class PredictionTaskSerializer(serializers.ModelSerializer):
    process_time = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S", required=False, read_only=True
    )
    finish_time = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S", required=False, read_only=True
    )

    def create(self, validated_data):
        return PredictionTask.objects.create(**validated_data)

    class Meta:
        model = PredictionTask
        fields = "__all__"
        read_only_fields = (
            "task_id",
            "process_time",
            "finish_time",
        )
