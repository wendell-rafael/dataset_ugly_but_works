#!/usr/bin/env bash
# Rodada do painel no escopo code_comment (eval_371, few-shot fixo, inglês).
#
# Um `run` por (modelo, k). O teto de gasto é POR EXECUÇÃO de propósito: com um
# teto global, um modelo que se comporte mal comeria o orçamento dos outros e a
# rodada terminaria incompleta sem aviso.
#
# `--max-completion-tokens 1000`: a saída medida com este prompt fica entre 215
# e 514 tokens, então 1000 é folga real e corta o pior caso em 2,5x contra o
# default de 2500 (que existe para modelo de raciocínio não sair truncado).
#
# Retomável: cada execução pula o que já está no JSONL com `ok: true`.
#
# Uso:
#   scripts/run_panel_cc.sh baratos    # os 4 mais baratos, para conferir números
#   scripts/run_panel_cc.sh resto      # os 7 restantes
#   scripts/run_panel_cc.sh sonnet     # o teto de capacidade, subconjunto
set -uo pipefail
cd "$(dirname "$0")/.."

INPUT=validation/panel/cc/eval_371.csv
# 4 workers, não 8. Com `allow_fallbacks: false` o endpoint fixado é único e 8
# threads geram fila: na primeira execução (gemma-3-4b, k=2) foram 129 respostas
# 429, e 11 itens esgotaram as 4 tentativas e ficaram com `ok: false` — o que
# derrubou a cobertura para 360/371 e fez o juiz ser excluído do relatório pelo
# mínimo de 98%. Menos concorrência troca vazão por completude, e completude é
# o que decide se o juiz entra na análise.
COMUM=(--strategy fewshot_cc --max-completion-tokens 1000 --workers 4)

BARATOS=(google/gemma-3-4b-it google/gemma-3-12b-it qwen/qwen3-14b qwen/qwen3-32b)
RESTO=(google/gemma-3-27b-it qwen/qwen3-8b meta-llama/llama-3.1-8b-instruct
       meta-llama/llama-3.3-70b-instruct qwen/qwen3-235b-a22b-2507
       minimax/minimax-m2.5)

roda() {  # $1 modelo, $2 k, $3 teto
  echo "=== $1 | k=$2 | teto US\$ $3"
  python3 scripts/07_judge_panel.py run --input "$INPUT" \
    --model "$1" --k "$2" --max-usd "$3" "${COMUM[@]}" \
    || echo "!!! $1 k=$2 terminou com erro (código $?) — segue para o próximo"

  # Repescagem: `_load_done` só considera feito o registro com `ok: true`, então
  # repetir o comando reprocessa exatamente os que esgotaram as tentativas em
  # 429 e não custa nada pelos que já passaram. Uma passada extra basta —
  # o rate limit é transitório, não capacidade zero.
  echo "--- repescagem $1 k=$2"
  python3 scripts/07_judge_panel.py run --input "$INPUT" \
    --model "$1" --k "$2" --max-usd "$3" "${COMUM[@]}" \
    || echo "!!! repescagem de $1 k=$2 falhou — conferir cobertura no relatório"
}

case "${1:-baratos}" in
  baratos) for m in "${BARATOS[@]}"; do for k in 2 8; do roda "$m" "$k" 0.30; done; done ;;
  resto)   for m in "${RESTO[@]}";   do for k in 2 8; do roda "$m" "$k" 0.80; done; done
           # grok custa ~6x a mediana dos outros; teto próprio.
           for k in 2 8; do roda x-ai/grok-4.3 "$k" 2.00; done ;;
  sonnet)  # Só k=8 e subconjunto: responde "o teto é do modelo ou da tarefa?",
           # que precisa de sinal, não de margem estreita. Nunca vai ao corpus.
           roda anthropic/claude-sonnet-5 8 2.20 ;;
  *) echo "uso: $0 {baratos|resto|sonnet}"; exit 1 ;;
esac
echo "=== fim de '${1:-baratos}'"
