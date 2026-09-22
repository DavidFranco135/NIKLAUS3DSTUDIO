# 3D AI Studio (nome provisório)

Plataforma SaaS multi-tenant de Inteligência Artificial para produção de impressão 3D — um "copiloto de produção 3D" que permite criar, converter, reparar, precificar e produzir peças 3D via chat, texto ou imagem, e administrar todo o negócio de impressão 3D (clientes, pedidos, estoque, impressoras, financeiro).

> **Status atual: FASE 10 — Slicer Engine (abstração + stubs, sem binário instalado).** `SlicerProvider` (`domain/ai/ports.py`) e os DTOs `PrinterProfile`/`MaterialProfile`/`SliceResult` (`domain/slicing/`) estão prontos, com `PrusaSlicerCLIProvider` e `OrcaSlicerCLIProvider` (`infrastructure/slicers/`) implementando a interface real — mas **nenhum binário de slicer foi baixado, instalado ou executado nesta máquina**: PrusaSlicer e OrcaSlicer são AGPL-3.0, e essa licença tem cláusula de "uso via rede" que precisa de confirmação jurídica antes de expor fatiamento como parte de um SaaS (ver `AI-LICENSES.md`). Decisão explícita: ficar no mesmo padrão *stub* já usado para os modelos generativos (Hunyuan3D/TRELLIS/Stable Fast 3D/SPAR3D na Fase 5) até essa confirmação existir. CAD paramétrico (Fase 7), Mesh Processing (Fase 8) e Printability (Fase 9) continuam reais; Text-to-3D e Image-to-3D continuam mock. Ver [docs/AI.md](docs/AI.md) e [docs/AI-LICENSES.md](docs/AI-LICENSES.md).
>
> **Limitação conhecida deste ambiente:** esta máquina não tem Docker instalado, então não há Redis/MinIO rodando de verdade aqui. Os jobs de IA rodam em modo síncrono (`CELERY_TASK_ALWAYS_EAGER=true`) para dev/testes sem broker — o mesmo código do worker, só sem fila de verdade por trás. O caminho de sucesso completo (job → validação de malha → arquivo salvo → nova versão) está coberto pelos testes automatizados; testado manualmente aqui foi até a persistência (storage indisponível), confirmando que a geração e a validação real de malha funcionam de ponta a ponta. Para rodar com Redis/MinIO de verdade, use `docker compose up` (Docker Desktop/WSL).

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
