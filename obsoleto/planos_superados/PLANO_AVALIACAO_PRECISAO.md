# Plano de Avaliação de Precisão do Dataset UBW

Como vamos medir se o que o léxico coletou é de fato o fenômeno que
estudamos, depois que as anotações humanas voltarem. O código que executa
cada etapa já existe (`scripts/03d_precision_report.py`, reusando
`scripts/03_metrics_llm_triage.py` sem alterá-lo); este documento explica o
raciocínio por trás de cada etapa, na ordem em que elas acontecem.

**Pré-requisito:** este plano só roda depois que os batches gerados em
`validation/batches_3anotadores/` estiverem preenchidos pelos três
anotadores (Wendell, Miguel, Bruno), seguindo o protocolo combinado na
reunião de 2026-07-29: calibração em conjunto com discussão depois, medição
independente, e só então paralelização.

**O que mudou em relação a versões anteriores deste plano:** categoria
semântica (A/B/C) deixou de ser dimensão analítica validada (a fronteira
entre as três famílias do léxico não se mostrou discriminável de forma
confiável, nem entre os próprios pesquisadores do projeto). O anotador não
preenche mais `category_confirmed`; a coluna `category_ubw` que ainda
aparece no CSV é só proveniência do léxico, não uma tarefa de anotação.
`issue_body` saiu da análise (mediana de tamanho 4x maior que
`code_comment`, dilui o sinal em texto conversacional).

---

## Etapa 1 — Resolver um rótulo final por item

Cada item da amostra principal tem, no mínimo, um rótulo, e até três,
dependendo de qual etapa do protocolo o produziu. Antes de medir qualquer
coisa, precisamos decidir qual rótulo vale para cada item.

Nos itens de **medição** (200 itens, os três anotadores rotulam de forma
independente), o rótulo final exige concordância unânime dos três. Se
algum discordar, o item fica marcado `unresolved`: não é descartado
silenciosamente, entra na contagem e aparece no relatório, mas não
participa do cálculo de precisão. Um volume alto de `unresolved` é, em si,
um sinal de alerta sobre o guideline.

Nos itens de **paralelização** (o restante da amostra principal, cada
anotador cobre um pedaço diferente sem sobreposição), o rótulo do único
anotador responsável é aceito diretamente, sem checagem cruzada. Isso é
aceitável porque a confiabilidade desse anotador específico já foi validada
na etapa de medição; se a concordância na medição vier baixa, a
paralelização não deveria ter sido liberada (ver Validação da Coleta,
abaixo).

Os pools de **watch** (expressões raras) e **near-miss** (adversarial)
também são cobertos por um anotador só, mas por um motivo diferente: são
diagnósticos, nunca tiveram checagem cruzada em nenhum desenho deste
projeto, e não entram nas tabelas de precisão (Etapa 3) nem na precisão
global reponderada (Etapa 4). Respondem outras perguntas, ver Etapa 5.

Os itens de calibração são excluídos automaticamente desta e de todas as
etapas seguintes. A discussão em grupo da calibração quebra a independência
que a medição de concordância exige.

## Etapa 2 — Concordância entre anotadores (κ e AC1)

Aqui medimos se os três anotadores enxergam a mesma coisa na etapa de
medição, não ainda se o léxico acertou. `is_ubw` é binário, é UBW ou não; é
a única tarefa medida, já que categoria não é mais anotada.

Calculamos duas métricas em paralelo, nunca uma sozinha. Cohen's κ é a
métrica padrão do campo (Landis & Koch, 1977), com a escala de
interpretação deles: 0,61 é o mínimo aceitável, 0,80 ou mais é excelente.
Gwet's AC1 é reportado ao lado porque κ sofre do paradoxo de prevalência:
se a maioria dos itens for realmente UBW, uma classe desbalanceada, κ pode
cair mesmo com concordância real alta. AC1 é mais robusto a isso (Gwet,
2008).

Essa concordância é a condição de liberação da paralelização: se vier
baixa, a leitura correta não é "o léxico está ruim", é "os anotadores ainda
não convergiram no critério", e a etapa de calibração precisa ser revisada
antes de qualquer um cobrir itens sozinho.

## Etapa 3 — Precisão por expressão e tipo de artefato

Com o rótulo final resolvido, calculamos a precisão propriamente dita: de
todos os itens de um recorte, uma expressão do léxico, um tipo de artefato,
quantos são verdadeiro-positivo (`is_ubw=True`)? Entram aqui os itens de
medição (resolvidos por consenso triplo) e os itens de paralelização
(resolvidos por anotador único, mas de um estrato já validado). Os pools de
watch e near-miss ficam de fora, mesmo quando o item individual tem um
rótulo resolvido, porque nunca tiveram checagem cruzada.

O intervalo de confiança usado é o de Wilson, não a aproximação normal
comum. Wilson se comporta melhor quando a proporção está perto de 0% ou
100% e quando `n` é pequeno, exatamente o caso das expressões mais raras do
léxico: `terrible but works` tem só 7 ocorrências no corpus inteiro, e um
IC normal ali seria enganoso.

Qualquer recorte com precisão abaixo de 0,50 gera um aviso automático no
log. Esse aviso cita explicitamente que o número é insumo para o
orientador decidir sobre o léxico, não um gatilho para o script mexer
nele, já que o léxico está congelado.

## Etapa 4 — Precisão global reponderada

A amostra principal não é proporcional só por acaso, ela é estratificada
por tipo de artefato (`commit_message`, `code_comment`, `pr_body`), então a
precisão global é uma soma ponderada: a precisão de cada tipo de artefato é
multiplicada pelo peso real daquele artefato no corpus consolidado, já
calculado em `sampling_weights_oficial.csv`, e somada.

Só entram no denominador os itens da amostra principal, medição e
paralelização juntas. Os pools de watch e near-miss foram escolhidos a
dedo, não representam a proporção real do corpus, então não contam para a
precisão global.

Se algum estrato ficar sem nenhum item anotado por algum motivo, o
relatório avisa explicitamente que a precisão global reportada é uma
aproximação, com peso coberto abaixo de 100%, em vez de fingir que está
completa.

## Etapa 5 — Especificidade sobre os itens adversariais (near-miss)

Isto não é a mesma coisa que precisão. Precisão pergunta "dos itens que o
léxico marcou, quantos são de verdade UBW?". Especificidade aqui pergunta
o oposto: "dos itens que parecem UBW mas que o guideline diz que
provavelmente não são, string de teste, citação de terceiro, negação,
texto gerado por ferramenta, uso não-técnico, quantos o anotador
corretamente rejeitou?"

Cada item desse pool carrega a heurística que o sinalizou como candidato
enganoso, então o relatório sai quebrado por heurística. Se uma heurística
específica, como citação de terceiro, tiver especificidade baixa, isso
aponta para um ponto fraco específico do guideline, não um problema
difuso.

## Etapa 6 — O que fazer com o resultado

Nenhuma das etapas acima decide nada sozinha. Todas produzem números que
viram insumo para decisão humana.

| Sinal | O que significa | Quem decide o próximo passo |
|---|---|---|
| κ de `is_ubw` na medição < 0,61 | Os três anotadores ainda não convergiram; paralelização não deveria ter sido liberada | Orientador. Revisar calibração e guideline antes de seguir |
| Precisão de uma expressão < 0,50 | Aquela expressão específica pode estar poluindo o corpus | Orientador. Decide se remove do léxico (léxico continua congelado até essa decisão) |
| Volume alto de `unresolved` na medição | Guideline pode ter uma zona cinzenta mal coberta | Revisar exemplos do guideline |
| Especificidade baixa numa heurística de near-miss | Ponto cego específico do critério de rejeição | Adicionar exemplo ou regra de desempate ao guideline |

## Etapa 7 (opcional) — Teste estatístico formal da triagem LLM

Depois que a validação humana (Etapas 1-6) estiver consolidada, cabe uma
checagem adicional, não obrigatória, que fortalece a defesa metodológica na
dissertação. Consiste em aplicar o alt-test (Calderon, Reichart & Dror, ACL
2025, DOI: 10.18653/v1/2025.acl-long.782) sobre a nossa própria triagem LLM
já implementada em `03_metrics_llm_triage.py`.

O alt-test usa uma estratégia leave-one-out: remove um anotador humano de
cada vez e testa estatisticamente se o LLM representa melhor o restante do
comitê do que o anotador removido representaria. É um teste formal pra
justificar, ou descartar, a hipótese de que o LLM poderia ter substituído
um humano naquela tarefa específica. Não decide nada sozinho, só
quantifica. Com três anotadores medindo o mesmo conjunto de 200 itens na
etapa de medição, já existe a base mínima de comitê que esse teste exige.

Um trabalho de MSR 2025 (Ahmed, Devanbu, Treude & Pradel, "Can LLMs Replace
Manual Annotation of Software Engineering Artifacts?", DOI:
10.1109/MSR66628.2025.00086, vencedor do ACM SIGSOFT Distinguished Paper
Award) dá contexto para essa checagem. Em tarefas de alto contexto, que
exigem julgar intenção ou ler o entorno de uma mudança em vez de comparar
texto de forma superficial, a concordância humano-modelo caiu para 0,15
num dos casos testados, contra 0,80 de concordância humano-humano na mesma
tarefa. Os autores concluíram que o LLM não substitui o humano com
segurança nesse tipo de tarefa. A decisão de `is_ubw` do UBW se parece
estruturalmente mais com esse caso de alto contexto do que com os casos de
baixo contexto em que o mesmo estudo encontrou concordância alta, o que já
é evidência empírica, não só argumento teórico, a favor de manter o LLM
como pré-filtro em vez de anotador.

Se o alt-test confirmar que o LLM não substituiria os humanos com
significância estatística, o resultado vira uma seção de validação extra
na dissertação, citando os dois trabalhos acima. Se o resultado sair
ambíguo ou favorável ao LLM, isso não muda o protocolo já em andamento: a
decisão de manter validação humana como referência já foi tomada e já
está sendo executada. O alt-test aqui é confirmatório, não decisório.

## O que este plano não cobre

Não substitui o κ LLM-vs-humano já implementado em
`03_metrics_llm_triage.py`, que é triagem, não validação de precisão. São
perguntas diferentes.

Não roda antes da anotação existir. Todos os arquivos de saída dependem de
`validation/batches_3anotadores/*_FILLED.csv` preenchidos.

Não decide o que fazer com o resultado. O script calcula, o orientador
decide, seguindo a tabela da Etapa 6.

## Comando de referência (quando os batches voltarem preenchidos)

```bash
python scripts/03d_precision_report.py report \
    --annotations validation/annotations_long_final.csv \
    --weights validation/sample_final_v2/sampling_weights_oficial.csv \
    --out-dir validation/precision_report_final
```

O CSV de `--annotations` precisa ser um formato longo, uma linha por item
por anotador, com a coluna `sample_stratum` já anexada a partir de
`_internal_stratum_map_oficial.csv` (valores `main_medicao`,
`main_paralelizacao`, `watch`, `near_miss`, gerados por
`03c_generate_batches.py build-v2`). O script recusa rodar sem essa
coluna, de propósito, para não deixar passar despercebido que a
reponderação ficaria incorreta sem ela. Como não há mais um 3º anotador de
desempate fixo, `--tiebreak-annotators` não é necessário neste desenho.
