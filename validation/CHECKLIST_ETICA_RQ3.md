# Checklist de Ética — Survey de RQ3 (CEP / Plataforma Brasil)

**Mandato:** Seção 3 do `PLANO_VALIDACAO_COWORK.md` (Agente D, parte de ética) e
`plano.md` (RQ3: survey de motivações com contribuidores reais dos repositórios do
corpus, recrutados por e-mail — e-mails obtidos dos commits minerados). **Data:** 2026-07-27.
**Complementa:** `validation/POLITICA_ANONIMIZACAO.md` (bases legais e datasets) e
`validation/A_REVISAO_LITERATURA.md` §2.4 (Gold & Krinke 2022 e prática MSR).

> **Regra de ouro (não negociável):** **nenhum e-mail de recrutamento é enviado antes do
> parecer de aprovação do CEP.** Gold & Krinke (2022) recomendam tratar o contato como
> coleta de dados com consentimento; a Res. CNS 466/2012 e a 510/2016 exigem apreciação
> ética prévia de pesquisa envolvendo seres humanos. A mineração (já feita) corre sob
> legítimo interesse; a survey é outra atividade, com outra base legal (consentimento) e
> aprovação própria.
>
> Itens que dependem de decisão do orientador estão marcados `[DECISÃO DO ORIENTADOR]`.

---

## 1. Enquadramento normativo

- [ ] **Definir a resolução de enquadramento junto ao CEP institucional**
  `[DECISÃO DO ORIENTADOR]` (qual CEP: o da instituição de vínculo do programa de
  pós-graduação — confirmar; `A_REVISAO_LITERATURA.md` §2.4 anota "confirmar com o
  comitê da instituição qual das duas resoluções enquadra o caso").
  - **Res. CNS 510/2016** (Ciências Humanas e Sociais) é o enquadramento natural: survey
    de opinião/percepção com profissionais, sem intervenção clínica, risco mínimo.
  - **Atenção ao art. 1º, parágrafo único, da 510/2016:** pesquisa de opinião pública
    "com participantes não identificados" é dispensada de registro — **essa dispensa NÃO
    se aplica aqui**, porque os participantes são identificados no recrutamento (e-mail
    extraído de commit, vinculado a nome/login). Não planejar com base na dispensa.
  - A Res. CNS 466/2012 permanece referência supletiva (TCLE, retenção de dados por 5
    anos — item XI.2.f).
- [ ] Registrar no projeto que o estudo é de **risco mínimo** (questionário voluntário
  sobre prática profissional; sem populações vulneráveis; sem dados sensíveis do art. 5º,
  II da LGPD), mas com o risco específico de **quebra de confidencialidade** — e como é
  mitigado (pseudonimização, separação identidade/respostas, `POLITICA_ANONIMIZACAO.md`).

## 2. Documentos para submissão na Plataforma Brasil

- [ ] **Cadastro** do pesquisador e do orientador na Plataforma Brasil (currículo Lattes
  vinculado); folha de rosto assinada pela instituição proponente.
- [ ] **Projeto de pesquisa detalhado**, incluindo: objetivos (RQ3 e ligação com RQ1/RQ2),
  justificativa, **como os contatos foram obtidos** (mineração de metadados públicos de
  commits sob legítimo interesse — citar Gold & Krinke 2022 e a política de anonimização),
  critérios de inclusão dos convidados, tamanho esperado da amostra e taxa de resposta
  típica de surveys MSR, procedimento de recrutamento (Seção 4 abaixo), análise prevista
  (Likert + análise temática do campo aberto — codebook TA com 2 codificadores, conforme
  P9 de `A_REVISAO_LITERATURA.md`), riscos e mitigação.
- [ ] **TCLE / Termo de Consentimento** em formato eletrônico (ver Seção 5).
- [ ] **Instrumento de coleta** (o questionário completo, nos 3 blocos previstos em
  `plano.md`: perfil, escala Likert de 12 itens, campo aberto). O instrumento precisa
  estar **fechado antes da submissão** — mudanças depois exigem emenda. Caminho crítico:
  desenhar o instrumento é pré-requisito da submissão, não tarefa paralela.
- [ ] **Termo de compromisso de confidencialidade e uso de dados**: quem acessa os dados
  (pesquisador + orientador), onde ficam armazenados, separação entre identidade e
  respostas, prazo de guarda (5 anos, CNS 466 XI.2.f) e forma de descarte.
- [ ] **Termo de anuência institucional** (se o CEP exigir para pesquisa sem instituição
  coparticipante, normalmente dispensado para survey online — confirmar no CEP).
- [ ] Cronograma e orçamento (Plataforma Brasil exige ambos, mesmo que orçamento ≈ zero).
- [ ] Anexar a **política de anonimização** como documento complementar — antecipa a
  pergunta óbvia do relator ("como vocês obtiveram esses e-mails e o que acontece com os
  dados?") e demonstra minimização já implementada.

## 3. Base legal e justificativa do contato (o ponto sensível)

O relator vai perguntar: *"vocês podem enviar e-mail para pessoas que não pediram para
ser contatadas?"*. Resposta a constar do projeto:

- [ ] O e-mail foi **tornado público pelo próprio titular** no metadado do commit (prática
  padrão do Git); o uso para convite único de pesquisa é a prática estabelecida em
  estudos MSR com surveys (recrutamento documentado em dezenas de estudos da área; a
  survey de baseline do próprio plano — Xavier et al. 2020 — usou recrutamento análogo).
- [ ] Base legal do **convite**: legítimo interesse para o ato do contato inicial (LGPD
  art. 7º, IX), migrando para **consentimento** (LGPD art. 7º, I; GDPR art. 6(1)(a)) no
  momento em que a pessoa aceita participar — o TCLE eletrônico registra esse
  consentimento. Este é o caminho conservador recomendado por Gold & Krinke (2022).
- [ ] **Normas de contato** (escrever explicitamente no projeto, é o que a literatura MSR
  pratica e o que desarma a objeção de spam):
  - contato **único**, com **no máximo 1 lembrete** após ~2 semanas; nenhuma insistência;
  - identificação completa: nome do pesquisador, orientador, programa/instituição,
    e-mail institucional (`[DECISÃO DO ORIENTADOR]` usar e-mail institucional, não
    pessoal), link para o parecer CEP;
  - explicação de **como o endereço foi obtido** (commit público no repositório X);
  - **opt-out de um clique/uma resposta**, honrado imediatamente e registrado em lista de
    supressão (nunca recontatar, nem em estudos futuros do grupo);
  - nenhum rastreamento de abertura de e-mail; nenhum incentivo financeiro
    (`[DECISÃO DO ORIENTADOR]` se houver sorteio/brinde, precisa constar do projeto e do
    TCLE).
- [ ] **Volume:** informar quantos convites serão enviados e em quantos lotes. Enviar em
  lotes pequenos também reduz risco de o e-mail institucional ser marcado como spam.

## 4. Recrutamento — operacional

- [ ] Lista de convidados extraída do **dataset de trabalho** (nunca do publicável), via
  tabela de correspondência (`POLITICA_ANONIMIZACAO.md` §3.3): filtrar bots (flags do
  Agente C), e-mails `noreply`, autores com opt-out prévio.
- [ ] Amostragem de convidados documentada (ex.: autores de registros UBW confirmados na
  validação, estratificados por categoria A/B/C) — o CEP quer saber quem e por quê.
- [ ] Ferramenta de survey `[DECISÃO DO ORIENTADOR]`: preferir instituição/UE-LGPD-friendly
  (LimeSurvey institucional > Google Forms); onde os dados de resposta residem entra no
  termo de confidencialidade.
- [ ] **Separação identidade ↔ respostas:** o questionário não pede nome/e-mail; o link é
  genérico (não tokenizado por pessoa) ou, se tokenizado para controle de lembrete, o
  mapeamento token↔e-mail fica na custódia restrita e é destruído após o fechamento da
  coleta. `[DECISÃO DO ORIENTADOR]` escolher entre anonimato total das respostas
  (impossibilita lembrete direcionado) vs. token efêmero.

## 5. Consentimento (TCLE eletrônico)

- [ ] Formato: página inicial do questionário com o TCLE integral + caixa de aceite
  obrigatória + opção de **baixar cópia** do termo (orientação da CONEP para meios
  virtuais — Carta Circular nº 1/2021-CONEP/SECNS/MS; citar na submissão).
- [ ] Conteúdo mínimo: objetivo da pesquisa; voluntariedade; ausência de riscos além do
  uso do tempo e quebra de confidencialidade (com mitigação); como o e-mail foi obtido;
  o que será feito com as respostas (agregadas; citações do campo aberto publicadas
  **sem identificação** e parafraseadas se forem buscáveis); prazo de guarda (5 anos) e
  descarte; direito de retirar o consentimento **a qualquer momento, sem justificativa**,
  e como exercê-lo (e-mail ao pesquisador); contatos do pesquisador, do orientador e do
  CEP (endereço/telefone — obrigatório).
- [ ] Deixar claro que retirar consentimento da survey **não** exige remoção do dataset
  minerado (bases legais distintas), mas que o participante **também pode** pedir essa
  remoção — e o TCLE aponta o canal (Seção 7).

## 6. Retenção e guarda dos dados da survey

- [ ] Respostas identificáveis (se houver token): guarda restrita, mesmas regras do
  dataset de trabalho (`POLITICA_ANONIMIZACAO.md` §2.1).
- [ ] Respostas pseudonimizadas para análise; publicação apenas agregada + citações
  não identificáveis.
- [ ] Prazo: **5 anos** após o término (CNS 466/2012, XI.2.f), depois descarte seguro
  documentado.

## 7. Direito de remoção e o efeito no dataset publicado

- [ ] Todo e-mail de convite e o TCLE informam o **canal de remoção** — que cobre três
  pedidos distintos, e o registro interno anota qual foi feito:
  1. **não ser recontatado** → lista de supressão (imediato);
  2. **retirar respostas da survey** → exclusão das respostas antes da análise (ou, se a
     análise já publicada for agregada, declarar que a retirada vale para usos futuros);
  3. **ser removido do dataset minerado** → procedimento da `POLITICA_ANONIMIZACAO.md`
     §6.2: localizar via tabela de correspondência, excluir as linhas do autor do dataset
     de trabalho e de **todas as versões futuras** do dataset publicado (release novo no
     repositório de dados com changelog "N linhas removidas a pedido de titular", sem
     identificar quem); limitação declarada: cópias de versões antigas com DOI fora do
     nosso controle.
- [ ] Manter **registro de pedidos** (data, tipo, atendimento) sem reter os dados
  removidos — prova de conformidade (LGPD art. 18; accountability).

## 8. Prazos realistas de tramitação (caminho crítico)

| Etapa | Estimativa |
|---|---|
| Fechar instrumento + TCLE + projeto detalhado | 3–6 semanas (depende do codebook TA e do aval do orientador) |
| Cadastro e submissão na Plataforma Brasil | 1 semana (a primeira vez sempre trava em documento faltante) |
| Checagem documental do CEP + entrada em pauta | 2–4 semanas (CEPs reúnem-se ~1×/mês) |
| Parecer inicial | 30–60 dias após entrada em pauta |
| **Pendências** (o caso típico, não a exceção — quase toda primeira submissão recebe pendência documental ou de TCLE) | +30–45 dias por rodada |
| **Total realista até "aprovado"** | **3 a 5 meses** |

- [ ] Consequência de planejamento: **submeter ao CEP não depende de a anotação da
  validação estar concluída** — o instrumento pode ser fechado em paralelo à anotação do
  Agente B. Iniciar a preparação da submissão imediatamente após o orientador aprovar o
  instrumento é o único jeito de a survey não virar o gargalo do cronograma
  (`[DECISÃO DO ORIENTADOR]` priorizar o fechamento do instrumento).
- [ ] Emendas (mudar instrumento/alvo depois de aprovado) tramitam de novo: fechar bem
  antes de submeter.

## 9. Resumo das decisões pendentes do orientador

| # | Decisão | Onde |
|---|---|---|
| 1 | CEP/instituição de submissão e enquadramento (510/2016 esperado) | §1 |
| 2 | E-mail institucional de envio; incentivo (se houver) | §3 |
| 3 | Ferramenta de survey e onde residem os dados | §4 |
| 4 | Anonimato total vs. token efêmero para lembrete | §4 |
| 5 | Priorização do fechamento do instrumento (gargalo do cronograma) | §8 |
| 6 | (Herdada da política) modo do `author_hash` e custódia da chave HMAC — afeta o texto do projeto submetido | `POLITICA_ANONIMIZACAO.md` §3.3 |
