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

| Modelo | Fornecedor/Origem | Licença (a reconfirmar na integração) | Uso comercial | Observações |
|---|---|---|---|---|
| **Hunyuan3D** (2 / 2.x) | Tencent | Licença própria "Tencent Hunyuan Community License" (não é MIT/Apache) | Historicamente com condições/restrições próprias — **verificar cláusulas de escala de usuários e região antes de assumir uso comercial livre** | Pesos e código costumam ter licenças separadas; verificar as duas |
| **TRELLIS** | Microsoft Research | Licença de pesquisa (frequentemente MIT no código, mas pesos podem ter condição própria) | **Verificar se os pesos publicados têm a mesma licença do código** — projetos de research lab frequentemente restringem uso comercial dos pesos mesmo com código MIT | Checar model card no momento da integração |
| **Stable Fast 3D** | Stability AI | Stability AI Community License (historicamente exige licença comercial paga acima de certa receita anual) | **Não assumir gratuito para uso comercial em escala** — Stability costuma exigir "Stability AI Membership" para empresas acima de um limite de receita | Reconfirmar termos vigentes antes de qualquer uso em produção |
| **SPAR3D** | Stability AI | Mesma família de licenciamento da Stability AI (ver acima) | Mesma ressalva de limite de receita/membership | Reconfirmar |
| Modelos futuros (TripoSR, Zero123++, InstantMesh, etc.) | Diversos | Variam por projeto | A verificar caso a caso | Nenhum entra na lista de providers ativos sem preencher este checklist |

## Candidatos — Ferramentas determinísticas (não-IA generativa, risco de licença baixo mas ainda a confirmar)

| Ferramenta | Licença | Uso comercial | Observações |
|---|---|---|---|
| **OpenSCAD** | GPL-2.0 (o programa) | Sim, como ferramenta externa via subprocess (não linkamos a lib no nosso binário) | Como é invocado via CLI (processo separado), não gera obrigação de copyleft sobre o código da plataforma — confirmar com jurídico se houver dúvida sobre o modelo de invocação |
| **build123d / CadQuery** (baseado em OCCT) | Apache-2.0 / LGPL (OCCT) | Sim | OCCT é LGPL — verificar forma de linkagem/distribuição se algum dia for embutido em binário distribuído ao cliente (não é o caso aqui, roda server-side) |
| **Blender** (headless) | GPL-2.0/3.0 | Sim, como ferramenta externa via subprocess | Mesma lógica do OpenSCAD — uso como processo externo, scripts próprios `.py` não precisam ser GPL |
| **trimesh** | MIT | Sim | Sem restrição relevante |
| **Open3D** | MIT | Sim | Sem restrição relevante |
| **PyMeshLab** | GPL-3.0 | Sim como ferramenta externa; **atenção especial** se for importado como lib Python dentro do mesmo processo do backend (pode implicar copyleft sobre o processo que a importa) | Recomenda-se isolar em worker próprio/processo separado, nunca importar dentro do processo principal da API |
| **PrusaSlicer** (CLI) | AGPL-3.0 | Sim, como binário externo via subprocess/CLI | AGPL tem cláusula de "uso via rede" — como é executado como ferramenta local pelo worker (não é modificado e redistribuído como serviço de terceiro), risco é baixo, mas **jurídico deve confirmar** antes de produção, especialmente se a plataforma for oferecida como SaaS público |
| **OrcaSlicer** (CLI) | AGPL-3.0 | Mesma observação do PrusaSlicer | Idem |
| **Cura Engine** | LGPL-3.0 (CuraEngine) / AGPL (Cura app completo) | Sim, via CLI do `CuraEngine` isoladamente | Preferir o `CuraEngine` (motor) e não a aplicação completa do Cura |

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
