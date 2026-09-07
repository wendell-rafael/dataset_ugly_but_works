# Procedência da anotação humana — amostra `code_comment` (n=269)

## Arquivos

Em `brutos/`, marcados somente-leitura (`chmod 444`). Não editar no lugar: se
precisar corrigir algo, gerar um arquivo novo com sufixo e registrar aqui.

| arquivo | sha256 | positivos |
|---|---|---|
| `anotacao_code_comment_Wendell.csv` | `34b906f9…4a76e3d4` | 243 / 269 |
| `anotacao_code_comment_Bruno.csv` | `935683bf…15ebd3ad` | 249 / 269 |
| `anotacao_code_comment_Miguel.csv` | `7b58ca7d…4d8273c9` | 250 / 269 |

Recebidos em 07/09/2026. Exportados pela UI gerada por
`scripts/12_build_annotation_ui.py`; a UI exige rótulo **e** observação em todo
item antes de liberar o avanço, o que explica zero campos vazios nos três.

Integridade conferida por `scripts/13_merge_code_comment.py`: 269/269 itens em
cada arquivo, `item_id` coincidindo com `amostra_code_comment.csv`, sem
duplicata, sem rótulo vazio, sem observação vazia.

## Resolvido: o ajuste no arquivo do Bruno era bug de exportação

O CSV do Bruno foi enviado duas vezes. A versão de 04/09 tinha 252 positivos; a
de 07/09, salva aqui, tem 249. Diferem em três itens, e **somente** neles:

| item | expressão | 04/09 | 07/09 | Miguel | Wendell |
|---|---|---|---|---|---|
| `cc0002` | `temp fix` | True | False | False | False |
| `cc0020` | `this is a hack` | True | False | False | False |
| `cc0049` | `stopgap` | True | False | False | False |

As três mudanças vão na mesma direção e as três caem sobre o voto dos outros
dois anotadores. Efeito no κ:

| | pré-ajuste | recebido |
|---|---|---|
| Wendell × Bruno | 0,723 | 0,810 |
| Bruno × Miguel | 0,702 | 0,807 |
| Wendell × Miguel | 0,831 | 0,831 |
| Fleiss (3) | 0,755 | 0,816 |

Sem o ajuste nenhum par atinge 0,80; com ele, todos atingem.

**Origem registrada em 07/09/2026: bug de exportação**, informado por Wendell
Nascimento. A versão de 04/09 saiu da ferramenta com esses três rótulos
errados; a de 07/09 é a que reflete o julgamento do anotador. Os votos seguem
independentes, então **κ de Fleiss = 0,816 é a estatística de confiabilidade
reportável**, e o cenário `recebido` é o oficial.

Duas ressalvas que ficam registradas por honestidade metodológica, não por
dúvida sobre o relato:

1. A causa foi **declarada, não verificada independentemente** — não há log da
   ferramenta que comprove o defeito, e os arquivos de 04/09 foram
   sobrescritos. Se um revisor pedir evidência, o que existe é este registro.
2. O padrão das três mudanças (mesma direção, todas caindo sobre o consenso dos
   outros dois, nenhuma outra célula alterada) é **compatível com** bug de
   exportação, mas também com revisão pós-discussão. Não distingue os dois.

Por isso `scripts/13_merge_code_comment.py` continua calculando e gravando os
**dois cenários** (`recebido` e `pre_ajuste_bruno`) em todos os arquivos de
saída, com `cenario_oficial: "recebido"` no `resumo.json`. O número
conservador (0,755) fica disponível sem precisar reexecutar nada, caso a
discussão com o orientador recomende reportá-lo.

## O que não depende da pendência

O gold por maioria é **idêntico** nos dois cenários: 247 positivos, 22
negativos. Wendell e Miguel já votavam `False` nos três itens em questão, então
a maioria nunca dependeu do voto do Bruno neles.

Precisão do léxico em `code_comment`: **91,8%** (247/269), IC95 de Wilson
[87,9 % – 94,5 %]. Vale nos dois cenários. O resultado central do trilho de
validação humana está firme independentemente de como o ajuste se resolva — a
pendência afeta só a estatística de confiabilidade.

## Assimetria entre anotadores

Wendell aplica um limiar mais restritivo, de forma consistente e não simétrica:

- Wendell × Bruno: 7 itens "Wendell False / Bruno True" contra **1** no inverso
- Wendell × Miguel: 7 itens "Wendell False / Miguel True" contra **0** no inverso

Não é ruído distribuído nos dois sentidos. Combina com o achado do trilho B, em
que os 10 modelos avaliados concordavam menos com Wendell e mais com Bruno.
Candidato a parágrafo na seção de ameaças à validade, e motivo para revisar se
o guia de anotação está deixando margem para um critério mais estrito do que o
que está escrito nele.

## Divergência residual

11 itens não-unânimes (4,1 %), concentrados nas mesmas expressões da rodada
multi-artefato:

`quick and dirty` (4) · `temporary fix` (2) · `temp fix` (1) ·
`workaround for now` (1) · `dirty hack` (1) · `dirty workaround` (1) ·
`this is a hack` (1)

Itens: `cc0034 cc0039 cc0101 cc0127 cc0156 cc0173 cc0176 cc0180 cc0224
cc0237 cc0249`. Lista completa com votos e observações em
`../analise/nao_unanimes.csv`.

A concentração em `quick and dirty` e nas variantes de `temp fix` repete o
padrão anterior, o que aponta regra de decisão faltando no guia — não
desatenção. A distinção que parece estar em jogo: a expressão descreve *o
código presente* ou *um plano futuro de conserto*?
