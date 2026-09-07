

Sugestoes anotacao wendell · MD
Sugestões de anotação — calibração UBW (Wendell, 200 itens)
Sugestões geradas seguindo o Guideline de Anotação — Dataset UBW (Seção 4, teste das 5 condições). Isto é apoio à sua decisão, não substitui seu julgamento. A ordem segue exatamente a mesma do seu CSV/da ferramenta anotador_ubw.html, então o item N aqui corresponde ao item N na ferramenta.

Resumo: 162 SIM · 38 NÃO · confiança: 136 certo / 42 provável / 22 incerto

Itens com confiança incerto merecem atenção redobrada sua — nesses casos a informação capturada no body_text costuma ser escassa demais para aplicar o checklist com segurança, ou há alguma ambiguidade genuína.

1/200 — tubearchivist/tubearchivist (code_comment)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

Comentário próprio referenciando issue upstream real; trade-off implícito de 'temporary fix' mantido no código, mas sem admissão explícita de feiura/erro além do rótulo.

2/200 — KhronosGroup/Vulkan-ValidationLayers (commit_message)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🔴 incerto

Commit próprio, deítico ao multi-EntryPoint pc, mas contexto de apenas uma linha é insuficiente para avaliar com segurança (regra da Seção 7).

3/200 — Autodesk/synthesis (code_comment)
dirty hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

Comentário no próprio código de teste: 'dirty hack, but we cannot rely on pthread_join' — admissão + justificativa explícitas, referência concreta, sem negação.

4/200 — aseprite/aseprite (code_comment)
dirty hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a dirty hack' anexado diretamente à linha de código real, admissão direta sem negação.

5/200 — mlavik1/UnityVolumeRendering (pr_body)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

PR próprio: 'Temporary fix... TODO: Change the slice mesh instead' — trade-off explícito e deítico, corresponde ao exemplo positivo do guideline (6.2).

6/200 — decred/decrediton (pr_body)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is an ugly hack, so hopefully we can have a better IPC mechanism' — admissão explícita + resignação com esperança futura, deítico ao parsing de stdout.

7/200 — eloqdata/eloqsql (commit_message)
temporary fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟢 certo

Mensagem é sobre REVERTER o fix temporário porque o bug raiz já foi corrigido no MySQL — resolução ativa, não resignação (falha condição 2, análogo ao exemplo negativo 6.2).

8/200 — OpenHUTB/hutb (commit_message)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'This makes evident that this is a stopgap measure, and should be looked into further' — admissão própria e deítica (port do recording leak), ainda que embutida em changelog extenso.

9/200 — microsoft/vscode (pr_body)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a stopgap until the underlying issue can be investigated and fixed' — trade-off explícito, deítico ao WorktreeCreatedTaskDispatcher, sem negação.

10/200 — MicrosoftDocs/azure-docs-sdk-dotnet (pr_body)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🔴 incerto

'Temp fix for #540' num changelog em lista; deítico mas contexto mínimo, sem detalhe do trade-off (regra da Seção 7 sobre contexto insuficiente).

11/200 — antlr/antlr4 (code_comment)
quick and dirty · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🔴 incerto

'quick and dirty debugging' descreve o propósito/uso do recurso de trace (depuração informal), não uma admissão de que o próprio código implementado é ruim e foi mantido assim — condição 2 não claramente satisfeita.

12/200 — grappa-py/grappa (pr_body)
ugly but it works · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'it's ugly but it works' — admissão explícita e literal, deítica ao tracebackhide adicionado, sem negação.

13/200 — go-gitea/gitea (pr_body)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🔴 incerto

'Fix #26977 (a temp fix)' — deítico mas sem detalhe do trade-off; contexto mínimo.

14/200 — votingworks/arlo (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'not as safe as our previous approach... but should be an ok temporary fix' — trade-off explícito e deítico à mudança no processamento de CVR.

15/200 — ICB-DCM/pyPESTO (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🔴 incerto

'Temporary fix for roadrunner fd objective' é um item isolado num changelog gigante de squash commits, sem contexto do trade-off — confiança baixa por insuficiência de contexto.

16/200 — mchalupa/dg (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a temporary fix. addBB procedure does not work, because...' — trade-off explícito com causa raiz explicada, deítico, sem negação.

17/200 — octobox/octobox (commit_message)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Quick, temp fix... before placing an intersticial in the flow' — workaround explícito antes de solução definitiva, deítico ao fluxo de doação.

18/200 — microhh/microhh (commit_message)
quick and dirty · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Quick and dirty temporary benchmarking' — autodescrição do próprio código como informal/temporário, mas sem elaborar o trade-off além do rótulo.

19/200 — Pyomo/pyomo (commit_message)
this is a hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'delete the symbol map... (this is a hack)' — admissão direta anexada à ação real do commit, sem negação.

20/200 — nickel-lang/nickel (pr_body)
temporary fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟢 certo

Mensagem é sobre REMOVER o fix temporário porque a dependência problemática foi atualizada — resolução ativa, não resignação (mesmo padrão do item 6).

21/200 — EngineHub/WorldEdit (pr_body)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a temporary fix to prevent errors before a proper fix is done' — trade-off explícito, deítico, sem negação.

22/200 — fortra/impacket (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🔴 incerto

'Temporary fix for #582' em mensagem de merge; deítico mas sem qualquer detalhe do trade-off.

23/200 — peercoin/peercoin (commit_message)
quick and dirty · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟢 certo

Descreve um exemplo antigo 'quick and dirty demo' que está sendo REMOVIDO por causar erros de build — resolução ativa, não retenção resignada.

24/200 — dmtrKovalenko/fff (commit_message)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Stopgap before the daemon-based process model' — trade-off explícito, deítico ao watchdog de timeout implementado, sem negação.

25/200 — ruvnet/ruflo (commit_message)
stopgap · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟢 certo

Descreve mudar a leitura DE um local 'stopgap' para o local correto — é a correção sendo feita, não a introdução/manutenção de um workaround.

26/200 — noir-lang/noir (commit_message)
dirty hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a dirty hack to get tests running in parallel... we instead wait...' — trade-off explícito com justificativa e resultado mensurável, deítico, sem negação.

27/200 — EasyCorp/EasyAdminBundle (pr_body)
dirty hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'But that's just a dirty hack and works only when...' — admissão explícita da própria solução usada no projeto do autor, deítico, sem negação.

28/200 — taikoxyz/taiko-mono (code_comment)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'// Todo: temporary fix for pinata gateway' — comentário próprio, deítico ao fetch, mas trade-off fica implícito só no rótulo 'temporary fix'.

29/200 — openng-org/optimus-ui (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🔴 incerto

'fix: temporary fix for demo' — commit mínimo, sem qualquer detalhe do trade-off ou do código afetado; contexto insuficiente.

30/200 — BerriAI/litellm (pr_body)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Temporary stopgap to unblock CI. The durable fix is...' — trade-off explícito com solução definitiva identificada e adiada, deítico, sem negação.

31/200 — algorandfoundation/algokit-cli (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Temporary fix for excessive build minutes... commenting out PyPi publishing code since it errors out' — workaround explícito e deítico ao pipeline de build.

32/200 — distributed-system-analysis/pbench (commit_message)
quick and dirty · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'this provides a temporary quick and dirty mechanism to define ADMIN roles' — trade-off explícito (solução paliativa até restaurar via Keycloak/LDAP), deítico, sem negação.

33/200 — activeloopai/deeplake (pr_body)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Temporary fix... The coverage test will decrease... is deactivated' — admite explicitamente o efeito colateral negativo do fix mantido, deítico.

34/200 — TryGhost/Ghost (pr_body)
duct tape fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is probably a hacky duct-tape fix, but should allow people to sign up' — trade-off explícito, deítico ao bug de deploy, sem negação.

35/200 — AcademySoftwareFoundation/OpenRV (code_comment)
this is a hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'this is a hack to get around the fact that some devices...' — comentário no próprio código, admissão + justificativa técnica, deítico, sem negação.

36/200 — Couchers-org/couchers (code_comment)
dirty workaround · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a bit of a dirty workaround, but I have no idea why...' — admissão explícita com incerteza sobre a causa, deítico ao código React real, sem negação.

37/200 — marqo-ai/marqo (code_comment)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'this a temporary fix due to the mixed use of pydantic v1 and v2... The workaround we use here...' — trade-off explícito e bem detalhado, deítico, sem negação.

38/200 — dotnet/project-system (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a targeted temporary fix... Post Preview5, we are going to consider alternate approaches' — trade-off explícito, deítico, sem negação.

39/200 — cockroachdb/cockroach (pr_body)
temp fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟢 certo

body_text vazio — não há evidência textual para avaliar nenhuma das 5 condições.

40/200 — okuramasafumi/alba (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Temporary fix to avoid LoadError on CI. Those tasks will not be run, but require causes an error' — trade-off explícito e deítico.

41/200 — mui/pigment-css (code_comment)
quick and dirty · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Very quick and dirty way of checking usage... May give false positives... Refine over time' — trade-off explícito com limitação assumida, deítico, sem negação.

42/200 — gsi-cyberjapan/gsimaps (code_comment)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'TODO refactor ugly hack' — admissão direta e concisa anexada a código real, sem negação (equivalente ao exemplo positivo curto da Seção 6.1).

43/200 — SAP/project-foxhound (commit_message)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

Comentário longo pesando alternativas e concluindo 'there's going to be something ugly, somewhere... I'm inclined to just do the simple thing for now' — resignação explícita e deliberada, deítica ao código de sync de bookmarks.

44/200 — SSSD/sssd (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a temporary fix until we can refactor the sysdb API in #2011' — trade-off explícito, deítico, sem negação.

45/200 — scribusproject/scribus (commit_message)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'it's ugly hack. I don't like thos fix, but I don't know how to solve it regulary. Sometime I feel like an idiot' — resignação explícita e pessoal, deítica ao próprio commit, sem negação.

46/200 — postmanlabs/newman (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Temporary fix to fetch the collection from https URL on Node v12' — deítico e claro, mas trade-off fica só no rótulo, sem elaboração.

47/200 — freelabz/secator (code_comment)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'TODO: temp fix for test fixture with item_loader' em código real (não string de teste) — deítico, trade-off implícito no rótulo.

48/200 — vllm-project/vllm (code_comment)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a temporary fix. We should provide a unified interface for different backends' — trade-off explícito com direção futura, deítico, sem negação.

49/200 — bruderstein/PythonScript (code_comment)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'This copy stuff is an ugly hack to avoid modifying the existing message' — admissão com justificativa técnica, deítica, sem negação.

50/200 — hyperhyperspace/hyperhyperspace-core (commit_message)
dirty hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'committing dirty hack to guess whether more ops are going to be sync'd' — admissão direta e deítica ao mecanismo real, sem negação.

51/200 — DataDog/jmxfetch (commit_message)
temp fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🔴 incerto

'temp fix' é um item isolado entre dezenas de commits 'temp X' de um squash de WIP; não há elaboração de trade-off nem alvo deítico específico — mais ruído de processo de desenvolvimento que admissão deliberada (condição 2 fraca).

52/200 — cms-sw/cmssw (commit_message)
ugly hack · léxico: categoria A

Sugestão: ❌ NÃO · confiança: 🟢 certo

'fixed Sam's ugly hack' — descreve a CORREÇÃO/remoção do hack de outra pessoa, não a introdução ou manutenção de um próprio (falha condição 1 e 2).

53/200 — SAP/project-foxhound (commit_message)
ugly workaround · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟡 provável

Changelog de bump agregando commits de outro subprojeto (gaia) de outro autor (David Flanagan); é citação de terceiro em log de versão, não admissão do próprio autor do commit sendo anotado.

54/200 — flatironinstitute/CaImAn (code_comment)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'consider it a longer-term todo to rework that call not to need this as a stopgap measure' — trade-off explícito, deítico à função real, sem negação.

55/200 — rstudio/rmarkdown (commit_message)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'use an ugly hack in the vignette... because it will significantly increase the size of the package' — trade-off explícito e justificado, deítico, sem negação.

56/200 — Pycord-Development/pycord (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'temporary fix for errors in register_commands' — deítico à função, mas trade-off fica só no rótulo.

57/200 — moonstream-to/api (commit_message)
temporary fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🔴 incerto

'temporary fix' isolado, sem qualquer elaboração ou alvo deítico identificável (idêntico em minimalismo ao item 123) — insuficiente para confirmar as condições 2 e 3.

58/200 — NebulaModTeam/nebula (commit_message)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'temp fix for broken building introduced by last commit' — deítico (build quebrado pelo commit anterior), trade-off implícito no rótulo.

59/200 — beancount/beancount (commit_message)
ugly hack · léxico: categoria A

Sugestão: ❌ NÃO · confiança: 🟢 certo

'Fix ugly hack... Use Python's shutil.copy() instead' — descreve a CORREÇÃO do hack (substituição por solução melhor), não a manutenção resignada dele.

60/200 — multitheftauto/mtasa-blue (commit_message)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Temp fix to get it to compile on Windows' — deítico ao problema de compilação, trade-off implícito no rótulo.

61/200 — Mentra-Community/MentraOS (commit_message)
stopgap · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🔴 incerto

O corpo é um changelog gigante de squash-merge (truncado); a ocorrência de 'stopgap' não aparece no trecho visível — recomendo checagem manual do texto completo na ferramenta antes de decidir.

62/200 — HabitRPG/habitica (commit_message)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This isn't the real solution we need something better' — admissão explícita e deítica ao balanceamento do jogo, sem negação.

63/200 — vercel/hyper (pr_body)
ugly workaround · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'this is an ugly workaround to release all the event listeners...' — trade-off explícito com justificativa técnica detalhada, deítico, sem negação.

64/200 — pytorch/ignite (code_comment)
this is a hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'this is a hack to avoid that' em código real de teste (não string literal) referenciando issue real do PyTorch — admissão explícita e deítica.

65/200 — ivaylokenov/MyTested.AspNetCore.Mvc (commit_message)
quick and dirty · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Removed licensing validation with a quick and dirty solution' — deítico à remoção da validação, trade-off implícito no rótulo.

66/200 — NRCan/geo-deep-learning (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Temporary fix to manage inconsistencies between provided number of band and image number of band' — trade-off explícito e deítico.

67/200 — playframework/play-samples (commit_message)
quick and dirty · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Adds a script to do a quick and dirty run of the samples locally' — deítico ao script adicionado, trade-off implícito no rótulo.

68/200 — alibaba/rtp-llm (code_comment)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'TODO temp fix sp with batch infer, will change request_id to str later' — trade-off explícito com plano futuro, deítico, sem negação.

69/200 — microsoft/vscode (commit_message)
temporary fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🔴 incerto

Commit 'temporary fix' é seguido por outro commit 'better fix' no mesmo PR squashado, sugerindo que a solução foi de fato aprimorada/corrigida antes do merge final — ambíguo se o que restou ainda é resignação.

70/200 — mousebird-consulting-inc/WhirlyGlobe (code_comment)
temporary fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟡 provável

Comentário está dentro de biblioteca vendored de terceiros (common/local_libs/eigen) — não é decisão própria da equipe deste repositório (falha condição 1).

71/200 — unkeyed/unkey (code_comment)
dirty workaround · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Without this... radix dialog traps the focus... This is a dirty workaround' — trade-off explícito e justificado, deítico ao componente próprio, sem negação.

72/200 — ROCm/rocm-systems (code_comment)
this is a hack · léxico: categoria A

Sugestão: ❌ NÃO · confiança: 🟡 provável

Comentário está dentro de script gerador vendored do googlemock (ferramenta de terceiros embutida no repositório), não código próprio do projeto ROCm — falha condição 1 (mesmo item que Miguel já sinalizou como incerto por esse motivo).

73/200 — eclipse-ee4j/jaxb-ri (code_comment)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'ugly, ugly hack' repetido, anexado a lógica real do compilador XJC (código próprio do projeto), deítico, sem negação.

74/200 — expo/expo (pr_body)
workaround for now · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'The workaround, for now, is to prevent replaceWith...' — explicação técnica detalhada e explícita do trade-off, deítica, sem negação.

75/200 — alex-petrenko/sample-factory (code_comment)
this is a hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'this is a hack! rewrite this code!' repetido inclusive em log de warning em runtime — admissão explícita e deítica, sem negação.

76/200 — HerculesWS/Hercules (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'(temporary fix) input box command does not show up...' — deítico ao bug específico, trade-off implícito no rótulo.

77/200 — scylladb/scylladb (commit_message)
dirty hack · léxico: categoria A

Sugestão: ❌ NÃO · confiança: 🟡 provável

O texto descreve a MUDANÇA de abordagem, saindo do 'dirty hack' (symlink único via scriptlet RPM) para uma solução melhor (symlinks por script) — é a correção sendo implementada neste commit, não a manutenção do hack.

78/200 — CTSRD-CHERI/cheribsd (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Temporary fix for guest idle detection'... 'needs more changes... these are forthcoming' — trade-off explícito com plano futuro, deítico, sem negação.

79/200 — chatwoot/chatwoot (pr_body)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This will be a temporary fix until #1556 is merged' — trade-off explícito e deítico, sem negação.

80/200 — MicrosoftDocs/azure-docs-sdk-dotnet (commit_message)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🔴 incerto

'Temp fix for #540' — mesmo padrão do item 9/12, deítico mas sem qualquer elaboração do trade-off.

81/200 — cogentcore/core (code_comment)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'we do not support yet. As a stopgap, we build a fixed zone...' — trade-off explícito e deítico ao driver Android, sem negação.

82/200 — TryGhost/Ghost (pr_body)
stopgap · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟡 provável

A ação do próprio PR é REMOVER/podar testes e2e legados; a menção a 'stopgap' é uma citação entre parênteses de um TODO antigo de outra pessoa, não uma admissão própria do autor sobre a mudança atual.

83/200 — apache/airflow (commit_message)
temporary fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟢 certo

'remove temporary fix scripts' — descreve a REMOÇÃO do fix temporário, não sua introdução ou manutenção.

84/200 — SkriptLang/Skript (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🔴 incerto

Título 'Temporary fix for plural endings error' mas o PR inclui trabalho substancial (classes de override, correção de testes) que não parece um hack rápido — rótulo e conteúdo real parecem em tensão, avaliação incerta.

85/200 — BlafKing/sd-civitai-browser-plus (commit_message)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🔴 incerto

'Update to v3.5.1 (Temp-fix)' — extremamente mínimo, sem qualquer referência deítica a código ou trade-off elaborado.

86/200 — Unvanquished/Unvanquished (code_comment)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'temp fix, terrain is having problems with lighting collapse' anexado a bloco de código real (desabilitado via if(0)) — trade-off explícito, deítico, sem negação.

87/200 — AztecProtocol/aztec-packages (pr_body)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Using SerialQueue as a stopgap measure, which forced me to skip the browser tests' — trade-off explícito com efeito colateral assumido, deítico, sem negação.

88/200 — nodejs/node (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is needed to give users a grace period... To be reverted in Node.js 7.0' — trade-off explícito e bem documentado, deítico, sem negação.

89/200 — OpenMDAO/OpenMDAO (code_comment)
this is a hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'this is a hack to strip of the top level directory else figure can't find file' — trade-off explícito e justificado, deítico, sem negação.

90/200 — category-labs/monad-bft (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Temporary fix for timestamper to workaround tokio behaviour' — deítico ao mecanismo de timestamper, trade-off implícito no rótulo.

91/200 — mytonwallet-org/mytonwallet (commit_message)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🔴 incerto

'[CI, Temp] Fix release for iOS' — extremamente mínimo, sem elaboração de trade-off nem alvo deítico específico.

92/200 — dillongoostudios/goo-engine (commit_message)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Temp fix for vertex format with batch instancing. This prevents memory alignment from being screwed up' — deítico e com alguma explicação técnica, mas rótulo 'temp' não é claramente justificado como feio/hacky além do nome.

93/200 — HDFGroup/hdf5 (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Add temporary fix for ARM64 Mac _Float16 build failure' — deítico ao problema específico de build, trade-off implícito no rótulo.

94/200 — vatesfr/xen-orchestra (code_comment)
dirty workaround · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'FIXME dirty workaround to custom a Chart.js tooltip template' — admissão direta anexada a código real, sem negação.

95/200 — svalinn/DAGMC (code_comment)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'using radius as tolerance for temporary fix' com contexto do problema de busca por vizinhança — trade-off explícito, deítico, sem negação.

96/200 — react-native-maps/react-native-maps (pr_body)
ugly but works · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'Ugly, but works' — admissão explícita e literal, deítica à feature de tooltip, sem negação.

97/200 — wireapp/wire-webapp (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'add temporary fix for bad welcome and commit messages types returned from core-crypto' — item específico e deítico dentro de um changelog extenso de squash commits.

98/200 — sqlmapproject/sqlmap (commit_message)
temporary fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🔴 incerto

'temporary fix (files left at home)' é uma nota críptica sem referência clara a um trade-off de código nem alvo deítico identificável — não dá pra confirmar as condições 2 e 3.

99/200 — sandialabs/pyGSTi (commit_message)
temporary fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟢 certo

O PR descreve a REMOÇÃO da chamada que havia sido identificada como fix temporário em PR anterior ('gaugeopt.py no longer calls ExplicitOpModel._excalc()') — resolução ativa, não manutenção.

100/200 — christophhart/HISE (code_comment)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'I know this is an ugly hack but it still beats polluting the global namespace...' — trade-off explícito com justificativa comparativa, deítico, sem negação.

101/200 — redwoodjs/graphql (pr_body)
stopgap · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🔴 incerto

A palavra 'stopgap' não aparece no trecho visível do corpo (truncado em ~3000/6374 chars) e o texto visível descreve uma feature bem projetada, não uma admissão de gambiarra — recomendo checar o texto completo na ferramenta.

102/200 — ZcashFoundation/zebra (pr_body)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a temporary fix, until we fix the caching (PR #4149)' — trade-off explícito com solução definitiva referenciada, deítico, sem negação.

103/200 — TrinityCore/TrinityCore (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Temporary fix for Aura::UpdateTargetMap assertion failure' — deítico à função específica, trade-off implícito no rótulo.

104/200 — mavlink/qgroundcontrol (code_comment)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a stopgap and should be removed once log file types are properly supported' — trade-off explícito e deítico, sem negação.

105/200 — workadventure/workadventure (code_comment)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'this is a ugly hack to reduce the amount of error in console. Find a better way' — trade-off explícito com admissão de solução incompleta, deítico, sem negação.

106/200 — restic/restic (commit_message)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'increase the test timeouts as a stopgap measure until we can use the mem backend' — trade-off explícito com plano futuro, deítico, sem negação.

107/200 — VirtualBox/virtualbox (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'temporary fix for an empty union on non-Windows platforms' — deítico ao problema específico, trade-off implícito no rótulo.

108/200 — uncodead/BrewUNO (code_comment)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'This ugly hack allows us to define C++ overloaded functions...' — trade-off explícito com justificativa técnica, deítico, sem negação.

109/200 — ent/ent (pr_body)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This can be merged in as a temporary fix but the real solution would be...' — trade-off explícito com solução real descrita, deítico, sem negação.

110/200 — bleskodev/rubyripper (commit_message)
dirty hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'Doing this by calling it track 0 is just a dirty hack. Besides it is conflicting with...' — trade-off explícito com limitação admitida, deítico, sem negação.

111/200 — MCCTeam/Minecraft-Console-Client (pr_body)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'I've added a certificate policy that bypasses certificate checking. This should be treated as a temporary fix' — trade-off explícito (inclusive de segurança), deítico, sem negação.

112/200 — citusdata/citus (commit_message)
quick and dirty · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'I am not super happy with it, but two flags that need to be kept in sync is also not desirable' — admissão pessoal explícita de trade-off, deítica ao rewrite dos testes, sem negação.

113/200 — kyren/piccolo (commit_message)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'it is still sort of a stopgap until arbitrary_self_types is available' — trade-off explícito mesmo reconhecendo melhoria, deítico, sem negação.

114/200 — maurosoria/dirsearch (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🔴 incerto

'Temporary fix for #1183' em mensagem de merge, deítico ao issue mas sem qualquer elaboração do trade-off.

115/200 — invoke-ai/InvokeAI (pr_body)
quick and dirty · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟢 certo

O texto descreve que a correção 'quick and dirty' foi feita numa versão anterior (3.0.1.post3) e ESTE PR faz a limpeza/refatoração dela — é a correção sendo aplicada agora, não a manutenção do hack.

116/200 — napframework/nap (code_comment)
dirty hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'dirty hack to work with mingw32' anexado a código real (#define), admissão direta, deítica, sem negação.

117/200 — supabase/postgres (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Temporary fix until STORAGE-211 is completed' — trade-off explícito com ticket de acompanhamento, deítico, sem negação.

118/200 — godotengine/godot (pr_body)
quick and dirty · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟡 provável

'Quick and dirty' aqui qualifica a descrição/rascunho do PR para uma reunião ('will give a more thorough description after the fact'), não uma admissão sobre a qualidade do próprio código retido — falha condição 3.

119/200 — mantidproject/mantid (pr_body)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'this fix just skips validation to avoid the error' — trade-off explícito e bem detalhado, deítico, sem negação.

120/200 — brailcom/speechd (code_comment)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'TODO: Fix this ugly hack with strstr bellow' — admissão direta com plano de correção futura, deítica, sem negação.

121/200 — rust-lang/rust-clippy (pr_body)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a temporary fix for needless_borrow. The proper fix is included in #8355' — trade-off explícito com correção real referenciada, deítico, sem negação.

122/200 — educates/educates-training-platform (commit_message)
workaround for now · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'gives a copy-paste workaround for now' como solução interina explicitamente descrita até a migração completa (step 10) — trade-off explícito, deítico, sem negação.

123/200 — apache/couchdb (code_comment)
quick and dirty · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟢 certo

Comentário está dentro do QuickJS vendored (couch_quickjs/quickjs/quickjs.c), motor de terceiros embutido no CouchDB — não é decisão própria da equipe (falha condição 1).

124/200 — zachwinter/kaleidosync (commit_message)
temp fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🔴 incerto

'temp fix' sem qualquer elaboração ou alvo deítico identificável — insuficiente para confirmar as condições 2 e 3.

125/200 — axelixlabs/axelix (code_comment)
dirty hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'That is a dirty hack to make Spring Data JDBC think that we're like postgres' — trade-off explícito com justificativa técnica, deítico, sem negação.

126/200 — openMSX/openMSX (code_comment)
quick and dirty · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'quick and dirty, doesn't look right yet' sobre o processo de embutir ícones — trade-off explícito, deítico, sem negação.

127/200 — MonoGame-Extended/Monogame-Extended (commit_message)
quick and dirty · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🔴 incerto

'implemented super quick and dirty enemy ai' é um item isolado entre centenas de commits de um squash de release; sem elaboração de trade-off nem alvo deítico específico além do rótulo — ruído de processo, não admissão deliberada.

128/200 — BlackArch/blackarch (commit_message)
dirty hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🔴 incerto

'package fix (tmp, dirty hack)' — trade-off implícito no rótulo, mas alvo deítico vago ('package fix') e sem elaboração.

129/200 — frappe/press (pr_body)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'added as a temp fix untill we find the permanent fix for this' — trade-off explícito, mas alvo deítico ('this') pouco específico no trecho capturado.

130/200 — envoyproxy/envoy (commit_message)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'As a stopgap solution... we've decided to test the JNI layer through unittests which fake X509Util' — trade-off explícito e detalhado, deítico, sem negação.

131/200 — karma-runner/karma (code_comment)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'temporary fix for [bug real]' com código real visível implementando o workaround (ff-684208-preventDefault) — deítico forte, trade-off implícito claro.

132/200 — IllDepence/unarXive (code_comment)
ugly solution but · léxico: categoria C

Sugestão: ✅ SIM · confiança: 🟢 certo

'ugly solution but no other way to get the primary key' — trade-off explícito (feio mas necessário), deítico, sem negação.

133/200 — camunda/camunda (pr_body)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Temporary fix to stop excessive logging, should be fixed by related issue' — trade-off explícito com issue relacionado, deítico, sem negação.

134/200 — charles-lunarg/vk-bootstrap (pr_body)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This may be a stopgap solution for a larger underlying problem of not being able to determine if an alias is promoted' — trade-off explícito, deítico, sem negação.

135/200 — triSYCL/sycl (commit_message)
band-aid fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a Band-Aid fix to a false positive... The proper solution would be to associate...' — trade-off explícito com solução real descrita, deítico, sem negação.

136/200 — matplotlib/matplotlib (pr_body)
temporary fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟢 certo

O trecho com a admissão está riscado (texto) no próprio PR e é seguido por 'Implemented in super class now' — o fix temporário foi substituído pela solução definitiva antes do fechamento do PR.

137/200 — vercel/next.js (commit_message)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This PR is a stopgap workaround for [issue npm/cli]... Until then...' — trade-off explícito e detalhado, deítico, sem negação.

138/200 — camueller/SmartApplianceEnabler (code_comment)
this is a hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'this is a hack to remove default namespace ns2 but I did not find any other way that worked :-(' — admissão explícita com frustração genuína, deítica, sem negação.

139/200 — elastic/elasticsearch (pr_body)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'As a temporary fix to our troubles loading cuvs... this PR contains a workaround to pre-load it' — trade-off explícito, deítico, sem negação.

140/200 — HackerN64/HackerSM64 (pr_body)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'As a stopgap before the readme rewrite' — trade-off explícito sobre artefato real do repositório (README), deítico, sem negação.

141/200 — alphagov/whitehall (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a temporary fix as there are people agitating for it. Further down the line we'll add a mechanism...' — trade-off explícito com plano futuro, deítico, sem negação.

142/200 — davis7dotsh/better-context (commit_message)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'max instances bumped, temp fix for this issue' — deítico ao issue #29 e à mudança de max instances, trade-off implícito no rótulo.

143/200 — buttercup/buttercup-desktop (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Temporary fix for High Sierra' — deítico à versão específica do macOS, trade-off implícito no rótulo.

144/200 — containers/ai-lab-recipes (commit_message)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Temporary fix for bootc CI builds' — deítico ao pipeline de CI específico, trade-off implícito no rótulo.

145/200 — thefrontside/simulacrum (commit_message)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'add stopgap debug in auth0-simulator... abstract logger on stopgap' — deítico ao simulador de auth0, trade-off implícito, elaboração mínima.

146/200 — vercel/ai (pr_body)
stopgap · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟡 provável

O 'stopgap' mencionado pertence a um PR companion (#15256, bump de timeout de CI) que 'pode ser revertido depois que este merge' — este PR é a correção definitiva, não a retenção de um workaround próprio.

147/200 — learning-unlimited/ESP-Website (pr_body)
quick and dirty · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'The changes are quick and dirty, but I can make improvements if anyone thinks it's worth the time' — trade-off explícito, deítico, sem negação.

148/200 — NVIDIA-NeMo/RL (code_comment)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'name_or_path is not available for AutoProcessor, temp fix in get_tokenizer' — deítico à função real, trade-off implícito no rótulo.

149/200 — ryo-ma/github-profile-trophy (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Temporary fix for retry bug' — deítico ao bug específico, trade-off implícito no rótulo.

150/200 — RailsEventStore/rails_event_store (code_comment)
temporary fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟡 provável

Arquivo é um bundle JS de terceiros (GitBook, contém código de jQuery/getDefaultComputedStyle) embutido na documentação — provável código vendored, não decisão própria da equipe (falha condição 1).

151/200 — getsentry/sentry (commit_message)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Stopgap until we get [PR] to work as expected. Using TransactionTestCase doesn't 100% solve the problem' — trade-off explícito e detalhado, deítico, sem negação.

152/200 — paperbits/paperbits-core (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Temporary fix for grid editor to handle email template layouts' — deítico ao componente específico, trade-off implícito no rótulo.

153/200 — plone/Products.CMFPlone (code_comment)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is an ugly hack. So it might as well be explained...' — admissão explícita com tentativa de justificar o raciocínio, deítica, sem negação.

154/200 — VictoriaMetrics/VictoriaMetrics (pr_body)
quick and dirty · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟡 provável

PR marcado explicitamente 'DONT MERGE!!!!' — é um experimento descartável, não uma solução que o autor está resignado a manter (falha o espírito da condição 2: não há intenção de reter).

155/200 — ember-fastboot/ember-cli-fastboot (code_comment)
this is a hack · léxico: categoria A

Sugestão: ❌ NÃO · confiança: 🟢 certo

Arquivo está em test/fixtures/.../vendor.js — código de terceiros vendored usado como fixture de teste, não código próprio do projeto (falha condições 1 e 5).

156/200 — ArcticaProject/nx-libs (code_comment)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'this is just a temp fix to stop redundant changes' — trade-off explícito, deítico ao bloco de comparação de retângulos, sem negação.

157/200 — patsonluk/airline (commit_message)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Temp fix for tooltip clipping. Cause overflow-y:scroll...' — deítico com explicação técnica da causa, trade-off implícito no rótulo.

158/200 — Tencent/TencentKona-11 (code_comment)
this is a hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'REMIND: this is a hack that attempts to cache the system memory image...' — admissão explícita com detalhe técnico, deítica, sem negação.

159/200 — szcompressor/SZ2 (code_comment)
ugly hack · léxico: categoria A

Sugestão: ❌ NÃO · confiança: 🟢 certo

Arquivo está em zstd/legacy/zstd_v07.c — código vendored de versão legada da biblioteca zstd (terceiros), não decisão própria da equipe do SZ2 (falha condição 1).

160/200 — ashvardanian/StringZilla (pr_body)
ugly solution but · léxico: categoria C

Sugestão: ✅ SIM · confiança: 🟢 certo

'I've now guarded first mrs probes with signal handlers. Ugly solution, but it may work' — trade-off explícito, deítico, sem negação.

161/200 — christophhart/HISE (code_comment)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'clang / gcc don't like extern template definitions... so we have to do this ugly hack' — trade-off explícito com justificativa técnica, deítico, sem negação.

162/200 — NetApp/harvest (pr_body)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'I left a proper fix for later. I think this is OK... also added a check in the Render() method (temporary fix)' — trade-off explícito e bem justificado, deítico, sem negação.

163/200 — pulp/pulpcore (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'THIS IS A TEMPORARY FIX to prevent test_pulpimport failures... See the related issue for other approaches' — trade-off explícito e evidenciado com testes, deítico, sem negação.

164/200 — vgvassilev/cling (commit_message)
ugly but it works · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'Ugly but it works, and it's sufficiently internal' — admissão explícita e literal, deítica ao cast de QualType, sem negação.

165/200 — blacklanternsecurity/bbot (pr_body)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a temporary fix and will be removed again once @liquidsec finishes his excavate overhaul' — trade-off explícito com plano de remoção, deítico, sem negação.

166/200 — google-ai-edge/ai-edge-quantizer (commit_message)
temporary fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟢 certo

'Remove temporary fix from ParamsGenerator' — descreve a REMOÇÃO do fix temporário, não sua introdução ou manutenção.

167/200 — BurntSushi/rebar (code_comment)
this is a hack · léxico: categoria A

Sugestão: ❌ NÃO · confiança: 🟢 certo

Arquivo é um corpus/haystack de benchmark (cópia de teste do CPython usada como dado de entrada, não código funcional do projeto); a expressão 'this is a hack' nem aparece no trecho correspondente — ruído de correspondência lexical (falha condição 5).

168/200 — samuelclay/NewsBlur (commit_message)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Stopgap solution for lack of timezone support. Marking a feed as read uses the timestamp...' — trade-off explícito e deítico, sem negação.

169/200 — numworks/epsilon (pr_body)
this is a hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a hack, we should find why this was broken after v12' — admissão explícita com intenção de investigar depois, deítica, sem negação.

170/200 — deepgram/deepgram-python-sdk (code_comment)
this is a hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'this is a hack to make the response look like a dict... otherwise it will throw an exception' — trade-off explícito com justificativa técnica, deítico, sem negação.

171/200 — premake/premake-core (pr_body)
quick and dirty · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a very quick and dirty implementation and works in my use case, but may break in some others' — trade-off explícito com limitação assumida, deítico, sem negação.

172/200 — lindenb/jvarkit (code_comment)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'Another ugly hack sponsored by the letters B, A, and M' em código real de produção (validação de sort order de registros BAM, não string de teste) — admissão explícita e deítica. (Nota: discordo da leitura do Miguel de que seria 'contexto de teste' — 'test the sort order' aqui é verificação/validação, não arquivo de teste.)

173/200 — vacp2p/zerokit (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'temporary fix of ark-circom' num PR de limpeza de qualidade de código — deítico à dependência específica, trade-off implícito no rótulo.

174/200 — mattermost/mattermost-mobile (code_comment)
this is a hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'this is a hack but I could not found another way to solve it' — admissão explícita com tentativa alternativa frustrada, deítica, sem negação.

175/200 — Metaculus/metaculus (code_comment)
dirty hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'Bit of a dirty hack but tl;dr If this was generated recently don't bother!' — trade-off explícito e informal, deítico, sem negação.

176/200 — israpps/Funtuna-Fork (code_comment)
quick and dirty · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a quick and dirty RLE compression algorithm... It could be slightly optimized, but the gains would be rather insignificant' — trade-off explícito com decisão deliberada de não otimizar, deítico, sem negação.

177/200 — corretto/corretto-21 (code_comment)
workaround for now · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'TBD: workaround for now, so test/java/time tests can be run against Java runtime that does not have tzdb' — trade-off explícito, deítico, sem negação.

178/200 — X11Libre/xserver (commit_message)
ugly workaround · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'we need to do an ugly workaround using some preprocessor black magic' até merge de outra MR — trade-off explícito com condição de remoção, deítico, sem negação.

179/200 — cockpit-project/cockpit (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'Temporary fix while shell frame loading gets refactored' — trade-off explícito com plano futuro, deítico, sem negação.

180/200 — metacpan/metacpan-api (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Possibly temporary fix to versions in CPANTesters import' — deítico ao import específico, trade-off implícito e hedgeado ('possibly').

181/200 — skeskinen/smartcut (pr_body)
quick and dirty · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'here's a quick-and-dirty patch to allow frame-number input' — trade-off explícito, deítico, com funcionalidade detalhada, sem negação.

182/200 — jbaublitz/neli (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Temporary fix for clippy' — deítico ao lint específico, trade-off implícito no rótulo.

183/200 — FRRouting/frr (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'allow for temporary startup while we iron out the network.target details' — trade-off explícito com plano futuro, deítico, sem negação.

184/200 — bmax121/APatch (commit_message)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🔴 incerto

'fix monitoring on the user side (temp)' — admissão mínima e deítica, mas sem elaboração do trade-off; nota: o Miguel marcou este mesmo item como NÃO/CERTEZA, então vale discutir na calibração.

185/200 — OpenTenBase/TXSQL (commit_message)
temporary fix · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟢 certo

'Reverted commit... since the temporary fix in it becomes obsolete' — descreve a REVERSÃO/remoção do fix temporário, não sua manutenção.

186/200 — PaddlePaddle/PaddleDetection (code_comment)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'FIXME(zcd): A temporary fix for some language model that has sparse parameter' — trade-off explícito, deítico, sem negação.

187/200 — paradigmxyz/reth (pr_body)
ugly workaround · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a temporary (and ugly) workaround until the chainspec is more generic' — trade-off explícito com plano futuro, deítico, sem negação.

188/200 — c-ares/c-ares (commit_message)
ugly hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'moved the curl_off_t check... since it is a somewhat ugly hack' — o hack é realocado mas mantido (não removido), admissão explícita, deítica, sem negação.

189/200 — EasyCorp/EasyAdminBundle (pr_body)
ugly hack · léxico: categoria A

Sugestão: ❌ NÃO · confiança: 🟢 certo

'finally allow us to get rid of the ugly hack' — descreve a REMOÇÃO do hack, não sua manutenção.

190/200 — serenity-rs/serenity (commit_message)
band-aid fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'Band-aid fix unused_async clippy errors' — deítico ao lint específico, trade-off implícito no rótulo ('band-aid').

191/200 — go-vikunja/vikunja (code_comment)
quick and dirty · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'this is a quick and dirty implementation of the WCAG 3.0 APCA color contrast formula' — admissão explícita de aproximação, deítica, sem negação.

192/200 — ScintillaOrg/lexilla (pr_body)
quick and dirty · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟡 provável

'Quick and dirty sample file' refere-se a um arquivo de teste pessoal usado durante o desenvolvimento para validar a ideia, não ao código do lexer efetivamente submetido no PR — falha condição 3.

193/200 — CleverRaven/Cataclysm-DDA (pr_body)
quick and dirty · léxico: categoria B

Sugestão: ❌ NÃO · confiança: 🟢 certo

'quick-and-dirty' descreve um conceito de lore/mecânica de jogo (endurecimento de metal na ficção), não uma admissão sobre a qualidade do código do PR — falha condição 3.

194/200 — LibreELEC/LibreELEC.tv (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'busybox: temporary fix for nfs based boot' — deítico ao componente específico, trade-off implícito no rótulo.

195/200 — Xilinx/qemu (commit_message)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'As a temporary fix... simply make the config size smaller at init time. Long term we probably want...' — trade-off explícito e bem documentado, deítico, sem negação.

196/200 — openfiletax/openfile (code_comment)
stopgap · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This component is a stopgap for a planned P2 and has not gone through standard design + testing / review' — trade-off explícito com admissão de processo pulado, deítico, sem negação.

197/200 — babashka/scittle (pr_body)
quick and dirty · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'a quick-and-dirty fix is to just append a bit of whitespace' — trade-off explícito, deítico, sem negação.

198/200 — Azure/azure-webjobs-sdk (pr_body)
temporary fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟢 certo

'This is a temporary fix as the ConfigurationUtility type will be removed as part of the DI work' — trade-off explícito com plano futuro, deítico, sem negação.

199/200 — HaxeFoundation/hashlink (commit_message)
temp fix · léxico: categoria B

Sugestão: ✅ SIM · confiança: 🟡 provável

'temp fix for #217' — deítico ao issue específico, trade-off implícito no rótulo.

200/200 — vaadin/flow-components (code_comment)
this is a hack · léxico: categoria A

Sugestão: ✅ SIM · confiança: 🟢 certo

'this is a hack to adjust the route used in tests' em script real de build (não string de teste) — trade-off explícito, deítico, sem negação.







