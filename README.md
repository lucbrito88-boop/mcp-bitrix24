# Bitrix24 MCP Server

MCP Server que integra o CRM Bitrix24 ao Claude, permitindo gerenciar deals diretamente via linguagem natural.

## O que você pode fazer

Após configurar, você pode pedir ao Claude coisas como:

- *"Liste meus deals em aberto"*
- *"Mostre os detalhes do deal 123"*
- *"Crie um deal chamado 'Proposta NTSec' no valor de R$ 50.000"*
- *"Mova o deal 456 para a etapa de negociação"*
- *"Adicione uma nota no deal 789: reunião realizada com sucesso"*
- *"Quais são os estágios do meu funil?"*
- *"Liste minhas tarefas atrasadas"*
- *"Quais tarefas estão pendentes para o responsável 42?"*

## Ferramentas disponíveis

| Ferramenta | Descrição |
|---|---|
| `list_deals` | Lista deals com filtros por estágio, responsável ou título |
| `get_deal` | Retorna todos os detalhes de um deal pelo ID |
| `create_deal` | Cria um novo deal no CRM |
| `update_deal` | Atualiza campos de um deal existente |
| `move_deal_stage` | Move um deal para outro estágio do funil |
| `list_stages` | Lista os estágios disponíveis no funil |
| `add_comment` | Adiciona nota/comentário a um deal |
| `add_task` | Cria uma tarefa vinculada a um deal |
| `list_tasks` | Lista tarefas pendentes; filtra por responsável ou só atrasadas |
| `list_pipelines` | Lista os funis de deals disponíveis |

## Pré-requisitos

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (gerenciador de pacotes)
- Claude Code CLI
- Conta no Bitrix24 com acesso à API (webhook configurado)

## Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/bitrix24-mcp.git
cd bitrix24-mcp
```

### 2. Crie o ambiente virtual e instale as dependências

```bash
uv venv .venv
uv pip install -r requirements.txt
```

### 3. Configure o webhook do Bitrix24

Copie o arquivo de exemplo e adicione sua URL:

```bash
cp .env.example .env
```

Edite o `.env`:

```env
BITRIX24_WEBHOOK_URL=https://seudominio.bitrix24.com.br/rest/USER_ID/WEBHOOK_TOKEN/
```

**Como obter o webhook no Bitrix24:**
1. Acesse seu Bitrix24 → Configurações → Integrações → Webhooks de entrada
2. Crie um webhook com permissões de CRM (leitura e escrita)
3. Copie a URL gerada

### 4. Configure o MCP Server no Claude Code

Adicione ao seu `.claude/settings.json` (ou `~/.claude/settings.json` para uso global):

```json
{
  "mcpServers": {
    "bitrix24": {
      "command": "/caminho/para/bitrix24-mcp/.venv/Scripts/python.exe",
      "args": ["/caminho/para/bitrix24-mcp/server.py"]
    }
  }
}
```

> **Windows:** use `.venv\Scripts\python.exe`  
> **Mac/Linux:** use `.venv/bin/python`

### 5. Reinicie o Claude Code

Feche e reabra o Claude Code. O MCP server `bitrix24` deve aparecer disponível.

## Estrutura do projeto

```
bitrix24-mcp/
├── src/mcp_bitrix24/
│   ├── server.py        # MCP server — define as ferramentas expostas ao Claude
│   └── client.py        # Wrapper da API REST do Bitrix24
├── pyproject.toml       # Configuração do pacote (PyPI)
├── requirements.txt     # Dependências Python
├── .env.example         # Template de configuração
└── .gitignore
```

## Dependências

- [`mcp`](https://github.com/anthropics/mcp) — SDK do Model Context Protocol
- [`httpx`](https://www.python-httpx.org/) — cliente HTTP assíncrono
- [`python-dotenv`](https://github.com/theskumar/python-dotenv) — carregamento do `.env`

## Segurança

- O arquivo `.env` está no `.gitignore` — nunca commite suas credenciais
- O webhook do Bitrix24 deve ter permissões de CRM e Tarefas (task)
- Recomenda-se criar um usuário de serviço dedicado no Bitrix24 para o webhook
