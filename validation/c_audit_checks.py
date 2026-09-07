#!/usr/bin/env python3
"""Agente C — Auditor de Mineração (validade interna do dataset UBW).

Forense de dados sobre o CSV coletado (schema da Tabela 3.5 / `ubw/schema.py`),
independente da anotação humana. Responde "a coleta capturou o que diz que
capturou?" — não "o item é mesmo UBW?" (isso é o Agente B).

Roda as checagens do mandato do Agente C (PLANO_VALIDACAO_COWORK.md, Seção
"Agente C"):

    1. Sanidade temporal (time_to_event_days, removed_at/created_at, is_censored)
    2. Amostragem para verificação de remoção acidental vs. real (Zampetti et al.,
       2018) — imprime a amostra e o procedimento; só verifica de fato se
       --live-checks estiver ligado E houver rede/token disponíveis.
    3. Deduplicação em escala (dentro de repo+artefato e ENTRE artefatos)
    4. Contas automatizadas (bots) — quantifica o que o filtro atual deixa
       passar
    5. Efetividade do filtro de path vendorizado — heurística estática sobre
       nomes de biblioteca conhecidos que não seguem a convenção de path do
       filtro oficial (`ubw/lexicon.py::is_vendored_path`)
    6. Reprodutibilidade — descreve o procedimento; roda de fato se
       --live-checks estiver ligado e clones locais/API estiverem acessíveis

IMPORTANTE: este script é DE LEITURA. Nunca escreve no CSV de coleta nem no
collection_state.json. Qualquer correção sugerida aqui é código (patch nos
scripts 02/lexicon), nunca edição manual do dataset.

Reexecutável no corpus consolidado (fatia A + fatia B) assim que a coleta
terminar — é por isso que todas as checagens são parametrizadas por --csv e
não hard-codeiam o caminho do full_run.

Uso:
    python validation/c_audit_checks.py --csv data/full_run/ubw_collected_full.csv
    python validation/c_audit_checks.py --csv data/full_run/ubw_collected_full.csv --out-json validation/audit_flags.json
"""
from __future__ import annotations

import argparse
import csv as csv_module
import json
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

csv_module.field_size_limit(10_000_000)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from ubw import lexicon  # noqa: E402
except ImportError:
    lexicon = None  # permite rodar checagens que não dependem do léxico


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def load_dataset(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, engine="python", on_bad_lines="warn")
    df["_created"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df["_removed"] = pd.to_datetime(df["removed_at"], errors="coerce", utc=True)
    df["_body_norm"] = df["body_text"].astype(str).str.strip().str.lower()
    return df


class Flag:
    """Um achado quantificado, com severidade e exemplos concretos."""

    def __init__(self, check: str, description: str, count: int, total: int,
                 severity: str, examples: Optional[list] = None, note: str = ""):
        self.check = check
        self.description = description
        self.count = count
        self.total = total
        self.pct = (count / total * 100) if total else 0.0
        self.severity = severity  # "info" | "baixa" | "média" | "alta"
        self.examples = examples or []
        self.note = note

    def to_dict(self) -> dict:
        return {
            "check": self.check, "description": self.description,
            "count": self.count, "total": self.total, "pct": round(self.pct, 2),
            "severity": self.severity, "examples": self.examples, "note": self.note,
        }

    def print(self) -> None:
        print(f"\n[{self.severity.upper()}] {self.check}: {self.description}")
        print(f"    {self.count}/{self.total} ({self.pct:.2f}%)")
        if self.note:
            print(f"    nota: {self.note}")
        for ex in self.examples[:5]:
            print(f"    ex: {ex}")


# ---------------------------------------------------------------------------
# CHECK 1 — Sanidade temporal
# ---------------------------------------------------------------------------

def check_temporal_sanity(df: pd.DataFrame) -> list[Flag]:
    flags = []
    total = len(df)

    neg = df[df["time_to_event_days"] < 0]
    flags.append(Flag(
        "1.1 time_to_event_days negativo", "registros com tempo até evento negativo (impossível)",
        len(neg), total, "alta" if len(neg) else "info",
        examples=neg[["repo_full_name", "artifact_type", "artifact_id"]].head(5).to_dict("records"),
    ))

    zero = df[df["time_to_event_days"] == 0]
    by_type = zero["artifact_type"].value_counts().to_dict()
    flags.append(Flag(
        "1.2 time_to_event_days == 0", "registros com evento no mesmo dia da introdução",
        len(zero), total, "baixa",
        note=f"concentração por artifact_type: {by_type} — pr_body costuma ter fração alta "
             f"(merges rápidos, inclusive PRs de bot); não é bug por si só, mas junto com o "
             f"CHECK 4 (bots) pode indicar 'eventos' triviais infláveis.",
    ))

    removed_before = df[(df["_removed"].notna()) & (df["_created"].notna()) & (df["_removed"] < df["_created"])]
    flags.append(Flag(
        "1.3 removed_at < created_at", "remoção registrada antes da introdução (impossível)",
        len(removed_before), total, "alta" if len(removed_before) else "info",
        examples=removed_before[["repo_full_name", "artifact_type", "artifact_id", "created_at", "removed_at"]]
        .head(5).to_dict("records"),
    ))

    censored_with_removed = df[(df["is_censored"] == 1) & (df["_removed"].notna())]
    flags.append(Flag(
        "1.4 is_censored=1 com removed_at preenchido", "incoerência censura/remoção",
        len(censored_with_removed), total, "alta" if len(censored_with_removed) else "info",
    ))

    notcensored_no_removed = df[(df["is_censored"] == 0) & (df["_removed"].isna())]
    flags.append(Flag(
        "1.5 is_censored=0 com removed_at nulo", "incoerência censura/remoção (evento sem data)",
        len(notcensored_no_removed), total, "alta" if len(notcensored_no_removed) else "info",
    ))

    absurd = df[(df["time_to_event_days"].notna()) & (df["repo_age_days"].notna())
                & (df["time_to_event_days"] > df["repo_age_days"])]
    by_type_absurd = absurd["artifact_type"].value_counts().to_dict()
    epoch = df[df["created_at"].astype(str).str.startswith("1970-01-01")]
    flags.append(Flag(
        "1.6 time_to_event_days > repo_age_days", "evento mais 'velho' do que a idade calculada do repositório — "
        "repo_age_days não é uma covariável confiável nesses casos",
        len(absurd), total, "alta",
        examples=absurd[["repo_full_name", "artifact_type", "created_at", "time_to_event_days", "repo_age_days"]]
        .sort_values("time_to_event_days", ascending=False).head(6).to_dict("records"),
        note=(
            f"por artifact_type: {by_type_absurd}. Duas causas raiz distintas (ver relatório, Flag 1.6): "
            f"(a) code_comment — get_first_commit_date() usa `git log --reverse` (só HEAD), enquanto a busca "
            f"de eventos usa `git log --all -S` (todas as refs) — assimetria de refs; (b) commit_message/"
            f"issue_body — repo_age_days vem do `created_at` do SEART/GitHub (entidade do repo), que pode ser "
            f"muito mais recente que o histórico git real importado de outra origem (conversões CVS/SVN antigas, "
            f"forks destacados). {len(epoch)} registro(s) com created_at = epoch 1970-01-01 (bug de data "
            f"provável, não idade real): {epoch[['repo_full_name','artifact_type','artifact_id']].to_dict('records')}"
        ),
    ))

    return flags


# ---------------------------------------------------------------------------
# CHECK 3 — Deduplicação em escala
# ---------------------------------------------------------------------------

def check_deduplication(df: pd.DataFrame) -> list[Flag]:
    flags = []
    total = len(df)

    dup_within = df[df.duplicated(subset=["repo_full_name", "artifact_type", "_body_norm"], keep=False)]
    by_type = dup_within["artifact_type"].value_counts().to_dict()
    top_offenders = (
        dup_within.groupby(["repo_full_name", "artifact_type"]).size().sort_values(ascending=False).head(8)
    )
    flags.append(Flag(
        "3.1 body_text duplicado (mesmo repo + mesmo artifact_type)",
        "possível contaminação por geração/backport/cherry-pick não capturada pelo dedup do script 02 "
        "(que hoje só roda para code_comment, dentro de uma única execução, por repo)",
        len(dup_within), total, "média" if len(dup_within) else "info",
        examples=[{"repo_artifact": f"{k[0]} / {k[1]}", "n_dup": int(v)} for k, v in top_offenders.items()],
        note=f"por artifact_type: {by_type}. Concentrado em commit_message — repositórios com histórico "
             f"CVS/SVN importado tendem a duplicar texto de commit entre branches de manutenção "
             f"(cherry-pick/backport preserva a mensagem, muda o SHA).",
    ))

    full_dup = df[df.duplicated(
        subset=["repo_full_name", "artifact_type", "artifact_id", "matched_expression"], keep=False
    )]
    flags.append(Flag(
        "3.2 (repo, artifact_type, artifact_id, matched_expression) repetido",
        "mesma célula path:line reaparece com created_at/removed_at diferentes — NÃO é bug de "
        "reprocessamento (inspeção manual confirma ciclos genuínos de introdução->remoção->reintrodução "
        "no mesmo local), mas quebra a suposição de chave única para quem for agregar por artifact_id",
        len(full_dup), total, "baixa" if len(full_dup) else "info",
        examples=full_dup[["repo_full_name", "artifact_id", "created_at", "removed_at"]].head(6).to_dict("records"),
    ))

    cm = df[df.artifact_type == "commit_message"][["repo_full_name", "_body_norm", "artifact_id"]].rename(
        columns={"artifact_id": "commit_sha"})
    pr = df[df.artifact_type == "pr_body"][["repo_full_name", "_body_norm", "artifact_id"]].rename(
        columns={"artifact_id": "pr_number"})
    ib = df[df.artifact_type == "issue_body"][["repo_full_name", "_body_norm", "artifact_id"]].rename(
        columns={"artifact_id": "issue_number"})

    cross_cm_pr = cm.merge(pr, on=["repo_full_name", "_body_norm"], how="inner")
    flags.append(Flag(
        "3.3 body_text idêntico entre commit_message e pr_body (mesmo repo)",
        "mesma admissão contada 2x em RQ1 (squash-merge copia a descrição do PR para a mensagem "
        "de commit, ou PR de commit único)",
        len(cross_cm_pr), total, "média" if len(cross_cm_pr) else "info",
        examples=cross_cm_pr[["repo_full_name", "commit_sha", "pr_number"]].head(8).to_dict("records"),
    ))

    cross_ib_pr = ib.merge(pr, on=["repo_full_name", "_body_norm"], how="inner")
    flags.append(Flag(
        "3.4 body_text idêntico entre issue_body e pr_body (mesmo repo)",
        "issue e PR com o mesmo corpo (ex.: PR que reusa o texto da issue)",
        len(cross_ib_pr), total, "baixa" if len(cross_ib_pr) else "info",
    ))

    return flags


# ---------------------------------------------------------------------------
# CHECK 4 — Contas automatizadas
# ---------------------------------------------------------------------------

_BOT_LOGIN_EXACT_CURRENT = {"dependabot", "renovate", "github-actions", "greenkeeper", "snyk-bot", "pull"}


def _current_filter_blocks(login) -> bool:
    """Reimplementação de `_is_bot_login` (scripts/02_collect_multiartifact.py)
    para simular o que o filtro ATUAL bloquearia — usada para medir o gap."""
    if pd.isna(login):
        return False
    lowered = str(login).lower()
    return ("[bot]" in lowered) or (lowered in _BOT_LOGIN_EXACT_CURRENT)


def _looks_botlike(value) -> bool:
    if pd.isna(value):
        return False
    v = str(value).lower()
    return ("bot" in v) or v.endswith("[bot]")


def check_bot_accounts(df: pd.DataFrame) -> list[Flag]:
    flags = []
    total = len(df)

    mask_login_botlike = df["author_login"].apply(_looks_botlike)
    leaked = df[mask_login_botlike & ~df["author_login"].apply(_current_filter_blocks)]
    leaked_counts = leaked["author_login"].value_counts().head(10).to_dict()
    flags.append(Flag(
        "4.1 author_login bot-like que ESCAPA do filtro atual",
        "contas automatizadas (CI, merge-bots, dependência de terceiros) que passam pelo filtro "
        "de bot porque não têm '[bot]' no login nem estão na lista exata "
        f"{sorted(_BOT_LOGIN_EXACT_CURRENT)}",
        len(leaked), total, "alta" if len(leaked) else "info",
        examples=[{"login": k, "n": int(v)} for k, v in leaked_counts.items()],
        note="pyup-bot é o caso mais volumoso (mudança de terceiro/changelog de dependência colada "
             "em PR de bump, não é admissão do time do repo) — exatamente o caso citado no mandato.",
    ))

    mask_name_botlike = df["author_name"].apply(_looks_botlike)
    only_name = df[mask_name_botlike & ~mask_login_botlike]
    flags.append(Flag(
        "4.2 author_name bot-like sem author_login bot-like",
        "commit_message cujo autor é claramente um bot pelo NOME do commit, mas o filtro atual só "
        "checa author_login — gap adicional e independente do 4.1",
        len(only_name), total, "média" if len(only_name) else "info",
        examples=only_name[["artifact_type", "author_name", "author_login"]].head(8).to_dict("records"),
    ))

    return flags


# ---------------------------------------------------------------------------
# CHECK 5 — Efetividade do filtro de path vendorizado
# ---------------------------------------------------------------------------

# Bibliotecas de terceiros amplamente vendorizadas sob nomes de diretório
# genéricos (sem "vendor/", sem sufixo de versão) — não cobertas por
# VENDORED_PATH_MARKERS nem por VENDORED_FILENAMES em ubw/lexicon.py.
# Curada a partir de achados concretos na amostragem manual deste relatório
# (gnina/gnina -> src/eigen/, kinectron/kinectron -> peerjsv104.noerror.js).
KNOWN_VENDORED_LIB_TOKENS = [
    "eigen", "zlib", "libpng", "peerjs", "jquery", "googletest", "gtest", "gmock",
    "catch2", "nlohmann", "rapidjson", "boost", "curl", "openssl", "sqlite3", "sqlite",
    "lua", "freetype", "harfbuzz", "angle", "skia", "llvm", "protobuf", "grpc",
    "abseil", "pybind11", "fmtlib", "spdlog", "stb_image", "imgui", "glfw", "glew",
    "civetweb", "mongoose", "cjson", "cpp-httplib", "httplib", "cpython",
]


def check_vendored_path_filter(df: pd.DataFrame) -> list[Flag]:
    flags = []
    cc = df[df.artifact_type == "code_comment"].copy()
    total = len(cc)
    if total == 0:
        return flags

    cc["_path"] = cc["artifact_id"].astype(str).str.rsplit(":", n=1).str[0]

    if lexicon is not None:
        still_vendored = cc[cc["_path"].apply(lexicon.is_vendored_path)]
        flags.append(Flag(
            "5.1 code_comment ainda em path vendorizado pelo filtro OFICIAL",
            "regressão do filtro atual (is_vendored_path) — deveria ser 0 por construção; se >0, "
            "há um caminho de código que grava registros sem passar pelo filtro",
            len(still_vendored), total, "alta" if len(still_vendored) else "info",
            examples=still_vendored[["repo_full_name", "_path"]].head(5).to_dict("records"),
        ))

    pattern = "|".join(rf"(^|/){tok}(/|-|_|\.|$)" for tok in KNOWN_VENDORED_LIB_TOKENS)
    generic_vendor_hit = cc[cc["_path"].str.lower().str.contains(pattern, regex=True, na=False)]
    by_lib_examples = generic_vendor_hit[["repo_full_name", "_path"]].head(10).to_dict("records")
    pct_vendor = len(generic_vendor_hit) / total * 100 if total else 0.0
    flags.append(Flag(
        "5.2 code_comment em diretório de lib de terceiros conhecida, SEM marcador de path oficial",
        "heurística adicional (nomes de libs vendorizadas amplamente conhecidas) que o filtro oficial "
        "(vendor/, node_modules/, dist/, sufixo -N.N.N) não cobre — gap de recall do filtro de vendoring",
        len(generic_vendor_hit), total, "alta" if pct_vendor >= 2.0 else ("média" if generic_vendor_hit.shape[0] else "info"),
        examples=by_lib_examples,
        note="cada ocorrência exige checagem manual (nem todo path contendo 'boost' é de fato a lib "
             "vendorizada; pode ser nome de variável/projeto) — não aplicar como filtro automático "
             "sem revisão, listar como candidato a novo marcador em VENDORED_PATH_MARKERS.",
    ))

    minified_like = cc[cc["_path"].str.lower().str.contains(r"\.min\.(js|css)$|[-_][0-9a-f]{8,}\.js$", regex=True, na=False)]
    flags.append(Flag(
        "5.3 code_comment em arquivo com cara de bundle minificado/hasheado",
        "nome de arquivo com padrão de build (hash de conteúdo, .min.js/.min.css) fora dos casos "
        "já cobertos por VENDORED_FILENAMES/_MINIFIED_SUFFIXES",
        len(minified_like), total, "média" if len(minified_like) else "info",
        examples=minified_like[["repo_full_name", "_path"]].head(5).to_dict("records"),
    ))

    return flags


# ---------------------------------------------------------------------------
# CHECK 2 — Remoção acidental vs. real (Zampetti et al., 2018)
# ---------------------------------------------------------------------------

def check_removal_validity_sample(df: pd.DataFrame, n: int = 25, seed: int = 42) -> tuple[list[Flag], pd.DataFrame]:
    """Amostra eventos de remoção de code_comment para inspeção manual/semi-
    automática. NÃO faz chamadas de rede por padrão (ver
    `live_check_removal_validity` para a versão que verifica de fato via
    GitHub API, com --live-checks).
    """
    cc_removed = df[(df.artifact_type == "code_comment") & (df.is_censored == 0)].copy()
    total = len(cc_removed)
    if total == 0:
        return [], cc_removed

    cc_removed["_path"] = cc_removed["artifact_id"].astype(str).str.rsplit(":", n=1).str[0]
    sample = cc_removed.drop_duplicates(subset=["repo_full_name"]).sample(
        n=min(n, cc_removed["repo_full_name"].nunique()), random_state=seed
    )

    flags = [Flag(
        "2.0 amostra para verificação Zampetti (remoção acidental vs. real)",
        "amostra de eventos de remoção de code_comment extraída para inspeção — ver "
        "check_removal_validity_sample() e --live-checks para a verificação de fato",
        len(sample), total, "info",
        examples=sample[["repo_full_name", "_path", "matched_expression", "created_at", "removed_at"]]
        .head(10).to_dict("records"),
        note="O schema (Tabela 3.5) NÃO retém o SHA do commit de remoção, só `removed_at` (timestamp). "
             "Isso é uma limitação estrutural para checagens Zampetti pós-hoc: para saber se a remoção "
             "foi textual genuína ou deleção do arquivo inteiro, é preciso re-rodar "
             "`git log --all -S <expr> -- <path>` no clone e localizar o commit próximo de removed_at, "
             "depois `git diff-tree --no-commit-id --name-status -r <sha> -- <path>` (status D = arquivo "
             "inteiro deletado -> deveria ter sido censura, não remoção; status M = edição real -> remoção "
             "genuína). Ver função live_check_removal_validity() abaixo para a implementação.",
    )]
    return flags, sample


def live_check_removal_validity(sample: pd.DataFrame, clone_dir: Optional[Path] = None) -> list[dict]:
    """Verificação de fato (Zampetti et al., 2018) via clone local: para cada
    linha da amostra, localiza o commit de remoção (git log -S) mais próximo
    de `removed_at` e verifica se o path inteiro foi deletado (git diff-tree
    --name-status) naquele commit.

    Requer `clone_dir` com clones já existentes (owner__repo) OU git clone
    sob demanda (não implementado aqui de propósito — este script não deve
    clonar repositórios enquanto a coleta principal estiver rodando, para
    não competir por rede/disco com o processo em andamento; ver relatório,
    Seção "Procedimento de reprodutibilidade").

    Retorna uma lista de dicts com o veredito por linha; imprime um resumo.
    """
    import subprocess

    results = []
    if clone_dir is None or not clone_dir.exists():
        print("live_check_removal_validity: --clone-dir não informado ou inexistente; pulando verificação ao vivo.")
        return results

    for _, row in sample.iterrows():
        repo_dir = clone_dir / row["repo_full_name"].replace("/", "__")
        verdict = "sem_clone_local"
        if repo_dir.exists():
            try:
                log_out = subprocess.run(
                    ["git", "-C", str(repo_dir), "log", "--all", "-S", row["matched_expression"],
                     "--pretty=format:%H|%aI", "--", row["_path"]],
                    capture_output=True, text=True, timeout=120,
                ).stdout
                shas = [ln.split("|") for ln in log_out.splitlines() if ln.strip()]
                target = pd.Timestamp(row["removed_at"])
                best = min(shas, key=lambda sd: abs(pd.Timestamp(sd[1]) - target), default=None) if shas else None
                if best is None:
                    verdict = "commit_de_remocao_nao_localizado"
                else:
                    sha = best[0]
                    status_out = subprocess.run(
                        ["git", "-C", str(repo_dir), "diff-tree", "--no-commit-id", "--name-status", "-r",
                         sha, "--", row["_path"]],
                        capture_output=True, text=True, timeout=60,
                    ).stdout.strip()
                    if status_out.startswith("D"):
                        verdict = "ARQUIVO_INTEIRO_DELETADO (deveria ser censura, não remoção)"
                    elif status_out.startswith("M"):
                        verdict = "remocao_textual_genuina"
                    else:
                        verdict = f"status_inesperado:{status_out[:50]}"
            except Exception as exc:  # noqa: BLE001
                verdict = f"erro:{exc}"
        results.append({"repo": row["repo_full_name"], "path": row["_path"], "verdict": verdict})

    counts = pd.Series([r["verdict"] for r in results]).value_counts()
    print("\n[CHECK 2 — verificação ao vivo, Zampetti et al. 2018]")
    print(counts.to_string())
    return results


# ---------------------------------------------------------------------------
# CHECK 6 — Reprodutibilidade
# ---------------------------------------------------------------------------

def describe_reproducibility_procedure() -> None:
    print("""
[CHECK 6 — Reprodutibilidade — procedimento documentado]

Objetivo: confirmar que re-rodar a coleta sobre um mesmo repositório, em outro
momento, produz um conjunto de registros consistente (mesmas introduções,
mesmas remoções observadas até a data de corte original), dentro do esperado
de variação por causa da Search API mudar no tempo (Seção 3.4 do plano).

Procedimento:
  1. Escolher 2-3 repositórios já 100% concluídos no checkpoint (todos os 4
     artifact_types), de tamanho pequeno/médio (evita timeout de clone).
  2. Rodar de novo, isolado, com --out-dir/--state-file/--clone-dir apontando
     para um diretório TEMPORÁRIO (nunca o data/full_run/ da coleta em
     andamento):
         python scripts/02_collect_multiartifact.py \\
             --repos-csv <csv com só os 2-3 repos escolhidos> \\
             --out-dir /tmp/ubw_repro_check \\
             --clone-dir /tmp/ubw_repro_check/clones \\
             --state-file /tmp/ubw_repro_check/state.json
  3. Comparar o CSV novo com o subconjunto correspondente do CSV original:
       - code_comment: os pares (path, expressão, created_at) devem bater
         exatamente (git log -S é determinístico sobre o mesmo histórico);
         is_censored pode diferir SE uma remoção aconteceu entre as duas
         coletas (esperado, não é erro).
       - issue_body/pr_body/commit_message: contagem pode diferir (a Search
         API indexa itens novos entre as duas datas de corte) — o critério de
         aceite é que TODO registro da coleta original continue presente na
         nova (nenhum "desaparece"), não que os totais sejam idênticos.
  4. Critério de aceite: 0 registros da coleta original ausentes na re-coleta
     para code_comment (determinístico); >= 95% de presença para
     issue/pr/commit (tolerância à evolução da Search API).

Por que não foi executado agora: a coleta da fatia A está rodando neste
exato diretório (data/full_run/), usando os únicos tokens GitHub disponíveis
no .env em rotação contra o rate limit da Search API (30 req/min/token). Uma
re-coleta concorrente competiria pelo mesmo orçamento de rate limit e,
pior, git clone concorrente nos MESMOS repositórios que os workers de
code_comment podem estar processando agora arrisca condição de corrida no
diretório de clone. Rede de saída deste ambiente de auditoria também está
bloqueada para chamadas diretas à API do GitHub autenticada (testado: chamada
via proxy do workspace retorna 403; chamadas não-autenticadas via fetch
externo funcionam mas esgotam o limite de 60 req/h não-autenticado em poucas
chamadas). Rode este procedimento manualmente depois que COLLECTION_COMPLETE
existir em data/full_run/.
""")


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", default=str(REPO_ROOT / "data" / "full_run" / "ubw_collected_full.csv"))
    parser.add_argument("--out-json", default=None, help="Se informado, grava todas as flags em JSON.")
    parser.add_argument("--removal-sample-n", type=int, default=25)
    parser.add_argument("--live-checks", action="store_true",
                         help="Tenta verificação ao vivo do CHECK 2 (requer --clone-dir com clones locais).")
    parser.add_argument("--clone-dir", default=None, help="Diretório de clones locais para --live-checks.")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERRO: {csv_path} não existe.", file=sys.stderr)
        sys.exit(1)

    is_partial = not (csv_path.parent / "COLLECTION_COMPLETE").exists()
    print(f"=== Agente C — auditoria de mineração ===")
    print(f"CSV: {csv_path}")
    if is_partial:
        print("AVISO: COLLECTION_COMPLETE não encontrado neste diretório — este é um corpus PARCIAL. "
              "Os números abaixo valem como auditoria de PROCESSO, não como números finais do dataset. "
              "Re-execute este script sobre o CSV consolidado (fatia A + fatia B) antes de citar números "
              "no relatório final.")

    df = load_dataset(csv_path)
    print(f"Total de registros: {len(df)} | repositórios distintos: {df['repo_full_name'].nunique()}")

    all_flags: list[Flag] = []
    all_flags += check_temporal_sanity(df)
    all_flags += check_deduplication(df)
    all_flags += check_bot_accounts(df)
    all_flags += check_vendored_path_filter(df)

    removal_flags, removal_sample = check_removal_validity_sample(df, n=args.removal_sample_n)
    all_flags += removal_flags

    for f in all_flags:
        f.print()

    if args.live_checks:
        clone_dir = Path(args.clone_dir) if args.clone_dir else None
        live_check_removal_validity(removal_sample, clone_dir)

    describe_reproducibility_procedure()

    if args.out_json:
        out = {
            "csv": str(csv_path), "is_partial_corpus": is_partial,
            "total_records": len(df), "n_repos": int(df["repo_full_name"].nunique()),
            "flags": [f.to_dict() for f in all_flags],
        }
        Path(args.out_json).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nFlags gravadas em {args.out_json}")


if __name__ == "__main__":
    main()
