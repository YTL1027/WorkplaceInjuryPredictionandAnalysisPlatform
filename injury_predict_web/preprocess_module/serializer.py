from rest_framework import serializers

from preprocess_module.models import UploadTask


class UploadTaskSerializer(serializers.ModelSerializer):
    upload_time = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S", required=False, read_only=True
    )

    def create(self, validated_data):
        return UploadTask.objects.create(**validated_data)

    class Meta:
        model = UploadTask
        fields = (
            "id",
            "file_name",
            "status",
            "file",
            "file_type",
            "upload_time",
            "log",
        )
        read_only_fields = ("upload_time",)
