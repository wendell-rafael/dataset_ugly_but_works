# Relatório descritivo do corpus UBW

Gerado de `/home/wendell/Documentos/dataset_ugly_but_works/data/full_run/ubw_collected_consolidated.csv`.
Números sujeitos a mudança até o congelamento do snapshot v1.0.

## Visão geral

| Métrica                                   | Valor      |
|:------------------------------------------|:-----------|
| Registros no corpus bruto                 | 116,192    |
| Repositórios no corpus bruto              | 26,667     |
| Registros no escopo                       | 91,458     |
| Repositórios com ao menos uma ocorrência  | 21,553     |
| Expressões do léxico                      | 25         |
| Expressões com ao menos uma ocorrência    | 25         |
| Linguagens principais distintas           | 44         |
| Primeira ocorrência                       | 1970-01-01 |
| Última ocorrência                         | 2026-07-23 |
| Comprimento mediano do texto (caracteres) | 275        |

## Por tipo de artefato

| artifact_type   |   registros |   repositorios |   chars_mediana |   chars_p90 |   participacao |
|:----------------|------------:|---------------:|----------------:|------------:|---------------:|
| commit_message  |       43351 |          13349 |             133 |         986 |         0.474  |
| code_comment    |       26036 |           9584 |             304 |         468 |         0.2847 |
| pr_body         |       22071 |           9557 |             588 |        2600 |         0.2413 |

## Por expressão

| matched_expression        |   registros |   repositorios |   participacao |
|:--------------------------|------------:|---------------:|---------------:|
| temporary fix             |       33660 |          11467 |        0.368   |
| temp fix                  |       11631 |           5296 |        0.1272  |
| this is a hack            |        9111 |           4215 |        0.09962 |
| ugly hack                 |        8443 |           3867 |        0.09232 |
| quick and dirty           |        8273 |           4726 |        0.09046 |
| stopgap                   |        8064 |           3368 |        0.08817 |
| dirty hack                |        4726 |           2641 |        0.05167 |
| workaround for now        |        2225 |           1504 |        0.02433 |
| ugly workaround           |        2044 |           1375 |        0.02235 |
| band-aid fix              |         962 |            586 |        0.01052 |
| dirty workaround          |         784 |            591 |        0.00857 |
| ugly but it works         |         358 |            313 |        0.00391 |
| ugly but works            |         277 |            233 |        0.00303 |
| hacky but works           |         270 |            235 |        0.00295 |
| not pretty but it works   |         179 |            148 |        0.00196 |
| not ideal but it works    |         107 |             89 |        0.00117 |
| ugly solution but         |          83 |             76 |        0.00091 |
| ugly code but             |          78 |             68 |        0.00085 |
| duct tape fix             |          62 |             36 |        0.00068 |
| crude but it works        |          42 |             36 |        0.00046 |
| messy but works           |          33 |             32 |        0.00036 |
| hope everything will work |          19 |             19 |        0.00021 |
| not elegant but works     |          17 |             15 |        0.00019 |
| horrible but works        |           7 |              5 |        8e-05   |
| terrible but works        |           3 |              2 |        3e-05   |

## Concentração por repositório

| Métrica                                         | Valor         |
|:------------------------------------------------|:--------------|
| Repositórios com ocorrência                     | 21,553        |
| Ocorrências por repositório, mediana            | 2             |
| Ocorrências por repositório, média              | 4.2           |
| Ocorrências por repositório, p90                | 9             |
| Ocorrências por repositório, máximo             | 432           |
| Repositórios com exatamente 1 ocorrência        | 9,094 (42.2%) |
| Repositórios com 3 ou mais (subconjunto de RQ2) | 8,263 (38.3%) |
| Participação dos 10 maiores repositórios        | 2.72%         |
| Participação dos 1% maiores                     | 16.70%        |

## Distribuição temporal

|   ano |   registros |   repositorios |   participacao |
|------:|------------:|---------------:|---------------:|
|  1970 |           1 |              1 |         0      |
|  1987 |           1 |              1 |         0      |
|  1988 |           1 |              1 |         0      |
|  1990 |           4 |              3 |         0      |
|  1993 |          10 |              4 |         0.0001 |
|  1994 |          10 |              8 |         0.0001 |
|  1995 |          25 |             12 |         0.0003 |
|  1996 |          25 |             15 |         0.0003 |
|  1997 |          27 |             11 |         0.0003 |
|  1998 |          87 |             29 |         0.001  |
|  1999 |         166 |             59 |         0.0018 |
|  2000 |         182 |             65 |         0.002  |
|  2001 |         234 |            100 |         0.0026 |
|  2002 |         265 |            115 |         0.0029 |
|  2003 |         361 |            163 |         0.0039 |
|  2004 |         435 |            189 |         0.0048 |
|  2005 |         523 |            232 |         0.0057 |
|  2006 |         636 |            299 |         0.007  |
|  2007 |         714 |            351 |         0.0078 |
|  2008 |        1071 |            459 |         0.0117 |
|  2009 |        1372 |            581 |         0.015  |
|  2010 |        1465 |            674 |         0.016  |
|  2011 |        1751 |            859 |         0.0191 |
|  2012 |        2184 |           1063 |         0.0239 |
|  2013 |        2686 |           1342 |         0.0294 |
|  2014 |        3226 |           1675 |         0.0353 |
|  2015 |        3907 |           2009 |         0.0427 |
|  2016 |        4343 |           2203 |         0.0475 |
|  2017 |        4592 |           2451 |         0.0502 |
|  2018 |        5024 |           2724 |         0.0549 |
|  2019 |        5449 |           2991 |         0.0596 |
|  2020 |        6453 |           3639 |         0.0706 |
|  2021 |        6771 |           3855 |         0.074  |
|  2022 |        7130 |           3874 |         0.078  |
|  2023 |        8345 |           4406 |         0.0912 |
|  2024 |        8818 |           4389 |         0.0964 |
|  2025 |        8176 |           4089 |         0.0894 |
|  2026 |        4988 |           2612 |         0.0545 |

## Evento de remoção, por artefato

| artefato       |   registros |   evento_observado |   taxa_evento |   dias_mediana_ate_evento | significado_do_evento                                 |
|:---------------|------------:|-------------------:|--------------:|--------------------------:|:------------------------------------------------------|
| commit_message |       43351 |                  0 |        0      |                       nan | fechamento/merge do artefato, NÃO é remoção de dívida |
| code_comment   |       26036 |              13846 |        0.5318 |                        83 | remoção do comentário (git log -S)                    |
| pr_body        |       22071 |              21436 |        0.9712 |                         0 | fechamento/merge do artefato, NÃO é remoção de dívida |

O evento só significa remoção de dívida em `code_comment`, onde vem do pareamento de eventos `+` e `-` do `git log -S`. Em `pr_body` é merge ou fechamento do pull request. Curva de Kaplan-Meier em `07_km_code_comment.csv`, restrita a `code_comment`.

## Linguagens principais

| primary_language   |   registros |   repositorios |   participacao |
|:-------------------|------------:|---------------:|---------------:|
| C++                |       17080 |           2403 |         0.1868 |
| Python             |       16344 |           4324 |         0.1787 |
| TypeScript         |       10983 |           2876 |         0.1201 |
| C                  |        8393 |           1571 |         0.0918 |
| Java               |        7123 |           1468 |         0.0779 |
| JavaScript         |        5856 |           1717 |         0.064  |
| Go                 |        5742 |           1521 |         0.0628 |
| Rust               |        3934 |           1206 |         0.043  |
| C#                 |        2626 |            723 |         0.0287 |
| PHP                |        2279 |            614 |         0.0249 |
| Ruby               |        2020 |            448 |         0.0221 |
| Kotlin             |        1020 |            321 |         0.0112 |
| Shell              |         912 |            313 |         0.01   |
| Lua                |         667 |            163 |         0.0073 |
| Scala              |         647 |            172 |         0.0071 |

## Precisão do léxico na amostra humana

| corte            | valor          |   n |   positivos |   precisao |   ic95_low |   ic95_high |   largura_pp |
|:-----------------|:---------------|----:|------------:|-----------:|-----------:|------------:|-------------:|
| Global           | todos          | 385 |         357 |     0.9273 |     0.8969 |      0.9492 |          5.2 |
| tipo de artefato | code_comment   | 110 |         104 |     0.9455 |     0.8861 |      0.9748 |          8.9 |
| tipo de artefato | commit_message | 182 |         169 |     0.9286 |     0.8816 |      0.9578 |          7.6 |
| tipo de artefato | pr_body        |  93 |          84 |     0.9032 |     0.8262 |      0.9482 |         12.2 |

## Figuras

- `figuras/temporal.png`
- `figuras/top_expressoes.png`
- `figuras/sobrevivencia_code_comment.png`
