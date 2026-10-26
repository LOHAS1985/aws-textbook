// 全ページ共通の読みやすさ・使いやすさの機能(直接編集する)。
// ・表示設定(テーマ・文字サイズ・読み上げの速さ):ヘッダーの「Aa」ボタン。設定は localStorage に保存し、
//   テーマと文字サイズは各ページの <head> の小さなスクリプトが描画前に反映する
// ・検索:ヘッダーの虫めがねでトップの全ページ検索へ。「/」キーでも移動する
// ・読み上げ・印刷:サービス・用語・運用シナリオなどのページ見出しの下にボタンを出す
// ・用語のポップアップ:本文中のサービス・用語へのリンクに、マウスを重ねる(スマホは1回タップ)と説明を出す
//   (内容は build.py が作る js/glossary.js)
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
    tools.appendChild(search);
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
      if (e.closest(SKIP) || e.closest("tr") && e.tagName !== "TR") continue;
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
    // 構成演習は解説(答え)まで読み上げてしまうので、読み上げは付けない
    if (!/\/exercises\//.test(location.pathname)) setupReader(main, tools);
    var print = el("button", "page-tool", '<span aria-hidden="true">⎙</span> 印刷');
    print.type = "button";
    print.title = "このページを印刷・PDFに保存";
    print.addEventListener("click", function () { window.print(); });
    tools.appendChild(print);
    text.appendChild(tools);
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
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
