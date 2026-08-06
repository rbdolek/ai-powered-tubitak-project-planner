from django.contrib import admin
from .models import Project, Task

class TaskInline(admin.TabularInline):
    model = Task
    extra = 1

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'ai_model_used', 'duration_months', 'created_at')
    list_filter = ('ai_model_used', 'created_at', 'duration_months')
    search_fields = ('title', 'description', 'owner__username')
    date_hierarchy = 'created_at'
    inlines = [TaskInline]

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'start_date', 'end_date', 'completed')
    list_filter = ('completed', 'start_date', 'end_date')
    search_fields = ('name', 'description', 'project__title')
    date_hierarchy = 'start_date'