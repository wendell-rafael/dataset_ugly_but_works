# Estrutura do dataset UBW de comentários de código

## Objetivo

Esta análise verifica se o recorte de comentários de código está organizado de
forma adequada para publicação e reúso. A comparação considera datasets de SATD
que já foram publicados e olha para a unidade de registro, contexto, localização,
rastreabilidade, rótulos, evolução temporal e documentação.

O recorte publicado contém 26.029 registros de 9.584 repositórios, distribuídos
em 42 linguagens principais. Foram observadas 24 das 25 expressões do léxico.
A data de corte da coleta é 23 de julho de 2026.

## Resultado da auditoria

| Verificação | Resultado | Avaliação |
|---|---:|---|
| Campos essenciais sem valores ausentes | 100% | adequado |
| `artifact_id` convertido em caminho e linha | 26.029/26.029 | adequado |
| URL convertida em repositório, commit, caminho e linha | 26.029/26.029 | adequado |
| URL coerente com os demais campos | 26.029/26.029 | adequado |
| Identificador estável e único após incluir a introdução | 26.029/26.029 | adequado |
| Contradições entre introdução, remoção e censura | 0 | adequado |
| Remoções com contagem de commits | 13.840/13.840 | adequado |
| Contextos em que a expressão permanece visível no arquivo publicado | 26.029/26.029 (100%) | adequado |
| Contextos limitados a exatamente 2.000 caracteres | 525/26.029 (2,0%) | precisa ser declarado |
| Contextos idênticos presentes em mais de um repositório | 7.390/26.029 (28,4%) | exige controle nas análises |
| Ocorrências de PII mascaradas no candidato de release | 993 | corrigido no export |

Uma checagem inicial apontou 816 contextos sem expressão visível. Desses, 245 já
continham a frase, mas ela estava colada ao token seguinte em código compactado
ou gerado. Outros 571 foram reconstruídos diretamente do arquivo no commit de
introdução. Em 68 reparos, a linha publicada foi corrigida para a localização
confirmada, enquanto `line_number_at_collection` preserva o valor original.

Depois do reparo, 26.029 dos 26.036 registros originais exibem a expressão. Os
sete casos restantes coincidiam com conteúdo removido pela máscara de
privacidade e foram excluídos do arquivo publicado. Nenhum deles pertencia à
amostra humana de 379 itens, portanto a estimativa de precisão não foi alterada.

Os textos repetidos entre repositórios aparecem sobretudo em forks e bibliotecas
copiadas. Eles representam ocorrências reais nos repositórios, mas não devem ser
tratados automaticamente como admissões independentes. O candidato de release
inclui `context_sha256` e `repositories_with_same_context`, permitindo agrupar ou
filtrar essas cópias.

## Comparação com datasets publicados

| Dataset | Escopo | Estrutura principal | Pontos fortes | Limitações para reúso |
|---|---|---|---|---|
| PENTACET | 23 milhões de comentários de 9.096 projetos Java | O TSV leve tem `comment_id` e `comment_content`; os dumps completos incluem contexto anterior e posterior e atributos da estrutura do código | escala, contexto bidirecional e grande cobertura de projetos | o arquivo leve perde quase todos os metadados; tamanho dos dumps completos dificulta o uso |
| CppSATD | 531.367 comentários de 5 projetos C++ | sete campos: id, texto do comentário, código anterior, código posterior, arquivo, projeto e anotação | separa comentário e contexto e fornece rótulo por linha | cobre uma linguagem e poucos projetos; os dados do depósito consultado estão com acesso restrito |
| SATD em software científico | 28.680 comentários de 9 projetos | arquivo, comentário, projeto, categoria, categoria científica, introdução e remoção | combina rótulo temático e ciclo de vida | não oferece commit, linha, URL ou contexto de código separado |
| Li et al., quatro fontes | comentários Java de 10 projetos no arquivo usado para treino | projeto, texto e classificação | formato simples e pronto para classificação supervisionada | não informa localização, commit, contexto ou ciclo de vida |
| SATDAUG | dados originais e aumentados de quatro fontes | status, texto e classificação | identifica exemplos sintéticos e oferece dados balanceados | é voltado ao treino de classificadores, sem rastreabilidade até o código |
| UBW code comments, candidato v1.0 | 26.029 ocorrências de 9.584 repositórios e 42 linguagens | 23 campos no corpus e 6 no arquivo de validação | grande diversidade de projetos e linguagens, permalink, caminho, linha, commit, expressão, contexto, introdução, remoção, duração e amostra humana ligada por id | não separa o comentário completo do código ao redor; o rótulo humano existe para a amostra, não para cada uma das 26.029 linhas |

Fontes consultadas:

- [PENTACET no Zenodo](https://zenodo.org/records/7757462)
- [Artigo do PENTACET](https://arxiv.org/abs/2303.14029)
- [CppSATD no Zenodo](https://zenodo.org/records/15211740)
- [Descritor do CppSATD](https://doi.org/10.1109/IEEEDATA.2025.3576339)
- [SATD em software científico](https://zenodo.org/records/13174322)
- [Dataset de SATD em quatro fontes](https://github.com/yikun-li/satd-different-sources-data)
- [SATDAUG](https://zenodo.org/records/10521909)

## Avaliação

A estrutura do UBW é suficiente para publicação e está acima dos datasets que
fornecem apenas projeto, texto e classe. O principal diferencial é a ligação de
cada ocorrência a um ponto específico do histórico do repositório. A combinação
de caminho, linha, commit de introdução e permalink permite conferir o registro,
enquanto as datas e as durações permitem estudar o ciclo de vida.

Ela ainda não alcança a separação de contexto do PENTACET e do CppSATD. O
`code_context` é uma janela de código, não o comentário isolado. Isso deve aparecer
no nome da coluna e no dicionário de dados. Uma versão futura pode guardar
separadamente o comentário completo, o código anterior e o código posterior.

Também é necessário deixar claro que as 26.029 linhas são candidatos encontrados
pelo léxico. A anotação humana cobre uma amostra aleatória de 379 itens, com 351
UBW e 28 falsos positivos por maioria dos três anotadores. A precisão estimada é
92,6%, com intervalo de Wilson de 95% entre 89,5% e 94,8%. Esse número descreve o
conjunto; não transforma as linhas não amostradas em rótulos manuais individuais.

## Estrutura recomendada para o Zenodo

O release foi gerado em `release/ubw-code-comments-v1.0.0/`.
Ele contém:

1. `ubw_code_comments.csv`, com os 26.029 registros, contexto mascarado e campos
   derivados explícitos;
2. `human_validation_379.csv`, com os três votos e o gabarito por maioria;
3. `data_dictionary.csv`, com a definição de cada coluna;
4. `manifest.json`, com origem, data de corte, contagens e hashes SHA-256.

O export remove nomes, logins, e-mails e hashes de autores. Também remove
`repo_age_days`, cuja interpretação não é confiável no recorte, e a categoria
A/B/C, que não faz parte da definição final do dataset. O arquivo passou pela
checagem automática de e-mails e colunas pessoais.

O pacote já inclui README, licença de dados CC BY 4.0, dicionário, léxico,
manifesto de amostragem e hashes dos arquivos. Antes do depósito definitivo,
O encerramento da coleta foi registrado em 23 de julho de 2026, com escopo
restrito a `code_comment`, e o pacote foi promovido para a versão 1.0.0. A
exclusão dos sete contextos ocultos está registrada no manifesto. Restam os
metadados editoriais do depósito e a revisão do rascunho no Zenodo.
