"""TaskRouter: the contact centre's routing engine (workspaces, activities, task queues, workflows,
task channels, workers and tasks). Paths live under /Workspaces, scoped to the caller's account."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp.exceptions import ToolError

from ._common import api, merge

WORKSPACES = "/Workspaces"
WS = WORKSPACES + "/{workspace_sid}"

Status = Literal["active", "inactive"]


def _crud_reads(mcp, client_factory, *, plural: str, singular: str, path: str, id_name: str, what: str) -> None:
    """list_<plural>, get_<singular> and delete_<singular> for a workspace sub-resource."""

    item = path + "/{" + id_name + "}"

    def list_items(workspace_sid: str, page: int | None = None, limit: int | None = None) -> Any:
        return api(client_factory, "GET", path, params={"page": page, "limit": limit}, workspace_sid=workspace_sid)

    def get_item(workspace_sid: str, sid: str) -> Any:
        return api(client_factory, "GET", item, workspace_sid=workspace_sid, **{id_name: sid})

    def delete_item(workspace_sid: str, sid: str) -> Any:
        return api(client_factory, "DELETE", item, workspace_sid=workspace_sid, **{id_name: sid})

    list_items.__name__, get_item.__name__, delete_item.__name__ = (
        f"list_{plural}",
        f"get_{singular}",
        f"delete_{singular}",
    )
    mcp.tool(name=f"siprtc.list_{plural}", description=f"List the {what} in a workspace.")(list_items)
    mcp.tool(name=f"siprtc.get_{singular}", description=f"Fetch one of a workspace's {what} by sid.")(get_item)
    mcp.tool(name=f"siprtc.delete_{singular}", description=f"Delete one of a workspace's {what} by sid.")(delete_item)


def register(mcp, client_factory):
    # --- workspaces -------------------------------------------------------------------------
    @mcp.tool(name="siprtc.list_workspaces", description="List TaskRouter workspaces (one per contact centre).")
    def list_workspaces(page: int | None = None, limit: int | None = None) -> Any:
        return api(client_factory, "GET", WORKSPACES, params={"page": page, "limit": limit})

    @mcp.tool(name="siprtc.get_workspace", description="Fetch one workspace by sid (WS...).")
    def get_workspace(workspace_sid: str) -> Any:
        return api(client_factory, "GET", WS, workspace_sid=workspace_sid)

    @mcp.tool(
        name="siprtc.create_workspace",
        description="Create a workspace. prioritize_queue_order: FIFO or LIFO. extra takes other API fields (e.g. metadata).",
    )
    def create_workspace(
        friendly_name: str,
        status: Status = "active",
        default_activity_sid: str | None = None,
        timeout_activity_sid: str | None = None,
        event_callback_url: str | None = None,
        multi_task_enabled: bool | None = None,
        prioritize_queue_order: Literal["FIFO", "LIFO"] | None = None,
        extra: dict | None = None,
    ) -> Any:
        body = merge(
            {
                "friendly_name": friendly_name,
                "status": status,
                "default_activity_sid": default_activity_sid,
                "timeout_activity_sid": timeout_activity_sid,
                "event_callback_url": event_callback_url,
                "multi_task_enabled": multi_task_enabled,
                "prioritize_queue_order": prioritize_queue_order,
            },
            extra,
        )
        return api(client_factory, "POST", WORKSPACES, json=body)

    @mcp.tool(
        name="siprtc.update_workspace",
        description="Update a workspace (friendly_name and status are required by the API).",
    )
    def update_workspace(
        workspace_sid: str,
        friendly_name: str,
        status: Status,
        default_activity_sid: str | None = None,
        timeout_activity_sid: str | None = None,
        event_callback_url: str | None = None,
        multi_task_enabled: bool | None = None,
        prioritize_queue_order: Literal["FIFO", "LIFO"] | None = None,
        extra: dict | None = None,
    ) -> Any:
        body = merge(
            {
                "friendly_name": friendly_name,
                "status": status,
                "default_activity_sid": default_activity_sid,
                "timeout_activity_sid": timeout_activity_sid,
                "event_callback_url": event_callback_url,
                "multi_task_enabled": multi_task_enabled,
                "prioritize_queue_order": prioritize_queue_order,
            },
            extra,
        )
        return api(client_factory, "PUT", WS, json=body, workspace_sid=workspace_sid)

    # --- activities -------------------------------------------------------------------------
    _crud_reads(
        mcp,
        client_factory,
        plural="activities",
        singular="activity",
        path=WS + "/Activities",
        id_name="activity_sid",
        what="activities (agent states such as Available, Break, Offline)",
    )

    @mcp.tool(
        name="siprtc.create_activity",
        description=(
            "Create an agent activity (state). available=true means agents in it get tasks. "
            "msteams_activity_name maps it to Teams presence: Available, Busy, DoNotDisturb, BeRightBack, Away or OffWork."
        ),
    )
    def create_activity(
        workspace_sid: str,
        friendly_name: str,
        display_name: str,
        msteams_activity_name: Literal["Available", "Busy", "DoNotDisturb", "BeRightBack", "Away", "OffWork"],
        available: bool = False,
        status: Status = "active",
        is_default: bool | None = None,
    ) -> Any:
        body = {
            "friendly_name": friendly_name,
            "display_name": display_name,
            "msteams_activity_name": msteams_activity_name,
            "available": available,
            "status": status,
            "is_default": is_default,
        }
        return api(client_factory, "POST", WS + "/Activities", json=body, workspace_sid=workspace_sid)

    # --- task queues ------------------------------------------------------------------------
    _crud_reads(
        mcp,
        client_factory,
        plural="task_queues",
        singular="task_queue",
        path=WS + "/TaskQueues",
        id_name="queue_sid",
        what="task queues",
    )

    def queue_body(
        friendly_name, status, waiting_time, target_workers, task_order, max_queue_size, virtual_hold, extra
    ) -> dict:
        return merge(
            {
                "friendly_name": friendly_name,
                "status": status,
                "waiting_time": waiting_time,
                "target_workers": target_workers,
                "task_order": task_order,
                "max_queue_size": max_queue_size,
                "virtual_hold": virtual_hold,
            },
            extra,
        )

    @mcp.tool(
        name="siprtc.create_task_queue",
        description=(
            "Create a task queue. waiting_time: max seconds a task waits (up to 3600); target_workers: "
            "an expression over worker attributes, e.g. \"skills HAS 'billing'\". extra takes other fields "
            "(sla_configurations, moh_url, max_wrap_up_time, overflow, ...)."
        ),
    )
    def create_task_queue(
        workspace_sid: str,
        friendly_name: str,
        waiting_time: int,
        status: Status = "active",
        target_workers: str | None = None,
        task_order: Literal["FIFO", "LIFO"] | None = None,
        max_queue_size: int | None = None,
        virtual_hold: bool = False,
        extra: dict | None = None,
    ) -> Any:
        body = queue_body(
            friendly_name, status, waiting_time, target_workers, task_order, max_queue_size, virtual_hold, extra
        )
        return api(client_factory, "POST", WS + "/TaskQueues", json=body, workspace_sid=workspace_sid)

    @mcp.tool(
        name="siprtc.update_task_queue",
        description="Update a task queue (friendly_name, status and waiting_time are required by the API).",
    )
    def update_task_queue(
        workspace_sid: str,
        queue_sid: str,
        friendly_name: str,
        waiting_time: int,
        status: Status = "active",
        target_workers: str | None = None,
        task_order: Literal["FIFO", "LIFO"] | None = None,
        max_queue_size: int | None = None,
        virtual_hold: bool = False,
        extra: dict | None = None,
    ) -> Any:
        body = queue_body(
            friendly_name, status, waiting_time, target_workers, task_order, max_queue_size, virtual_hold, extra
        )
        return api(
            client_factory,
            "PUT",
            WS + "/TaskQueues/{queue_sid}",
            json=body,
            workspace_sid=workspace_sid,
            queue_sid=queue_sid,
        )

    # --- workflows --------------------------------------------------------------------------
    _crud_reads(
        mcp,
        client_factory,
        plural="workflows",
        singular="workflow",
        path=WS + "/Workflows",
        id_name="workflow_sid",
        what="workflows (routing rules from tasks to queues)",
    )

    @mcp.tool(
        name="siprtc.create_workflow",
        description=(
            'Create a workflow. configuration is the routing document, e.g. {"task_routing": '
            '{"filters": [...], "default_filter": {"queue": "WQ..."}}}.'
        ),
    )
    def create_workflow(
        workspace_sid: str,
        friendly_name: str,
        configuration: dict,
        status: Status = "active",
        assignment_callback_url: str | None = None,
        task_reservation_timeout: int | None = None,
    ) -> Any:
        body = {
            "friendly_name": friendly_name,
            "configuration": configuration,
            "status": status,
            "assignment_callback_url": assignment_callback_url,
            "task_reservation_timeout": task_reservation_timeout,
        }
        return api(client_factory, "POST", WS + "/Workflows", json=body, workspace_sid=workspace_sid)

    @mcp.tool(
        name="siprtc.update_workflow",
        description="Replace a workflow (send every field; the API overwrites the whole workflow).",
    )
    def update_workflow(
        workspace_sid: str,
        workflow_sid: str,
        friendly_name: str,
        configuration: dict,
        status: Status = "active",
        assignment_callback_url: str | None = None,
        task_reservation_timeout: int | None = None,
    ) -> Any:
        body = {
            "friendly_name": friendly_name,
            "configuration": configuration,
            "status": status,
            "assignment_callback_url": assignment_callback_url,
            "task_reservation_timeout": task_reservation_timeout,
        }
        return api(
            client_factory,
            "PUT",
            WS + "/Workflows/{workflow_sid}",
            json=body,
            workspace_sid=workspace_sid,
            workflow_sid=workflow_sid,
        )

    # --- task channels ----------------------------------------------------------------------
    @mcp.tool(name="siprtc.list_task_channels", description="List a workspace's task channels (voice, chat, sms, ...).")
    def list_task_channels(workspace_sid: str) -> Any:
        return api(client_factory, "GET", WS + "/Taskchannel", workspace_sid=workspace_sid)

    # --- workers ----------------------------------------------------------------------------
    _crud_reads(
        mcp,
        client_factory,
        plural="workers",
        singular="worker",
        path=WS + "/Workers",
        id_name="worker_sid",
        what="workers (agents)",
    )

    @mcp.tool(
        name="siprtc.create_worker",
        description=(
            "Create a worker (agent) in a workspace. attributes is a JSON object used for routing, "
            'e.g. {"skills": ["billing"], "languages": ["en"]}.'
        ),
    )
    def create_worker(
        workspace_sid: str,
        friendly_name: str,
        attributes: dict,
        status: Status = "active",
        activity_sid: str | None = None,
        extra: dict | None = None,
    ) -> Any:
        body = merge(
            {"friendly_name": friendly_name, "attributes": attributes, "status": status, "activity_sid": activity_sid},
            extra,
        )
        return api(client_factory, "POST", WS + "/Workers", json=body, workspace_sid=workspace_sid)

    @mcp.tool(
        name="siprtc.update_worker",
        description="Update a worker's name, routing attributes or status (friendly_name, attributes and status are required).",
    )
    def update_worker(
        workspace_sid: str,
        worker_sid: str,
        friendly_name: str,
        attributes: dict,
        status: Status = "active",
        extra: dict | None = None,
    ) -> Any:
        body = merge({"friendly_name": friendly_name, "attributes": attributes, "status": status}, extra)
        return api(
            client_factory,
            "PUT",
            WS + "/Workers/{worker_sid}",
            json=body,
            workspace_sid=workspace_sid,
            worker_sid=worker_sid,
        )

    @mcp.tool(
        name="siprtc.set_worker_activity",
        description="Change an agent's live state (e.g. to Available or Offline) by activity sid.",
    )
    def set_worker_activity(workspace_sid: str, worker_sid: str, activity_sid: str) -> Any:
        return api(
            client_factory,
            "POST",
            WS + "/Workers/{worker_sid}/Activities/{activity_sid}",
            params={"source": "api"},
            workspace_sid=workspace_sid,
            worker_sid=worker_sid,
            activity_sid=activity_sid,
        )

    # --- tasks ------------------------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_tasks",
        description="List tasks (calls, chats, ... being routed or done) in a workspace; dates are yyyy-mm-dd.",
    )
    def list_tasks(
        workspace_sid: str,
        from_date: str | None = None,
        to_date: str | None = None,
        assignment_status: str | None = None,
        task_queue_sid: str | None = None,
        task_channel_sid: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        params = {
            "fromdate": from_date,
            "todate": to_date,
            "assignment_status": assignment_status,
            "taskQueueSid": task_queue_sid,
            "taskChannelSid": task_channel_sid,
            "page": page,
            "limit": limit,
        }
        return api(client_factory, "GET", WS + "/Tasks", params=params, workspace_sid=workspace_sid)

    @mcp.tool(
        name="siprtc.get_task", description="Fetch one task by sid (WT...), with its status, queue and attributes."
    )
    def get_task(workspace_sid: str, task_sid: str) -> Any:
        found = api(client_factory, "GET", WS + "/Tasks", params={"sid": task_sid}, workspace_sid=workspace_sid)
        tasks = found.get("Tasks") if isinstance(found, dict) else None
        match = [task for task in tasks or [] if task.get("sid") == task_sid]
        if not match:
            raise ToolError(f"No task {task_sid} in workspace {workspace_sid}.")
        return match[0]

    @mcp.tool(
        name="siprtc.create_task",
        description=(
            "Create a task: the workflow routes it to a queue and reserves an agent, who is alerted. "
            "attributes is a JSON object the workflow filters on."
        ),
    )
    def create_task(
        workspace_sid: str,
        workflow_sid: str,
        task_channel_sid: str,
        attributes: dict,
        priority: int | None = None,
        timeout: int | None = None,
    ) -> Any:
        body = {
            "workflow_sid": workflow_sid,
            "task_channel_sid": task_channel_sid,
            "attributes": attributes,
            "priority": priority,
            "timeout": timeout,
        }
        return api(client_factory, "POST", WS + "/Tasks", json=body, workspace_sid=workspace_sid)

    @mcp.tool(
        name="siprtc.update_task_status",
        description="Move a task on: complete, cancel or wrap it up, optionally with a reason and a disposition.",
    )
    def update_task_status(
        workspace_sid: str,
        task_sid: str,
        status: Literal["completed", "canceled", "wrapping"],
        reason: str | None = None,
        disposition_id: str | None = None,
        disposition_name: str | None = None,
    ) -> Any:
        body = {
            "status": status,
            "reason": reason,
            "dispositionId": disposition_id,
            "dispositionName": disposition_name,
        }
        return api(
            client_factory, "PUT", WS + "/Tasks/{task_sid}", json=body, workspace_sid=workspace_sid, task_sid=task_sid
        )
