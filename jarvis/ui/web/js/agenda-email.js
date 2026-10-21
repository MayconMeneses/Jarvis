  // ── Botão "Bom dia" e tela "Agenda e e-mail". Segredos: só vão da caixa de senha para a ponte; o campo é limpo e nada volta. ──
  (() => {
    const $ = (id) => document.getElementById(id);
    const dlg = $("agenda-email");
    const api = () => (window.pywebview && window.pywebview.api) || null;
    function no(tag, texto, cls) { const e = document.createElement(tag); if (texto != null) e.textContent = texto; if (cls) e.className = cls; return e; }
    function dizer(id, texto, ok) { const e = $(id); e.textContent = texto || ""; e.className = "feedback " + (ok ? "on-ok" : "on-no"); }

    // Bom dia: pede o resumo (a Jarvis também fala) e mostra na conversa.
    $("bom-dia").addEventListener("click", async (ev) => {
      const botao = ev.currentTarget, ponte = api();
      if (!ponte || !ponte.bom_dia_agora) return;
      botao.disabled = true;
      const espera = addTyping();
      try {
        const texto = await ponte.bom_dia_agora();
        espera.remove();
        add("jarvis", texto);
      } catch (e) {
        espera.remove();
        add("error", "Não consegui montar o bom dia agora. Tente de novo em instantes.");
      }
      botao.disabled = false;
    });

    // Linha de uma conta/agenda já conectada: só o nome (e o servidor), com Testar e Remover.
    function linha(nome, detalhe, testar, remover, fbId) {
      const li = no("li"), t = no("button", "Testar"), r = no("button", "Remover");
      t.type = r.type = "button"; r.className = "danger";
      const SEM = "Não consegui falar com a Jarvis agora. Tente de novo.";
      t.addEventListener("click", async () => { dizer(fbId, "Testando…", true); try { const x = await testar(nome); dizer(fbId, x.mensagem, x.ok); } catch (e) { dizer(fbId, SEM, false); } });
      r.addEventListener("click", async () => { try { const x = await remover(nome); await recarregar(); dizer(fbId, x.mensagem, x.ok); } catch (e) { dizer(fbId, SEM, false); } });
      li.append(no("span", nome + (detalhe ? " · " + detalhe : "")), t, r);
      return li;
    }

    async function recarregar() {
      const ponte = api();
      if (!ponte) return;
      const s = await ponte.agenda_email_status();
      $("ae-ag-lista").replaceChildren(...s.agendas.map((a) => linha(a.apelido, a.cor, (n) => ponte.testar_agenda(n), (n) => ponte.remover_agenda(n), "ae-ag-fb")));
      $("ae-im-lista").replaceChildren(...s.imap.map((c) => linha(c.apelido, c.host, (n) => ponte.testar_imap(n), (n) => ponte.desconectar_imap(n), "ae-im-fb")));
      const sel = $("ae-im-host");
      if (!sel.options.length) sel.replaceChildren(...s.hosts.map((h) => new Option(h, h)));
    }

    $("ae-ag-conectar").addEventListener("click", async () => {
      const ponte = api(), nome = $("ae-ag-nome").value.trim(), link = $("ae-ag-link").value.trim();
      if (!ponte) return;
      if (!nome || !link) { dizer("ae-ag-fb", "Preencha o nome e o link da agenda.", false); return; }
      dizer("ae-ag-fb", "Conectando…", true);
      let r;
      try { r = await ponte.conectar_agenda(nome, link, $("ae-ag-cor").value); } catch (e) { $("ae-ag-link").value = ""; dizer("ae-ag-fb", "Não consegui falar com a Jarvis agora. Tente de novo.", false); return; }
      $("ae-ag-link").value = "";  // o link não fica na tela
      if (!r.ok) { dizer("ae-ag-fb", r.mensagem, false); return; }
      await recarregar();
      const t = await ponte.testar_agenda(nome);
      dizer("ae-ag-fb", r.mensagem + " " + t.mensagem, t.ok);
    });

    $("ae-im-conectar").addEventListener("click", async () => {
      const ponte = api(), nome = $("ae-im-nome").value.trim(), user = $("ae-im-user").value.trim(), senha = $("ae-im-senha").value;
      if (!ponte) return;
      if (!nome || !user || !senha) { dizer("ae-im-fb", "Preencha nome, e-mail e senha de app.", false); return; }
      dizer("ae-im-fb", "Conectando…", true);
      let r;
      try { r = await ponte.conectar_imap(nome, $("ae-im-host").value, user, senha); } catch (e) { $("ae-im-senha").value = ""; dizer("ae-im-fb", "Não consegui falar com a Jarvis agora. Tente de novo.", false); return; }
      $("ae-im-senha").value = "";  // a senha não fica na tela
      if (!r.ok) { dizer("ae-im-fb", r.mensagem, false); return; }
      await recarregar();
      const t = await ponte.testar_imap(nome);
      dizer("ae-im-fb", t.ok ? t.mensagem : "Conta guardada, mas o teste falhou: " + t.mensagem, t.ok);
    });

    $("open-agenda").addEventListener("click", async () => { dlg.showModal(); try { await recarregar(); } catch (e) { dizer("ae-ag-fb", "Sem resposta da Jarvis.", false); } });
    $("close-agenda-email").addEventListener("click", () => { $("ae-ag-link").value = ""; $("ae-im-senha").value = ""; dlg.close(); });
    dlg.addEventListener("close", () => { $("ae-ag-link").value = ""; $("ae-im-senha").value = ""; });
  })();
