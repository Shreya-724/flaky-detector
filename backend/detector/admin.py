from django.contrib import admin

from .models import CaseResult, CIRun, ErrorGroup, Project, TrackedTest


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_public", "default_branch")
    list_editable = ("is_public",)


@admin.register(TrackedTest)
class TrackedTestAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "flakiness_score", "executions", "conflict_commits")
    list_filter = ("status", "project")
    search_fields = ("name",)


admin.site.register([CIRun, ErrorGroup, CaseResult])