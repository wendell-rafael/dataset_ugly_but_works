#!/usr/bin/env python3
"""Gera a interface local de anotação, um arquivo HTML por anotador.

Cada arquivo é autocontido: os itens vão embutidos como JSON, não há servidor
nem dependência de rede. O anotador abre no navegador, marca com o teclado, e
baixa um CSV no fim. O progresso fica em `localStorage`, então fechar a aba não
perde trabalho.

**PII fica fora.** A amostra vem do dataset de trabalho, que inclui
`author_name`, `author_login` e `author_email` (`validation/POLITICA_ANONIMIZACAO.md`).
O anotador não precisa desses campos para julgar, e embutir PII em três arquivos
HTML que circulam por e-mail ou pendrive multiplicaria a superfície de exposição
sem nenhum ganho. Só os campos necessários ao julgamento são embarcados.

O schema de saída é o do `ANNOTATION_GUIDELINE.md`: `is_ubw` (booleano),
`confidence` (`certo` | `provável` | `incerto`) e `observacao` (texto livre).

Uso:
    python 12_build_annotation_ui.py
    python 12_build_annotation_ui.py --anotador Wendell --anotador Miguel
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "validation" / "sample_code_comment" / "amostra_code_comment.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.annotation_ui")

ANOTADORES = ("Wendell", "Bruno", "Miguel")

# Campos que o anotador precisa ver. Tudo que identifica pessoa fica fora.
CAMPOS = ["item_id", "repo_full_name", "matched_expression", "body_text",
          "url", "primary_language"]

BODY_LIMIT = 1800  # o corpo já vem cortado em 2000 na coleta; isto é folga de layout


TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Anotação UBW — comentários de código — __ANOTADOR__</title>
<style>
  :root{
    --bg:#f5f5f3; --card:#fff; --card2:#ecece9; --ink:#17191d; --ink2:#5a616a;
    --ink3:#8a9099; --line:#dbdbd7; --line2:#c4c4bf;
    --ac:#0c6f8a; --acbg:#dbeef4;
    --yes:#1f8f5f; --yesbg:#e2f1ea; --no:#c43a3a; --nobg:#fbe7e7; --warn:#b8862b;
  }
  @media (prefers-color-scheme:dark){
    :root{
      --bg:#131519; --card:#1a1d22; --card2:#22252b; --ink:#e6e8ec; --ink2:#98a0aa;
      --ink3:#6a7280; --line:#292d34; --line2:#373c45;
      --ac:#3fa8c9; --acbg:#14313c;
      --yes:#34ad79; --yesbg:#13312a; --no:#e2645a; --nobg:#391e1e; --warn:#d9a54b;
    }
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;height:100%}
  body{background:var(--bg);color:var(--ink);
    font-family:-apple-system,"Segoe UI","Helvetica Neue",Arial,sans-serif;line-height:1.5}
  .mono{font-family:ui-monospace,"SF Mono","Cascadia Code","Roboto Mono",Consolas,monospace}

  .top{position:sticky;top:0;z-index:10;background:var(--card);border-bottom:1px solid var(--line);
    padding:10px 18px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
  .top h1{font-size:14px;margin:0;font-weight:650}
  .top .who{font-size:12px;color:var(--ink2);font-family:ui-monospace,monospace}
  .prog{flex:1;min-width:160px;display:flex;align-items:center;gap:9px}
  .track{flex:1;height:6px;background:var(--card2);border-radius:3px;overflow:hidden}
  .fill{height:100%;background:var(--ac);width:0%;transition:width .18s}
  .pnum{font-family:ui-monospace,monospace;font-variant-numeric:tabular-nums;font-size:12px;color:var(--ink2)}
  .btn{font:inherit;font-size:12.5px;padding:6px 12px;border-radius:6px;border:1px solid var(--line2);
    background:var(--card2);color:var(--ink);cursor:pointer}
  .btn:hover{border-color:var(--ac);color:var(--ac)}
  .btn.pri{background:var(--ac);border-color:var(--ac);color:#fff}

  .wrap{max-width:860px;margin:0 auto;padding:22px 18px 120px}

  .meta{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--ink2);margin-bottom:10px}
  .meta b{color:var(--ink);font-weight:600}
  .meta a{color:var(--ac)}
  .expr{display:inline-block;background:var(--acbg);color:var(--ac);padding:1px 7px;border-radius:4px;
    font-family:ui-monospace,monospace;font-size:12px;font-weight:600}

  .body{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:16px 18px;
    font-family:ui-monospace,"SF Mono",Consolas,monospace;font-size:13px;line-height:1.72;
    white-space:pre-wrap;word-break:break-word;max-height:52vh;overflow-y:auto;margin-bottom:6px}
  .body mark{background:#ffd84d;color:#1a1a1a;padding:0 2px;border-radius:2px;font-weight:600}
  .nomatch{font-size:12px;color:var(--warn);margin:0 0 14px}

  .qbox{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:15px 18px;margin-top:14px}
  .q{font-size:14.5px;font-weight:600;margin:0 0 11px}
  .opts{display:flex;gap:9px;flex-wrap:wrap;margin-bottom:4px}
  .opt{flex:1;min-width:130px;padding:11px 13px;border:1.5px solid var(--line2);border-radius:7px;
    background:var(--card2);cursor:pointer;text-align:left}
  .opt kbd{display:inline-block;font-family:ui-monospace,monospace;font-size:11px;background:var(--card);
    border:1px solid var(--line2);border-radius:3px;padding:0 5px;margin-right:7px}
  .opt .lb{font-size:13.5px;font-weight:600}
  .opt .ds{font-size:11.5px;color:var(--ink3);margin-top:2px}
  .opt.on-yes{border-color:var(--yes);background:var(--yesbg)}
  .opt.on-yes .lb{color:var(--yes)}
  .opt.on-no{border-color:var(--no);background:var(--nobg)}
  .opt.on-no .lb{color:var(--no)}
  .opt.on{border-color:var(--ac);background:var(--acbg)}
  .opt.on .lb{color:var(--ac)}

  .sub{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--ink3);margin:14px 0 7px}
  textarea{width:100%;min-height:58px;font:inherit;font-size:13px;padding:9px 11px;border-radius:7px;
    border:1px solid var(--line2);background:var(--card2);color:var(--ink);resize:vertical}
  textarea:focus{outline:none;border-color:var(--ac)}
  textarea.vazio{border-color:var(--warn);background:var(--card)}
  @keyframes pisca{0%,100%{box-shadow:0 0 0 0 rgba(184,134,43,0)}50%{box-shadow:0 0 0 3px rgba(184,134,43,.5)}}
  .pisca{animation:pisca .45s ease-in-out 2}
  .obrig{color:var(--warn);font-weight:600}

  .nav{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);
    padding:9px 18px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
  .keys{flex:1;font-size:11.5px;color:var(--ink3);display:flex;gap:13px;flex-wrap:wrap}
  .keys kbd{font-family:ui-monospace,monospace;background:var(--card2);border:1px solid var(--line2);
    border-radius:3px;padding:0 5px;font-size:11px}

  .done{text-align:center;padding:48px 18px}
  .done h2{font-size:20px;margin:0 0 10px}
  .done p{color:var(--ink2);font-size:14px;max-width:46ch;margin:0 auto 18px}
  .hide{display:none!important}
  .toast{position:fixed;bottom:64px;left:50%;transform:translateX(-50%);background:var(--ink);
    color:var(--bg);font-size:12.5px;padding:7px 14px;border-radius:6px;opacity:0;
    transition:opacity .2s;pointer-events:none}
  .toast.show{opacity:1}
</style>
</head>
<body>

<div class="top">
  <h1>Anotação UBW · comentários de código</h1>
  <span class="who">__ANOTADOR__</span>
  <div class="prog">
    <div class="track"><div class="fill" id="fill"></div></div>
    <span class="pnum" id="pnum">0 / 0</span>
  </div>
  <button class="btn" id="btnPend">Pendências</button>
  <button class="btn pri" id="btnCsv">Baixar CSV</button>
</div>

<div class="wrap" id="main">
  <div class="meta">
    <span>item <b class="mono" id="mId"></b></span>
    <span>repo <b class="mono" id="mRepo"></b></span>
    <span>ling. <b class="mono" id="mLang"></b></span>
    <span>expressão <span class="expr" id="mExpr"></span></span>
    <span><a id="mUrl" target="_blank" rel="noopener">abrir no GitHub &nearr;</a></span>
  </div>

  <div class="body" id="body"></div>
  <p class="nomatch hide" id="noMatch">A expressão não aparece no trecho abaixo. Isso acontece
    quando o texto foi cortado na coleta — use o link do GitHub se precisar do contexto completo.</p>

  <div class="qbox">
    <p class="q">É uma instância genuína de UBW?</p>
    <div class="opts">
      <div class="opt" id="oYes" data-v="1"><kbd>F</kbd><span class="lb">Sim, é UBW</span>
        <div class="ds">admite solução subótima e a mantém porque funciona</div></div>
      <div class="opt" id="oNo" data-v="0"><kbd>D</kbd><span class="lb">Não é UBW</span>
        <div class="ds">ruído lexical, negação, citação, ou sem resignação</div></div>
    </div>

    <p class="sub">Confiança na sua decisão</p>
    <div class="opts">
      <div class="opt" id="c1" data-c="certo"><kbd>J</kbd><span class="lb">Certo</span>
        <div class="ds">padrão — não precisa apertar</div></div>
      <div class="opt" id="c2" data-c="provável"><kbd>K</kbd><span class="lb">Provável</span></div>
      <div class="opt" id="c3" data-c="incerto"><kbd>L</kbd><span class="lb">Incerto</span></div>
    </div>

    <p class="sub">Observação <span class="obrig" style="text-transform:none;letter-spacing:0">— obrigatória: o que te fez decidir</span></p>
    <textarea id="obs" placeholder="Obrigatório. Tecle A para vir aqui, Esc para sair, Enter avança."></textarea>
  </div>
</div>

<div class="done hide" id="done">
  <h2 id="doneH">Anotação concluída</h2>
  <p id="doneP">Baixe o CSV e mande para o Wendell. O progresso continua salvo neste
     navegador caso precise revisar algo.</p>
  <button class="btn pri" id="btnCsv2">Baixar CSV</button>
  <button class="btn" id="btnPend2">Ir para as pendências</button>
  <button class="btn" id="btnBack">Voltar e revisar</button>
</div>

<div class="nav">
  <div class="keys">
    <span><b>esquerda</b> <kbd>D</kbd> não &middot; <kbd>F</kbd> sim</span>
    <span><kbd>A</kbd> escrever observação <span class="obrig">(obrigatória)</span></span>
    <span><b>direita</b> <kbd>J</kbd> certo <kbd>K</kbd> provável <kbd>L</kbd> incerto</span>
    <span><kbd>Enter</kbd> próximo</span>
    <span><kbd>Espaço</kbd> adiar</span>
    <span><kbd>&larr;</kbd> voltar</span>
  </div>
  <button class="btn" id="btnPrev">&larr; Anterior</button>
  <button class="btn" id="btnNext">Próximo &rarr;</button>
</div>

<div class="toast" id="toast"></div>

<script>
const ANOTADOR = "__ANOTADOR__";
const ITENS = __ITENS__;
const CHAVE = "ubw_cc_" + ANOTADOR;

let i = 0;
let resp = JSON.parse(localStorage.getItem(CHAVE) || "{}");

const $ = id => document.getElementById(id);
const esc = s => String(s == null ? "" : s)
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");

function destaca(txt, expr){
  const t = esc(txt);
  if(!expr) return t;
  const e = expr.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\\\$&");
  return t.replace(new RegExp(e, "gi"), m => "<mark>" + m + "</mark>");
}

function salva(){ localStorage.setItem(CHAVE, JSON.stringify(resp)); }

function toast(msg){
  const t = $("toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(()=>t.classList.remove("show"), 1300);
}

// Um item só conta como feito quando tem rótulo E justificativa. A observação é
// obrigatória por decisão de protocolo: a justificativa escrita é o que permite
// auditar a divergência entre anotadores depois, e também alimenta os exemplos
// few-shot do painel. Na rodada anterior só 52 de 200 itens tinham justificativa,
// e isso limitou as duas coisas.
function completo(it){
  const r = resp[it.item_id];
  return !!r && r.is_ubw !== undefined && (r.observacao || "").trim().length > 0;
}
function contaFeitos(){ return ITENS.filter(completo).length; }

function falta(it){
  const r = resp[it.item_id] || {};
  if(r.is_ubw === undefined && !(r.observacao || "").trim()) return "Falta o rótulo e a observação";
  if(r.is_ubw === undefined) return "Falta marcar o rótulo (D ou F)";
  if(!(r.observacao || "").trim()) return "Falta a observação (tecle A)";
  return null;
}

// Saída de emergência para item que o anotador quer rever depois. Não marca nada
// e o item continua contando como pendente — diferente de "avançar", que exige
// item completo.
function adia(){
  if(i + 1 >= ITENS.length){ toast("Último item"); return; }
  i++; pinta(); toast("Adiado — continua na lista de pendências");
}

function pinta(){
  const it = ITENS[i], r = resp[it.item_id] || {};
  $("mId").textContent = it.item_id;
  $("mRepo").textContent = it.repo_full_name;
  $("mLang").textContent = it.primary_language || "—";
  $("mExpr").textContent = it.matched_expression;
  $("mUrl").href = it.url || "#";
  $("body").innerHTML = destaca(it.body_text, it.matched_expression);

  const tem = (it.body_text||"").toLowerCase().includes((it.matched_expression||"").toLowerCase());
  $("noMatch").classList.toggle("hide", tem);

  $("oYes").classList.toggle("on-yes", r.is_ubw === 1);
  $("oNo").classList.toggle("on-no", r.is_ubw === 0);
  ["c1","c2","c3"].forEach(id => $(id).classList.remove("on"));
  if(r.confidence === "certo") $("c1").classList.add("on");
  if(r.confidence === "provável") $("c2").classList.add("on");
  if(r.confidence === "incerto") $("c3").classList.add("on");
  $("obs").value = r.observacao || "";
  $("obs").classList.toggle("vazio", !(r.observacao || "").trim());

  const feitos = contaFeitos();
  $("pnum").textContent = (i+1) + " / " + ITENS.length + "  ·  " + feitos + " feitos";
  $("fill").style.width = (100*feitos/ITENS.length) + "%";
  $("body").scrollTop = 0;
}

function marca(v){
  const id = ITENS[i].item_id;
  resp[id] = Object.assign({}, resp[id], {is_ubw: v});
  if(resp[id].confidence === undefined) resp[id].confidence = "certo";
  salva(); pinta();
}
function marcaConf(c){
  const id = ITENS[i].item_id;
  resp[id] = Object.assign({}, resp[id], {confidence: c});
  salva(); pinta();
}
function vai(d){
  if(d > 0){
    const f = falta(ITENS[i]);
    if(f){ toast(f); avisaFalta(); return; }
  }
  const n = i + d;
  if(n < 0) return;
  if(n >= ITENS.length){ fim(); return; }
  i = n; pinta();
}

function avisaFalta(){
  const r = resp[ITENS[i].item_id] || {};
  if(r.is_ubw === undefined){
    $("oYes").classList.add("pisca"); $("oNo").classList.add("pisca");
  }
  if(!(r.observacao || "").trim()){
    $("obs").classList.add("pisca"); $("obs").focus();
  }
  setTimeout(() => {
    ["oYes","oNo","obs"].forEach(id => $(id).classList.remove("pisca"));
  }, 900);
}
function fim(){
  $("main").classList.add("hide"); $("done").classList.remove("hide");
  const feitos = contaFeitos(), pend = ITENS.length - feitos;
  $("doneH").textContent = feitos + " de " + ITENS.length + " itens completos";
  $("doneP").textContent = pend === 0
    ? "Tudo com rótulo e observação. Baixe o CSV e mande para o Wendell."
    : pend + (pend === 1 ? " item ainda está" : " itens ainda estão")
      + " sem rótulo ou sem observação. O CSV só exporta os completos.";
  $("btnPend2").classList.toggle("hide", pend === 0);
}
function volta(){
  $("done").classList.add("hide"); $("main").classList.remove("hide"); pinta();
}

function pendencias(){
  const idx = ITENS.findIndex(it => !completo(it));
  if(idx < 0){ toast("Nenhuma pendência"); return; }
  i = idx; volta(); toast("Primeira pendência: item " + ITENS[idx].item_id);
}

function csv(){
  const cab = ["annotator_id","item_id","repo_full_name","artifact_type",
               "matched_expression","url","is_ubw","confidence","observacao"];
  const q = s => '"' + String(s == null ? "" : s).replace(/"/g,'""') + '"';
  const linhas = [cab.join(",")];
  ITENS.forEach(it => {
    const r = resp[it.item_id] || {};
    if(!completo(it)) return;   // item sem rótulo ou sem observação não vai ao CSV
    linhas.push([ANOTADOR, it.item_id, it.repo_full_name, "code_comment",
      it.matched_expression, it.url,
      r.is_ubw === 1 ? "True" : "False",
      r.confidence || "certo", r.observacao || ""].map(q).join(","));
  });
  if(linhas.length === 1){ toast("Nada anotado ainda"); return; }
  const blob = new Blob(["\\ufeff" + linhas.join("\\n")], {type:"text/csv;charset=utf-8"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "anotacao_code_comment_" + ANOTADOR + ".csv";
  a.click(); URL.revokeObjectURL(a.href);
  toast((linhas.length-1) + " itens exportados");
}

$("oYes").onclick = () => marca(1);
$("oNo").onclick  = () => marca(0);
$("c1").onclick = () => marcaConf("certo");
$("c2").onclick = () => marcaConf("provável");
$("c3").onclick = () => marcaConf("incerto");
$("btnPrev").onclick = () => vai(-1);
$("btnNext").onclick = () => vai(1);
$("btnCsv").onclick = csv;
$("btnCsv2").onclick = csv;
$("btnBack").onclick = volta;
$("btnPend").onclick = pendencias;
$("btnPend2").onclick = pendencias;
$("obs").oninput = () => {
  const id = ITENS[i].item_id;
  resp[id] = Object.assign({}, resp[id], {observacao: $("obs").value});
  salva();
};

document.addEventListener("keydown", ev => {
  if(ev.target.tagName === "TEXTAREA"){
    if(ev.key === "Escape") ev.target.blur();
    return;                                     // digitando observação: teclas passam
  }
  if(ev.ctrlKey || ev.metaKey || ev.altKey) return;
  const k = ev.key.toLowerCase();
  // F e D ficam sob os dedos índice e médio da mão esquerda, na linha de
  // descanso; J/K/L sob a mão direita. Rotular NÃO avança: a observação é
  // obrigatória, e avanço automático faria o anotador passar por cima dela.
  if(k === "f" || k === "s"){ marca(1); ev.preventDefault(); }
  else if(k === "d" || k === "n"){ marca(0); ev.preventDefault(); }
  else if(k === "j" || k === "1"){ marcaConf("certo"); ev.preventDefault(); }
  else if(k === "k" || k === "2"){ marcaConf("provável"); ev.preventDefault(); }
  else if(k === "l" || k === "3"){ marcaConf("incerto"); ev.preventDefault(); }
  else if(k === "a" || k === "o"){ $("obs").focus(); ev.preventDefault(); }
  else if(ev.key === "Enter" || ev.key === "ArrowRight"){ vai(1); ev.preventDefault(); }
  else if(ev.key === " "){ adia(); ev.preventDefault(); }
  else if(ev.key === "ArrowLeft"){ vai(-1); ev.preventDefault(); }
});

// Retoma de onde parou.
const pend = ITENS.findIndex(it => !completo(it));
i = pend < 0 ? 0 : pend;
if(pend < 0 && contaFeitos() === ITENS.length) fim(); else pinta();
</script>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anotador", action="append", help="repita a flag; default: os três")
    ap.add_argument("--sample", default=str(SAMPLE))
    ap.add_argument("--out-dir", default=str(ROOT / "validation" / "sample_code_comment" / "ui"))
    args = ap.parse_args()

    anotadores = args.anotador or list(ANOTADORES)
    amostra = pd.read_csv(args.sample)

    faltando = [c for c in CAMPOS if c not in amostra.columns]
    if faltando:
        raise SystemExit(f"colunas ausentes na amostra: {faltando}")

    dados = amostra[CAMPOS].copy()
    dados["body_text"] = dados["body_text"].fillna("").astype(str).str[:BODY_LIMIT]
    dados["primary_language"] = dados["primary_language"].fillna("")
    dados["url"] = dados["url"].fillna("")
    registros = dados.to_dict("records")

    pii = [c for c in amostra.columns if c.startswith("author")]
    logger.info("%d itens embarcados; %d colunas de PII deixadas de fora (%s)",
                len(registros), len(pii), ", ".join(pii) or "nenhuma")

    itens_json = json.dumps(registros, ensure_ascii=False)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    for nome in anotadores:
        html = (TEMPLATE
                .replace("__ITENS__", itens_json)
                .replace("__ANOTADOR__", nome))
        destino = out / f"anotar_code_comment_{nome}.html"
        destino.write_text(html, encoding="utf-8")
        logger.info("%s -> %s (%.0f KB)", nome, destino, destino.stat().st_size / 1024)


if __name__ == "__main__":
    main()
