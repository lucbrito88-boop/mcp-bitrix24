import httpx
import os
from typing import Any


class BitrixClient:
    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = (webhook_url or os.getenv("BITRIX24_WEBHOOK_URL", "")).rstrip("/")
        if not self.webhook_url:
            raise ValueError("BITRIX24_WEBHOOK_URL não configurado")

    def _call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.webhook_url}/{method}"
        response = httpx.post(url, json=params or {}, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(f"Bitrix24 error: {data.get('error_description', data['error'])}")
        return data.get("result")

    def list_deals(
        self,
        filter: dict | None = None,
        select: list[str] | None = None,
        order: dict | None = None,
        start: int = 0,
    ) -> list[dict]:
        params: dict[str, Any] = {"start": start}
        if filter:
            params["filter"] = filter
        if select:
            params["select"] = select
        if order:
            params["order"] = order
        result = self._call("crm.deal.list", params)
        return result if isinstance(result, list) else []

    def get_deal(self, deal_id: int) -> dict:
        return self._call("crm.deal.get", {"id": deal_id})

    def create_deal(self, fields: dict) -> int:
        return self._call("crm.deal.add", {"fields": fields})

    def update_deal(self, deal_id: int, fields: dict) -> bool:
        return self._call("crm.deal.update", {"id": deal_id, "fields": fields})

    def get_stages(self, pipeline_id: int | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if pipeline_id is not None:
            params["filter"] = {"CATEGORY_ID": pipeline_id}
        return self._call("crm.dealcategory.stage.list", params) or []

    def add_comment(self, deal_id: int, comment: str) -> int:
        fields = {
            "OWNER_TYPE_ID": 2,
            "OWNER_ID": deal_id,
            "TYPE_ID": 12,
            "SUBJECT": "Nota",
            "DESCRIPTION": comment,
            "DESCRIPTION_TYPE": 1,
            "COMPLETED": "Y",
            "DIRECTION": 0,
        }
        return self._call("crm.activity.add", {"fields": fields})

    def add_task(self, deal_id: int, subject: str, description: str = "", deadline: str = "") -> int:
        fields: dict[str, Any] = {
            "OWNER_TYPE_ID": 2,
            "OWNER_ID": deal_id,
            "TYPE_ID": 6,
            "SUBJECT": subject,
            "DESCRIPTION": description,
            "COMPLETED": "N",
            "DIRECTION": 0,
        }
        if deadline:
            fields["DEADLINE"] = deadline
        return self._call("crm.activity.add", {"fields": fields})

    def list_pipelines(self) -> list[dict]:
        return self._call("crm.dealcategory.list") or []

    def list_tasks(
        self,
        responsible_id: int | None = None,
        overdue_only: bool = False,
        start: int = 0,
    ) -> list[dict]:
        filter: dict[str, Any] = {"!STATUS": 5}
        if responsible_id:
            filter["RESPONSIBLE_ID"] = responsible_id
        if overdue_only:
            from datetime import date
            filter["<=DEADLINE"] = date.today().isoformat()

        params: dict[str, Any] = {
            "filter": filter,
            "select": ["ID", "TITLE", "DEADLINE", "RESPONSIBLE_ID", "STATUS", "UF_CRM_TASK"],
            "start": start,
        }
        result = self._call("tasks.task.list", params)
        if isinstance(result, dict):
            return result.get("tasks", [])
        return []
