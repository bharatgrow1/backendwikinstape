from base.api.permissions import (PermissionComponent, ResourcePermission, IsAuthenticated, AllowAny)


class IsTheSameUser(PermissionComponent):
    def has_permission(self, request, view):
        return request.user.is_authenticated()

    def has_object_permission(self, request, view, obj=None):
        return request.user.is_authenticated() and request.user.pk == obj.pk

class UserPermissions(ResourcePermission):
    metadata_perms = IsAuthenticated()
    enough_perms = IsAuthenticated()
    global_perms = None
    retrieve_perms = IsAuthenticated()
    create_perms = IsAuthenticated()
    update_perms = IsAuthenticated()
    partial_update_perms = IsAuthenticated()
    destroy_perms = IsAuthenticated()
    list_perms = IsAuthenticated()
    templatesUser_perms = IsAuthenticated()
    tasktarget_perms = IsAuthenticated()
    taskpoint_perms = IsAuthenticated()
    start_task_perms = IsAuthenticated()
    stop_task_perms = IsAuthenticated()
    comment_perms = IsAuthenticated()
    details_perms = IsAuthenticated()
    assignee_perms = IsAuthenticated()
    reporter_perms = IsAuthenticated()
    complete_task_perms = IsAuthenticated()
    complete_request_perms = IsAuthenticated()
    templates_perms = IsAuthenticated()
    deltemplates_perms = IsAuthenticated()
    assign_template_perms = IsAuthenticated()
    rating_perms = IsAuthenticated()
    datewise_ratings_perms = IsAuthenticated()
    day_summary_perms = IsAuthenticated()
    rating_reports_perms = IsAuthenticated()
    task_reports_perms = IsAuthenticated()
    heads_perms = IsAuthenticated()
    monthly_targets_perms = IsAuthenticated()
    month_target_status_perms = IsAuthenticated()
    user_target_status_perms = IsAuthenticated()
    department_target_status_perms = IsAuthenticated()
    user_targets_perms = IsAuthenticated()
    statistics_perms = IsAuthenticated()