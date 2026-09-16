# Relatório descritivo do corpus UBW

Gerado de `/home/wendell/Documentos/dataset_ugly_but_works/data/full_run/ubw_collected_consolidated.csv`.
Números sujeitos a mudança até o congelamento do snapshot v1.0.

## Visão geral

| Métrica                                   | Valor        |
|:------------------------------------------|:-------------|
| Registros no corpus bruto                 | 116,192      |
| Repositórios no corpus bruto              | 26,667       |
| Registros no frame (sem issue_body)       | 91,458       |
| Escopo do relatório                       | code_comment |
| Participação do escopo no frame           | 28.5%        |
| Registros no escopo                       | 26,036       |
| Repositórios com ao menos uma ocorrência  | 9,584        |
| Expressões do léxico                      | 25           |
| Expressões com ao menos uma ocorrência    | 24           |
| Linguagens principais distintas           | 42           |
| Primeira ocorrência                       | 1990-06-05   |
| Última ocorrência                         | 2026-07-23   |
| Comprimento mediano do texto (caracteres) | 304          |

## Por tipo de artefato

| artifact_type   |   registros |   repositorios |   chars_mediana |   chars_p90 |   participacao |
|:----------------|------------:|---------------:|----------------:|------------:|---------------:|
| code_comment    |       26036 |           9584 |             304 |         468 |              1 |

## Por expressão

| matched_expression        |   registros |   repositorios |   participacao |
|:--------------------------|------------:|---------------:|---------------:|
| this is a hack            |        6741 |           3259 |        0.2589  |
| temporary fix             |        5063 |           2934 |        0.1945  |
| ugly hack                 |        4840 |           2538 |        0.1859  |
| dirty hack                |        2665 |           1605 |        0.1024  |
| quick and dirty           |        1802 |           1219 |        0.06921 |
| temp fix                  |        1269 |            836 |        0.04874 |
| stopgap                   |        1168 |            760 |        0.04486 |
| ugly workaround           |         955 |            677 |        0.03668 |
| workaround for now        |         774 |            550 |        0.02973 |
| dirty workaround          |         319 |            239 |        0.01225 |
| hacky but works           |         110 |             94 |        0.00422 |
| ugly but works            |          91 |             65 |        0.0035  |
| ugly but it works         |          82 |             65 |        0.00315 |
| band-aid fix              |          66 |             54 |        0.00253 |
| not ideal but it works    |          19 |             12 |        0.00073 |
| ugly code but             |          14 |             12 |        0.00054 |
| hope everything will work |          14 |             14 |        0.00054 |
| ugly solution but         |          11 |             10 |        0.00042 |
| crude but it works        |           8 |              8 |        0.00031 |
| not elegant but works     |           7 |              6 |        0.00027 |
| not pretty but it works   |           6 |              5 |        0.00023 |
| messy but works           |           5 |              5 |        0.00019 |
| horrible but works        |           4 |              2 |        0.00015 |
| duct tape fix             |           3 |              3 |        0.00012 |
| terrible but works        |           0 |              0 |        0       |

## Concentração por repositório

| Métrica                                         | Valor         |
|:------------------------------------------------|:--------------|
| Repositórios com ocorrência                     | 9,584         |
| Ocorrências por repositório, mediana            | 1             |
| Ocorrências por repositório, média              | 2.7           |
| Ocorrências por repositório, p90                | 6             |
| Ocorrências por repositório, máximo             | 99            |
| Repositórios com exatamente 1 ocorrência        | 4,976 (51.9%) |
| Repositórios com 3 ou mais (subconjunto de RQ2) | 2,754 (28.7%) |
| Participação dos 10 maiores repositórios        | 2.37%         |
| Participação dos 1% maiores                     | 10.97%        |

## Distribuição temporal

|   ano |   registros |   repositorios |   participacao |
|------:|------------:|---------------:|---------------:|
|  1990 |           4 |              3 |         0.0002 |
|  1993 |           4 |              2 |         0.0002 |
|  1994 |           6 |              5 |         0.0002 |
|  1995 |           2 |              2 |         0.0001 |
|  1996 |          10 |             10 |         0.0004 |
|  1997 |           4 |              4 |         0.0002 |
|  1998 |          35 |             15 |         0.0013 |
|  1999 |          32 |             25 |         0.0012 |
|  2000 |          54 |             35 |         0.0021 |
|  2001 |          76 |             46 |         0.0029 |
|  2002 |          92 |             51 |         0.0035 |
|  2003 |         125 |             70 |         0.0048 |
|  2004 |         186 |            106 |         0.0071 |
|  2005 |         189 |            110 |         0.0073 |
|  2006 |         220 |            144 |         0.0084 |
|  2007 |         305 |            178 |         0.0117 |
|  2008 |         409 |            246 |         0.0157 |
|  2009 |         542 |            301 |         0.0208 |
|  2010 |         566 |            336 |         0.0217 |
|  2011 |         674 |            406 |         0.0259 |
|  2012 |         861 |            510 |         0.0331 |
|  2013 |         900 |            558 |         0.0346 |
|  2014 |        1104 |            723 |         0.0424 |
|  2015 |        1243 |            854 |         0.0477 |
|  2016 |        1364 |            908 |         0.0524 |
|  2017 |        1352 |            899 |         0.0519 |
|  2018 |        1405 |           1007 |         0.054  |
|  2019 |        1505 |           1039 |         0.0578 |
|  2020 |        1700 |           1214 |         0.0653 |
|  2021 |        1648 |           1178 |         0.0633 |
|  2022 |        1732 |           1203 |         0.0665 |
|  2023 |        2132 |           1441 |         0.0819 |
|  2024 |        2458 |           1462 |         0.0944 |
|  2025 |        2161 |           1373 |         0.083  |
|  2026 |         936 |            637 |         0.036  |

## Evento de remoção, por artefato

| artefato     |   registros |   evento_observado |   taxa_evento |   dias_mediana_ate_evento | significado_do_evento              |
|:-------------|------------:|-------------------:|--------------:|--------------------------:|:-----------------------------------|
| code_comment |       26036 |              13846 |        0.5318 |                        83 | remoção do comentário (git log -S) |

O evento só significa remoção de dívida em `code_comment`, onde vem do pareamento de eventos `+` e `-` do `git log -S`. Em `pr_body` é merge ou fechamento do pull request. Curva de Kaplan-Meier em `07_km_code_comment.csv`, restrita a `code_comment`.

## Linguagens principais

| primary_language   |   registros |   repositorios |   participacao |
|:-------------------|------------:|---------------:|---------------:|
| C++                |        5786 |           1574 |         0.2222 |
| Python             |        5078 |           2133 |         0.195  |
| TypeScript         |        3247 |           1390 |         0.1247 |
| C                  |        3023 |            953 |         0.1161 |
| Java               |        2780 |            858 |         0.1068 |
| JavaScript         |        1811 |            861 |         0.0696 |
| Go                 |        1788 |            765 |         0.0687 |
| Ruby               |         506 |            192 |         0.0194 |
| Rust               |         366 |            136 |         0.0141 |
| PHP                |         295 |            149 |         0.0113 |
| Kotlin             |         195 |             68 |         0.0075 |
| Jupyter Notebook   |         191 |             98 |         0.0073 |
| C#                 |         183 |             88 |         0.007  |
| Julia              |         102 |              3 |         0.0039 |
| Scala              |          72 |             50 |         0.0028 |

## Precisão do léxico na amostra humana

| corte   | valor   |   n |   positivos |   precisao |   ic95_low |   ic95_high |   largura_pp |
|:--------|:--------|----:|------------:|-----------:|-----------:|------------:|-------------:|
| Global  | todos   | 379 |         351 |     0.9261 |     0.8953 |      0.9484 |          5.3 |

## Figuras

- `figuras/temporal.png`
- `figuras/top_expressoes.png`
- `figuras/sobrevivencia_code_comment.png`
