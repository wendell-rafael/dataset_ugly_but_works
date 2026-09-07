# Roteiro de slides — UBW, achados da coleta

**Instrução para quem vai diagramar:** o texto abaixo é final. Diagrame como
está, sem reescrever, sem expandir, sem adicionar frases de ligação, sem
gerar rodapés explicativos que não estejam aqui. Onde não há texto, o slide
é só o gráfico. Oito slides, nada além disso.

Gráficos em `figures/slides/` (já sem título embutido — o título do slide
não deve ser repetido dentro da imagem).

---

## 1 — Capa

**UBW — Ugly But It Works**
Achados da coleta e desenho da validação

Wendell Rafael · PPGCC/UFCG · julho de 2026

---

## 2 — O léxico

**Título:** 25 expressões, 3 categorias

*Três colunas, cada uma com o cabeçalho da categoria, o total, e a lista de
expressões abaixo. Sem imagem.*

**A — Julgamento estético e hack explícito** · 26.553 registros (22,9%)
this is a hack · ugly hack · dirty hack · ugly but it works · ugly but works ·
hacky but works · messy but works · horrible but works · terrible but works

**B — Workaround e urgência** · 89.219 registros (76,8%)
temporary fix · temp fix · quick and dirty · stopgap · workaround for now ·
ugly workaround · dirty workaround · band-aid fix · not pretty but it works ·
duct tape fix · crude but it works

**C — Resignação e incerteza** · 420 registros (0,4%)
not ideal but it works · ugly solution but · ugly code but ·
not elegant but works · hope everything will work

**Rodapé:** A categoria separa a intenção declarada pelo autor, não o tipo de
dívida técnica. Potdar e Shihab (2014) tratam expressões equivalentes como
lista plana; Maldonado e Shihab (2015) estratificam por tipo de dívida
(design, teste, documentação), não por intenção.

---

## 3 — O corpus

**Título:** O que a coleta produziu

*Três números grandes, lado a lado. Sem imagem, sem texto adicional.*

**116.192** registros coletados
**26.667** repositórios com ao menos uma ocorrência
**74.807** repositórios processados

---

## 4 — Distribuição por expressão

**Título:** Quatro expressões promovidas por mineração concentram 61% do corpus

**Imagem:** `figures/slides/expressoes.png`

**Texto à esquerda do gráfico:**
`temporary fix`, `temp fix`, `stopgap` e `workaround for now` somam 70.574
registros, 60,7% de tudo que foi coletado. As quatro foram promovidas ao
léxico em julho de 2026, depois de uma rodada de mineração de padrões sobre
50 repositórios. `quick and dirty`, que também aparece no topo do ranking,
já estava no léxico original e não faz parte desse grupo.

A família "but works", que dá nome ao projeto, responde por 1,4% do corpus.
São 1.662 registros em dez expressões, todas na metade inferior do ranking.

---

## 5 — Categoria por tipo de artefato

**Título:** O perfil se repete nos quatro artefatos

**Imagem:** `figures/slides/categoria_x_artefato.png`

**Texto acima do gráfico:**
Comentário de código é o único artefato em que a Categoria A supera a B
(14.538 contra 11.433). Nos outros três, B abre vantagem de 6 a 7 vezes.
A Categoria C fica entre 65 e 141 registros em todos eles.

---

## 6 — Desenho da amostra de validação

**Título:** Como escolhemos o que validar à mão

*Tabela de três colunas. Sem imagem.*

| Decisão | Por quê | Precedente |
|---|---|---|
| 385 itens estratificados, 95% de confiança e margem de 5% | Tamanho padrão para estimar uma proporção nessa área | Bavota e Russo (2016) |
| Censo de 419 itens da Categoria C, em vez de amostra | Uma amostra de algo raro não sustenta estimativa por categoria | Decisão própria |
| 100 itens escolhidos por parecerem falsos positivos | Mede se o critério rejeita o que deve rejeitar, não só se aceita o óbvio | Decisão própria |
| Reponderação por estrato no cálculo final | A amostra é desproporcional de propósito; sem peso, a precisão global sai enviesada | — |

**Rodapé:** Total de 1.181 itens, contando a rodada de calibração.

---

## 7 — Como a precisão será medida

**Título:** Decisões de medição

*Tabela de três colunas. Sem imagem.*

| Decisão | Por quê | Precedente |
|---|---|---|
| Dois anotadores independentes, terceiro só para desempate | Rótulo humano é a referência; o desempate não entra no cálculo de concordância | Maldonado e Shihab (2015); Li, Soliman e Avgeriou (2023) |
| Calibração de 200 itens antes da anotação valer | Alinha critério entre anotadores sem contaminar a independência da medição | Awon (2024); multi-artefato em software científico (2026) |
| Kappa de Cohen e AC1 de Gwet lado a lado | Kappa despenca quando uma classe domina, mesmo com concordância alta | Gwet (2008); escala de Landis e Koch (1977) |
| Intervalo de Wilson, não aproximação normal | Nove das 25 expressões têm menos de 100 ocorrências; a menor tem 7 | Brown, Cai e DasGupta (2001) |
| LLM apenas como pré-filtro, nunca como rótulo final | O mesmo texto gera classificações diferentes entre execuções | Reiss (2023); Ziems et al. (2024) |

---

## 8 — Próximos passos

**Título:** Próximos passos

*Lista numerada. Sem imagem, sem texto de apoio.*

1. Anotação em pares dos 1.181 itens
2. RQ2 — sobrevivência por categoria (Kaplan-Meier, log-rank, Cox), com
   ajuste para registros do mesmo repositório
3. RQ3 — escrever o instrumento da survey e submeter ao comitê de ética
4. Consultoria estatística antes de rodar RQ2 e a survey

---

## O que ficou de fora, e por quê

Não entram neste deck: correções de filtro aplicadas durante a coleta,
reparo de registro corrompido, histórico de rodadas anteriores, cronograma
por mês, slide de status. São decisões operacionais — o lugar delas é o
`CHANGELOG.md` e a seção de ameaças à validade da dissertação, não uma
apresentação de achados.
