from rest_framework import serializers
from .models import Project, Task
from .models import FundDuration

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'name', 'description', 'start_date', 'end_date', 'completed', 'project', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ProjectSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'title', 'description', 'ai_model_used', 'duration_months', 
            'owner', 'tasks', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at','owner']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['owner'] = user
        return super().create(validated_data)

class ProjectListSerializer(serializers.ModelSerializer):
    task_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'title', 'description', 'ai_model_used', 'duration_months', 
            'task_count', 'created_at', 'updated_at'
        ]
    
    def get_task_count(self, obj):
        return obj.tasks.count()
    
class FundDurationSerializer(serializers.ModelSerializer):
    # Frontend'in beklediği alan adlarına uygun olarak isimlendirme
    code = serializers.CharField(source='kod')
    duration_months = serializers.IntegerField(source='ay_suresi')
    name = serializers.CharField(source='tur')
    
    class Meta:
        model = FundDuration
        fields = ['code', 'duration_months', 'name']  # Frontend'in beklediği alan adları