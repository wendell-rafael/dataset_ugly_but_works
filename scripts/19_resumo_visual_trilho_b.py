#!/usr/bin/env python3
"""Gera o resumo visual do Trilho B: figuras + prompts reais numa página só.

Página HTML autocontida — as três figuras entram como data URI porque o destino
é um artefato hospedado, onde requisição a host externo é bloqueada por CSP.

Os prompts não são reescritos aqui: são renderizados por
`panel_prompts_cc.build_prompt` a partir do pool travado em
`validation/panel/cc/exemplar_pool.json`, com um item real do conjunto de
avaliação. Copiar o texto do prompt para dentro do HTML deixaria os dois
divergirem na primeira alteração.

Uso:
    python3 scripts/19_resumo_visual_trilho_b.py
"""

from __future__ import annotations

import base64
import html
import importlib.util
import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
FIGS = RAIZ / "figures" / "trilho_b_cc"
CC = RAIZ / "validation" / "panel" / "cc"
ANALISE = RAIZ / "validation" / "panel" / "analysis"
SAIDA = RAIZ / "figures" / "trilho_b_cc" / "resumo_visual.html"

# Item usado para mostrar o prompt: um dos NEGATIVOS, porque é onde a tarefa
# fica visível. Num positivo o prompt não ensina nada ao leitor -- 93,5% do
# conjunto é positivo e responder "é UBW" acerta quase sempre.
ITEM_DEMO = "cc0053"


def carrega_prompt() -> tuple[str, str, dict]:
    spec = importlib.util.spec_from_file_location(
        "cc", RAIZ / "scripts" / "panel_prompts_cc.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pool = json.loads((CC / "exemplar_pool.json").read_text(encoding="utf-8"))
    aval = pd.read_csv(CC / "eval_371.csv")
    linha = aval.loc[aval.item_id == ITEM_DEMO]
    if linha.empty:
        linha = aval.loc[~aval.gold.astype(bool)].head(1)
    cand = linha.iloc[0].to_dict()
    sistema, usuario = mod.build_prompt(cand, exemplars=pool, k=2)
    return sistema, usuario, cand


def respostas_do_item(item_id: str) -> list[dict]:
    """O que cada juiz respondeu para o item demonstrado."""
    out = []
    for f in sorted((RAIZ / "validation/panel/runs/eval_371").glob("*k8.jsonl")):
        nome = f.stem.replace("_fewshot_cc_k8", "")
        for linha in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(linha)
            if str(r.get("item_id")) == str(item_id) and r.get("ok"):
                out.append({"juiz": nome, "label": r["label"],
                            "rationale": r.get("rationale", "")})
                break
    return out


def data_uri(caminho: Path) -> str:
    return ("data:image/png;base64,"
            + base64.b64encode(caminho.read_bytes()).decode("ascii"))


def tabela_juizes() -> str:
    d = pd.read_csv(ANALISE / "eval_371__judges.csv")
    d = d[d.juiz.str.endswith("k8")].copy()
    d["m"] = d.juiz.str.replace("_fewshot_cc_k8", "", regex=False)
    d = d.sort_values("kappa_penalizado", ascending=False)
    linhas = []
    for _, r in d.iterrows():
        prec = "—" if pd.isna(r.precisao_alerta) else f"{r.precisao_alerta:.0%}"
        ic = ("—" if pd.isna(r.ic95_low)
              else f"{r.ic95_low:.0%}–{r.ic95_high:.0%}")
        destaque = ' class="destaque"' if r.kappa_penalizado >= 0.47 else ""
        linhas.append(
            f"<tr{destaque}><td>{html.escape(r.m)}</td>"
            f"<td class='n'>{int(r.alertas)}</td><td class='n'>{prec}</td>"
            f"<td class='n ic'>{ic}</td><td class='n'>{r.cobertura:.0%}</td>"
            f"<td class='n forte'>{r.kappa_penalizado:.3f}</td></tr>")
    return "\n".join(linhas)


def main() -> None:
    sistema, usuario, cand = carrega_prompt()
    respostas = respostas_do_item(cand["item_id"])
    concordam = sum(1 for r in respostas if (r["label"] == "não-UBW")
                    != (not bool(cand["gold"])))

    blocos_resposta = "\n".join(
        f"<tr><td>{html.escape(r['juiz'])}</td>"
        f"<td class='{'erro' if (r['label']=='não-UBW') != (not bool(cand['gold'])) else 'acerto'}'>"
        f"{html.escape(r['label'])}</td>"
        f"<td class='just'>{html.escape(r['rationale'][:190])}</td></tr>"
        for r in respostas)

    figuras = [
        ("escada_tamanho.png", "Tamanho não prediz desempenho",
         "Qwen 3 sobe de 8B a 14B e desce em 32B; Gemma 3 sobe de 4B a 12B e "
         "desce em 27B. A faixa verde é a concordância entre os três "
         "anotadores humanos. A linha tracejada marca Grok 4.3 e Sonnet 5, que "
         "deram κ idêntico e não estão na escala de parâmetros."),
        ("correlacao_erro.png", "Os juízes erram nos mesmos itens",
         "Sonnet 5 e Grok 4.3 têm 0,78 de sobreposição nos vetores de erro — "
         "21 dos 24 erros são os mesmos itens. Isso dá 1,24 votos "
         "efetivamente independentes de 3, e a regra de maioria reproduz "
         "exatamente o melhor juiz sozinho. O Llama 70B em 0,26 mostra que "
         "existe diversidade de erro, só não o suficiente."),
        ("dev200_vs_eval371.png", "Por que o κ da rodada anterior não valia",
         "A fatia de comentários de código do conjunto de 200 tinha 57 itens e "
         "<strong>1 negativo</strong>. Vinte e quatro de 53 juízes obtiveram "
         "κ = 1,000 emitindo exatamente um alerta que calhava de acertar — "
         "incluindo modelos do fundo do ranking geral. Com 24 negativos, a "
         "distribuição é real."),
    ]
    blocos_fig = "\n".join(f"""
    <figure>
      <img src="{data_uri(FIGS / nome)}" alt="{html.escape(titulo)}">
      <figcaption><strong>{html.escape(titulo)}</strong> — {legenda}</figcaption>
    </figure>""" for nome, titulo, legenda in figuras)

    pagina = TEMPLATE.format(
        blocos_fig=blocos_fig,
        tabela=tabela_juizes(),
        sistema=html.escape(sistema),
        usuario=html.escape(usuario),
        item=html.escape(str(cand["item_id"])),
        expressao=html.escape(str(cand["matched_expression"])),
        repo=html.escape(str(cand["repo_full_name"])),
        gold="não-UBW (falso positivo do léxico)" if not bool(cand["gold"]) else "UBW",
        respostas=blocos_resposta,
        n_juizes=len(respostas),
        n_acertos=concordam,
    )
    SAIDA.write_text(pagina, encoding="utf-8")
    print(f"{SAIDA.relative_to(RAIZ)}  ({SAIDA.stat().st_size // 1024} KB)")


TEMPLATE = """<title>Trilho B — triagem por LLM em comentários de código</title>
<style>
  :root {{
    --tinta: #16181d; --tinta-2: #4a4f5a; --tinta-3: #7b8290;
    --fundo: #f7f8fa; --papel: #ffffff; --linha: #e2e5ea;
    --azul: #1d4ed8; --laranja: #c2410c; --verde: #15803d; --vermelho: #b91c1c;
    --codigo-fundo: #f2f4f7;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --tinta: #e8eaee; --tinta-2: #a8aeba; --tinta-3: #767d8b;
      --fundo: #14161a; --papel: #1b1e24; --linha: #2b3038;
      --azul: #7ba2f5; --laranja: #f0895a; --verde: #5cc98a; --vermelho: #f08a84;
      --codigo-fundo: #14171c;
    }}
  }}
  :root[data-theme="dark"] {{
    --tinta: #e8eaee; --tinta-2: #a8aeba; --tinta-3: #767d8b;
    --fundo: #14161a; --papel: #1b1e24; --linha: #2b3038;
    --azul: #7ba2f5; --laranja: #f0895a; --verde: #5cc98a; --vermelho: #f08a84;
    --codigo-fundo: #14171c;
  }}
  :root[data-theme="light"] {{
    --tinta: #16181d; --tinta-2: #4a4f5a; --tinta-3: #7b8290;
    --fundo: #f7f8fa; --papel: #ffffff; --linha: #e2e5ea;
    --azul: #1d4ed8; --laranja: #c2410c; --verde: #15803d; --vermelho: #b91c1c;
    --codigo-fundo: #f2f4f7;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--fundo); color: var(--tinta);
    font: 16px/1.65 ui-sans-serif, -apple-system, "Segoe UI", Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ max-width: 68rem; margin: 0 auto; padding: 3rem 1.5rem 5rem; }}
  header {{ border-bottom: 2px solid var(--tinta); padding-bottom: 1.4rem; margin-bottom: 2.5rem; }}
  .eyebrow {{
    font-size: .72rem; letter-spacing: .13em; text-transform: uppercase;
    color: var(--tinta-3); font-weight: 600; margin-bottom: .5rem;
  }}
  h1 {{ font-size: clamp(1.6rem, 3.6vw, 2.35rem); line-height: 1.15; margin: 0 0 .7rem;
        text-wrap: balance; letter-spacing: -.02em; }}
  .sub {{ color: var(--tinta-2); font-size: 1.03rem; max-width: 52ch; margin: 0; }}
  h2 {{ font-size: 1.3rem; margin: 3.2rem 0 .3rem; letter-spacing: -.01em; text-wrap: balance; }}
  h2 + .dica {{ color: var(--tinta-3); font-size: .9rem; margin: 0 0 1.3rem; }}
  h3 {{ font-size: 1rem; margin: 2rem 0 .6rem; }}
  p {{ max-width: 68ch; }}
  .placar {{ display: grid; gap: .9rem; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
             margin: 0 0 1rem; }}
  .card {{ background: var(--papel); border: 1px solid var(--linha); border-radius: 3px;
           padding: .95rem 1.05rem; }}
  .card .v {{ font-size: 1.62rem; font-weight: 650; letter-spacing: -.02em;
              font-variant-numeric: tabular-nums; line-height: 1.1; }}
  .card .r {{ font-size: .78rem; color: var(--tinta-3); margin-top: .25rem; }}
  .card.alerta .v {{ color: var(--vermelho); }}
  .card.bom .v {{ color: var(--verde); }}
  figure {{ margin: 0 0 2.6rem; background: var(--papel); border: 1px solid var(--linha);
            border-radius: 3px; overflow: hidden; }}
  figure img {{ display: block; width: 100%; height: auto; }}
  figcaption {{ padding: .9rem 1.1rem 1rem; font-size: .88rem; color: var(--tinta-2);
                border-top: 1px solid var(--linha); }}
  .rolar {{ overflow-x: auto; background: var(--papel); border: 1px solid var(--linha);
            border-radius: 3px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: .87rem; }}
  th, td {{ text-align: left; padding: .5rem .8rem; border-bottom: 1px solid var(--linha);
            white-space: nowrap; }}
  th {{ font-size: .73rem; letter-spacing: .06em; text-transform: uppercase;
        color: var(--tinta-3); font-weight: 600; }}
  td.n {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.ic {{ color: var(--tinta-3); font-size: .8rem; }}
  td.forte {{ font-weight: 650; }}
  tr.destaque td {{ background: color-mix(in srgb, var(--azul) 7%, transparent); }}
  td.just {{ white-space: normal; min-width: 22rem; color: var(--tinta-2); font-size: .82rem; }}
  td.erro {{ color: var(--vermelho); font-weight: 600; }}
  td.acerto {{ color: var(--verde); font-weight: 600; }}
  pre {{ margin: 0; padding: 1.1rem 1.2rem; background: var(--codigo-fundo);
         border: 1px solid var(--linha); border-radius: 3px; overflow-x: auto;
         font: .795rem/1.6 ui-monospace, "SF Mono", Menlo, Consolas, monospace;
         white-space: pre-wrap; word-break: break-word; color: var(--tinta); }}
  .rotulo-pre {{ font-size: .73rem; letter-spacing: .07em; text-transform: uppercase;
                 color: var(--tinta-3); font-weight: 600; margin: 1.5rem 0 .45rem; }}
  .nota {{ border-left: 3px solid var(--laranja); padding: .1rem 0 .1rem 1rem;
           margin: 1.5rem 0; color: var(--tinta-2); font-size: .92rem; }}
  .nota strong {{ color: var(--tinta); }}
  .veredito {{ background: var(--papel); border: 1px solid var(--linha);
               border-left: 3px solid var(--vermelho); border-radius: 3px;
               padding: 1.2rem 1.3rem; margin: 1.5rem 0; }}
  footer {{ margin-top: 4rem; padding-top: 1.2rem; border-top: 1px solid var(--linha);
            color: var(--tinta-3); font-size: .82rem; }}
  code {{ font: .87em ui-monospace, Menlo, Consolas, monospace;
          background: var(--codigo-fundo); padding: .1em .35em; border-radius: 2px; }}
</style>

<div class="wrap">
<header>
  <div class="eyebrow">UBWSet · trilho B · 08 set 2026</div>
  <h1>Triagem automática de falsos positivos por painel de LLM</h1>
  <p class="sub">Doze configurações de juiz, seis famílias de modelo, de 4 B a 235 B de
  parâmetros, sobre 371 comentários de código com gabarito de três anotadores humanos.
  Resultado negativo.</p>
</header>

<div class="placar">
  <div class="card alerta"><div class="v">0,537</div><div class="r">melhor κ obtido — o mesmo da rodada anterior</div></div>
  <div class="card"><div class="v">0,79–0,83</div><div class="r">κ entre os anotadores humanos</div></div>
  <div class="card alerta"><div class="v">50%</div><div class="r">melhor precisão de alerta (piso exigido: 60%)</div></div>
  <div class="card"><div class="v">1,24</div><div class="r">votos efetivamente independentes, de 3</div></div>
  <div class="card bom"><div class="v">92,6%</div><div class="r">precisão do léxico, por anotação humana</div></div>
  <div class="card"><div class="v">US$ 5,59</div><div class="r">custo total, 5.944 chamadas</div></div>
</div>

<h2>O prompt que foi enviado</h2>
<p class="dica">Renderizado do código, não transcrito: mesma função que gerou as
{n_juizes} execuções.</p>

<p>Uma estratégia só — few-shot com pool fixo, em inglês, específica de comentário
de código. A regra de decisão não veio da literatura: veio das 16 justificativas
que os anotadores escreveram nos negativos unânimes, que revelaram um teste de
<strong>referente</strong> — a frase recorrente nos positivos é literalmente
&ldquo;classifica o código logo abaixo&rdquo;.</p>

<div class="nota"><strong>Uma versão anterior transformou as cinco condições do
guia de anotação em checklist explícito e foi reprovada</strong> — κ caiu para
perto de zero, porque enumerar condições a verificar faz o modelo procurar
motivo para rejeitar. Por isso o prompt abaixo tem duas perguntas, não uma lista,
e descreve a classe negativa por <em>padrão observado</em> em vez de condição
violada.</div>

<div class="rotulo-pre">system</div>
<pre>{sistema}</pre>

<div class="rotulo-pre">user — com k = 2 exemplos, e um item real do conjunto</div>
<pre>{usuario}</pre>

<h2>O que os juízes responderam nesse item</h2>
<p class="dica">Item <code>{item}</code> · expressão <code>{expressao}</code> ·
repositório <code>{repo}</code> · gabarito humano: <strong>{gold}</strong></p>

<p>Os três anotadores foram unânimes: a expressão se refere às atualizações que o
código deduplica, não classifica a implementação como inadequada. Dos
{n_juizes} juízes, <strong>{n_acertos} acertaram</strong>.</p>

<div class="rolar">
<table>
  <thead><tr><th>juiz</th><th>resposta</th><th>justificativa que ele deu</th></tr></thead>
  <tbody>
{respostas}
  </tbody>
</table>
</div>

<h2>Resultado por juiz</h2>
<p class="dica">Todos com cobertura de 371/371 itens. Alerta = o juiz respondeu
&ldquo;não-UBW&rdquo;, marcando o item como falso positivo do léxico.</p>

<div class="rolar">
<table>
  <thead><tr><th>juiz</th><th>alertas</th><th>precisão</th><th>IC95</th><th>cobertura</th><th>κ</th></tr></thead>
  <tbody>
{tabela}
  </tbody>
</table>
</div>

<h2>As três evidências</h2>
<p class="dica">Geradas dos CSV de análise, sem chamada de API.</p>
{blocos_fig}

<div class="veredito">
<h3 style="margin-top:0">Decisão</h3>
<p style="margin-bottom:.6rem">Pelo critério fixado antes da execução, <strong>duas
das quatro linhas apontam para não publicar a marcação automática</strong>, por
caminhos independentes: precisão de alerta abaixo de 60%, e concordância alta
entre juízes com concordância baixa contra o humano — que é indício de viés
compartilhado, não de acerto.</p>
<p style="margin-bottom:0">O resultado negativo sobrevive à seleção mais
favorável possível: das 20 composições de painel testadas, a melhor chega a
55,6% de precisão. <strong>O dataset não depende disso</strong> — a precisão do
léxico é 92,6%, IC95 [89,5–94,8], por anotação humana independente.</p>
</div>

<footer>
Documento completo, com as sete seções e as seis ameaças à validade, em
<code>validation/RESULTADO_TRILHO_B_CODE_COMMENT.md</code>. Votos e
justificativas por item em <code>validation/panel/runs/eval_371/</code>.
Temperatura zero em todas as chamadas, endpoint fixado sem fallback, provedor
gravado por item.
</footer>
</div>
"""


if __name__ == "__main__":
    main()
