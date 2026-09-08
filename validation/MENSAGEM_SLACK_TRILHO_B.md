# Mensagem para o Slack

Copiar o bloco abaixo. Anexar as três imagens de `figures/trilho_b_cc/`, na
ordem em que são citadas: `escada_tamanho.png`, `correlacao_erro.png`,
`dev200_vs_eval371.png`.

---

Professor, fechei o braço de triagem automática por LLM no escopo de comentários
de código. Resultado é **negativo**, e acho que vale mais do que se fosse
positivo. Resumo em três pontos e os números completos no repositório.

**1. O teto da tarefa é ~0,54 de κ e não cede a modelo maior nem a prompt melhor.**

Testei 12 configurações, 6 famílias de modelo, de 4B a 235B de parâmetros, sobre
371 comentários com gabarito dos três anotadores. `claude-sonnet-5` e `grok-4.3`
deram **exatamente o mesmo** κ, precisão, número de alertas e MCC (0,537214 nos
dois — modelos de empresas diferentes com a mesma matriz de confusão).

E 0,537 é o mesmo valor que o `llama-3.3-70b` já dava na rodada de agosto, quando
o prompt era em português, o escopo era multi-artefato e a definição da classe
negativa vinha da literatura. Entre as duas rodadas mudei idioma, escopo,
taxonomia (agora extraída das justificativas que os anotadores escreveram) e a
família do melhor modelo. **O número não se moveu.**

O modelo mais caro que testei custa 25× o `qwen3-14b` e empata com ele dentro do
intervalo de confiança.

**2. Tamanho não prediz desempenho** — é o gráfico da escada.

Qwen 3, mesma geração, densa: 8B → 0,383, **14B → 0,465**, 32B → 0,376,
235B → 0,321. Gemma 3: 4B → 0,000, 12B → 0,316, 27B → 0,215. Sobe e desce nas
duas famílias.

Os extremos falham de formas opostas: o 4B respondeu "é UBW" nos 371 itens
(nunca alerta, κ zero); o 235B alerta 79 vezes, acha 83% dos negativos e cai a
25% de precisão — três falsos alarmes por acerto. Modelo grande não ficou melhor,
ficou mais desconfiado.

Isso replica Sheikhaei et al. (EMSE 2024), onde um modelo de 11B em zero-shot era
competitivo em **identificação binária** de SATD, e Li et al. (TOSEM 2026), que
registram que a identificação é "relatively straightforward" — ao contrário da
classificação multi-classe, onde LLM colapsa.

**3. O erro é correlacionado, então o painel não resolve** — é a matriz.

`sonnet-5` e `grok-4.3` concordam em 98,4% dos itens e erram nos **mesmos 21 de
24** (Jaccard 0,778). Dá **1,24 votos efetivamente independentes de 3**: a regra
de maioria reproduz exatamente o melhor juiz sozinho. É o cenário que o plano
previu como "concordância alta entre juízes com concordância baixa contra o
humano = viés compartilhado, não acerto" (Ahmed et al., MSR 2025).

Testei as 20 composições possíveis de painel de 3 como exploratório. A melhor
chega a 55,6% de precisão — ainda abaixo do piso de 60% que fixamos antes de
rodar. **O resultado negativo sobrevive até à seleção mais favorável possível.**

---

**Decisão.** Pelo critério da Seção 6, duas das quatro linhas apontam para não
publicar a marcação automática, por caminhos independentes: precisão abaixo de
60% e viés compartilhado entre juízes. Recomendo reportar como limitação.

**Isso não afeta o dataset.** A precisão do léxico em comentários de código é
**92,6%** (IC95 89,5–94,8%), por anotação humana independente, com κ de 0,79 a
0,83 entre os três anotadores.

---

**Uma correção que preciso registrar.** Na rodada de agosto eu havia mencionado
κ = 1,000 na fatia de comentários de código. **Aquele número não media nada** — é
o terceiro gráfico. A fatia tinha 57 itens com **1 negativo**, e 24 de 53 juízes
obtiveram 1,000 emitindo exatamente um alerta que calhava de acertar, incluindo
modelos que ficaram no fundo do ranking geral. Com 24 negativos em vez de 1, o
mesmo tipo de modelo dá 0,3 a 0,5. Não citar aquele valor.

**Custo:** US$ 5,59 em 5.944 chamadas, todas com temperatura zero, endpoint
fixado sem fallback e provedor gravado por item.

**Próximos passos que eu sugiro:**

- fechar a ameaça de não-determinismo repetindo um juiz (US$ 1,22) — hoje está
  declarada mas não medida;
- se quisermos mesmo empurrar este braço, o gargalo **não é orçamento, são os 24
  negativos** — toda largura de IC vem daí. Precisaria de uma amostra de
  confiabilidade com classes balanceadas, ~150 itens sobreamostrando near-misses,
  e isso é tempo de anotação, não crédito de API.

Documento completo com as sete seções, ameaças à validade e comandos de
reprodução: `validation/RESULTADO_TRILHO_B_CODE_COMMENT.md`.
