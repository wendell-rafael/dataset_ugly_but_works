#!/usr/bin/env bash
# Fase 1 do PLANO_EXPERIMENTO_LLM.md — roda a matriz completa de juízes sobre o
# conjunto de desenvolvimento (200 itens).
#
# Cada combinação (modelo × estratégia) grava seu próprio JSONL e é retomável,
# então interromper e rodar de novo continua de onde parou. Ordem dos modelos:
# do mais barato para o mais caro, para que uma interrupção deixe pelo menos os
# baratos completos.
#
# Uso:
#   bash run_panel_fase1.sh                    # conjunto de desenvolvimento
#   SET=gold_test_385 bash run_panel_fase1.sh  # conjunto de teste (só depois do congelamento)
#
# Requer OPENROUTER_API_KEY no .env da raiz do projeto.
set -euo pipefail

cd "$(dirname "$0")"

PY="${PY:-../.venv/bin/python}"
SET="${SET:-gold_dev_200}"
INPUT="../validation/panel/${SET}.csv"
POOL="${POOL:-../validation/panel/gold_dev_200.csv}"  # exemplos SEMPRE do desenvolvimento
WORKERS="${WORKERS:-6}"
K="${K:-3}"

# Ordem: do mais barato para o mais caro (preços de 31/08/2026, verify-judges).
MODELS=(
  "openai/gpt-oss-120b"
  "mistralai/mistral-small-3.2-24b-instruct"
  "qwen/qwen3-32b"
  "google/gemma-3-27b-it"
  "deepseek/deepseek-v3.2-exp"
  "deepseek/deepseek-chat"
  "qwen/qwen3-coder"
  "moonshotai/kimi-k2.5"
  "meta-llama/llama-3.3-70b-instruct"
  "z-ai/glm-5.2"
)

STRATEGIES=("zero_shot_nodef" "zero_shot" "fewshot_fixed" "fewshot_retrieved")

# Esforços de raciocínio varridos na fase 2. `high` fica de fora: medido no
# gpt-oss-120b, gasta 4x mais tokens de saída que `low` e concorda MENOS com o
# gabarito humano (88% contra 92%), então pagar por ele seria comprar piora.
EFFORTS=("low")

# Qual fase rodar. A base sozinha já responde a QP4 e entrega os `reasoning_tokens`
# reais, que é o que permite orçar a varredura sem extrapolar de um modelo só.
PHASE="${PHASE:-all}"   # base | sweep | all

# --- Fase 1: matriz base, no esforço default do provedor ---------------------
# Roda todo mundo sem o parâmetro `reasoning`. Além de ser a linha de base, é o
# que revela empiricamente quais modelos raciocinam: o campo `reasoning_tokens`
# vem preenchido no JSONL de quem raciocina e zerado/nulo no de quem não. A fase
# 2 usa essa lista, em vez de assumi-la de catálogo.
if [ "$PHASE" != "sweep" ]; then
for model in "${MODELS[@]}"; do
  for strategy in "${STRATEGIES[@]}"; do
    echo "=== [base] ${model} | ${strategy} | ${SET}"
    "$PY" 07_judge_panel.py run \
      --input "$INPUT" \
      --model "$model" \
      --strategy "$strategy" \
      --pool "$POOL" \
      --k "$K" \
      --workers "$WORKERS"
  done
done
fi

# --- Fase 2: varredura de esforço, só nos modelos que de fato raciocinam -----
REASONERS=$("$PY" - <<'PYEOF'
import json, pathlib, os, collections
set_name = os.environ.get("SET", "gold_dev_200")
runs = pathlib.Path("../validation/panel/runs") / set_name
gastos = collections.defaultdict(int)
for path in runs.glob("*.jsonl"):
    for line in path.open(encoding="utf-8"):
        rec = json.loads(line)
        if rec.get("reasoning_effort"):      # já é resultado da fase 2
            continue
        gastos[rec["model"]] += rec.get("reasoning_tokens") or 0
print(" ".join(sorted(m for m, tokens in gastos.items() if tokens > 0)))
PYEOF
)

if [ "$PHASE" = "base" ]; then
  echo "PHASE=base — varredura de esforço não executada."
elif [ -z "$REASONERS" ]; then
  echo "Nenhum modelo emitiu tokens de raciocínio — fase 2 dispensada."
else
  echo "Modelos que raciocinam: ${REASONERS}"
  for model in $REASONERS; do
    for strategy in "${STRATEGIES[@]}"; do
      for effort in "${EFFORTS[@]}"; do
        echo "=== [effort=${effort}] ${model} | ${strategy} | ${SET}"
        "$PY" 07_judge_panel.py run \
          --input "$INPUT" \
          --model "$model" \
          --strategy "$strategy" \
          --pool "$POOL" \
          --k "$K" \
          --reasoning-effort "$effort" \
          --workers "$WORKERS"
      done
    done
  done
fi

"$PY" 07_judge_panel.py status
echo
echo "Próximo passo: $PY 08_panel_analysis.py report --set ${SET}"
