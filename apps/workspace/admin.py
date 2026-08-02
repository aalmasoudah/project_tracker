from typing import TYPE_CHECKING

from django.contrib import admin

from apps.workspace.models import SavedFilter

if TYPE_CHECKING:

    class SavedFilterAdminBase(admin.ModelAdmin[SavedFilter]):
        pass

else:
    SavedFilterAdminBase = admin.ModelAdmin


@admin.register(SavedFilter)
class SavedFilterAdmin(SavedFilterAdminBase):
    list_display = ("name", "owner", "view_type", "schema_version", "updated_at")
    list_filter = ("view_type", "schema_version")
    search_fields = ("name", "owner__username", "owner__display_name")
    readonly_fields = (
        "owner",
        "criteria",
        "schema_version",
        "created_at",
        "updated_at",
    )
