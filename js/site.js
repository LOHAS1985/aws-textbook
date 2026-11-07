// 全ページ共通の読みやすさ・使いやすさの機能(直接編集する)。
// ・表示設定(テーマ・文字サイズ・読み上げの速さ):ヘッダーの「Aa」ボタン。設定は localStorage に保存し、
//   テーマと文字サイズは各ページの <head> の小さなスクリプトが描画前に反映する
// ・検索:ヘッダーの虫めがねでトップの全ページ検索へ。「/」キーでも移動する
// ・読み上げ・印刷:サービス・用語・運用シナリオなどのページ見出しの下にボタンを出す
// ・用語のポップアップ:本文中のサービス・用語へのリンクに、マウスを重ねる(スマホは1回タップ)と説明を出す
//   (内容は build.py が作る js/glossary.js)
// ・しおり・学習メモ:ページ見出しの下のボタン。localStorage に保存し、ヘッダーの「しおり」からマイページ(js/mypage.js)で見返す
// ・図の拡大:図の下のボタンで全画面に広げる。長いページの2章は、節(h3)ごとに開閉できる
// JavaScript が動かない環境では、どのボタンも表示されない(ページはそのまま読める)。
(function () {
  var PREFS = "aws-textbook-prefs";
  var script = document.currentScript;
  var base = script ? script.src.replace(/js\/site\.js(\?.*)?$/, "") : "../";
  var root = document.documentElement;

  function load() {
    try { return JSON.parse(localStorage.getItem(PREFS) || "{}") || {}; } catch (e) { return {}; }
  }
  function save(p) {
    try { localStorage.setItem(PREFS, JSON.stringify(p)); } catch (e) {}
  }
  var prefs = load();

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  // ---- しおり・メモの保存(この端末のブラウザにだけ保存する) ----
  var BM_KEY = "aws-textbook-bookmarks", NOTE_KEY = "aws-textbook-notes";
  var syncers = [];  // 保存内容が変わったときに、ボタンや件数の表示を合わせる関数の一覧
  function readJSON(key, fallback) {
    try { var v = JSON.parse(localStorage.getItem(key) || "null"); return v === null ? fallback : v; } catch (e) { return fallback; }
  }
  function writeJSON(key, v) {
    try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) {}
  }
  function bookmarks() {
    var v = readJSON(BM_KEY, []);
    return Array.isArray(v) ? v.filter(function (b) { return b && typeof b.url === "string"; }) : [];
  }
  function notes() {
    var v = readJSON(NOTE_KEY, {});
    return v && typeof v === "object" && !Array.isArray(v) ? v : {};
  }
  function pageTitle() { var h = document.querySelector(".page-head h1"); return h ? h.textContent.trim() : document.title; }
  function pageLead() { var l = document.querySelector(".page-head .lead"); return l ? l.textContent.trim() : ""; }
  function syncAll() { for (var i = 0; i < syncers.length; i++) syncers[i](); }
  function changed() { window.dispatchEvent(new Event("aws-textbook-change")); }

  // ---- 表示設定 ----
  var THEMES = [["", "自動"], ["light", "ライト"], ["dark", "ダーク"]];
  var SIZES = [["s", "小"], ["", "標準"], ["l", "大"], ["xl", "特大"]];
  var RATES = [["0.8", "ゆっくり"], ["", "標準"], ["1.3", "速く"], ["1.6", "とても速く"]];

  function apply() {
    if (prefs.theme) root.setAttribute("data-theme", prefs.theme); else root.removeAttribute("data-theme");
    if (prefs.size) root.setAttribute("data-size", prefs.size); else root.removeAttribute("data-size");
    var metas = document.querySelectorAll('meta[name="theme-color"]');
    for (var i = 0; i < metas.length; i++) {
      var m = metas[i];
      if (!m.hasAttribute("data-media")) m.setAttribute("data-media", m.getAttribute("media") || "");
      var dark = m.getAttribute("data-media").indexOf("dark") >= 0;
      if (prefs.theme) {
        m.setAttribute("media", (prefs.theme === "dark") === dark ? "all" : "not all");
      } else {
        m.setAttribute("media", m.getAttribute("data-media"));
      }
    }
  }

  function choiceRow(label, key, options) {
    var row = el("div", "prefs-row");
    row.appendChild(el("span", "prefs-label", label));
    var group = el("div", "prefs-seg");
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", label);
    options.forEach(function (o) {
      var b = el("button", "", o[1]);
      b.type = "button";
      b.setAttribute("aria-pressed", (prefs[key] || "") === o[0]);
      b.addEventListener("click", function () {
        if (o[0]) prefs[key] = o[0]; else delete prefs[key];
        save(prefs);
        apply();
        var bs = group.querySelectorAll("button");
        for (var i = 0; i < bs.length; i++) bs[i].setAttribute("aria-pressed", bs[i] === b);
      });
      group.appendChild(b);
    });
    row.appendChild(group);
    return row;
  }

  function setupHeader() {
    var inner = document.querySelector(".site-header .inner");
    if (!inner) return;
    var tools = el("div", "site-tools");
    var search = el("a", "tool-btn",
      '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>');
    search.href = base + "index.html#search";
    search.setAttribute("aria-label", "全ページを検索");
    search.title = "全ページを検索(/)";
    var btn = el("button", "tool-btn tool-aa", "Aa");
    btn.type = "button";
    btn.setAttribute("aria-label", "表示設定");
    btn.setAttribute("aria-expanded", "false");
    btn.title = "表示設定(テーマ・文字サイズ・読み上げの速さ)";
    var panel = el("div", "prefs-panel");
    panel.hidden = true;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "表示設定");
    panel.appendChild(choiceRow("テーマ", "theme", THEMES));
    panel.appendChild(choiceRow("文字サイズ", "size", SIZES));
    if ("speechSynthesis" in window) panel.appendChild(choiceRow("読み上げの速さ", "rate", RATES));
    function toggle(open) {
      panel.hidden = !open;
      btn.setAttribute("aria-expanded", open);
    }
    btn.addEventListener("click", function (e) { e.stopPropagation(); toggle(panel.hidden); });
    panel.addEventListener("click", function (e) { e.stopPropagation(); });
    document.addEventListener("click", function () { toggle(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !panel.hidden) { toggle(false); btn.focus(); } });
    // しおり・メモ(マイページへ)。件数は保存済みのしおりの数
    var mine = el("a", "tool-btn tool-mine",
      '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M6 3h12v18l-6-4-6 4z"/></svg><span class="tool-count" hidden></span>');
    mine.href = base + "mypage.html";
    mine.setAttribute("aria-label", "しおり・メモ");
    mine.title = "しおり・メモ(この端末に保存)";
    var count = mine.querySelector(".tool-count");
    syncers.push(function () {
      var n = bookmarks().length;
      count.hidden = !n;
      count.textContent = n;
    });
    tools.appendChild(search);
    tools.appendChild(mine);
    tools.appendChild(btn);
    tools.appendChild(panel);
    inner.appendChild(tools);

    // 「/」キーで検索へ(検索欄のあるページは、そのページの検索欄を使う)
    if (!document.getElementById("site-q") && !document.getElementById("toc-q")) {
      document.addEventListener("keydown", function (e) {
        var t = e.target.tagName;
        if (e.key === "/" && t !== "INPUT" && t !== "TEXTAREA" && !e.ctrlKey && !e.metaKey) {
          e.preventDefault();
          location.href = search.href;
        }
      });
    }
  }

  // ---- 読み上げ ----
  var BLOCKS = "h2, h3, h4, p, li, dt, dd, figcaption, tr";
  var SKIP = ".backlinks, .graph-chapter, .page-toc, pre, svg, .ex-tabs, .ex-free, .anchor";

  function blockText(e) {
    if (e.tagName === "TR") {
      var cells = e.querySelectorAll("th, td");
      return Array.prototype.map.call(cells, function (c) { return c.textContent.trim(); }).filter(Boolean).join("、");
    }
    var c = e.cloneNode(true);
    var drop = c.querySelectorAll("ul, ol, p, table, figure, dl, div, pre, svg, .anchor");
    for (var i = 0; i < drop.length; i++) drop[i].remove();
    return c.textContent.replace(/\s+/g, " ").trim();
  }

  function readingList(main) {
    var list = [];
    var head = main.querySelector(".page-head h1");
    if (head) list.push({ el: main.querySelector(".page-head"), text: head.textContent + "。" +
      ((main.querySelector(".page-head .lead") || {}).textContent || "") });
    var found = main.querySelectorAll("section.chapter :is(" + BLOCKS + ")");
    for (var i = 0; i < found.length; i++) {
      var e = found[i];
      // 閉じているタブ(運用シナリオの解説など)は読まない
      // 閉じている節(章の折りたたみ)の本文も読まない。節の見出し(summary の中)は読む
      var folded = e.closest("details:not([open])") && !e.closest("summary");
      if (e.closest(SKIP) || e.closest("[hidden]") || folded || e.closest("tr") && e.tagName !== "TR") continue;
      var text = blockText(e);
      if (text) list.push({ el: e, text: text });
    }
    return list;
  }

  function setupReader(main, tools) {
    if (!("speechSynthesis" in window)) return;
    var synth = window.speechSynthesis;
    var list = null, index = 0, playing = false, token = 0, bar = null, status, playBtn;
    var btn = el("button", "page-tool", '<span aria-hidden="true">▶</span> 読み上げ');
    btn.type = "button";
    tools.appendChild(btn);

    function voice() {
      var vs = synth.getVoices().filter(function (v) { return /^ja/i.test(v.lang); });
      return vs.filter(function (v) { return v.localService; })[0] || vs[0] || null;
    }
    function mark() {
      var cur = main.querySelector(".tts-now");
      if (cur) cur.classList.remove("tts-now");
      if (!list[index]) return;
      var e = list[index].el;
      e.classList.add("tts-now");
      var r = e.getBoundingClientRect();
      if (r.top < 60 || r.bottom > innerHeight - 80) e.scrollIntoView({ block: "center", behavior: "smooth" });
      status.textContent = (index + 1) + " / " + list.length;
    }
    var failures = 0;
    function next(my) {
      if (my !== token || !playing) return;
      index++;
      setTimeout(speak, 0);
    }
    function speak() {
      if (!playing) return;
      if (index >= list.length) { stop(); return; }
      mark();
      var my = ++token;
      var u = new SpeechSynthesisUtterance(list[index].text);
      u.lang = "ja-JP";
      var v = voice();
      if (v) u.voice = v;
      u.rate = parseFloat(load().rate || "1");
      u.onstart = function () { failures = 0; };
      u.onend = function () { next(my); };
      u.onerror = function (e) {
        if (e.error === "interrupted" || e.error === "canceled") return;
        // 音声が使えない環境では、何度も失敗するので止めて知らせる
        if (++failures >= 3) {
          pause();
          status.textContent = "この端末では読み上げできません";
          return;
        }
        next(my);
      };
      synth.speak(u);
    }
    function setPlaying(on) {
      playing = on;
      playBtn.innerHTML = on ? "❚❚" : "▶";
      playBtn.setAttribute("aria-label", on ? "一時停止" : "再開");
    }
    function play() { setPlaying(true); synth.cancel(); speak(); }
    function pause() { setPlaying(false); token++; synth.cancel(); }
    function stop() {
      pause();
      var cur = main.querySelector(".tts-now");
      if (cur) cur.classList.remove("tts-now");
      if (bar) bar.hidden = true;
    }
    function move(d) {
      index = Math.max(0, Math.min(list.length - 1, index + d));
      if (playing) play(); else mark();
    }
    function makeBar() {
      bar = el("div", "tts-bar");
      bar.setAttribute("role", "region");
      bar.setAttribute("aria-label", "読み上げ");
      function b(label, text, fn) {
        var x = el("button", "", text);
        x.type = "button";
        x.setAttribute("aria-label", label);
        x.title = label;
        x.addEventListener("click", fn);
        bar.appendChild(x);
        return x;
      }
      b("前の段落", "⏮", function () { move(-1); });
      playBtn = b("一時停止", "❚❚", function () { if (playing) pause(); else play(); });
      b("次の段落", "⏭", function () { move(1); });
      status = el("span", "tts-status");
      bar.appendChild(status);
      b("読み上げを終了", "✕", stop);
      document.body.appendChild(bar);
    }
    btn.addEventListener("click", function () {
      list = readingList(main);
      if (!list.length) return;
      if (!bar) makeBar();
      bar.hidden = false;
      // 少しでもスクロールしていれば、画面に見えている段落から読む
      index = 0;
      if (scrollY > 200) {
        for (var i = 0; i < list.length; i++) {
          if (list[i].el.getBoundingClientRect().bottom > 80) { index = i; break; }
        }
      }
      play();
    });
    // 本文の段落をダブルクリックすると、そこから読む(読み上げ中のみ)
    main.addEventListener("dblclick", function (e) {
      if (!bar || bar.hidden || !list) return;
      for (var i = 0; i < list.length; i++) {
        if (list[i].el.contains(e.target)) { index = i; play(); return; }
      }
    });
    addEventListener("pagehide", function () { synth.cancel(); });
  }

  function setupPageTools() {
    var main = document.querySelector("main");
    var text = main && main.querySelector(".page-head.hero .hero-text");
    if (!text) return;
    var tools = el("div", "page-tools");
    setupReader(main, tools);
    var print = el("button", "page-tool", '<span aria-hidden="true">⎙</span> 印刷');
    print.type = "button";
    print.title = "このページを印刷・PDFに保存";
    print.addEventListener("click", function () { window.print(); });
    tools.appendChild(print);
    setupMarks(main, tools);
    text.appendChild(tools);
  }

  // ---- しおり・学習メモ(ページ見出しの下のボタン。メモ欄は本文の下に開く) ----
  function setupMarks(main, tools) {
    var url = location.pathname;
    var mark = el("button", "page-tool");
    mark.type = "button";
    mark.title = "このページをしおりに追加・解除";
    mark.addEventListener("click", function () {
      var list = bookmarks();
      var at = -1;
      list.forEach(function (b, k) { if (b.url === url) at = k; });
      if (at >= 0) list.splice(at, 1); else list.push({ url: url, title: pageTitle(), lead: pageLead() });
      writeJSON(BM_KEY, list);
      changed();
    });

    var note = el("button", "page-tool");
    note.type = "button";
    note.setAttribute("aria-expanded", "false");
    note.setAttribute("aria-controls", "note-panel");
    note.innerHTML = '<span aria-hidden="true">✎</span> メモ';
    var panel = el("div", "note-panel");
    panel.id = "note-panel";
    panel.hidden = true;
    var label = el("label", "note-label", "このページのメモ");
    label.setAttribute("for", "note-text");
    var ta = el("textarea", "note-text");
    ta.id = "note-text";
    ta.rows = 5;
    ta.placeholder = "気づいたことや覚えておきたいことを書けます(自動で保存されます)";
    panel.appendChild(label);
    panel.appendChild(ta);
    panel.appendChild(el("p", "note-hint", "メモはこの端末のブラウザにだけ保存されます。ヘッダーの「しおり」で見返せます。"));
    note.addEventListener("click", function () {
      var open = panel.hidden;
      panel.hidden = !open;
      note.setAttribute("aria-expanded", open);
      if (open) ta.focus();
    });
    ta.addEventListener("input", function () {
      var all = notes();
      if (ta.value.trim()) all[url] = { title: pageTitle(), text: ta.value }; else delete all[url];
      writeJSON(NOTE_KEY, all);
      changed();
    });
    main.appendChild(panel);

    syncers.push(function () {
      var on = bookmarks().some(function (b) { return b.url === url; });
      mark.setAttribute("aria-pressed", on);
      mark.innerHTML = '<span aria-hidden="true">' + (on ? "★" : "☆") + "</span> しおり";
      var n = notes()[url];
      var has = !!(n && typeof n.text === "string" && n.text.trim());
      note.classList.toggle("has-note", has);
      if (document.activeElement !== ta) ta.value = has ? n.text : "";
    });
    tools.appendChild(mark);
    tools.appendChild(note);
  }

  // ---- 図の拡大表示(図の下のボタンで全画面にする。運用シナリオの構成演習は対象外) ----
  function setupFigures(main) {
    var figs = main.querySelectorAll("figure.figure");
    for (var i = 0; i < figs.length; i++) {
      var fig = figs[i];
      var svgEl = fig.querySelector("svg");
      if (!svgEl || svgEl.classList.contains("ex-canvas") || fig.closest(".ex-free")) continue;
      var bar = el("div", "fig-tools");
      var b = el("button", "page-tool fig-open-btn", '<span aria-hidden="true">⤢</span> 図を拡大して見る');
      b.type = "button";
      b.addEventListener("click", openFigure.bind(null, fig, svgEl, b));
      bar.appendChild(b);
      fig.appendChild(bar);
    }
  }
  function openFigure(fig, svgEl, opener) {
    var ov = el("div", "fig-overlay");
    ov.setAttribute("role", "dialog");
    ov.setAttribute("aria-modal", "true");
    ov.setAttribute("aria-label", "図の拡大表示");
    var head = el("div", "fig-overlay-head");
    var close = el("button", "fig-close", '<span aria-hidden="true">✕</span> 閉じる');
    close.type = "button";
    head.appendChild(close);
    var zoom = el("div", "fig-zoom");
    zoom.tabIndex = 0;
    zoom.setAttribute("role", "region");
    zoom.setAttribute("aria-label", "図(横にスクロールできます)");
    var copy = svgEl.cloneNode(true);
    copy.removeAttribute("style");
    copy.setAttribute("class", "fig-zoom-svg");
    zoom.appendChild(copy);
    ov.appendChild(head);
    ov.appendChild(zoom);
    var cap = fig.querySelector("figcaption");
    if (cap) {
      var capText = el("p", "fig-cap");
      capText.textContent = cap.textContent.trim();
      ov.appendChild(capText);
    }

    function done() {
      document.removeEventListener("keydown", onKey, true);
      document.documentElement.classList.remove("fig-open");
      ov.remove();
      opener.focus();
    }
    // Escape で閉じる。Tab は閉じるボタンと図の間だけで回す
    function onKey(e) {
      if (e.key === "Escape") { e.preventDefault(); done(); return; }
      if (e.key !== "Tab") return;
      var f = document.activeElement;
      if (e.shiftKey && f === close) { e.preventDefault(); zoom.focus(); }
      else if (!e.shiftKey && f === zoom) { e.preventDefault(); close.focus(); }
      else if (f !== close && f !== zoom) { e.preventDefault(); close.focus(); }
    }
    close.addEventListener("click", done);
    document.body.appendChild(ov);
    document.documentElement.classList.add("fig-open");
    document.addEventListener("keydown", onKey, true);
    close.focus();
  }

  // ---- 長いページの2章:節(h3)ごとに開閉できる(節が5つ以上のとき。本文は変えず details で包む) ----
  function setupFolds(main) {
    var chapters = main.querySelectorAll("section.chapter");
    var ch = null;
    for (var c = 0; c < chapters.length && !ch; c++) {
      var h = chapters[c].querySelector("h2");
      if (h && /^2[.．]/.test(h.textContent.trim())) ch = chapters[c];
    }
    if (!ch) return;
    var h3s = ch.querySelectorAll(":scope > h3");
    if (h3s.length < 5) return;
    var folds = [];
    for (var i = 0; i < h3s.length; i++) {
      var d = el("details", "fold");
      d.open = true;
      var s = el("summary");
      var h3 = h3s[i];
      h3.parentNode.insertBefore(d, h3);
      s.appendChild(h3);
      d.appendChild(s);
      // 次の節(h3)までを、この節の本文として包む
      for (var nx = d.nextElementSibling; nx && nx.tagName !== "H3";) {
        var next = nx.nextElementSibling;
        d.appendChild(nx);
        nx = next;
      }
      folds.push(d);
    }
    function setAll(on) { for (var k = 0; k < folds.length; k++) folds[k].open = on; }
    var tools = el("div", "fold-tools");
    var openAll = el("button", "page-tool", "すべて開く");
    var closeAll = el("button", "page-tool", "すべて閉じる");
    openAll.type = closeAll.type = "button";
    openAll.addEventListener("click", function () { setAll(true); });
    closeAll.addEventListener("click", function () { setAll(false); });
    tools.appendChild(openAll);
    tools.appendChild(closeAll);
    ch.insertBefore(tools, folds[0]);

    // 印刷・PDFは全部開いて出す。終わったら元に戻す
    var before = null;
    addEventListener("beforeprint", function () {
      before = folds.map(function (d) { return d.open; });
      setAll(true);
    });
    addEventListener("afterprint", function () {
      if (before) for (var k = 0; k < folds.length; k++) folds[k].open = before[k];
      before = null;
    });
    // 目次やリンクで閉じた節に飛んだときは、その節を開く
    function openHash() {
      var t = null;
      try { t = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch (e) {}
      for (var p = t && t.closest("details"); p; p = p.parentElement && p.parentElement.closest("details")) p.open = true;
    }
    openHash();
    addEventListener("hashchange", openHash);
  }

  // ---- 用語のポップアップ ----
  function setupPopups() {
    var main = document.querySelector("main");
    if (!main || !main.querySelector("section.chapter")) return;
    var links = Array.prototype.filter.call(main.querySelectorAll("section.chapter a[href]"), function (a) {
      return !a.closest(".backlinks, .graph-chapter, .page-toc, .anchor") && !a.classList.contains("anchor");
    });
    if (!links.length) return;
    var s = document.createElement("script");
    s.src = base + "js/glossary.js";
    s.onload = function () { attach(links, window.AWSB_GLOSSARY || {}); };
    document.head.appendChild(s);
  }

  function attach(links, data) {
    var self = location.pathname.replace(/^.*\/((?:services|terms)\/[\w-]+)\.html$/, "$1");
    var pop = el("div", "term-pop");
    pop.setAttribute("role", "tooltip");
    pop.id = "term-pop";
    pop.hidden = true;
    document.body.appendChild(pop);
    var current = null, showTimer = 0, hideTimer = 0, lastTouch = 0;

    function keyOf(a) {
      var m = a.pathname.match(/\/((?:services|terms)\/[\w-]+)\.html$/);
      return m && m[1] !== self && data[m[1]] ? m[1] : null;
    }
    function esc(t) { return t.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
    function show(a) {
      clearTimeout(hideTimer);
      var d = data[a.getAttribute("data-pop")];
      current = a;
      pop.innerHTML = '<div class="term-pop-head"><span class="badge">' + esc(d.c) + "</span>" +
        (d.i ? '<img src="' + base + "icons/services/" + a.getAttribute("data-pop").split("/")[1] + '.svg" alt="" width="20" height="20">' : "") +
        "<strong>" + esc(d.t) + "</strong></div>" + (d.d ? "<p>" + esc(d.d) + "</p>" : "") +
        '<a class="term-pop-go" href="' + a.href + '">ページを開く →</a>';
      pop.hidden = false;
      a.setAttribute("aria-describedby", "term-pop");
      var r = a.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight;
      var left = Math.max(8, Math.min(r.left + scrollX, scrollX + document.documentElement.clientWidth - w - 8));
      var top = r.bottom + scrollY + 6;
      if (r.bottom + h + 12 > innerHeight && r.top - h - 6 > 0) top = r.top + scrollY - h - 6;
      pop.style.left = left + "px";
      pop.style.top = top + "px";
    }
    function hide() {
      clearTimeout(showTimer);
      pop.hidden = true;
      if (current) current.removeAttribute("aria-describedby");
      current = null;
    }
    function later() { clearTimeout(showTimer); hideTimer = setTimeout(hide, 200); }

    links.forEach(function (a) {
      var k = keyOf(a);
      if (!k) return;
      a.setAttribute("data-pop", k);
      a.classList.add("has-pop");
      a.addEventListener("pointerdown", function (e) { if (e.pointerType === "touch") lastTouch = Date.now(); });
      a.addEventListener("mouseenter", function () {
        if (Date.now() - lastTouch < 800) return;
        clearTimeout(hideTimer);
        showTimer = setTimeout(function () { show(a); }, 300);
      });
      a.addEventListener("mouseleave", later);
      a.addEventListener("focus", function () { if (Date.now() - lastTouch > 800) show(a); });
      a.addEventListener("blur", later);
      // スマホ:1回目のタップで説明を出し、もう1回タップするとページを開く
      a.addEventListener("click", function (e) {
        if (Date.now() - lastTouch < 800 && current !== a) { e.preventDefault(); show(a); }
      });
    });
    pop.addEventListener("mouseenter", function () { clearTimeout(hideTimer); });
    pop.addEventListener("mouseleave", later);
    pop.addEventListener("focusout", function (e) { if (!pop.contains(e.relatedTarget)) later(); });
    document.addEventListener("click", function (e) {
      if (current && !pop.contains(e.target) && e.target.closest("a") !== current) hide();
    });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") hide(); });
    addEventListener("scroll", function () { if (current && Date.now() - lastTouch > 800) hide(); }, { passive: true });
  }

  function init() {
    apply();
    setupHeader();
    setupPageTools();
    setupPopups();
    var main = document.querySelector("main");
    if (main) { setupFigures(main); setupFolds(main); }
    addEventListener("aws-textbook-change", syncAll);
    addEventListener("storage", function (e) { if (e.key === BM_KEY || e.key === NOTE_KEY) syncAll(); });
    syncAll();
    // マイページ(しおり・メモの一覧・書き出し・読み込み)は、#my-root があるページだけ読み込む
    if (document.getElementById("my-root")) {
      var s = document.createElement("script");
      s.src = base + "js/mypage.js";
      document.head.appendChild(s);
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
