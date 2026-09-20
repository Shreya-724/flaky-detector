from django.contrib import admin

from .models import CaseResult, CIRun, ErrorGroup, Project, TrackedTest


@admin.register(TrackedTest)
class TrackedTestAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "flakiness_score", "executions", "conflict_commits")
    list_filter = ("status", "project")
    search_fields = ("name",)


admin.site.register([Project, CIRun, ErrorGroup, CaseResult])