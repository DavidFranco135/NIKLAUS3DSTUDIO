# 3D AI Studio — AI Orchestrator e Providers

Este documento explica como o pipeline de IA está montado hoje (Fases 4-7) e, principalmente, **como conectar um provider generativo real** quando a infraestrutura de GPU e a licença de um modelo estiverem prontas — sem precisar redesenhar nada.

## Status atual (honesto)

- **NLU**: `MockLLMProvider` — extrai `StructuredSpecification` do prompt por regex determinística, não por um LLM de verdade.
- **CAD paramétrico**: **real** desde a Fase 7 — `Build123DCADProvider` gera geometria de verdade (BREP/OCCT: furos por boolean subtraction, texto embossado, cantos arredondados, containers ocos) via build123d, sem GPU. `MockBoxCADProvider` (Fase 4) ainda existe em `mocks/` mas não está mais registrado — só usado diretamente em testes.
- **Text-to-3D generativo**: dois mocks (`AlwaysFailingMockProvider` + `PlaceholderMockProvider`) que só existem para provar o fallback. Nenhum modelo generativo real integrado.
- **Image-to-3D**: `MockImageTo3DProvider` — **ignora completamente a imagem enviada** e devolve o mesmo cubo placeholder. Deixa isso explícito em `result_metadata.development_only = true` e numa nota de texto, tanto na resposta da API quanto na UI (faixa amarela na página do projeto). **Nunca deve ser apresentado a um usuário como uma reconstrução 3D real.**
- **Mesh repair / textura**: mocks no-op/placeholder, sem nenhuma biblioteca de processamento de malha ainda.
- **4 candidatos reais de IA generativa** (Hunyuan3D, TRELLIS, Stable Fast 3D, SPAR3D) têm *stubs* que implementam a interface de verdade mas levantam `ProviderNotConfiguredError` — decisão explícita de não integrar API paga nem rodar modelo local sem GPU confirmada. **Isso é diferente do CAD paramétrico**: CAD não precisa de um modelo de IA generativa nem de GPU — é geometria determinística — por isso pôde virar real nesta fase enquanto text/image-to-3D continuam mock.

Essa separação (mock de desenvolvimento vs. stub de vendor real vs. provider real) é intencional: o mock prova que o *pipeline* funciona; o stub é o *lugar exato* onde a implementação de verdade entra depois; o provider real (CAD) mostra que essa mesma arquitetura, quando o motor não depende de GPU/licença incerta, vira produção sem nenhuma mudança estrutural.

## Como o AI Orchestrator despacha um job

```
POST /organizations/{org_id}/ai/jobs {prompt?, image_file_id?, project_id?}
        │
        ▼
create_ai_job (application/ai/use_cases.py)
        │  - idempotência (mesmo prompt+imagem+projeto não duplica trabalho)
        │  - se image_file_id: valida metadata da imagem (kind/mime/tamanho/status) e
        │    define task_type=IMAGE_TO_3D direto
        │  - senão: MockLLMProvider extrai spec do prompt → classify_task decide
        │    PARAMETRIC_CAD (dimensões exatas) ou TEXT_TO_GENERATIVE_3D
        ▼
Celery task `process_ai_job` (fila "ai")
        ▼
execute_job (application/ai/orchestrator.py)
        │  1. mark_processing
        │  2. se IMAGE_TO_3D: storage.get_object() lê os bytes da imagem
        │  3. para cada provider em registry.get_providers_for_task(task_type), em ordem:
        │       tenta gerar → sucesso: registra attempt SUCCEEDED e para
        │                    → falha: registra attempt FAILED e tenta o próximo
        │  4. mark_validating → validate_generation_result (sanidade estrutural básica,
        │     não é o Printability Engine real — isso é Fase 9)
        │  5. persiste resultado: storage.put_object + FileAsset + ProjectVersion,
        │     project.active_version_id atualizado
        │  6. mark_completed (com result_metadata do provider) ou mark_failed
```

## Como plugar um provider real (passo a passo)

Isto é o que muda quando, por exemplo, o Stable Fast 3D estiver aprovado (licença confirmada) e houver GPU disponível:

1. **Reconfirmar a licença na fonte oficial** na data da integração (ver checklist em `AI-LICENSES.md`) — condições mudam entre versões.
2. Implementar o corpo real do adapter em `infrastructure/ai_providers/stable_fast_3d/adapter.py` (novo arquivo — os stubs atuais ficam em `stubs/`, um adapter real ganha seu próprio pacote, com o download/carregamento do modelo, inferência, etc.), implementando a mesma interface `ImageTo3DProvider` de `domain/ai/ports.py`. **Nenhuma mudança na interface é necessária** — `generate_from_image(image: ImageInput, spec: StructuredSpecification) -> GenerationResult` já é o contrato.
3. Em `infrastructure/ai_providers/registry.py`, trocar (ou adicionar antes) `StableFast3DProvider()` (o stub) pelo novo adapter real na lista `_IMAGE_TO_3D_PROVIDERS`. Ordem = prioridade de fallback.
4. Se o modelo precisar de GPU dedicada, o `ComputeProvider` (ainda não implementado — ver ARCHITECTURE.md §16) entra aqui como uma dependência do adapter, não do orchestrator.
5. Nenhuma mudança em `application/ai/orchestrator.py`, nenhuma mudança nas rotas HTTP, nenhuma mudança no frontend — é exatamente o propósito da abstração `AIProvider`.
6. Atualizar `AI-LICENSES.md`: mudar o status do modelo de "Stub" para "Integrado" com data e responsável.
7. Adicionar testes de contrato contra o adapter real (fora do CI padrão se exigir GPU — ver ARCHITECTURE.md §21) e manter os testes existentes contra o mock/stub intactos.

## Antes de escolher o primeiro modelo real: critérios de comparação

Nenhuma decisão foi tomada ainda — esta tabela é o template a preencher quando chegar a hora, não uma recomendação.

| Critério | Hunyuan3D | TRELLIS | Stable Fast 3D | SPAR3D | (futuro candidato) |
|---|---|---|---|---|---|
| Licença exata (link para a fonte, reconfirmada na data) | — | — | — | — | — |
| Uso comercial permitido nas condições da plataforma? | — | — | — | — | — |
| Requisitos de GPU/VRAM (mínimo e recomendado) | — | — | — | — | — |
| Qualidade da geometria gerada (avaliação própria) | — | — | — | — | — |
| Adequação para impressão 3D (watertight, espessura mínima, etc.) | — | — | — | — | — |
| Velocidade de geração (segundos por peça, no hardware alvo) | — | — | — | — | — |
| Execução local viável (self-hosting) vs. exige API do detentor | — | — | — | — | — |
| Custo de infraestrutura estimado (GPU própria vs. cloud sob demanda) | — | — | — | — | — |

Preenchimento e decisão final ficam para quando houver infraestrutura de GPU adequada disponível para os testes — ver `AI-LICENSES.md` para o checklist de licença que precisa ser fechado antes de qualquer integração real, independentemente do resultado desta comparação.

## Documentos relacionados

- [AI-LICENSES.md](AI-LICENSES.md) — checklist de licença obrigatório por modelo, status atual de cada stub.
- [ARCHITECTURE.md §8-9](ARCHITECTURE.md#8-ai-orchestrator) — desenho original do AI Orchestrator e das interfaces de provider.
- [DATABASE.md](DATABASE.md) — schema de `ai_jobs`/`ai_job_attempts`.
