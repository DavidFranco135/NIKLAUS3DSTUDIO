# 3D AI Studio (nome provisório)

Plataforma SaaS multi-tenant de Inteligência Artificial para produção de impressão 3D — um "copiloto de produção 3D" que permite criar, converter, reparar, precificar e produzir peças 3D via chat, texto ou imagem, e administrar todo o negócio de impressão 3D (clientes, pedidos, estoque, impressoras, financeiro).

> **Status atual: FASE 18A — SaaS/Billing (infraestrutura interna, sem pagamento real).** Só o que foi combinado antes de implementar: `plans`/`plan_entitlements`/`subscriptions`/`billing_events`, `domain/billing/` puro (máquina de estados da assinatura, entitlements, enforcement de limite), `BillingProvider` + `MockBillingProvider` (sem nenhum código Stripe, nem stub), webhook idempotente, e enforcement real ligado em `max_projects` e `max_storage_mb` — limite atingido responde `402 Payment Required` com corpo estruturado. Toda organização nasce com uma assinatura ao plano semente `dev_unlimited` (**não é um plano comercial**). Trocar de plano/cancelar exige `OWNER`. Painel de frontend em `/billing` (plano, uso, limites, cancelar/trocar de plano). **Nenhuma conta Stripe, credencial real, checkout ou cobrança foi criada** — isso é Fase 18B, sob aprovação explícita. Pendência sinalizada: `Organization.plan` (campo antigo da Fase 1) ficou órfão, superado por `Subscription`/`Plan`. Dashboard (Fase 16), Financeiro (Fase 15), Pedidos (Fase 14), Clientes (Fase 13), Estoque (Fase 12), Calculadora (Fase 11) e Impressoras (Fase 17) continuam reais. O recurso de geração de modelos 3D por IA (texto/imagem) foi removido do produto. Ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (nota "Status na Fase 18A") e [docs/DATABASE.md](docs/DATABASE.md) (seção "Billing").

## Como rodar localmente

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000/api/v1/health
- Web: http://localhost:3000
- MinIO console: http://localhost:9001

Rodar as migrations (dentro do container `api`, ou localmente com o venv de `apps/api`):

```bash
alembic upgrade head
```

## Documentação

| Documento | Conteúdo |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Visão geral, diagramas de componentes/infra, stack, estrutura de pastas, AI Orchestrator, AI Providers, pipeline 3D, Printability Engine, Calculadora, filas/workers, GPU, storage, segurança, multi-tenancy, testes, roadmap, riscos |
| [docs/DATABASE.md](docs/DATABASE.md) | Diagrama ER, schema PostgreSQL completo, tabelas e relacionamentos |
| [docs/AI.md](docs/AI.md) | Como o AI Orchestrator despacha um job, como plugar um provider real, critérios de comparação entre modelos |
| [docs/AI-LICENSES.md](docs/AI-LICENSES.md) | Modelos de IA candidatos, licenças, restrições de uso comercial |

## Princípio fundamental

A plataforma **não** é construída em torno de um único modelo de IA. Todo acesso a modelos de geração/processamento 3D passa por interfaces (`AIProvider`, `Model3DProvider`, `ImageTo3DProvider`, etc.) implementadas por adaptadores específicos de cada motor (Hunyuan3D, TRELLIS, Stable Fast 3D, SPAR3D, CAD paramétrico, ...). Motores podem ser adicionados, removidos ou substituídos sem alterar o restante da aplicação. Ver [AI Orchestrator](docs/ARCHITECTURE.md#7-ai-orchestrator).

## Próximo passo

Revisar `docs/ARCHITECTURE.md` e `docs/DATABASE.md`. Ao final da revisão, responder **"ARQUITETURA APROVADA. POSSO COMEÇAR O MÓDULO 1?"** para iniciar a FASE 1 (Fundação) do roadmap.
