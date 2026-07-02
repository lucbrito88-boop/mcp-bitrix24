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


@mcp.tool()
def list_tasks(
    responsible_id: int = 0,
    overdue_only: bool = False,
    due_this_week: bool = False,
    limit: int = 20,
) -> str:
    """Lista tarefas pendentes do Bitrix24. overdue_only=true retorna só as atrasadas. due_this_week=true retorna tarefas com prazo nos próximos 7 dias."""
    tasks = client.list_tasks(
        responsible_id=responsible_id or None,
        overdue_only=overdue_only,
        due_this_week=due_this_week,
    )
    tasks = tasks[:limit]

    if not tasks:
        return "Nenhuma tarefa encontrada."

    lines = [f"Encontradas {len(tasks)} tarefas:\n"]
    for t in tasks:
        deadline = t.get("deadline") or t.get("DEADLINE") or "sem prazo"
        crm_link = t.get("ufCrmTask") or t.get("UF_CRM_TASK") or ""
        lines.append(
            f"• [{t.get('id') or t.get('ID')}] {t.get('title') or t.get('TITLE')}\n"
            f"  Prazo: {deadline} | Status: {t.get('status') or t.get('STATUS')}\n"
            f"  Responsável ID: {t.get('responsibleId') or t.get('RESPONSIBLE_ID')} | CRM: {crm_link}"
        )
    return "\n".join(lines)


@mcp.tool()
def daily_briefing(dormant_days: int = 20) -> str:
    """
    Gera o briefing diário completo de pré-vendas:
    - Principais deals qualificados/forecast
    - Deals sem qualificação (viável, diferencial, RO)
    - Tarefas atrasadas
    - Tarefas desta semana
    - Deals dormentes
    - Fechamento previsto esta semana
    dormant_days: dias sem atividade para considerar dormente (padrão: 20).
    """
    from datetime import date
    today = date.today().strftime("%d/%m/%Y")
    sections = [f"BRIEFING DO DIA — {today}\n"]

    # 1. Principais deals
    top = client.list_top_deals(limit=10)
    if top:
        sections.append(f"PRINCIPAIS DEALS ({len(top)})")
        for d in top:
            valor = f"R$ {float(d.get('OPPORTUNITY') or 0):,.0f}".replace(",", ".")
            closedate = (d.get("CLOSEDATE") or "")[:10]
            sections.append(
                f"  • [{d['ID']}] {d['TITLE']}\n"
                f"    {d['_qualificacao']} | {valor} | fecha: {closedate} | "
                f"Viável: {d['_viavel']} | Diferencial: {d['_diferencial']} | RO: {d['_ro'] or '—'}"
            )
    else:
        sections.append("PRINCIPAIS DEALS\n  Nenhum deal qualificado/forecast.")
    sections.append("")

    # 2. Deals sem qualificação completa
    unqual = client.list_unqualified_deals(limit=15)
    if unqual:
        sections.append(f"DEALS SEM QUALIFICAÇÃO COMPLETA ({len(unqual)})")
        for d in unqual:
            valor = f"R$ {float(d.get('OPPORTUNITY') or 0):,.0f}".replace(",", ".")
            missing = ", ".join(d["_missing"])
            sections.append(
                f"  • [{d['ID']}] {d['TITLE']} | {valor} | faltando: {missing}"
            )
    else:
        sections.append("DEALS SEM QUALIFICAÇÃO COMPLETA\n  Todos os deals em Pipeline estão qualificados.")
    sections.append("")

    # 3. Tarefas atrasadas
    overdue = client.list_tasks(overdue_only=True)
    if overdue:
        sections.append(f"TAREFAS ATRASADAS ({len(overdue)})")
        for t in overdue[:10]:
            deal = (t.get("ufCrmTask") or [""])[0]
            deadline = (t.get("deadline") or "sem prazo")[:10]
            sections.append(f"  • [{t.get('id')}] {t.get('title')} | prazo: {deadline} | deal: {deal}")
    else:
        sections.append("TAREFAS ATRASADAS\n  Nenhuma.")
    sections.append("")

    # 4. Tarefas desta semana
    week_tasks = client.list_tasks(due_this_week=True)
    if week_tasks:
        sections.append(f"TAREFAS DESTA SEMANA ({len(week_tasks)})")
        for t in week_tasks[:10]:
            deal = (t.get("ufCrmTask") or [""])[0]
            deadline = (t.get("deadline") or "")[:10]
            sections.append(f"  • [{t.get('id')}] {t.get('title')} | prazo: {deadline} | deal: {deal}")
    else:
        sections.append("TAREFAS DESTA SEMANA\n  Nenhuma.")
    sections.append("")

    # 5. Deals dormentes
    dormant = client.list_dormant_deals(days=dormant_days)
    if dormant:
        sections.append(f"DEALS DORMENTES — sem atividade há +{dormant_days} dias ({len(dormant)})")
        for d in dormant[:10]:
            modified = (d.get("DATE_MODIFY") or "")[:10]
            valor = f"R$ {float(d.get('OPPORTUNITY') or 0):,.0f}".replace(",", ".")
            sections.append(f"  • [{d['ID']}] {d['TITLE']} | último update: {modified} | {valor}")
    else:
        sections.append(f"DEALS DORMENTES\n  Nenhum deal parado há mais de {dormant_days} dias.")
    sections.append("")

    # 6. Forecast da semana
    closing = client.list_closing_this_week()
    if closing:
        sections.append(f"FECHAMENTO PREVISTO ESTA SEMANA ({len(closing)})")
        for d in closing[:10]:
            closedate = (d.get("CLOSEDATE") or "")[:10]
            valor = f"R$ {float(d.get('OPPORTUNITY') or 0):,.0f}".replace(",", ".")
            sections.append(f"  • [{d['ID']}] {d['TITLE']} | fecha: {closedate} | {valor}")
    else:
        sections.append("FECHAMENTO PREVISTO ESTA SEMANA\n  Nenhum deal.")

    return "\n".join(sections)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
