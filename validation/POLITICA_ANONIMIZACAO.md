# Política de Anonimização e Tratamento de Dados Pessoais — Dataset UBW

**Mandato:** Seção 3 do `PLANO_VALIDACAO_COWORK.md` (Agente D, parte de política) e princípio 3
da Seção 2 ("dois datasets distintos"). **Data:** 2026-07-27.
**Complementa:** `validation/D1_EXPORT_PII_FINDINGS.md` (mecanismo e evidência empírica) e
`scripts/06_export_publishable.py` (implementação). Este documento é a política escrita que
configura aquele mecanismo; a prosa foi redigida para ser aproveitável na dissertação
(Seção de método e Seção de ameaças à validade).
**Âncoras legais e de literatura:** LGPD (Lei nº 13.709/2018), GDPR (Regulamento (UE)
2016/679), Gold & Krinke (2022, EMSE, *Ethics in the mining of software repositories*),
Resoluções CNS 466/2012 e 510/2016 (estas últimas detalhadas em
`validation/CHECKLIST_ETICA_RQ3.md`).

> **Status das decisões.** Este documento distingue, em todo o texto, (i) o que é
> **constatação técnica ou exigência legal** — não negociável — de (ii) o que é
> **recomendação ao orientador**, marcada como `[DECISÃO DO ORIENTADOR]`. Nenhuma
> recomendação aqui é executada unilateralmente; isso segue a mesma disciplina do léxico
> congelado (plano de validação, Seção 2, princípio 4).

---

## 1. Definições operacionais

### 1.1 Anonimização vs. pseudonimização

**Anonimização** é o processo pelo qual o dado perde, de forma **irreversível por meios
razoáveis**, a possibilidade de associação a uma pessoa natural. Dado efetivamente
anonimizado deixa de ser dado pessoal (LGPD, art. 12, *caput*; GDPR, Recital 26: os
princípios de proteção de dados "não se aplicam a informações anônimas"). O teste legal
não é "o pesquisador consegue reverter?", e sim se a reversão é viável por **qualquer
agente**, considerando "todos os meios suscetíveis de serem razoavelmente utilizados"
(Recital 26) — incluindo custo, tempo e tecnologia disponível. A LGPD adota teste
equivalente: o dado anonimizado volta a ser pessoal se o processo de anonimização puder
ser revertido "mediante esforços razoáveis" (art. 12, *caput* e §1º).

**Pseudonimização** é a substituição do identificador direto por um pseudônimo, de modo
que a reassociação **permanece possível** para quem detém informação adicional mantida
separadamente (GDPR, art. 4(5); LGPD, art. 13, §4º — a LGPD define pseudonimização no
capítulo de pesquisa em saúde, mas é a única definição legal do termo na lei brasileira e
é a leitura corrente para pesquisa em geral). O ponto decisivo: **dado pseudonimizado
continua sendo dado pessoal** (GDPR, Recital 26, expressamente; LGPD por simetria com o
art. 12), e portanto continua sujeito a base legal, minimização e direitos do titular.

### 1.2 O que isso implica para dados de commit públicos

Três consequências práticas estruturam toda esta política:

1. **`author_hash` sem salt é pseudonimização, não anonimização.** O SHA-256 do
   e-mail/login normalizado (`ubw/schema.py`, `compute_author_hash`) é determinístico e o
   espaço de entradas é **enumerável publicamente**: qualquer pessoa com uma lista de
   logins/e-mails do GitHub calcula o hash de cada candidato e compara — um ataque de
   dicionário sem custo relevante, que se enquadra com folga em "meios razoáveis"
   (Recital 26). O próprio `schema.py` já registra isso em comentário. Publicar esse hash
   é publicar dado pessoal pseudonimizado.
2. **A origem pública do dado não o torna livre.** Dados de commit são públicos, mas LGPD
   (art. 7º, §§3º–4º) e GDPR não excluem dado publicamente acessível do regime de
   proteção; a publicidade facilita a base legal (legítimo interesse), não a dispensa.
   Gold & Krinke (2022) são explícitos: mineração de repositórios é pesquisa que envolve
   seres humanos, porque os traços minerados são registros de interação de pessoas.
3. **Anonimização perfeita de texto público citável é inatingível.** Qualquer `body_text`
   publicado na íntegra é uma consulta de busca: colar o texto na busca do GitHub recupera
   o commit/issue original e, com ele, o autor. Esse limite é estrutural (Seção 6) e a
   postura correta é declará-lo como limitação, não fingir anonimato que não existe —
   exatamente a postura que Gold & Krinke recomendam para material citável de fontes
   públicas.

Em consequência, esta política **não reivindica anonimização** do dataset publicável.
Reivindica, e documenta: (a) **pseudonimização robusta** do identificador de autor;
(b) **minimização** dos dados pessoais no texto (LGPD art. 6º, III; GDPR art. 5(1)(c));
(c) **transparência** sobre o risco residual.

---

## 2. Os dois datasets

O desenho segue o princípio 3 da Seção 2 do plano de validação: um dataset **de
trabalho** (com PII) e um **publicável** (sem PII bruta). O de trabalho **nunca** é
publicado, versionado em repositório público ou anexado a artefato de replicação.

### 2.1 Dataset de trabalho (restrito)

| Aspecto | Política |
|---|---|
| Conteúdo | Schema completo da Tabela 3.5, incluindo `author_name`, `author_login`, `author_email` e `body_text` bruto |
| Finalidade | (i) contato com autores na survey de RQ3; (ii) auditoria interna (dedup, concentração por autor, forense do Agente C); (iii) extensão humano-vs-IA (plano de validação, Seção 6) |
| Base legal | **Legítimo interesse** para a mineração e guarda (LGPD art. 7º, IX; GDPR art. 6(1)(f)), conforme a leitura consolidada por Gold & Krinke (2022) para mineração de dados públicos de desenvolvimento. O **contato** para a survey muda de base legal — consentimento — e é tratado em `CHECKLIST_ETICA_RQ3.md` |
| Acesso | Restrito ao pesquisador e ao orientador. Sem cópias em serviços de terceiros fora do controle da instituição; sem compartilhamento com outros pesquisadores sem novo juízo de base legal |
| Armazenamento | Fora de controle de versão (já garantido: `data/` e `*.csv` no `.gitignore`); mídia com controle de acesso do sistema operacional; backup segue a mesma restrição |
| Retenção | Guardar por **5 anos** após o término da pesquisa (prazo padrão da Res. CNS 466/2012, item XI.2.f, adotado aqui também para os dados minerados por coerência), depois descarte seguro. `[DECISÃO DO ORIENTADOR]` confirmar o prazo com o CEP na submissão de RQ3 |
| Linha vermelha | **Nenhuma análise publicada centrada em indivíduo identificável** (ranking de autores, caracterização de desempenho individual). Isso configuraria *profiling*, que desloca a base legal para consentimento explícito (Gold & Krinke, 2022; GDPR art. 22 por analogia). Agregações por repositório, categoria e artefato são o formato seguro; estatísticas de concentração por autor (ex.: caso `ableplayer`) só aparecem em relatórios internos de qualidade de dados ou, se publicadas, apenas via pseudônimo e sem atributos que reidentifiquem |

### 2.2 Dataset publicável

| Aspecto | Política |
|---|---|
| Geração | **Exclusivamente** via `scripts/06_export_publishable.py export`, nunca por edição manual do CSV. O manifesto JSON gerado (SHA-256 da entrada, colunas removidas, contagens de máscara por categoria, modo do hash, versão do script) acompanha cada release como trilha de auditoria |
| Colunas removidas | `author_name`, `author_login`, `author_email` (minimização — LGPD art. 6º, III) |
| Identificador de autor | `author_hash` recalculado conforme a decisão da Seção 3 |
| `body_text` | Mascarado conforme a Seção 4 |
| Momento | O export final só é gerado sobre o corpus **consolidado** (fatias A + B), com a varredura de PII re-executada antes (aviso já registrado em `D1_EXPORT_PII_FINDINGS.md` — os números atuais são de coleta parcial, 73.412 linhas) |
| Publicação | Repositório de dados com versionamento e DOI (ex.: Zenodo), com ficha de dataset que declare explicitamente: pseudonimização (não anonimização), política de remoção (Seção 6.2) e contato do responsável |

---

## 3. Decisão de `author_hash`: as três opções e a recomendação

O script 06 implementa três modos, todos testados (`self-test` — ver D1, Seção 1):
**(a)** sem salt (SHA-256 puro, padrão atual), **(b)** `--salt` (SHA-256 de salt +
identificador), **(c)** `--hmac-key` (HMAC-SHA256 com chave secreta). A avaliação abaixo
cruza cada opção com os três requisitos que o mandato impõe.

### 3.1 Requisitos

**R1 — Linkage interno para RQ3.** As análises por autor (e a amostragem de contatos da
survey) exigem que o mesmo autor receba sempre o mesmo pseudônimo dentro do dataset.
**As três opções satisfazem R1 integralmente**, porque as três são funções determinísticas
sobre o identificador normalizado (verificado no self-test: a normalização de case/espaço
de `--salt`/`--hmac-key` é idêntica à de `compute_author_hash`). Em particular, é um erro
comum — que o próprio plano de validação chegou a registrar como trade-off — supor que
salt/HMAC "perde a capacidade de ligar o mesmo autor entre registros": **com chave/salt
fixos, o linkage interno é preservado a 100%**. O que se perde é outra coisa (R3).

**R2 — Contato com autores (RQ3) não passa pelo hash.** Contatar um autor exige o
e-mail dele, e nenhum hash — salgado ou não — fornece e-mail por si. O contato usa o
**dataset de trabalho**, que funciona como tabela de correspondência
`author_hash ↔ (nome, login, e-mail)`. Ou seja: a reversibilidade do hash publicado é
**irrelevante para RQ3**; a capacidade de contato vem de um artefato separado, protegido,
sob custódia do time (GDPR art. 4(5) descreve exatamente essa arquitetura: pseudônimo +
informação adicional "mantida separadamente" e sujeita a medidas técnicas de proteção).
Logo, endurecer o hash não custa nada a RQ3.

**R3 — Extensão humano-vs-IA (plano de validação, Seção 6).** A comparação de resignação
funcional em código humano vs. gerado por IA exige (i) linkage interno estável e
(ii) capacidade de cruzar `author_hash` com metadados de autoria (padrões de bot/agente,
lista de contas conhecidas). Com HMAC, **o time** faz esse cruzamento normalmente —
recalcula o HMAC dos candidatos com a chave, ou consulta a tabela de correspondência.
Um **terceiro** sem a chave não consegue refazer o cruzamento a partir do CSV publicável.
Isso é aceitável porque a extensão é trabalho futuro do próprio grupo, não um requisito
de reprodutibilidade externa; e é precisamente a propriedade de privacidade desejada — se
qualquer terceiro pudesse cruzar, o hash seria reidentificável por definição.

**R4 — Risco de reidentificação por dicionário.** O critério do Recital 26 ("meios
razoáveis"). A lista de candidatos é pública (GitHub); o custo do ataque é o custo de um
hash por candidato.

### 3.2 Avaliação

| | (a) Sem salt | (b) `--salt` | (c) `--hmac-key` |
|---|---|---|---|
| R1 linkage interno | Sim | Sim (salt fixo entre exports) | **Sim (chave fixa entre exports)** |
| R2 contato RQ3 | Indiferente (contato via tabela de correspondência, nas três) | Indiferente | Indiferente |
| R3 extensão humano-vs-IA | Sim, inclusive para terceiros | Sim, para quem tem o salt | **Sim, para o time; não para terceiros (desejável)** |
| R4 dicionário | **Reidentificável trivialmente** — dado pessoal pseudonimizado em forma fraca | Resiste enquanto o salt for secreto e de alta entropia; construção *ad hoc* sem garantia formal | **Resiste por construção** (HMAC é projetado para impedir verificação de candidatos sem a chave), enquanto a chave for secreta |
| Reprodutibilidade externa do hash | Total | Nenhuma sem o salt | Nenhuma sem a chave |
| Precedente legal/técnico | Aceitável **se declarado** como pseudonimização (prática existente na área, ver A_REVISAO_LITERATURA §2.4) | Sem vantagem sobre (c): mesmo custo operacional, garantia mais fraca | Recomendação padrão para pseudonimização robusta de identificadores enumeráveis |

A opção (b) é dominada: exige exatamente a mesma disciplina de custódia que (c) (um
segredo fora do repo, fixo entre exports) e entrega garantia estritamente mais fraca —
SHA-256 com prefixo concatenado é uma construção artesanal, enquanto HMAC-SHA256 tem a
resistência a verificação de candidatos como propriedade de projeto. Não há cenário em
que (b) seja preferível a (c).

A escolha real é entre (a) e (c), e é um trade-off entre **reprodutibilidade externa do
hash** (única vantagem de (a)) e **proteção dos autores** (vantagem de (c)). O peso da
vantagem de (a) é pequeno: nenhum resultado da dissertação depende de um terceiro
recomputar `author_hash` — as análises publicadas usam o hash como fator de agrupamento
opaco, e a auditoria externa da construção do dataset é garantida pelo manifesto e pelo
algoritmo público, não pela reversibilidade do pseudônimo. Já o custo de (a) é publicar
dado pessoal em forma trivialmente reidentificável, o que (i) enfraquece a posição de
minimização perante o CEP na submissão de RQ3 e (ii) transfere aos autores um risco sem
contrapartida científica.

### 3.3 Recomendação `[DECISÃO DO ORIENTADOR]`

**Recomenda-se a opção (c): `--hmac-key`, com chave fixa, aleatória, de no mínimo 256
bits.** Esta é uma recomendação ao orientador, não uma decisão tomada — o export final
não deve ser gerado antes do aval. Se o orientador preferir (a), a condição mínima é
declarar na ficha do dataset, em destaque, que `author_hash` é pseudonimização
reidentificável por dicionário (alternativa registrada como aceitável em
`A_REVISAO_LITERATURA.md`, §2.4, e coerente com a prática publicada da área).

**Regras de custódia (valem se (c) for aprovada):**

1. **Chave HMAC:** gerada uma única vez (ex.: `openssl rand -hex 32`); custodiada pelo
   pesquisador **e** pelo orientador (duas cópias independentes, em gerenciador de senhas
   ou cofre institucional). `[DECISÃO DO ORIENTADOR]` definir o meio concreto de guarda.
2. **Onde a chave NÃO pode estar:** no repositório (nem em branch, nem em histórico),
   em `.env` versionado, em histórico de shell (passar via variável de ambiente ou
   arquivo fora do repo com permissão 600), em CI, em qualquer artefato publicado —
   inclusive no manifesto (o manifesto registra o **modo** `hmac`, nunca a chave).
3. **Tabela de correspondência** (`author_hash ↔` identidade): é o próprio dataset de
   trabalho; se for materializada em arquivo próprio para a operação da survey de RQ3,
   herda integralmente as regras da Seção 2.1 (acesso restrito, fora do repo, retenção,
   descarte). É essa tabela — não o hash — que operacionaliza o contato (R2) e o direito
   de remoção (Seção 6.2).
4. **Estabilidade:** a mesma chave é usada em todos os exports de todas as versões do
   dataset, senão o linkage entre versões quebra. Consequência assumida: se a chave
   vazar, o dataset publicado degrada para o nível de proteção de (b)/(a); a resposta
   seria rotacionar a chave em versões futuras, aceitando a quebra de linkage entre a
   versão antiga e a nova — custo documentado, considerado aceitável dada a baixa
   probabilidade com custódia dupla.
5. **Transparência algorítmica:** a ficha do dataset publica o algoritmo
   (HMAC-SHA256 sobre e-mail > login > nome, normalizado para minúsculas/sem espaços nas
   bordas, conforme `compute_author_hash`) e omite apenas a chave. Auditores externos
   podem verificar a construção do pipeline pelo script 06 (código aberto) e pelo
   manifesto, sem poder reverter pseudônimos.

---

## 4. Política de mascaramento de `body_text` no dataset publicável

### 4.1 Por que mascarar: a evidência de D1

A varredura sobre o corpus parcial (73.412 linhas; `D1_EXPORT_PII_FINDINGS.md`, Seção 2)
mostrou que **remover as colunas `author_*` não basta**: **12,6% das linhas** (9.217)
carregam pelo menos um achado de PII dentro do próprio `body_text`, e a maior fonte
isolada são os **trailers de commit** — 23.250 ocorrências de
`Co-authored-by:`/`Signed-off-by:` com **nome completo + e-mail** (≈46% de todas as
ocorrências mascaradas), frequentemente de **terceiros** (coautores) que nem sequer são o
autor do registro. Somam-se 7.949 e-mails soltos, 18.518 candidatos a `@menção` (teto —
~26% são escopos de pacote npm, falso positivo conhecido), 61 URLs com credencial
embutida e um conjunto pequeno de tokens/chaves (Seção 5). Sem o passe de máscara, o
dataset "sem colunas de autor" republicaria dezenas de milhares de pares nome+e-mail.

### 4.2 O que é mascarado, e por quê

Cada ocorrência é substituída por um placeholder tipado (`[PII_EMAIL_REDACTED]`,
`[PII_COAUTHOR_TRAILER_REDACTED]`, `[PII_TOKEN_..._REDACTED]` etc.), preservando a
estrutura e a legibilidade do texto — o leitor sabe **que havia** um trailer ou um
e-mail ali, sem acesso ao conteúdo. Isso mantém a utilidade analítica (o texto do UBW em
si nunca é o dado mascarado) e cumpre minimização (LGPD art. 6º, III; GDPR art. 5(1)(c)).

| Categoria | Justificativa |
|---|---|
| Trailers `Co-authored-by`/`Signed-off-by` | Nome completo + e-mail, muitas vezes de terceiros; maior volume (23.250) |
| E-mails soltos | Identificador direto (7.949) |
| `@menções` (com filtro de anotações de código e, em iteração futura, de escopos npm `@x/...`) | Identificador de conta; mascarar por excesso é o erro barato — o self-test prova que `@Override`/`@property` sobrevivem |
| URLs com credencial (`user:senha@host`) | Segredo + identificador (61) |
| Tokens/chaves com prefixo estruturado (GitHub PAT, AWS, JWT, `Bearer`, blocos `PRIVATE KEY`) | Segurança, não só privacidade — Seção 5 |

**Princípio de desenho:** na dúvida, mascarar. Falso positivo de máscara custa um
placeholder a mais num texto; falso negativo custa republicar PII ou um segredo. Os
falsos positivos conhecidos (escopos npm em `mention`, parâmetros de URL em `token_jwt`)
estão quantificados em D1 §2.3–2.4 e são aceitos por esse princípio.

### 4.3 Limitações declaradas do mascaramento

Herdam-se as limitações de D1 §2.4, que devem constar da ficha do dataset e da seção de
ameaças à validade: **nomes em texto livre** sem estrutura ("thanks John for the fix")
não são detectados (não há NER no pipeline); **segredos sem prefixo reconhecível**
(`password = "..."` genérico) não são cobertos; a varredura final deve ser re-executada
sobre o corpus consolidado. Complemento de processo: a amostra que passar por anotação
humana (Agente B) serve de verificação por amostragem do mascaramento — anotadores
instruídos a sinalizar PII residual que encontrarem (custo zero, já estarão lendo o
texto).

---

## 5. Segredos vivos (tokens, chaves, credenciais)

Achados de D1: 1 GitHub PAT clássico (`ghp_`), 9 AWS Access Key IDs (8 da mesma issue,
uma URL presignada colada de log de CI), 29 candidatos a JWT (mistura de fixture de
teste, exemplo de bug report e falso positivo), 4 blocos `PRIVATE KEY` (ao menos um
provavelmente payload de ferramenta ofensiva), 4 `Bearer` genéricos, 61 URLs com
credencial. Política:

1. **Não republicar, nunca, em nenhuma forma** — nem truncada. Todo candidato a segredo
   é mascarado no publicável, independentemente de parecer fixture ou expirado
   (indistinguível sem verificação, e verificar é vedado — item 3). D1 já segue esta
   regra nos próprios exemplos do relatório.
2. **Disclosure responsável `[DECISÃO DO ORIENTADOR]`:** para os poucos candidatos com
   plausibilidade de segredo real e vivo (as chaves AWS de
   `ansible-collections/community.aws#637` e `nextcloud/server#40082`, o `ghp_`),
   recomenda-se notificação de boa-fé ao mantenedor do repositório (issue privada ou
   e-mail de segurança do projeto) — o vazamento não é nosso (o dado já está público no
   GitHub, e o *secret scanning* do GitHub provavelmente já revogou o PAT), mas notificar
   é a prática de cidadania da área e custa pouco. Registrar as notificações feitas.
3. **Proibição de teste de validade:** em hipótese alguma testar se uma credencial
   funciona (chamar a API com o token, tentar a URL presignada). Isso seria acesso não
   autorizado a sistema de terceiro — problema legal qualitativamente pior do que
   qualquer questão de dataset.
4. Os números de segredos reportados na dissertação devem ser lidos como "candidatos
   mascarados", não "N segredos vazados" (D1 §2.4).

---

## 6. Ameaças residuais e direitos do titular

### 6.1 Reidentificação por busca do texto — limitação estrutural

Mesmo com colunas de autor removidas, hash HMAC e `body_text` mascarado, **qualquer
registro do dataset publicável é reidentificável por busca**: o texto do commit/issue é
único o suficiente para que uma consulta na busca do GitHub recupere o artefato original
— que carrega autor, avatar e histórico. O campo `url` e `repo_full_name`/`artifact_id`
tornam isso ainda mais direto (e são mantidos deliberadamente: sem eles o dataset perde
verificabilidade e utilidade científica). Não existe mitigação que preserve a utilidade:
parafrasear ou truncar o texto destruiria o objeto de estudo (a expressão de resignação
funcional é o dado).

A postura adotada — alinhada a Gold & Krinke (2022) e à prática dos datasets SATD
publicados, que em sua maioria publicam texto bruto sem sequer discutir o problema — é:

- **declarar a limitação** explicitamente na ficha do dataset e na seção de ameaças à
  validade: o dataset é *pseudonimizado com risco residual de reidentificação inerente à
  natureza pública da fonte*; a proteção efetiva oferecida é contra reidentificação **em
  massa e mecânica** (não há coluna de identidade, não há hash reversível por dicionário),
  não contra reidentificação **pontual e deliberada** de um registro específico;
- compensar com a **linha vermelha de profiling** (Seção 2.1): como nenhuma análise
  publicada caracteriza indivíduos, o dano potencial da reidentificação pontual é o mesmo
  de ler o commit no próprio GitHub — o dataset não agrega informação nova sobre a pessoa,
  apenas seleciona textos já públicos;
- registrar que a alternativa maximalista (não publicar `body_text`) destruiria a
  reprodutibilidade da anotação e a utilidade do dataset — desproporcional dado o risco
  (juízo de balanceamento típico de legítimo interesse, LGPD art. 10).

### 6.2 Direito de remoção

Titulares podem pedir eliminação (LGPD art. 18, IV/VI; GDPR art. 17). Operacionalização:

- canal de contato do responsável na ficha do dataset;
- pedido recebido → localizar registros via tabela de correspondência (Seção 3.3, item 3)
  → excluir as linhas do autor da **próxima versão** do dataset publicado e do dataset de
  trabalho (registro do pedido é mantido, sem os dados, para provar atendimento);
- limitação a declarar: versões já publicadas com DOI podem ter cópias fora de controle;
  o compromisso exequível é a remoção de todas as versões futuras e a solicitação de
  remoção/atualização no repositório de dados. Esse mesmo mecanismo atende o opt-out da
  survey de RQ3 (ver `CHECKLIST_ETICA_RQ3.md`, item 7).

---

## 7. Resumo operacional (ordem de execução)

1. `[DECISÃO DO ORIENTADOR]` aprovar: modo do hash (recomendado: HMAC), meio de custódia
   da chave, prazo de retenção, disclosure dos segredos plausivelmente vivos.
2. Consolidar fatias A + B; re-rodar `scan`; atualizar os números desta política se a
   distribuição de PII mudar materialmente.
3. Gerar chave HMAC e distribuí-la às duas custódias; jamais ao repo.
4. `06_export_publishable.py export --hmac-key ...` sobre o consolidado; arquivar o
   manifesto junto ao release.
5. Publicar com ficha de dataset contendo: declaração de pseudonimização, algoritmo do
   hash (sem a chave), categorias de máscara e contagens (do manifesto), limitação da
   Seção 6.1, canal e política de remoção da Seção 6.2.
6. Survey de RQ3 só após CEP (`CHECKLIST_ETICA_RQ3.md`).
