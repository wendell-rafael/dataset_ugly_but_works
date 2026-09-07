# Anexo — Trilho B (ensemble LLM): fundamentação, plano e experimentos

> Material de apoio, separado de `METODOLOGIA_E_VALIDACAO_ORIENTADOR.md`
> para manter o documento principal focado. Nada aqui é decisão fechada.

## 9. Fundamentação do uso de LLM na validação (base do Trilho B)

Levantamento de 2026-08-11. Responde à pergunta que o orientador
provavelmente faz: *"dá pra confiar em LLM decidindo se é UBW ou não?"*
A resposta da literatura é **"depende da tarefa"**, e o recorte favorece
exatamente o desenho que adotamos.

### 9.1 Em SATD, identificação binária é onde LLM se sustenta — classificação é onde desaba

Dois trabalhos medem isso diretamente, e o contraste é grande:

| Trabalho | Tarefa | Configuração | Resultado |
|---|---|---|---|
| Sheikhaei, Tian, Wang & Xu (2024), *EMSE* 29:159 | **Identificação** de SATD (binária) | Flan-T5-XXL, **zero-shot ICL** (só prompt) | "Competitivo com abordagens tradicionais", **6,4–9,2% abaixo** do mesmo modelo com *fine-tuning* |
| Sheikhaei et al. (2024) | Identificação de SATD | Flan-T5 com *fine-tuning* | **+4,4 a +7,2% de F1** sobre o melhor baseline não-LLM (CNN) |
| Li et al. (2026) — **IMPACT**, *TOSEM* 35(4):102 | **Classificação** de SATD (8 categorias) | Flan-T5-XXL com ICL *few-shot* | F1 médio máximo **0,351** — o pior de todos os comparados |
| Li et al. (2026) — IMPACT | Classificação de SATD | Pipeline com *fine-tuning* | F1 médio **0,927** |

Os próprios autores do IMPACT explicitam o porquê (Seção 3 do artigo):

> "Identification is relatively straightforward, and a small model, once
> fine-tuned, can achieve comparable performance to a large model. However,
> multi-class classification is more complex, and fine-tuning alone is
> insufficient to enable small models to reach the capability of larger
> models."

**Por que isso é bom pra nós.** O Trilho B faz **só identificação binária**
(`is_ubw` sim/não) com LLM de prateleira via prompt, sem *fine-tuning* — que
é exatamente o cenário onde a literatura mostra desempenho competitivo. E
**abandonamos a classificação por categoria A/B/C** (decisão de 2026-07-29),
que é exatamente a tarefa onde LLM sem *fine-tuning* colapsa. A decisão de
escopo tomada por outro motivo acabou alinhada com o que a evidência
recomenda — vale registrar isso explicitamente no texto do artigo.

### 9.2 Precedentes de validação humana sobre saída de LLM

O próprio IMPACT valida saída de LLM com humano em dois pontos, e os dois
servem de molde:

- **Ameaça 2 (confiabilidade do dado gerado por ChatGPT).** Amostraram
  **500** instâncias aumentadas; **3 pesquisadores de SE** verificaram
  independentemente se texto e rótulo batiam; item aceito se **≥2 dos 3**
  concordassem. Resultado: 478/500 = **95,6%** corretos.
- **Construção do conjunto de teste cross-project.** **6** alunos de
  pós-graduação classificaram manualmente; **Fleiss Kappa = 0,825**; só
  ficaram os itens em que **≥5 dos 6** concordaram.

Ou seja: em ambos os casos, saída automática só vira dado depois de passar
por painel humano com métrica de concordância reportada — que é o papel do
nosso Trilho A sobre os 385.

### 9.3 O risco que o nosso desenho precisa endereçar de frente

**Ahmed, Devanbu, Treude & Pradel (MSR 2025)** — o achado mais incômodo e o
mais importante pra nós:

- LLM pode substituir **um** anotador humano em tarefas **de baixo contexto,
  dedutivas, com categorias claras**, sem perder confiabilidade.
- Em tarefas **de alto contexto**, é não confiável (o κ humano-LLM despenca).
- Método proposto: usar concordância **modelo-a-modelo** como triagem
  inicial (limiar α > 0,5) e a confiança do modelo pra decisão item a item.
- **A ressalva crítica:** concordância alta entre modelos **pode refletir
  viés compartilhado entre eles, não validade** — e portanto não substitui
  checagem contra humano.

Isso atinge o nosso desenho em cheio: a regra de decisão do Trilho B hoje é
**unanimidade entre modelos**. Se DeepSeek e Qwen erram junto pelo mesmo
motivo (ambos treinados em corpora parecidos, ambos com o mesmo viés sobre o
que "parece" dívida técnica), a unanimidade não prova nada — ela só mede
homogeneidade dos modelos.

Consequências práticas que já estão no desenho, e que passam a ter
justificativa citável:

1. O gate humano dos 385 **não é opcional nem cerimonial** — é a única
   coisa que separa "os modelos concordam" de "os modelos acertam".
2. Vale escolher modelos de **famílias/origens diferentes** pra reduzir viés
   compartilhado (hoje: DeepSeek V3.2 + Qwen3 Coder, ambos chineses e de
   perfil semelhante — uma âncora Claude ou Llama diminuiria a correlação de
   erro; depende da `ANTHROPIC_API_KEY`, ainda pendente).
3. Nossa tarefa é **de baixo contexto e dedutiva** (texto curto + critério
   fechado no guideline), que é a faixa onde Ahmed et al. consideram o uso
   defensável — argumento a favor, mas que precisa ser afirmado com o κ
   modelo-vs-humano na mão, não por suposição.

### 9.4 Frameworks metodológicos a seguir no texto do artigo

- **PRIMES 2.0** — De Martino, Castaño, Palomba, Franch &
  Martínez-Fernández (2025), *A Methodological Framework for LLM-Based
  Mining of Software Repositories* (arXiv 2508.02233). Framework de 6
  estágios, 23 subpassos, 9 ameaças e 25 estratégias de mitigação,
  específico pra estudos de MSR com LLM. É o esqueleto natural pra descrever
  o Trilho B de forma auditável.
- **Baltes et al. (2025)**, *Guidelines for Empirical Studies in Software
  Engineering involving Large Language Models* (arXiv 2508.15503; 22
  pesquisadores; recurso vivo em llm-guidelines.org). A diretriz de
  *human validation* pede, concretamente: reportar a construção medida,
  o instrumento, o método de agregação, e a concordância **quebrada por
  rodada**; α de Krippendorff ≥ 0,8 pra dado confiável, 0,667–0,8 só pra
  conclusão tentativa, < 0,667 descartar.
- **Não-determinismo.** IMPACT lista como ameaça externa a variação de saída
  por `top_k`/`temperature`. Nosso pipeline já roda com **`temperature=0`**
  (`scripts/03_metrics_llm_triage.py`) — mitigação que precisa aparecer
  escrita no artigo, junto com modelo, versão e data de execução.

### 9.5 Ajustes que essa leitura pede no Trilho B

- Reportar κ **modelo-vs-humano** por modelo, não só a taxa de unanimidade
  do ensemble — é o número que a literatura cobra.
- Reportar também a concordância **modelo-a-modelo** e discutir
  explicitamente o risco de viés compartilhado (Ahmed et al.), em vez de
  tratar unanimidade como evidência de acerto.
- Diversificar as famílias de modelo do ensemble, se a chave da Anthropic
  for liberada.
- Documentar modelo/versão/`temperature`/data de execução no manifest da
  rodada, seguindo PRIMES 2.0 e Baltes et al.

## 10. Trilho B — plano para passar o LLM por todo o corpus

Ensemble multi-modelo (DeepSeek V3.2 + Qwen3 Coder via OpenRouter),
paralelizado, incremental/retomável, regra de decisão por unanimidade.
Camada **descritiva/exploratória** — não gera rótulo de dataset e não
substitui o Trilho A em nenhuma hipótese.

### 10.1 Calibragem do prompt: um experimento feito e reprovado

**Como o conjunto de desenvolvimento foi definido.** Os 200 itens de
calibração já têm rótulo humano dos 3 anotadores e, por desenho, estão
excluídos de toda métrica oficial (Seção 5). Isso os torna o conjunto de
**desenvolvimento** legítimo para ajustar o prompt: mexer nele não contamina
nada, e os 385 permanecem intocados como conjunto de **teste**. Separação
treino/teste adequada, e mais defensável do que ajustar prompt no olho.

Gabarito humano da calibração (voto majoritário dos 3): **173 True / 27
False = 86,5% de positivos.** Por expressão, "temporary fix" vem 88% True,
"temp fix" 83%, "stopgap" 83%.

**Hipótese testada.** O prompt original (v1) descreve a classe negativa
apenas como ruído lexical (string de teste, nome de variável, citação,
negação) — que é só a condição 5 das **cinco** condições da definição
operacional (`ANNOTATION_GUIDELINE.md`, Seção 4). Ele nunca pede que o
modelo verifique auto-admissão (cond. 1), resignação em manter a solução
(cond. 2) nem referência a código real (cond. 3). Hipótese: transformar as
cinco condições em checklist explícito, com exemplos negativos, melhoraria a
discriminação.

**Resultado: a hipótese foi refutada, com folga.** Os dois prompts rodados
nos mesmos 200 itens, mesmos modelos, `temperature=0`:

| Prompt | Modelo | κ (itens decididos) | Acurácia | Negativos capturados |
|---|---|---|---|---|
| v1 | DeepSeek V3.2 | 0,408 | 89,4% | 7 de 16 |
| v1 | Qwen3 Coder | **0,611** | 94,5% | 7 de 15 |
| v2 | DeepSeek V3.2 | 0,004 | 14,2% | 22 de 22 |
| v2 | Qwen3 Coder | 0,027 | 24,7% | 18 de 19 |

O v2 captura quase todos os negativos — e destrói tudo o mais, rejeitando
~85% do que os humanos aceitam. Saídas brutas em
`validation/experimentos_prompt/`.

**O achado que interessa não é sobre o prompt, é sobre o guideline.** As
justificativas geradas pelo v2 são internamente corretas. Diante de
`temporary fix for Java 1.5` (mensagem de commit seca), o modelo responde:
*"apenas anuncia um 'temporary fix' sem expressar resignação em mantê-lo"* —
e, lendo a condição 2 ao pé da letra ("não basta admitir que o código é ruim
— é preciso haver, no mesmo trecho, a resignação de mantê-lo assim mesmo"),
isso é `não-UBW`. Mas os anotadores humanos marcaram 88% dos itens com
"temporary fix" como True.

### 10.1.2 A pergunta a decidir, isolada

Parte da divergência **não** é dúvida legítima — é o v2 sendo estrito demais.
Ele rejeitou, entre outros, este item:

> `added __tracebackhide__, it's ugly but it works.` — *grappa-py/grappa*
> Justificativa da rejeição: *"admite que a solução é feia, mas não expressa
> resignação em mantê-la"*.

É a frase que dá nome ao fenômeno. Exigir, além de "é feio mas funciona", uma
declaração explícita de "e vou manter assim" é uma leitura que ninguém
sustenta. Para os itens com juízo estético explícito (`ugly hack`,
`quick and dirty`, `dirty hack`…), está decidido: o v2 erra, o guideline
está bem.

O que sobra é **uma única pergunta**, e ela vale muito:

> **Uma ocorrência cujo único marcador é temporal — "temporary fix for X",
> "temp fix", "stopgap" — sem nenhum juízo sobre a qualidade da solução,
> conta como UBW?**

Peso da decisão no corpus:

| Recorte do léxico | Itens | % do corpus | Como os 3 votaram na calibração |
|---|---|---|---|
| Só marcador temporal (`temporary fix`, `temp fix`, `stopgap`, `workaround for now`, `band-aid fix`, `duct tape fix`) | 56.623 | **61,9%** | 86% True (105 de 122) |
| Com juízo de qualidade (`ugly`, `hack`, `dirty`, `messy`…) | 34.835 | 38,1% | 87% True (68 de 78) |

Os anotadores trataram os dois grupos como equivalentes — 86% contra 87%.
A decisão, portanto, não muda a margem: muda **o que o dataset é**.

- **Resposta "sim, conta"** (o que foi praticado): o corpus segue com 91.458
  itens; a condição 2 do guideline precisa ser reescrita para registrar que
  rotular a própria solução de "temporária" já constitui juízo de qualidade e
  resignação suficientes.
- **Resposta "não conta"**: 61,9% do corpus vira falso positivo por
  definição, o léxico precisa ser podado e a calibração refeita sob o
  critério estrito.
- **Terceira via, recomendada:** manter tudo e **reportar as duas fatias
  separadamente**. A separação é derivável mecanicamente do léxico (não custa
  anotação nenhuma), divide o corpus em 62/38, e deixa o leitor aplicar a
  própria definição. Converte um problema de definição em uma dimensão
  reportada — e provavelmente é um achado por si só ("dívida admitida por
  urgência" × "dívida admitida por estética").

**É a pergunta mais importante desta reunião.**

### 10.1.1 Onde o v1 realmente é fraco

Corrigindo o diagnóstico anterior: o v1 **não** é uma "máquina de dizer sim"
sem serventia — ele bate 89-94% de acurácia contra o humano, e o Qwen3 Coder
já passa o portão de κ ≥ 0,61 (κ = 0,611). A fraqueza dele é específica:
**recall na classe negativa** — captura só ~44% dos negativos (7 de ~16).

A distância entre acurácia alta (89,4%) e κ mais baixo (0,408) é o paradoxo
de prevalência outra vez (Seção 6.2), agora do lado do modelo: com 86,5% da
classe sendo positiva, acertar os positivos domina a acurácia e esconde a
cegueira para os negativos. Por isso o κ é a métrica de portão, não a
acurácia.

Qualquer prompt novo deve mirar **especificamente** o recall de negativos,
sem derrubar o κ — e ser medido contra este mesmo conjunto de calibração
antes de rodar em escala.

### 10.2 Plano em 5 estágios, com portão em cada um

**Estágio 0 — resolver a divergência guideline × prática (Seção 10.1).**
*Bloqueia tudo, e é decisão humana, não técnica.* Enquanto não se decidir se
a condição 2 do guideline vale como está escrita ou se o texto será
afrouxado, não há alvo contra o qual calibrar prompt nenhum — o v2 mostrou
que os dois critérios levam a resultados opostos (86,5% vs ~14% de
positivos). Depois de decidido: se o guideline for afrouxado, o v1 já passa
o portão (κ=0,611 no Qwen) e segue-se direto ao Estágio 1; se o guideline
for mantido como está, a calibração humana precisa ser refeita sob o
critério estrito antes de qualquer coisa.

A infraestrutura de calibragem de prompt já está pronta e é barata (~$0,03
por rodada nos 200): `--prompt-version` seleciona a versão, a distribuição
de rótulos é logada em toda rodada, e o conjunto de calibração serve de
conjunto de desenvolvimento sem contaminar os 385.

**Estágio 1 — portão contra o humano (385).** Depende da anotação terminar.
Roda `ensemble-triage` nos 385, junta com o gabarito humano, roda
`ensemble-validate`. Três números, não um:

- κ **modelo-vs-humano**, por modelo (critério de corte: ≥ 0,61);
- κ **modelo-a-modelo**;
- concordância bruta + prevalência das classes (Seção 6.2).

Regra de decisão, incluindo o caso que a literatura manda vigiar:

| Situação | Decisão |
|---|---|
| κ modelo-vs-humano ≥ 0,61 | libera Estágio 2 |
| κ modelo-vs-humano < 0,61 | não roda o corpus; volta ao Estágio 0 ou Trilho B vira só ilustrativo |
| κ modelo-a-modelo alto **e** κ modelo-vs-humano baixo | **viés compartilhado** — não libera, mesmo com os modelos "concordando" |

**Estágio 2 — piloto em escala (~2.000 itens).** Não pular de 385 pra 91 mil.
Amostra estratificada por artefato/expressão, serve pra medir o que 385 não
mede: vazão real com paralelismo, taxa de erro/timeout de rede, custo
efetivo, e se a distribuição de rótulos se mantém fora da amostra que
guiou o ajuste do prompt (evita superajuste ao gate).

**Estágio 3 — corpus inteiro (91.458).** Só depois dos dois portões.
Execução já está pronta: `--max-workers` (thread pool), checkpoint
incremental, retomada sem reprocessar — a rodada de 200 já sobreviveu a uma
queda de rede e retomou sem perda. Custo do par atual (DeepSeek V3.2 $14 +
Qwen3 Coder $27) ≈ **$41** pelo corpus todo. Tempo: sequencial seria ~24
dias; com paralelismo o gargalo passa a ser o *rate limit* do OpenRouter, não
o nosso código — calibrar no Estágio 2.

**Estágio 4 — auditoria da saída em massa.** O portão do Estágio 1 valida
numa amostra; o corpus inteiro pode ter deriva de distribuição. Amostrar a
saída final e revisar por humano, no molde do próprio IMPACT (500 itens, 3
pesquisadores, aceite por ≥2/3 — Seção 9.2). Isso vira uma linha de
"validação da camada automática" no artigo.

**Estágio 5 — reporte.** Seguir PRIMES 2.0 e Baltes et al. (Seção 9.4):
modelo, versão, `temperature=0`, data de execução, prompt na íntegra, custo,
concordância quebrada por rodada, e a afirmação explícita de que o Trilho B
é descritivo e o número de precisão do artigo vem do Trilho A.

### 10.3 O problema de escala da fila de revisão humana

No piloto, 82/200 (**41%**) caíram em `requires_human_review` (divergência
ou "incerto" de algum modelo). Se essa taxa se mantiver nos 91.458 itens,
são **~37.500 itens** na fila — impossível revisar à mão. Três saídas, a
decidir antes do Estágio 3:

1. **Não forçar resolução.** Reportar três blocos: unânime-sim,
   unânime-não, e indeterminado — assumindo o indeterminado como resultado
   legítimo, com seu tamanho declarado. É o mais honesto e o mais barato.
2. **Terceiro modelo como desempate**, de família diferente (reduz a fila e
   ataca o viés compartilhado ao mesmo tempo). Depende da
   `ANTHROPIC_API_KEY`, ainda pendente.
3. **Revisar por amostragem**, não a fila inteira — o que já é o Estágio 4.

Recomendação: **(1) + (3)**, com (2) se a chave sair. Tentar revisar 37 mil
itens à mão contradiz a própria razão de existir do Trilho B.

