import httpx
import os
from datetime import date, timedelta
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
        due_today: bool = False,
        due_this_week: bool = False,
        start: int = 0,
    ) -> list[dict]:
        filter: dict[str, Any] = {"!STATUS": 5}
        if responsible_id:
            filter["RESPONSIBLE_ID"] = responsible_id
        if overdue_only:
            filter["<=DEADLINE"] = date.today().isoformat()
        if due_today:
            filter[">=DEADLINE"] = date.today().isoformat()
            filter["<=DEADLINE"] = date.today().isoformat()
        if due_this_week:
            filter[">=DEADLINE"] = date.today().isoformat()
            filter["<=DEADLINE"] = (date.today() + timedelta(days=7)).isoformat()

        params: dict[str, Any] = {
            "filter": filter,
            "select": ["ID", "TITLE", "DEADLINE", "RESPONSIBLE_ID", "STATUS", "UF_CRM_TASK"],
            "order": {"ID": "desc"},
            "start": start,
        }
        result = self._call("tasks.task.list", params)
        if isinstance(result, dict):
            return result.get("tasks", [])
        return []

    def list_dormant_deals(self, days: int = 20) -> list[dict]:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        return self.list_deals(
            filter={"<=DATE_MODIFY": cutoff, "CLOSED": "N"},
            select=["ID", "TITLE", "STAGE_ID", "DATE_MODIFY", "ASSIGNED_BY_ID", "OPPORTUNITY", "CURRENCY_ID"],
            order={"DATE_MODIFY": "ASC"},
        )

    def list_closing_this_week(self) -> list[dict]:
        today = date.today().isoformat()
        next_week = (date.today() + timedelta(days=7)).isoformat()
        return self.list_deals(
            filter={">=CLOSEDATE": today, "<=CLOSEDATE": next_week, "CLOSED": "N"},
            select=["ID", "TITLE", "STAGE_ID", "CLOSEDATE", "OPPORTUNITY", "CURRENCY_ID", "ASSIGNED_BY_ID"],
            order={"CLOSEDATE": "ASC"},
        )

    _QUAL_SELECT = [
        "ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID",
        "ASSIGNED_BY_ID", "CLOSEDATE",
        "UF_CRM_1564075666375",  # qualificacao: Pipeline/Qualificado/Forecast
        "UF_CRM_1706292905087",  # viavel tecnicamente: Sim/Nao/Sem Informacao
        "UF_CRM_1706292722058",  # diferenciais tecnicos: Nenhum/Baixo/Medio/Alto
        "UF_CRM_1581432810546",  # numero do RO
    ]

    # Mapa de IDs de opcao para valores legíveis
    _VIAVEL_MAP = {"3617": "Sim", "3613": "Não", "3615": "Sem Info"}
    _DIFER_MAP = {"3585": "Nenhum", "3587": "Baixo", "3589": "Médio", "3591": "Alto"}

    def _resolve_qual(self, deal: dict) -> dict:
        """Resolve campos de qualificação para valores legíveis."""
        qual_id = str(deal.get("UF_CRM_1564075666375", "") or "")
        qual_map = {"376": "Pipeline", "378": "Qualificado", "380": "Forecast"}
        deal["_qualificacao"] = qual_map.get(qual_id, qual_id or "—")
        viavel_id = str(deal.get("UF_CRM_1706292905087", "") or "")
        deal["_viavel"] = self._VIAVEL_MAP.get(viavel_id, "—")
        difer_id = str(deal.get("UF_CRM_1706292722058", "") or "")
        deal["_diferencial"] = self._DIFER_MAP.get(difer_id, "—")
        deal["_ro"] = deal.get("UF_CRM_1581432810546") or ""
        return deal

    def list_top_deals(self, limit: int = 10) -> list[dict]:
        """Deals qualificados/forecast ordenados por valor."""
        deals = self.list_deals(
            filter={"CLOSED": "N", "UF_CRM_1564075666375": [378, 380]},
            select=self._QUAL_SELECT,
            order={"OPPORTUNITY": "DESC"},
        )
        return [self._resolve_qual(d) for d in deals[:limit]]

    def list_unqualified_deals(self, limit: int = 20) -> list[dict]:
        """Deals em Pipeline sem qualificação completa de pré-vendas."""
        deals = self.list_deals(
            filter={"CLOSED": "N", "UF_CRM_1564075666375": 376},
            select=self._QUAL_SELECT,
            order={"OPPORTUNITY": "DESC"},
        )
        result = []
        for d in deals:
            self._resolve_qual(d)
            viavel = d["_viavel"]
            diferencial = d["_diferencial"]
            ro = d["_ro"]
            missing = []
            if viavel in ("—", "Sem Info", "Não"):
                missing.append("Viável?")
            if diferencial in ("—", "Nenhum"):
                missing.append("Diferencial")
            if not ro:
                missing.append("N° RO")
            d["_missing"] = missing
            if missing:
                result.append(d)
        return result[:limit]
