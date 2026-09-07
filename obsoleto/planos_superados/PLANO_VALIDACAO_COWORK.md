# Plano de Validação do Dataset UBW — Orquestração via Claude Cowork

Documento de trabalho para dividir, entre agentes do Cowork, a etapa de
validação do dataset coletado: medir falsos positivos, verificar se a
mineração foi feita corretamente, anonimizar para publicação e ancorar cada
decisão na literatura de SATD e de fora dela. A anotação humana em si
continua sendo humana. Os agentes preparam, medem, revisam e documentam o
trabalho ao redor dela.

---

## 1. O que já existe (não refazer)

Antes de delegar qualquer coisa, o ponto de partida é o que o repositório já
tem. Todo agente deve ler estes arquivos antes de propor algo novo:

| Artefato | O que cobre |
|---|---|
| `ANNOTATION_GUIDELINE.md` | Protocolo de anotação: as 5 condições de `is_ubw`, definição das categorias A/B/C, exemplos positivos/negativos por artefato, regras de desempate, cheat sheet |
| `plano.md` (Seção 5) | Desenho da validação: amostra estratificada (~385, 95%/5%), 2 anotadores + desempate, κ de Cohen e AC1 de Gwet, LLM como pré-triagem |
| `scripts/03_metrics_llm_triage.py` | Já implementa: pré-triagem LLM (Anthropic/OpenRouter), amostragem estratificada, κ e AC1, limiar de descarte da triagem (κ < 0,61) |
| `ubw/schema.py` | Schema de coleta; campos de autor (`author_name/login/email` brutos + `author_hash` SHA-256) e a nota sobre pseudonimização vs. anonimização |
| `LEXICO.md` | As 25 expressões e as três categorias, com as marcações de risco (⚠) |
| `RESULTADOS_ROUND_*.md` | Histórico de contaminação por arquivo gerado/build (já corrigido) e números por rodada |

**Estado dos dados, verificar antes de amostrar:** a coleta da fatia A ainda
está rodando (`data/full_run/`, sem `COLLECTION_COMPLETE`); a fatia B foi
coletada em outra máquina. A amostragem de validação só deve ser fechada
sobre o dataset consolidado das duas fatias. Antes disso, qualquer amostra é
provisória e serve só para calibrar o processo.

---

## 2. Princípios que valem para todos os agentes

Humano é o ground truth. LLM entra como pré-triagem e como sinal de
discordância, nunca como rótulo final para as métricas de precisão e
concordância. Isso já está no guideline (Seção 2) e no script 03.

A precisão léxica bruta é medida antes da triagem LLM, separando a precisão
do filtro léxico da precisão do pipeline completo. Sem essa separação não dá
para saber se um ganho de precisão veio do léxico ou do LLM (plano.md,
Seção 5.1).

Existem dois datasets distintos: um de trabalho, com PII, usado para
contatar autores na survey de RQ3, e um publicável, sem os campos brutos de
autor. O primeiro nunca é publicado.

O léxico não muda no meio da validação. Ele foi fechado e aprovado pelo
orientador, e qualquer proposta de mudança sai como recomendação para o
orientador decidir, não como alteração unilateral de um agente (guideline,
Seção 7.5).

Toda decisão de método tem uma âncora na literatura, ou é registrada como
decisão própria explícita quando não há precedente.

---

## 3. Os agentes e a delegação

Quatro agentes delegáveis mais a sua orquestração. B e C rodam em paralelo;
A alimenta todos; D pode começar cedo porque não depende da anotação.

| Agente | Foco | Depende de | Modelo | Entrega |
|---|---|---|---|---|
| A · Revisor de Literatura | Como o campo valida e anota dados minerados | — | Fable (coleta em Sonnet, síntese em Fable) | Síntese comparativa + recomendações |
| B · Auditor de Falsos Positivos | Validade de construto (o item é UBW mesmo?) | A | Sonnet (partes mecânicas em Haiku) | Amostras de anotação, precisão por expressão/categoria/artefato, gold set |
| C · Auditor de Mineração | Validade interna (a coleta está correta?) | A (parcial) | Sonnet | Relatório de qualidade de dados + flags de anomalia |
| D · Anonimização & Ética | PII, pseudonimização, LGPD/ética para RQ3 | A (parcial) | Sonnet para o script, Fable para política e ética | Política de anonimização + script de geração do dataset publicável |

**Atribuição de modelo.** O modelo é escolhido por agente, no frontmatter da
definição de cada um ou no lançamento. A regra de corte é verificabilidade,
não tamanho do agente: quanto mais mecânica e checável a tarefa, mais barato
pode ser o modelo.

Fable planeja, escreve as specs delegáveis com entrada exata, formato de
saída e critério de "pronto", e fica com a síntese pesada e a prosa que pode
entrar na dissertação, como o agente A e a política de ética do D. Sonnet
fica com o executável verificável: a forense de dados do agente C e os
scripts do B e do D. Haiku fica com o mais mecânico e fechado: rodar a
amostragem, computar κ/AC1, gerar os batches. Humano fica com a anotação e
o aval de ética, que não é modelo nenhum.

Um cuidado que vale manter: a prosa que vai pra dissertação fica no modelo
forte, mesmo quando o resto do agente é mecânico. Sonnet ou Haiku coletam e
rodam; Fable escreve a versão final. E cada unidade delegada a modelo menor
precisa de um verificador, como o gold set do B ou as flags numéricas do C,
ou um teste no caso de código. Sem isso, delegar vira aposta.

---

### Agente A — Revisor de Literatura (metodologia de validação)

A validação manual é trabalhosa e tem que ser feita com cuidado, então vale
ver como os outros fazem antes de gastar esforço humano. Este agente cobre
duas trilhas.

**Trilha 1 — SATD.** Como os trabalhos de SATD validam a coleta e anotam.
Cobre o protocolo de calibração e concordância de Maldonado & Shihab (2015),
Awon (2024, κ = 0,926) e Bavota & Russo (2016, amostra ~385); a validade de
remoção segundo Zampetti et al. (2018), que reportam 20 a 50% das remoções
de SATD como acidentais, e como eles distinguem remoção real de deleção de
arquivo; os desenhos multi-artefato recentes de Li et al. (2023), do
SATDAUG/Sutoyo (MSR'24) e do multi-artifact de scientific software (arXiv
2601.10850), olhando quantos anotadores, que amostra e que métrica de
concordância cada um usa; e a revisão sistemática de detecção de SATD
(arXiv 2312.15020), pra confirmar que ninguém mede precisão de "resignação
funcional" isoladamente.

**Trilha 2 — Fora de SATD.** Como a engenharia de software empírica e a
pesquisa qualitativa validam anotação manual em geral. Cobre confiabilidade
inter-avaliador em Landis & Koch (1977) e Gwet (2008), incluindo o paradoxo
do κ em classes desbalanceadas, que é o motivo de reportar AC1 em paralelo;
boas práticas de anotação em estudos de mineração de repositórios, como se
constrói guideline, calibração, tamanho de amostra e gold set; análise
temática e codificação qualitativa (Braun & Clarke e afins), relevante
porque a survey de RQ3 vai codificar respostas abertas, não só rotular
texto; e anonimização/pseudonimização de dados de commit em estudos de
mineração, incluindo o que LGPD/GDPR exigem ao contatar desenvolvedores,
o que alimenta a trilha do agente D.

**Entrega:** um único `.md` com uma tabela "o que o campo faz × o que o UBW
já faz × lacuna/recomendação", mais uma lista curta e priorizada de ajustes
ao protocolo atual. Não é uma revisão exaustiva, é um benchmark para
calibrar o esforço humano. Reaproveitar a memória de literatura já levantada
(os papers de `RESULTADOS_*` e do related work) em vez de começar do zero.

---

### Agente B — Auditor de Falsos Positivos (validade de construto)

Responde "quantos dos candidatos coletados são UBW de verdade?" e prepara o
material para os anotadores humanos. Não substitui o anotador, reduz e
organiza o trabalho dele.

**Estratégia de amostragem** sobre o dataset consolidado. Estratificar por
categoria (A/B/C) e tipo de artefato, como no plano. Sobre-amostrar a
categoria C e as expressões marcadas ⚠ (`magic number`, `don't touch`,
`hope everything will work`), já que são raras e de maior risco de falso
positivo, e uma amostra proporcional não daria N suficiente para estimar a
precisão delas com intervalo aceitável. Incluir também near-misses
adversariais de propósito: candidatos que casam a expressão mas
provavelmente são os negativos do guideline, como string de teste, citação
de terceiro, negação ou uso não-técnico. Isso mede especificidade, não só
precisão, e verifica se anotadores e LLM pegam os casos difíceis.

**Execução:** primeiro roda `03_metrics_llm_triage.py llm-triage` para a
pré-triagem, que já marca "incerto" como revisão humana obrigatória e
amostra 15% do resto. Depois gera os batches de anotação a partir do
`annotation_template.csv`, sem vazar o rótulo do LLM para o anotador antes
da decisão dele. Depois da anotação humana, computa precisão por expressão,
por categoria e por artefato, com IC binomial, κ e AC1 entre os dois
anotadores, e em separado o κ entre LLM e humano — se vier abaixo de 0,61 a
triagem LLM é descartada, regra que já está no script. Por fim constrói um
gold set de itens verificados à mão, que vira teste de regressão para
qualquer mudança futura no léxico ou no prompt do LLM.

**Entrega:** os batches prontos, o relatório de precisão e concordância, o
gold set versionado, e uma lista das expressões cuja precisão ficou abaixo
do aceitável. Essa lista é insumo para o orientador decidir sobre o léxico,
não uma instrução para o agente alterá-lo.

**O que continua sendo humano:** a anotação em si, com mínimo de dois
anotadores independentes e desempate. O agente não conta como anotador para
o κ.

---

### Agente C — Auditor de Mineração (validade interna)

Responde "a coleta capturou o que diz que capturou?". É forense de dados
sobre o CSV, independente da anotação.

As checagens, cada uma virando uma flag no relatório com exemplos: sanidade
temporal, olhando `time_to_event_days` negativo, zero ou absurdamente
grande, `removed_at` anterior a `created_at`, e `is_censored` coerente com
`removed_at` nulo ou preenchido. Remoção acidental versus real, seguindo
Zampetti: amostrar eventos de remoção de `code_comment` e checar se a
remoção foi textual genuína ou deleção do arquivo inteiro ou arquivamento
do repositório, casos que deveriam estar censurados, não contados como
remoção. Deduplicação em escala, confirmando que a correção de contaminação
por arquivo gerado ou build, já aplicada nas rodadas menores, segura no
corpus completo — duplicata exata de `body_text` por repositório, e também
entre artefatos, quando a mesma frase aparece como commit_message e depois
como pr_body do mesmo autor. Contas automatizadas, detectando `-bot`,
`[bot]` e o caso recorrente do `pyup-bot`, que traz texto de changelog de
terceiro em PRs de bump de dependência, quantificando e decidindo a política
de excluir ou marcar. Efetividade do filtro de path vendorizado, amostrando
`code_comment` para ver se ainda entra código de `vendor/`, `node_modules/`,
`dist/` ou minificado. E reprodutibilidade, re-rodando a coleta num punhado
de repositórios e conferindo se o resultado bate dentro do esperado, já que
a Search API muda no tempo, o que é justamente por que os SHAs e as
respostas brutas ficam arquivados.

**Entrega:** um `RELATORIO_QUALIDADE_DADOS.md` com cada flag quantificada,
exemplos e recomendação de correção. Correções de código que saírem disso
vão para os scripts, não para o CSV à mão.

---

### Agente D — Anonimização e Ética

Responde "o que pode ser publicado e o que fica restrito?". Pode começar
cedo, não depende da anotação.

Separar os dois datasets: definir e implementar a geração do dataset
publicável, sem `author_name/login/email`, a partir do de trabalho. O
schema já prevê isso via `author_hash`; falta o script de export e a
política escrita. Decidir sobre salt: hoje o `author_hash` é SHA-256 sem
salt, reidentificável por quem tiver a lista de candidatos, que no caso é o
próprio GitHub. Documentar se isso é aceitável como pseudonimização
declarada ou se precisa de salt/HMAC, e registrar o trade-off: com salt,
perde-se a capacidade de ligar o mesmo autor entre registros, capacidade que
RQ3 usa. Levantar a ética e a LGPD para RQ3, já que a survey contata
desenvolvedores reais identificados no dataset — o que o comitê de ética da
instituição exige em termos de consentimento, base legal, retenção e
direito de remoção, e o que a literatura de mineração faz ao contatar
autores; isso conecta com a Trilha 2 do agente A. E verificar PII no
`body_text`, checando se o texto coletado carrega e-mails, nomes ou tokens
embutidos que precisem ser mascarados na versão publicável.

**Entrega:** `POLITICA_ANONIMIZACAO.md`, o script de export do dataset
publicável, e um checklist do que submeter ao comitê de ética.

---

## 4. Sequenciamento

```
A (literatura)  ──┬──> B (falsos positivos)  ──┐
                  ├──> C (mineração)          ──┼──> consolidação (você)
                  └──> D (anonimização/ética) ──┘
```

A vem primeiro, ou em paralelo na frente dos outros, porque calibra o
esforço de B, C e D. B e C rodam em paralelo entre si, um cuidando de
construto e o outro de validade interna. D também roda em paralelo,
precisando só do schema e da trilha de ética de A. O gargalo real é a
anotação humana de B — tudo que os agentes fazem existe para que esse
tempo humano seja gasto só onde importa: itens incertos, near-misses,
categoria C.

---

## 5. Riscos e cuidados

Não tratar o LLM como anotador. Ele pré-tria e sinaliza discordância; o κ
que vale é entre humanos. Se o κ LLM-vs-humano vier baixo, é a triagem que
é descartada, nunca o contrário.

Amostra sobre dataset provisório engana. Fechar as amostras de precisão só
depois de consolidar fatia A e fatia B.

O léxico continua congelado. Precisão baixa de uma expressão é recomendação
ao orientador, não gatilho para o agente reescrever o léxico.

A sobre-amostragem tem que ser corrigida na leitura. Ao reportar precisão
global, ponderar de volta pelos pesos reais das categorias e expressões,
senão o número fica enviesado pela categoria C sobre-representada.

---

## 6. Outros insights (aberto a ajuste)

O gold set funciona como teste de regressão: o conjunto verificado à mão
vira o baseline para qualquer mudança futura de léxico, prompt ou modelo,
medindo se um ajuste melhorou ou piorou sem precisar re-anotar tudo.

Os negativos adversariais medem especificidade. Os near-misses do guideline
não são só ilustração; postos na amostra, viram teste de que o pipeline
rejeita o que tem que rejeitar.

A concordância deve ser reportada por categoria, não só globalmente. O
indicador que decide a viabilidade da taxonomia A/B/C é o κ da atribuição
de categoria entre os verdadeiros positivos (guideline, Seção 5.5), e ele
precisa aparecer separado do κ binário de `is_ubw`.

Há uma extensão possível de humano versus IA: o dataset já captura autor.
A área de SATD em código gerado por IA está em ebulição, com o MSR 2026
Mining Challenge nesse tema, então comparar resignação funcional em código
humano e em código gerado por IA é uma contribuição adicional possível.
Está fora do escopo desta validação, mas a anonimização do agente D deve
preservar essa possibilidade ao decidir o salt.

---

Ao terminar, cada agente entrega um `.md` próprio. A consolidação, feita por
você, junta as recomendações num único parecer de validade do dataset, que
alimenta a seção de ameaças à validade da dissertação.
