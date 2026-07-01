import json
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp_bitrix24.client import BitrixClient

load_dotenv()

mcp = FastMCP("Bitrix24 CRM")
client = BitrixClient()


@mcp.tool()
def list_deals(
    stage: str = "",
    responsible_id: int = 0,
    title_contains: str = "",
    limit: int = 20,
) -> str:
    """Lista deals do Bitrix24. Filtre por estágio, responsável ou texto no título."""
    filter: dict = {}
    if stage:
        filter["STAGE_ID"] = stage
    if responsible_id:
        filter["ASSIGNED_BY_ID"] = responsible_id
    if title_contains:
        filter["%TITLE"] = title_contains

    select = ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID",
              "ASSIGNED_BY_ID", "DATE_CREATE", "CLOSEDATE", "COMMENTS"]

    deals = client.list_deals(filter=filter or None, select=select)
    deals = deals[:limit]

    if not deals:
        return "Nenhum deal encontrado com os filtros fornecidos."

    lines = [f"Encontrados {len(deals)} deals:\n"]
    for d in deals:
        valor = f"{d.get('OPPORTUNITY', '0')} {d.get('CURRENCY_ID', '')}"
        lines.append(
            f"• [{d['ID']}] {d['TITLE']}\n"
            f"  Estágio: {d.get('STAGE_ID')} | Valor: {valor}\n"
            f"  Responsável ID: {d.get('ASSIGNED_BY_ID')} | Fechamento: {d.get('CLOSEDATE', 'N/A')}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_deal(deal_id: int) -> str:
    """Retorna todos os detalhes de um deal específico pelo ID."""
    deal = client.get_deal(deal_id)
    if not deal:
        return f"Deal {deal_id} não encontrado."
    return json.dumps(deal, ensure_ascii=False, indent=2)


@mcp.tool()
def create_deal(
    title: str,
    stage_id: str = "",
    value: float = 0.0,
    currency: str = "BRL",
    contact_id: int = 0,
    company_id: int = 0,
    responsible_id: int = 0,
    comments: str = "",
    close_date: str = "",
) -> str:
    """
    Cria um novo deal no Bitrix24.
    close_date deve estar no formato YYYY-MM-DD.
    """
    fields: dict = {"TITLE": title, "CURRENCY_ID": currency}
    if stage_id:
        fields["STAGE_ID"] = stage_id
    if value:
        fields["OPPORTUNITY"] = value
    if contact_id:
        fields["CONTACT_ID"] = contact_id
    if company_id:
        fields["COMPANY_ID"] = company_id
    if responsible_id:
        fields["ASSIGNED_BY_ID"] = responsible_id
    if comments:
        fields["COMMENTS"] = comments
    if close_date:
        fields["CLOSEDATE"] = f"{close_date}T00:00:00+03:00"

    new_id = client.create_deal(fields)
    return f"Deal criado com sucesso! ID: {new_id}"


@mcp.tool()
def update_deal(deal_id: int, fields_json: str) -> str:
    """
    Atualiza campos de um deal existente.
    fields_json deve ser um JSON com os campos a atualizar.
    Exemplo: {"TITLE": "Novo nome", "OPPORTUNITY": 5000}
    """
    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError as e:
        return f"Erro: fields_json inválido — {e}"

    client.update_deal(deal_id, fields)
    return f"Deal {deal_id} atualizado com sucesso."


@mcp.tool()
def move_deal_stage(deal_id: int, stage_id: str) -> str:
    """
    Move um deal para um estágio do funil.
    Use list_stages para ver os estágios disponíveis.
    """
    client.update_deal(deal_id, {"STAGE_ID": stage_id})
    return f"Deal {deal_id} movido para o estágio '{stage_id}'."


@mcp.tool()
def list_stages(pipeline_id: int = 0) -> str:
    """Lista os estágios disponíveis no funil. pipeline_id=0 lista o funil padrão."""
    stages = client.get_stages(pipeline_id if pipeline_id else None)
    if not stages:
        return "Nenhum estágio encontrado."
    lines = ["Estágios disponíveis:"]
    for s in stages:
        lines.append(f"• {s.get('STATUS_ID')} — {s.get('NAME')}")
    return "\n".join(lines)


@mcp.tool()
def add_comment(deal_id: int, comment: str) -> str:
    """Adiciona uma nota/comentário a um deal."""
    activity_id = client.add_comment(deal_id, comment)
    return f"Comentário adicionado ao deal {deal_id}. Atividade ID: {activity_id}"


@mcp.tool()
def add_task(deal_id: int, subject: str, description: str = "", deadline: str = "") -> str:
    """
    Adiciona uma tarefa a um deal.
    deadline deve estar no formato YYYY-MM-DDTHH:MM:SS+HH:MM.
    """
    activity_id = client.add_task(deal_id, subject, description, deadline)
    return f"Tarefa '{subject}' adicionada ao deal {deal_id}. Atividade ID: {activity_id}"


@mcp.tool()
def list_pipelines() -> str:
    """Lista todos os funis (pipelines) de deals disponíveis."""
    pipelines = client.list_pipelines()
    if not pipelines:
        return "Apenas o funil padrão (ID: 0) está disponível."
    lines = ["Funis disponíveis:"]
    for p in pipelines:
        lines.append(f"• ID: {p.get('ID')} — {p.get('NAME')}")
    return "\n".join(lines)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
