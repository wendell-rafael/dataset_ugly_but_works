# Painel de juízes — eval_371

371 itens, 347 positivos e 24 negativos no gabarito humano (prevalência de positivos: 93.5%).
12 configurações de juiz carregadas de `validation/panel/runs/eval_371/`.

## Passo 1 — desempenho individual

                                          juiz   n  sem_voto  abstencoes  alertas  taxa_positivos  precisao_alerta  ic95_low  ic95_high  cobertura  tp  fn  fp  tn  conc_positivos  conc_pos_wilson_low  conc_pos_wilson_high  conc_negativos  conc_neg_wilson_low  conc_neg_wilson_high   mcc  acuracia_decididos  kappa   ac1  kappa_penalizado kappa_leitura
           google_gemma_3_12b_it_fewshot_cc_k8 371         0           0        6           0.984            0.833     0.500      1.000      0.208 346   1  19   5           0.997                0.984                 0.999           0.208                0.092                 0.405 0.401               0.946  0.316 0.942             0.316      razoável
                   x_ai_grok_4_3_fewshot_cc_k8 371         0           0       32           0.914            0.500     0.312      0.688      0.667 331  16   8  16           0.954                0.926                 0.971           0.667                0.467                 0.820 0.544               0.935  0.537 0.925             0.537      moderada
                  qwen_qwen3_14b_fewshot_cc_k8 371         0           0       24           0.935            0.500     0.292      0.708      0.500 335  12  12  12           0.965                0.941                 0.980           0.500                0.314                 0.686 0.465               0.935  0.465 0.926             0.465      moderada
                   qwen_qwen3_8b_fewshot_cc_k8 371         0           0       19           0.949            0.474     0.263      0.684      0.375 337  10  15   9           0.971                0.948                 0.984           0.375                0.212                 0.573 0.386               0.933  0.383 0.924             0.383      razoável
                  qwen_qwen3_32b_fewshot_cc_k8 371         0           0       24           0.935            0.417     0.249      0.625      0.417 333  14  14  10           0.960                0.933                 0.976           0.417                0.245                 0.612 0.376               0.925  0.376 0.914             0.376      razoável
            minimax_minimax_m2_5_fewshot_cc_k8 371         0           0       45           0.879            0.400     0.244      0.556      0.750 320  27   6  18           0.922                0.889                 0.946           0.750                0.551                 0.880 0.506               0.911  0.478 0.893             0.478      moderada
           google_gemma_3_12b_it_fewshot_cc_k2 371         0           0       44           0.881            0.318     0.182      0.455      0.583 317  30  10  14           0.914                0.879                 0.939           0.583                0.388                 0.755 0.378               0.892  0.358 0.871             0.358      razoável
       qwen_qwen3_235b_a22b_2507_fewshot_cc_k8 371         0           0       79           0.787            0.253     0.165      0.354      0.833 288  59   4  20           0.830                0.787                 0.866           0.833                0.641                 0.933 0.399               0.830  0.321 0.777             0.321      razoável
meta_llama_llama_3_1_8b_instruct_fewshot_cc_k8 371         0           0       20           0.946            0.250     0.100      0.450      0.208 332  15  19   5           0.957                0.930                 0.974           0.208                0.092                 0.405 0.180               0.908  0.179 0.897             0.179          leve
                  qwen_qwen3_14b_fewshot_cc_k2 371         1           0       59           0.841            0.237     0.136      0.339      0.583 301  45  10  14           0.870                0.830                 0.901           0.583                0.388                 0.755 0.305               0.851  0.270 0.814             0.265      razoável
                  qwen_qwen3_32b_fewshot_cc_k2 371         0           0       32           0.914            0.219     0.094      0.375      0.292 322  25  17   7           0.928                0.896                 0.951           0.292                0.149                 0.492 0.192               0.887  0.190 0.868             0.190          leve
            google_gemma_3_4b_it_fewshot_cc_k8 371         0           0        0           1.000              NaN       NaN        NaN      0.000 347   0  24   0           1.000                0.989                 1.000           0.000                0.000                 0.138   NaN               0.935  0.000 0.931             0.000          leve

Corte: FALLBACK: nenhum juiz atingiu kappa penalizado ≥ 0.75, então o painel usa os 3 melhores acima de 0.40. Eliminados: google_gemma_3_12b_it_fewshot_cc_k2, google_gemma_3_12b_it_fewshot_cc_k8, google_gemma_3_4b_it_fewshot_cc_k8, meta_llama_llama_3_1_8b_instruct_fewshot_cc_k8, qwen_qwen3_14b_fewshot_cc_k2, qwen_qwen3_235b_a22b_2507_fewshot_cc_k8, qwen_qwen3_32b_fewshot_cc_k2, qwen_qwen3_32b_fewshot_cc_k8, qwen_qwen3_8b_fewshot_cc_k8.

> **O painel opera abaixo da barra pretendida.** A barra de kappa ≥ 0.75 foi fixada na faixa dos anotadores humanos (0,844 a 0,925) e nenhum juiz a alcançou. O fallback estava pré-registrado no plano antes desta execução. Toda leitura das colunas publicadas precisa carregar essa ressalva.
Painel: x_ai_grok_4_3_fewshot_cc_k8, minimax_minimax_m2_5_fewshot_cc_k8, qwen_qwen3_14b_fewshot_cc_k8.

### Kappa contra cada anotador individual

`is_ubw_gold` já é o voto majoritário dos três — comparar o juiz contra ele é uma régua mais fácil do que a usada para reportar 0,844 a 0,925 entre os humanos, que é par a par. Abaixo, o mesmo cálculo par a par aplicado a cada juiz, ordenado pela média das três comparações individuais (não pelo kappa contra a maioria).

Referência — kappa humano-humano, par a par, neste conjunto:

           par   n  kappa
 Wendell×Bruno 371  0.811
Wendell×Miguel 371  0.829
  Bruno×Miguel 371  0.787

                                          juiz  kappa_vs_Wendell  kappa_vs_Bruno  kappa_vs_Miguel  kappa_vs_anotador_medio  kappa_vs_maioria  kappa_vs_anotador_medio_penalizado  kappa_vs_maioria_penalizado
                   x_ai_grok_4_3_fewshot_cc_k8             0.529           0.628            0.602                    0.586             0.537                               0.586                        0.537
                  qwen_qwen3_14b_fewshot_cc_k8             0.463           0.568            0.444                    0.492             0.465                               0.492                        0.465
            minimax_minimax_m2_5_fewshot_cc_k8             0.471           0.519            0.432                    0.474             0.478                               0.474                        0.478
                   qwen_qwen3_8b_fewshot_cc_k8             0.388           0.496            0.355                    0.413             0.383                               0.413                        0.383
                  qwen_qwen3_32b_fewshot_cc_k8             0.380           0.387            0.351                    0.373             0.376                               0.373                        0.376
           google_gemma_3_12b_it_fewshot_cc_k2             0.327           0.431            0.342                    0.367             0.358                               0.367                        0.358
           google_gemma_3_12b_it_fewshot_cc_k8             0.275           0.398            0.340                    0.338             0.316                               0.338                        0.316
       qwen_qwen3_235b_a22b_2507_fewshot_cc_k8             0.316           0.349            0.312                    0.326             0.321                               0.326                        0.321
                  qwen_qwen3_14b_fewshot_cc_k2             0.270           0.330            0.257                    0.286             0.270                               0.281                        0.265
                  qwen_qwen3_32b_fewshot_cc_k2             0.202           0.275            0.203                    0.227             0.190                               0.227                        0.190
meta_llama_llama_3_1_8b_instruct_fewshot_cc_k8             0.155           0.186            0.192                    0.178             0.179                               0.178                        0.179
            google_gemma_3_4b_it_fewshot_cc_k8             0.000           0.000            0.000                    0.000             0.000                               0.000                        0.000

### Desempenho por tipo de artefato (QP1)

(escopo de artefato único — quebra não se aplica)

### Desempenho por expressão do léxico (QP1)

Estratos com menos de 10 itens agrupados em `(outros)`: o gabarito cobre apenas parte das 25 expressões, e células de dois ou três itens não sustentam leitura.

                              juiz matched_expression   n  negativos_humanos  decididos  acuracia  conc_negativos    mcc  kappa
       x_ai_grok_4_3_fewshot_cc_k8           (outros)  10                  0         10     1.000             NaN    NaN  1.000
       x_ai_grok_4_3_fewshot_cc_k8         dirty hack  36                  1         36     0.917           0.000 -0.041 -0.038
       x_ai_grok_4_3_fewshot_cc_k8    quick and dirty  27                  9         27     0.889           0.667  0.756  0.727
       x_ai_grok_4_3_fewshot_cc_k8            stopgap  16                  2         16     0.875           0.500  0.429  0.429
       x_ai_grok_4_3_fewshot_cc_k8           temp fix  16                  1         16     0.812           0.000 -0.098 -0.091
       x_ai_grok_4_3_fewshot_cc_k8      temporary fix  56                  1         56     0.964           1.000  0.567  0.486
       x_ai_grok_4_3_fewshot_cc_k8     this is a hack 101                  5        101     0.960           0.600  0.579  0.579
       x_ai_grok_4_3_fewshot_cc_k8          ugly hack  76                  3         76     0.961           1.000  0.692  0.648
       x_ai_grok_4_3_fewshot_cc_k8    ugly workaround  17                  0         17     0.824             NaN    NaN  0.000
       x_ai_grok_4_3_fewshot_cc_k8 workaround for now  16                  2         16     0.938           1.000  0.787  0.765
minimax_minimax_m2_5_fewshot_cc_k8           (outros)  10                  0         10     1.000             NaN    NaN  1.000
minimax_minimax_m2_5_fewshot_cc_k8         dirty hack  36                  1         36     0.889           0.000 -0.051 -0.043
minimax_minimax_m2_5_fewshot_cc_k8    quick and dirty  27                  9         27     0.926           0.889  0.833  0.833
minimax_minimax_m2_5_fewshot_cc_k8            stopgap  16                  2         16     0.812           0.500  0.303  0.294
minimax_minimax_m2_5_fewshot_cc_k8           temp fix  16                  1         16     0.938           1.000  0.683  0.636
minimax_minimax_m2_5_fewshot_cc_k8      temporary fix  56                  1         56     0.893           1.000  0.357  0.226
minimax_minimax_m2_5_fewshot_cc_k8     this is a hack 101                  5        101     0.941           0.600  0.477  0.469
minimax_minimax_m2_5_fewshot_cc_k8          ugly hack  76                  3         76     0.908           0.667  0.371  0.325
minimax_minimax_m2_5_fewshot_cc_k8    ugly workaround  17                  0         17     0.824             NaN    NaN  0.000
minimax_minimax_m2_5_fewshot_cc_k8 workaround for now  16                  2         16     0.938           1.000  0.787  0.765
      qwen_qwen3_14b_fewshot_cc_k8           (outros)  10                  0         10     1.000             NaN    NaN  1.000
      qwen_qwen3_14b_fewshot_cc_k8         dirty hack  36                  1         36     0.917           0.000 -0.041 -0.038
      qwen_qwen3_14b_fewshot_cc_k8    quick and dirty  27                  9         27     0.815           0.444  0.590  0.516
      qwen_qwen3_14b_fewshot_cc_k8            stopgap  16                  2         16     0.938           0.500  0.683  0.636
      qwen_qwen3_14b_fewshot_cc_k8           temp fix  16                  1         16     0.875           0.000 -0.067 -0.067
      qwen_qwen3_14b_fewshot_cc_k8      temporary fix  56                  1         56     0.929           1.000  0.431  0.313
      qwen_qwen3_14b_fewshot_cc_k8     this is a hack 101                  5        101     0.980           0.600  0.767  0.740
      qwen_qwen3_14b_fewshot_cc_k8          ugly hack  76                  3         76     0.921           0.333  0.219  0.211
      qwen_qwen3_14b_fewshot_cc_k8    ugly workaround  17                  0         17     1.000             NaN    NaN  1.000
      qwen_qwen3_14b_fewshot_cc_k8 workaround for now  16                  2         16     0.938           1.000  0.787  0.765

## Passo 2 — correlação e votos efetivos

Kappa juiz-juiz sobre o alerta:

                             index  x_ai_grok_4_3_fewshot_cc_k8  minimax_minimax_m2_5_fewshot_cc_k8  qwen_qwen3_14b_fewshot_cc_k8
       x_ai_grok_4_3_fewshot_cc_k8                        1.000                               0.697                         0.691
minimax_minimax_m2_5_fewshot_cc_k8                        0.697                               1.000                         0.604
      qwen_qwen3_14b_fewshot_cc_k8                        0.691                               0.604                         1.000

Correlação média entre os vetores de erro: 0.596. Votos efetivamente independentes: **1.37** de 3.

## Passo 3 — regras de agregação

                                            regra  alertas  precisao_alerta  cobertura
melhor juiz sozinho (x_ai_grok_4_3_fewshot_cc_k8)       32            0.500      0.667
                                  maioria simples       32            0.500      0.667
                                ao menos 2 juízes       32            0.500      0.667
                                      unanimidade       19            0.526      0.417

**Regra escolhida: melhor juiz sozinho (x_ai_grok_4_3_fewshot_cc_k8).** votos efetivos = 1.37, abaixo de 2: os juízes erram nos mesmos itens e o painel é redundante. Agregar seria cosmético.

## Passo 4 — detectores externos

DebtHunter e MT-MoE-BERT não entram na votação: o voto deles é assimétrico ("não é SATD" é evidência forte de falso positivo, "é SATD" é evidência fraca). Saem como coluna própria e como variável do agregador, quando houver.
