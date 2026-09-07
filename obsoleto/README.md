# Obsoleto

Material que documenta etapas já superadas do projeto. Nada aqui é usado pelo
pipeline atual. Fica no repositório porque descreve decisões e rodadas reais —
não é lixo temporário, é histórico que perdeu a validade operacional.

**Não citar número daqui em texto submetido sem conferir contra a rodada atual.**
Vários destes arquivos apontam para caminhos de dados que mudaram de significado.

## `resultados_historicos/`

As quatro rodadas de coleta anteriores ao corpus atual, em ordem:

| arquivo | corpus | dataset que descreve |
|---|---|---|
| `RESULTADOS_PILOTO.md` | 140 repos | piloto exploratório |
| `RESULTADOS_ROUND_800.md` | 784 repos | `data/round_800/` |
| `RESULTADOS_ROUND_3000.md` | 3.000 repos | primeiro bloco do `full_run` |
| `RESULTADOS_FINAL.md` | 134 repos | `data/final/` |

Saíram da raiz porque enganam. O `RESULTADOS_FINAL.md` se chama "final" e aponta
para `data/final/ubw_collected_full.csv`, que tem **103 linhas** — de julho. O
corpus de trabalho atual é `data/full_run/ubw_collected_consolidated.csv`, com
**116.192 registros** em 26.667 repositórios.

## `reunioes/`

Roteiros de apoio para as reuniões de 28/07/2026 (orientador e consultoria em
análise quantitativa). As reuniões aconteceram; os roteiros cumpriram a função.

## `planos_superados/`

- `PLANO_AVALIACAO_PRECISAO.md` — superado por `validation/PLANO_EXPERIMENTO_LLM.md`,
  que incorpora a revisão de escopo para `code_comment` e o desenho do painel de
  juízes.
- `PLANO_VALIDACAO_COWORK.md` — divisão de tarefas entre agentes do Cowork para a
  etapa de validação. Documento de coordenação, sem valor metodológico.
- `dicas.md` — exemplos de categoria A por artefato. Recorte da seção 6.1 do
  `ANNOTATION_GUIDELINE.md`, que segue sendo a fonte para anotadores.

## `sugestoes_llm_calibracao_200.md`

Era `Untitled-1` na raiz, criado em 04/08/2026. Contém **sugestões de anotação
geradas por LLM para os 200 itens de calibração**, na mesma ordem do CSV do
anotador, uma por item, com veredito e nível de confiança:

> `6/200 — decred/decrediton (pr_body)` · `ugly hack` ·
> **Sugestão: ✅ SIM · confiança: 🟢 certo**

**Procedência de uso ainda não esclarecida.** O arquivo está preservado porque é
evidência sobre o processo de anotação, não arquivo descartável. Duas leituras
com consequências diferentes:

- Se foi gerado **depois** da anotação (checagem retrospectiva), não afeta nada.
- Se estava **à vista durante** a anotação dos 200, há viés de ancoragem, e isso
  atinge a rodada de calibração que serviu para escolher o método do trilho B —
  entra nas ameaças à validade.

Enquanto não for esclarecido, tratar a calibração dos 200 como potencialmente
ancorada. A rodada de 269 itens de `code_comment` não tem esse problema: a UI
gerada por `scripts/12_build_annotation_ui.py` não exibe sugestão nenhuma.
