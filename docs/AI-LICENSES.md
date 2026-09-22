# 3D AI Studio — Modelos de IA candidatos e licenças

**Regra fundamental do projeto: nenhum modelo é integrado à plataforma sem que este checklist esteja preenchido e revisado.** "Open source" ou "open weight" **não** significa automaticamente "uso comercial livre" — cada linha abaixo precisa de verificação humana da licença vigente **no momento da integração**, pois licenças de modelos de IA mudam de versão para versão (ex. cláusulas de "uso comercial até N usuários/receita", exigência de atribuição, restrição de hospedagem de output).

> Este documento reflete o entendimento no momento da elaboração da arquitetura (2026), a partir de conhecimento geral sobre esses projetos. **Antes de integrar qualquer modelo, a equipe deve reconfirmar a licença diretamente na fonte oficial (repositório/model card) na data da integração**, pois condições podem ter mudado.

## Checklist obrigatório por modelo (preencher antes de qualquer integração)

- [ ] Nome exato do modelo e versão/checkpoint usado
- [ ] Licença exata (nome + link para o texto oficial, não para um resumo de terceiros)
- [ ] Uso comercial permitido? Sob quais condições?
- [ ] Redistribuição do modelo/pesos permitida?
- [ ] Hospedagem própria (self-hosting) permitida, ou exige uso via API do detentor?
- [ ] Restrições sobre o **output** gerado (ex. exigência de atribuição no produto final, restrição de uso do output gerado)?
- [ ] Limitações por escala (usuários, receita, região)?
- [ ] Dependências de terceiros embutidas no modelo com licenças próprias (ex. pesos derivados de outro modelo com licença mais restritiva)?
- [ ] Aprovação registrada (responsável + data)

## Candidatos — Image-to-3D / Text-to-3D generativo

*(Status na Fase 5: cada modelo abaixo tem um **adapter stub** em `infrastructure/ai_providers/stubs/` — implementa a interface do provider (`ImageTo3DProvider`/`TextTo3DProvider`) e está registrado no `registry.py`, mas todo método levanta `ProviderNotConfiguredError` em vez de chamar um modelo de verdade. Isso existe para que a troca por um adapter real, quando a infra de GPU e a licença estiverem prontas, não exija tocar no AI Orchestrator nem no restante do sistema — só implementar o método do stub correspondente.)*

| Modelo | Fornecedor/Origem | Licença (a reconfirmar na integração) | Uso comercial | Status | Observações |
|---|---|---|---|---|---|
| **Hunyuan3D** (2 / 2.x) | Tencent | Licença própria "Tencent Hunyuan Community License" (não é MIT/Apache) | Historicamente com condições/restrições próprias — **verificar cláusulas de escala de usuários e região antes de assumir uso comercial livre** | Stub (`stubs/hunyuan3d.py`) | Pesos e código costumam ter licenças separadas; verificar as duas. Único candidato com stub para as duas interfaces (image-to-3D **e** text-to-3D) |
| **TRELLIS** | Microsoft Research | Licença de pesquisa (frequentemente MIT no código, mas pesos podem ter condição própria) | **Verificar se os pesos publicados têm a mesma licença do código** — projetos de research lab frequentemente restringem uso comercial dos pesos mesmo com código MIT | Stub (`stubs/trellis.py`) | Checar model card no momento da integração |
| **Stable Fast 3D** | Stability AI | Stability AI Community License (historicamente exige licença comercial paga acima de certa receita anual) | **Não assumir gratuito para uso comercial em escala** — Stability costuma exigir "Stability AI Membership" para empresas acima de um limite de receita | Stub (`stubs/stable_fast_3d.py`) | Reconfirmar termos vigentes antes de qualquer uso em produção |
| **SPAR3D** | Stability AI | Mesma família de licenciamento da Stability AI (ver acima) | Mesma ressalva de limite de receita/membership | Stub (`stubs/spar3d.py`) | Reconfirmar |
| Modelos futuros (TripoSR, Zero123++, InstantMesh, etc.) | Diversos | Variam por projeto | A verificar caso a caso | Sem stub ainda | Nenhum entra na lista de providers ativos sem preencher este checklist |

**Decisão explícita da Fase 5 (registrada aqui para não se perder):** nenhuma API paga de terceiros foi integrada e nenhum modelo foi baixado/executado localmente nesta fase — esta máquina de desenvolvimento não tem GPU confirmada. Quando a infraestrutura de GPU adequada existir, a prioridade é integrar primeiro modelos open source/open weight cuja licença permita o uso comercial pretendido, verificando o checklist acima modelo a modelo antes de qualquer integração real.

**Fase 6:** o fluxo de upload de imagem → job → orquestrador ficou real e testado de ponta a ponta (ver [AI.md](AI.md)), mas continua usando `MockImageTo3DProvider` (ignora a imagem, devolve um cubo placeholder, rotulado `development_only` na API/UI). Os 4 stubs acima seguem inalterados — nenhum foi promovido a integração real. Ver [AI.md](AI.md) para os critérios de comparação a preencher antes de escolher o primeiro modelo de verdade.

## Candidatos — Ferramentas determinísticas (não-IA generativa, risco de licença baixo mas ainda a confirmar)

| Ferramenta | Licença | Uso comercial | Status | Observações |
|---|---|---|---|---|
| **build123d** (baseado em OCCT) | Apache-2.0 / LGPL (OCCT/OCP) | Sim | **Integrado (Fase 7)** — `infrastructure/ai_providers/real/build123d_cad.py` | Roda server-side, em processo Python puro (sem subprocess) — verificar forma de linkagem/distribuição se algum dia for embutido em binário distribuído ao cliente (não é o caso aqui) |
| **CadQuery** (alternativa, também OCCT) | Apache-2.0 / LGPL (OCCT) | Sim | Não usado (build123d escolhido) | Mesma base OCCT do build123d; considerar se build123d apresentar limitação futura |
| **OpenSCAD** | GPL-2.0 (o programa) | Sim, como ferramenta externa via subprocess (não linkamos a lib no nosso binário) | Não usado (build123d escolhido na Fase 7) | Como é invocado via CLI (processo separado), não gera obrigação de copyleft sobre o código da plataforma — confirmar com jurídico se houver dúvida sobre o modelo de invocação |
| **Blender** (headless) | GPL-2.0/3.0 | Sim, como ferramenta externa via subprocess | Não usado ainda | Mesma lógica do OpenSCAD — uso como processo externo, scripts próprios `.py` não precisam ser GPL |
| **trimesh** | MIT | Sim | **Integrado (Fase 8)** — `domain/mesh/operations.py`, `TrimeshMeshRepairProvider` | Roda em processo Python puro, sem GPU |
| **networkx** | BSD-3-Clause (a reconfirmar na fonte oficial no momento da integração, como todo o resto desta lista) | Sim | **Integrado (Fase 8)** — dependência do `trimesh.repair.fill_holes` | Biblioteca de grafos, sem restrição relevante conhecida |
| **fast-simplification** | MIT (a reconfirmar) | Sim | **Integrado (Fase 8)** — usado por `trimesh.simplify_quadric_decimation` | Wrapper Python/C++ para decimação de malha (projeto PyVista) |
| **rtree** | MIT (wrapper de `libspatialindex`, também MIT) | Sim | **Integrado (Fase 9)** — usado por `trimesh.ray.intersects_location` (`domain/printability/thin_walls.py`) | Índice espacial para acelerar ray-casting; roda em processo Python puro, sem GPU |
| **Open3D** | MIT | Sim | Não usado ainda | Sem restrição relevante — trimesh cobriu as operações necessárias na Fase 8 |
| **PyMeshLab** | GPL-3.0 | Sim como ferramenta externa; **atenção especial** se for importado como lib Python dentro do mesmo processo do backend (pode implicar copyleft sobre o processo que a importa) | Não usado ainda | Recomenda-se isolar em worker próprio/processo separado, nunca importar dentro do processo principal da API |
| **PrusaSlicer** (CLI) | AGPL-3.0 | Sim, como binário externo via subprocess/CLI | Não usado ainda | AGPL tem cláusula de "uso via rede" — como é executado como ferramenta local pelo worker (não é modificado e redistribuído como serviço de terceiro), risco é baixo, mas **jurídico deve confirmar** antes de produção, especialmente se a plataforma for oferecida como SaaS público |
| **OrcaSlicer** (CLI) | AGPL-3.0 | Mesma observação do PrusaSlicer | Não usado ainda | Idem |
| **Cura Engine** | LGPL-3.0 (CuraEngine) / AGPL (Cura app completo) | Sim, via CLI do `CuraEngine` isoladamente | Não usado ainda | Preferir o `CuraEngine` (motor) e não a aplicação completa do Cura |

**Fase 7:** build123d foi instalado (`pip install build123d`) e testado nesta máquina — funciona sem GPU, sem binário externo, sem subprocess (roda dentro do processo Python do worker). Boolean ops (furos), fillets/cantos arredondados e extrusão de texto (embossing) confirmados funcionando. Substituiu o `MockBoxCADProvider` como o provider ativo de `PARAMETRIC_CAD`.

## Candidatos — LLM para NLU / extração de especificação

| Fornecedor | Modelo | Licença/Termos | Observações |
|---|---|---|---|
| Anthropic | Claude (via API) | Termos de serviço comerciais da Anthropic (não é "licença" de modelo aberto — é uso via API paga) | Sem preocupação de licença de peso/redistribuição pois não hospedamos o modelo; sim de **termos de uso de dados** (verificar retenção/treinamento com dados de clientes, exigir configuração de não-retenção se disponível) |
| Alternativa self-hosted (ex. Llama, Mistral) | Varia (Llama Community License, Apache-2.0, etc.) | A verificar por versão | Só considerar se custo de API se tornar proibitivo; cada versão do Llama tem condições próprias (ex. limite de usuários ativos mensais em versões antigas) |

## Regra de fallback de licença

Se, no momento da integração, a licença de um modelo candidato não permitir uso comercial nas condições da plataforma (SaaS multi-tenant cobrando dos clientes), esse modelo **não é integrado** — a arquitetura de `AIProvider` permite substituí-lo por outro candidato ou por CAD paramétrico sem impacto no restante do sistema. Isso é o propósito central da abstração descrita no [ARCHITECTURE.md](ARCHITECTURE.md#2-princípio-de-independência-de-modelo-de-ia).

## Fontes de mensagem gratuita vs. custo de infraestrutura

A plataforma **nunca** anuncia "IA ilimitada gratuita". Toda comunicação de produto deve separar claramente:

1. O modelo/software usado é gratuito ou de licença aberta (quando for o caso), **e**
2. O custo computacional (GPU, storage, banda) de rodar esse modelo é sempre um custo real da infraestrutura, refletido no plano de billing do usuário.
