# Roteiro — Reunião com especialista em análise quantitativa

Documento de apoio pra reunião de consultoria. Pensado pra ser rápido de
seguir na hora: contexto mínimo, depois as perguntas em ordem de prioridade
(a mais valiosa primeiro), cada uma com o que já foi feito e o que
especificamente eu quero que a pessoa avalie.

---

## Contexto (30 segundos, se precisar dar antes de entrar nas perguntas)

Dataset de mineração de repositórios GitHub (116 mil registros, ~26.700
repositórios): comentários de código, mensagens de commit, issues e PRs onde
o desenvolvedor admite que uma solução é imperfeita mas funciona. Três
questões de pesquisa: RQ1 caracteriza a frequência/distribuição (pronta,
descritiva), RQ2 mede tempo até remoção via sobrevivência (planejada, ainda
não rodada), RQ3 é uma survey com os autores reais sobre o porquê da decisão
(instrumento ainda em desenho — é o achado central do trabalho).

---

## 1. Não-independência das observações (o ponto mais importante — ainda não resolvido)

**O que temos:** 116 mil registros vindos de só ~26.700 repositórios — média de
4,4 registros por repositório, alguns com muito mais. Isso significa que
observações do mesmo repositório provavelmente não são independentes entre
si (compartilham cultura de código, mesmo time, mesma linguagem, etc.).

**O que ainda não fizemos:** nenhum ajuste pra isso em nenhuma das análises
planejadas — nem no modelo de Cox (RQ2), nem na estimativa de precisão da
amostra de validação (RQ1).

**O que quero perguntar:**
- Isso é motivo suficiente pra exigir erro-padrão clusterizado (cluster-robust
  SE por `repo_full_name`) no Cox, ou um modelo de fragilidade (*frailty
  model*)? Qual a diferença prática de decisão entre os dois nesse caso?
- Isso afeta a validade do intervalo de confiança da precisão amostrada (RQ1)
  também, ou esse problema é específico de modelos de regressão/sobrevivência?
- Existe um jeito simples de quantificar o quanto isso importa aqui antes de
  decidir a complexidade da correção (ex.: ICC — *intraclass correlation* —
  por repositório)?

---

## 2. Tamanho de amostra e correção por estratificação

**O que temos:** amostra de validação manual com 385 itens (Cochran,
95%/±5%), mais um censo completo da categoria rara (419 itens), mais
sobre-amostragem de itens raros/adversariais, com pesos de reponderação por
estrato calculados depois pra não enviesar a precisão global.

**O que quero perguntar:**
- O cálculo de Cochran assume amostragem aleatória simples. Com um desenho
  estratificado + censo parcial + sobre-amostragem deliberada, o "N efetivo"
  de confiança real é menor do que 385 por causa do design effect da
  estratificação? Como eu calcularia isso corretamente?
- O jeito que fizemos a reponderação (peso = N da população do estrato / N
  total, aplicado pra recalcular a precisão global) está certo, ou existe uma
  forma padrão (ex.: Horvitz-Thompson) que eu deveria usar em vez disso?
- Pra estimar a precisão de um subgrupo pequeno (ex.: só a Categoria A, ou só
  um tipo de artefato dentro dela), qual o intervalo de confiança correto
  quando a contagem observada de "verdadeiro positivo" pode estar perto de
  0% ou 100% (Wilson vs. normal aproximada)?

---

## 3. Concordância inter-anotador: κ, AC1 e o paradoxo de prevalência

**O que temos:** dois anotadores independentes, Cohen's κ e Gwet's AC1 em
paralelo (decisão deliberada porque o campo tem classes desbalanceadas — se a
maioria dos itens for verdadeiro-positivo, κ pode cair mesmo com concordância
real alta).

**O que quero perguntar:**
- AC1 em paralelo ao κ é suficiente, ou existe algo melhor (ex.: Krippendorff's
  alpha) que eu deveria reportar também, considerando que tenho itens
  avaliados por só 2 anotadores primários + um 3º só pra desempate (não
  todos os itens por todos os anotadores)?
- O κ da atribuição de categoria (A/B/C) só é calculado entre os itens que os
  dois anotadores concordaram ser verdadeiro-positivo — isso introduz viés de
  seleção na métrica (*restriction of range*)? Tem um jeito melhor de
  reportar isso?

---

## 4. Modelo de sobrevivência (RQ2) — pressupostos e covariáveis

**O que está planejado:** Kaplan-Meier por categoria semântica → teste de
log-rank (correção de Bonferroni pra comparações múltiplas) → Cox com
covariáveis (categoria, tipo de artefato, idade do repositório, popularidade,
linguagem).

**O que quero perguntar:**
- Verificação do pressuposto de riscos proporcionais (resíduos de Schoenfeld)
  — em que ponto do processo eu devo rodar isso, e o que fazer se o
  pressuposto falhar pra alguma covariável (estratificar por ela em vez de
  incluir como termo)?
- As covariáveis propostas (idade do repo, estrelas, commits) provavelmente
  são correlacionadas entre si — vale a pena checar multicolinearidade
  (VIF) antes de rodar o modelo cheio?
- Bonferroni é conservador demais pra quantas comparações estamos fazendo no
  total (log-rank entre categorias + comparações da survey depois)? Faria
  sentido usar Benjamini-Hochberg (FDR) pro conjunto todo da dissertação em
  vez de Bonferroni em cada análise isolada?

---

## 5. Desenho estatístico da survey (RQ3) — ainda não fechado

**O que está decidido:** 3 blocos (perfil, escala Likert de 12 itens ainda
não escritos, campo aberto). Comparação planejada entre grupos de categoria
semântica usa qui-quadrado (variáveis categóricas) e Kruskal-Wallis
(ordinais).

**O que quero perguntar:**
- Os 12 itens da escala devem ser tratados como ordinais item a item, ou dá
  pra somar/agregar em um escore composto por dimensão (se eu desenhar os
  itens em 3 blocos temáticos alinhados às categorias A/B/C)? Se for
  composto, preciso validar confiabilidade interna (Cronbach's alpha ou
  McDonald's omega) antes de usar o escore em qualquer teste?
- Faz sentido rodar uma análise fatorial exploratória nas respostas pra ver
  se os 12 itens realmente se agrupam nas 3 dimensões esperadas, ou isso é
  over-engineering pro tamanho de amostra que uma survey de recrutamento por
  e-mail costuma atingir?
- Existe uma forma de estimar, antes de rodar a survey, quantas respostas
  são necessárias pra ter poder estatístico razoável nas comparações
  qui-quadrado/Kruskal-Wallis planejadas — ou isso só dá pra saber depois de
  ver a taxa de resposta real?

---

## Se sobrar tempo

- Peço uma opinião geral sobre se o desenho todo (estratificação + censo +
  adversarial + reponderação) é "over-engineered" pro que a dissertação
  realmente precisa provar, ou se está no ponto certo.
- Pergunto se a pessoa conhece algum caso de estudo de mineração de
  repositórios (MSR) que tenha lidado com o mesmo problema de clusterização
  por repositório, pra eu citar como precedente metodológico.
