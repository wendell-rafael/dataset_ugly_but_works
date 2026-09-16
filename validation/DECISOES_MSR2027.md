# Decisões pendentes para o MSR 2027, Data and Tool Showcase

Lista de decisão para o paper e para o congelamento do dataset. Cada item traz o
fato apurado, a pergunta e uma recomendação. Ordem é de bloqueio: os do Bloco 0
travam todos os números do paper.

Prazos declarados: abstract em 05/11/2026, paper em 10/11/2026. Autonomeação de
Junior PC em 15/09/2026.

---

## Bloco 0. Congelamento do snapshot v1.0

Nenhum número entra no paper antes disso.

### 1. O dataset publicado inclui `issue_body`?

O corpus consolidado tem 116.192 registros em 26.667 repositórios. Sem
`issue_body` são 91.458 em 21.553. A precisão de 92,7% cobre só o frame sem
`issue_body`, porque foi dele que a amostra saiu. `issue_body` foi excluído da
análise em 29/07 por ter mediana de 1.383 caracteres contra 275 dos outros três,
texto conversacional que dilui o sinal.

**Pergunta: publicamos 91.458, ou 116.192 com as linhas de issue marcadas como
não validadas?**

Recomendação: publicar os 91.458 como o dataset. `issue_body` no máximo como
arquivo separado, declarado sem estimativa de precisão.

### 2. O que fazer com o segredo encontrado em `body_text`?

A varredura de 27/07, sobre 73.405 linhas parciais, achou 9.217 linhas com PII.
Entre elas 4 chaves privadas, 9 AWS access key IDs, 1 PAT clássico do GitHub, 29
JWTs e 61 URLs com credencial embutida, além de 7.949 e-mails e 18.518 menções.
Publicar isso com CC-BY é republicar segredo ativo de terceiro. A varredura
precisa ser refeita sobre o consolidado, que é maior.

**Pergunta: qual a política? Redigir o trecho e manter a linha, remover a linha
inteira, ou tratar diferente por classe (segredo remove, e-mail e menção
redigem)?**

Recomendação: por classe. Credencial e chave saem por remoção do trecho com
marcador, e-mail e menção viram máscara, e o número de linhas afetadas entra no
paper como nota de construção. O mecanismo já existe em
`scripts/06_export_publishable.py`.

### 3. Qual a data de corte do snapshot?

A coleta está pausada, não concluída. O paper precisa declarar uma data de corte
e o dataset precisa corresponder a ela.

**Pergunta: congelamos no estado atual e declaramos a data, ou tem coleta
pendente que você quer terminar antes?**

### 4. O que vai no Zenodo do código?

São dois registros, dataset em CC-BY e código em MIT. O repositório hoje tem o
pipeline de coleta, os scripts de amostragem e anotação, e o painel de juízes
LLM, que não entra no paper.

**Pergunta: o registro de código leva o repositório inteiro, ou só coleta,
amostragem e anotação?**

Recomendação: repositório inteiro, com o painel declarado no README como
trabalho em andamento não usado no paper. Esconder código que existe é pior que
explicar.

---

## Bloco 1. Conteúdo do paper

### 5. A subseção Lexicon Coverage fica?

Cobertura no sentido de recall do fenômeno, quanto UBW existe fora das 25
expressões, não é mensurável com este desenho. Exigiria varrer o texto bruto dos
projetos com um gabarito independente do léxico. Está declarado fora de escopo
em outro documento nosso.

**Pergunta: cortamos, ou trocamos por distribuição de ocorrências por expressão
e por repositório, que é cobertura do léxico dentro do corpus?**

Recomendação: trocar, e nomear de forma que não prometa recall.

### 6. A curva de sobrevivência entra neste paper?

Só é válida para `code_comment`, onde `removed_at` vem do pareamento de eventos
`+` e `−` do `git log -S`, com 13.846 remoções observadas. Para `pr_body`,
`removed_at` é `merged_at` ou `closed_at`, que é fechamento de PR e não remoção
de dívida: 21.436 de 22.071, mediana de 4 dias. Numa curva conjunta, os PRs
dominam e a curva mede outra coisa.

**Pergunta: entra descritiva restrita a `code_comment`, ou fica inteira para o
technical paper futuro?**

Recomendação: um parágrafo descritivo de `code_comment` neste paper, com a
análise completa guardada. Mostra que o campo temporal serve para alguma coisa,
que é o argumento de reusabilidade.

### 7. Reportamos precisão por categoria A/B/C?

A amostra não foi estratificada por categoria, só por tipo de artefato. Mesmo
assim a mistura da amostra aderiu à do frame (qui-quadrado p = 0,81), então
estimativa por domínio é válida. A: n=103, 94,2%, IC 87,9 a 97,3. B: n=281,
92,2%, IC 88,4 a 94,8. C: n=1, não estimável.

**Pergunta: reportamos A e B com IC, e C como frase no texto?**

Recomendação: sim, com a nota de que a categoria não foi dimensão de
estratificação.

### 8. Como o painel de LLM aparece, se aparecer?

A justificativa atual no roteiro, de que provavelmente não conseguiríamos rodar,
não é verdadeira: a infraestrutura está construída e rodando, e o custo no
corpus inteiro com o modelo mais barato é da ordem de US$ 3. Mas não cabe em 4
páginas e não é o que a trilha avalia.

**Pergunta: sai por completo, ou vira uma frase em trabalho futuro com o motivo
correto?**

Recomendação: uma frase em trabalho futuro. O motivo escrito não pode ser
incapacidade de execução, porque o código vai junto no Zenodo.

### 9. Como a resolução de divergências é reportada?

O protocolo teve duas fases: medição cega, e depois discussão entre os três com
mudança de rótulo declarada por quem mudou. Kappa de medição: 0,840, 0,711 e
0,657. Kappa final: 0,925, 0,872 e 0,844. Unanimidade final 375 de 385, com os
10 restantes resolvidos por maioria.

**Pergunta: reportamos os dois números, medição e pós-discussão, ou só o final
com a discussão descrita no método?**

Recomendação: os dois. Cabe em duas frases, é o padrão da área, e reportar só o
final sem dizer que houve discussão seria omissão.

---

## Bloco 2. Lacunas que dependem de pessoas

### 10. Anotamos os negativos duros?

A pool `near_miss` tem 100 itens, construída adversarialmente, nunca anotada.
Hoje temos 27 negativos no conjunto de desenvolvimento e 28 no de teste. É isso
que limita qualquer afirmação sobre especificidade.

**Pergunta: Bruno e Miguel topam mais uma rodada? Se for você sozinho, perde a
redundância, e aí a especificidade vira medida de um anotador só.**

Recomendação: se os três não estiverem disponíveis, não anotar. Para este paper
os 28 negativos bastam, e uma medida sem redundância enfraquece mais do que o
ganho de tamanho compensa.

### 11. O guia de anotação vai no Zenodo?

São 354 linhas com a definição operacional em cinco condições, os exemplos por
categoria e os casos limítrofes. É o que permite alguém replicar a anotação.

**Pergunta: publicamos junto?**

Recomendação: sim, é o item de maior peso para a barra de reusabilidade.

### 12. Autonomeação para Junior PC até 15/09?

**Pergunta: você vai se autonomear?**

---

## Bloco 3. Depois do paper

### 13. O painel de LLM continua?

A infraestrutura está pronta e a matriz roda por poucos dólares.

**Pergunta: continua em paralelo mirando o technical paper, ou pausa até o
Showcase estar submetido?**

Recomendação: pausar a execução e retomar depois de 10/11. O que estiver rodando
não muda nada no Showcase, e o congelamento do snapshot é o caminho crítico.
