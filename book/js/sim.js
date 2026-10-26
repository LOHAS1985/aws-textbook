// 構成演習(build.py が構成演習のページと目次で読み込む。直接編集する)
// ・穴埋め:図の空欄と設定の問いを選び、答え合わせをする
// ・自由構成:部品を図に置いて矢印でつなぎ、正解の構成(build.py が #ex-graph に埋め込む)と比べる
// 本文の書き方:
//   <div class="ex-item" data-node="図のノードID(省略可)">
//     <p class="ex-q">問い</p>
//     <ul class="ex-choices">
//       <li data-ok data-short="図に出す短い名前">正解の選択肢<span class="ex-why">解説</span></li>
//       <li data-short="…">不正解の選択肢<span class="ex-why">解説</span></li>
//     </ul>
//   </div>
// 選択肢・部品は表示のたびに並べ替える。結果は閲覧者のブラウザ(localStorage)にだけ保存する。
(function () {
  var KEY = "aws-textbook-ex:", FREE_KEY = "aws-textbook-free:";
  var SVGNS = "http://www.w3.org/2000/svg";

  function store(key, value) {
    try {
      if (value === undefined) return JSON.parse(localStorage.getItem(key) || "null");
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) { return null; }
  }
  function slugOf(path) {
    var m = /([^\/]+)\.html$/.exec(path);
    return m ? m[1] : "";
  }
  function today() {
    var d = new Date();
    return d.getFullYear() + "-" + (d.getMonth() + 1) + "-" + d.getDate();
  }
  function shuffle(list) {
    for (var i = list.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = list[i]; list[i] = list[j]; list[j] = t;
    }
    return list;
  }
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }
  function svg(tag, attrs) {
    var e = document.createElementNS(SVGNS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }

  // ---- 目次:解いたことのある演習に結果を表示する ----
  function markIndex() {
    var links = document.querySelectorAll(".toc-category li a");
    for (var i = 0; i < links.length; i++) {
      var slug = slugOf(links[i].getAttribute("href"));
      var r = store(KEY + slug), f = store(FREE_KEY + slug);
      var name = links[i].querySelector(".name");
      if (r) {
        var b = el("span", "ex-badge" + (r.score === r.total ? " ex-badge-ok" : ""));
        b.textContent = "穴埋め " + r.score + "/" + r.total;
        name.appendChild(b);
      }
      if (f && f.ok) {
        var c = el("span", "ex-badge ex-badge-ok");
        c.textContent = "自由構成 ✓";
        name.appendChild(c);
      }
    }
  }

  // ---- 穴埋め ----
  function setupFill(items, slug, wrap) {
    function nodeOf(item) {
      var id = item.getAttribute("data-node");
      return id ? wrap.querySelector('svg g[data-node="' + id + '"]') : null;
    }
    function setNode(item, text, cls) {
      var g = nodeOf(item);
      if (!g) return;
      var label = g.querySelector("text");
      if (!label.hasAttribute("data-blank")) label.setAttribute("data-blank", label.textContent);
      label.textContent = text === null ? label.getAttribute("data-blank") : text;
      g.querySelector("rect").setAttribute("class", cls);
    }
    function shortOf(li) {
      return li.getAttribute("data-short") || li.querySelector("label").textContent;
    }

    for (var i = 0; i < items.length; i++) {
      var ul = items[i].querySelector(".ex-choices");
      var lis = shuffle(Array.prototype.slice.call(ul.children));
      for (var j = 0; j < lis.length; j++) {
        var li = lis[j];
        ul.appendChild(li);
        var label = el("label");
        var input = el("input");
        input.type = "radio";
        input.name = "ex" + i;
        label.appendChild(input);
        var nodes = Array.prototype.slice.call(li.childNodes);
        for (var k = 0; k < nodes.length; k++) {
          if (!(nodes[k].classList && nodes[k].classList.contains("ex-why"))) label.appendChild(nodes[k]);
        }
        li.insertBefore(label, li.firstChild);
        input.addEventListener("change", (function (item, li) {
          return function () {
            var all = item.querySelectorAll("li");
            for (var k = 0; k < all.length; k++) all[k].classList.remove("ex-selected");
            li.classList.add("ex-selected");
            setNode(item, shortOf(li), "dg-blank dg-filled");
          };
        })(items[i], li));
      }
      items[i].appendChild(el("div", "ex-feedback"));
    }

    var bar = el("div", "ex-actions",
      '<button type="button" class="ex-check">答え合わせ</button>'
      + '<button type="button" class="ex-reset" hidden>もう一度解く</button>'
      + '<p class="ex-result" role="status"></p>');
    items[items.length - 1].parentNode.insertBefore(bar, items[items.length - 1].nextSibling);
    var result = bar.querySelector(".ex-result");
    var prev = store(KEY + slug);
    if (prev) result.textContent = "前回:" + prev.total + "問中" + prev.score + "問正解(" + prev.date + ")";

    function choiceHtml(li) {
      var label = li.querySelector("label").cloneNode(true);
      label.removeChild(label.querySelector("input"));
      return label.innerHTML;
    }

    bar.querySelector(".ex-check").addEventListener("click", function () {
      var score = 0;
      for (var i = 0; i < items.length; i++) {
        var item = items[i];
        var chosen = item.querySelector("input:checked");
        var chosenLi = chosen ? chosen.closest("li") : null;
        var answer = item.querySelector("li[data-ok]");
        var ok = chosenLi === answer;
        if (ok) score++;
        item.classList.add(ok ? "is-ok" : "is-ng");
        answer.classList.add("ex-answer");
        if (chosenLi && !ok) chosenLi.classList.add("ex-wrong");
        var inputs = item.querySelectorAll("input");
        for (var k = 0; k < inputs.length; k++) inputs[k].disabled = true;
        var fb = "";
        if (!ok) {
          fb += chosenLi
            ? '<p><span class="ex-mark ng">×</span>' + choiceHtml(chosenLi) + ":"
              + chosenLi.querySelector(".ex-why").innerHTML + "</p>"
            : '<p><span class="ex-mark ng">×</span>未回答</p>';
        }
        fb += '<p><span class="ex-mark ok">○</span>' + choiceHtml(answer) + ":"
          + answer.querySelector(".ex-why").innerHTML + "</p>";
        item.querySelector(".ex-feedback").innerHTML = fb;
        setNode(item, shortOf(answer), ok ? "dg-ok" : "dg-ng");
      }
      store(KEY + slug, { score: score, total: items.length, date: today() });
      result.textContent = items.length + "問中" + score + "問正解"
        + (score === items.length ? "。3章の解説で、構成全体の考え方も確かめましょう。" : "。各問の下の解説で、正解との違いを確かめましょう。");
      this.hidden = true;
      bar.querySelector(".ex-reset").hidden = false;
    });

    bar.querySelector(".ex-reset").addEventListener("click", function () {
      for (var i = 0; i < items.length; i++) {
        var item = items[i];
        item.classList.remove("is-ok", "is-ng");
        var lis = item.querySelectorAll("li");
        for (var k = 0; k < lis.length; k++) lis[k].classList.remove("ex-answer", "ex-wrong", "ex-selected");
        var inputs = item.querySelectorAll("input");
        for (k = 0; k < inputs.length; k++) { inputs[k].disabled = false; inputs[k].checked = false; }
        item.querySelector(".ex-feedback").innerHTML = "";
        setNode(item, null, "dg-blank");
      }
      result.textContent = "";
      this.hidden = true;
      bar.querySelector(".ex-check").hidden = false;
      wrap.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  // ---- 自由構成 ----
  function setupFree(graph, slug, box) {
    var colw = graph.colw, rowh = graph.rowh, M = 24, NW = colw - 20, NH = 46;
    var maxX = 0, maxY = 0;
    graph.nodes.forEach(function (n) { maxX = Math.max(maxX, n.x); maxY = Math.max(maxY, n.y); });
    var W = M * 2 + (Math.ceil(maxX) + 1) * colw, H = M * 2 + (Math.ceil(maxY) + 1) * rowh;
    var byId = {};
    graph.nodes.forEach(function (n) { byId[n.id] = n; });

    box.innerHTML = '<p class="ex-free-help">要件を満たすように、下の部品から必要なものだけを置き、'
      + '<strong>2つを順にタップすると矢印でつながります</strong>(同じ2つをもう一度で解除)。部品はドラッグで動かせます。</p>'
      + '<div class="ex-palette"></div>'
      + '<div class="fig-scroll ex-canvas-wrap"></div>'
      + '<div class="ex-actions"><button type="button" class="ex-judge">判定する</button>'
      + '<button type="button" class="ex-del ex-sub">選んだ部品を外す</button>'
      + '<button type="button" class="ex-clear ex-sub">すべて消す</button>'
      + '<button type="button" class="ex-show ex-sub">正解を表示</button></div>'
      + '<ul class="ex-free-result" role="status"></ul>';
    var palette = box.querySelector(".ex-palette");
    var canvas = svg("svg", { "class": "ex-canvas", viewBox: "0 0 " + W + " " + H,
      style: "max-width:" + W + "px;min-width:" + Math.min(W, 480) + "px", role: "img", "aria-label": "自由構成の作業エリア" });
    var defs = svg("defs", {});
    var marker = svg("marker", { id: "exfree-head", viewBox: "0 0 10 10", refX: 9, refY: 5,
      markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" });
    marker.appendChild(svg("path", { d: "M0,0 L10,5 L0,10 z", "class": "dg-head" }));
    defs.appendChild(marker);
    canvas.appendChild(defs);
    var edgeLayer = svg("g", {}), nodeLayer = svg("g", {});
    canvas.appendChild(edgeLayer);
    canvas.appendChild(nodeLayer);
    box.querySelector(".ex-canvas-wrap").appendChild(canvas);
    var resultList = box.querySelector(".ex-free-result");

    var placed = [], links = [], selected = null, seq = 0;

    var parts = shuffle(graph.nodes.map(function (n) { return n.label; }).concat(graph.distractors));
    parts.forEach(function (label) {
      var b = el("button", "ex-part");
      b.type = "button";
      b.textContent = label;
      b.addEventListener("click", function () { addNode(label); });
      palette.appendChild(b);
    });
    function syncPalette() {
      var used = {};
      placed.forEach(function (n) { used[n.label] = true; });
      var bs = palette.querySelectorAll(".ex-part");
      for (var i = 0; i < bs.length; i++) bs[i].disabled = !!used[bs[i].textContent];
    }

    function freeSlot() {
      for (var r = 0; ; r++) {
        for (var c = 0; c * colw + NW + M <= W; c++) {
          var x = M + c * colw + 10, y = M + r * rowh + (rowh - NH) / 2;
          var hit = placed.some(function (n) { return Math.abs(n.x - x) < NW && Math.abs(n.y - y) < NH + 10; });
          if (!hit) {
            if (y + NH + M > H) { H = y + NH + M; canvas.setAttribute("viewBox", "0 0 " + W + " " + H); }
            return { x: x, y: y };
          }
        }
      }
    }

    function addNode(label, x, y) {
      var pos = x === undefined ? freeSlot() : { x: x, y: y };
      var n = { id: "n" + (seq++), label: label, x: pos.x, y: pos.y };
      n.g = svg("g", { "class": "ex-node", tabindex: 0 });
      n.rect = svg("rect", { width: NW, height: NH, rx: 8, "class": "dg-box" });
      n.text = svg("text", { x: NW / 2, y: NH / 2 + 5, "text-anchor": "middle", "class": "dg-t" });
      n.text.textContent = label;
      n.g.appendChild(n.rect);
      n.g.appendChild(n.text);
      nodeLayer.appendChild(n.g);
      placed.push(n);
      move(n);
      bindDrag(n);
      syncPalette();
      clearResult();
      return n;
    }
    function move(n) {
      n.g.setAttribute("transform", "translate(" + n.x + "," + n.y + ")");
    }
    function select(n) {
      if (selected) selected.rect.classList.remove("ex-sel");
      selected = n;
      if (n) n.rect.classList.add("ex-sel");
    }
    function tap(n) {
      if (!selected) return select(n);
      if (selected === n) return select(null);
      var a = selected, b = n;
      var idx = -1;
      links.forEach(function (l, i) { if (l.a === a && l.b === b) idx = i; });
      if (idx >= 0) links.splice(idx, 1); else links.push({ a: a, b: b });
      select(null);
      drawLinks();
      clearResult();
    }
    function bindDrag(n) {
      var start = null;
      n.g.addEventListener("pointerdown", function (e) {
        var p = point(e);
        start = { px: p.x, py: p.y, x: n.x, y: n.y, moved: false };
        n.g.setPointerCapture(e.pointerId);
        e.preventDefault();
      });
      n.g.addEventListener("pointermove", function (e) {
        if (!start) return;
        var p = point(e), dx = p.x - start.px, dy = p.y - start.py;
        if (Math.abs(dx) + Math.abs(dy) > 4) start.moved = true;
        if (!start.moved) return;
        n.x = Math.max(0, Math.min(W - NW, start.x + dx));
        n.y = Math.max(0, Math.min(H - NH, start.y + dy));
        move(n);
        drawLinks();
      });
      n.g.addEventListener("pointerup", function () {
        if (start && !start.moved) tap(n);
        start = null;
      });
      n.g.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); tap(n); }
      });
    }
    function point(e) {
      var pt = canvas.createSVGPoint();
      pt.x = e.clientX; pt.y = e.clientY;
      var m = canvas.getScreenCTM();
      return m ? pt.matrixTransform(m.inverse()) : { x: e.clientX, y: e.clientY };
    }
    function clip(n, tx, ty) {
      var cx = n.x + NW / 2, cy = n.y + NH / 2, dx = tx - cx, dy = ty - cy;
      if (!dx && !dy) return [cx, cy];
      var t = Math.min(dx ? NW / 2 / Math.abs(dx) : 1e9, dy ? NH / 2 / Math.abs(dy) : 1e9);
      return [cx + dx * t, cy + dy * t];
    }
    function drawLinks() {
      while (edgeLayer.firstChild) edgeLayer.removeChild(edgeLayer.firstChild);
      links.forEach(function (l) {
        var p1 = clip(l.a, l.b.x + NW / 2, l.b.y + NH / 2), p2 = clip(l.b, l.a.x + NW / 2, l.a.y + NH / 2);
        edgeLayer.appendChild(svg("path", { d: "M" + p1[0] + "," + p1[1] + " L" + p2[0] + "," + p2[1],
          "class": "dg-line" + (l.dash ? " dg-dash" : ""), "marker-end": "url(#exfree-head)" }));
      });
    }
    function removeNode(n) {
      links = links.filter(function (l) { return l.a !== n && l.b !== n; });
      placed.splice(placed.indexOf(n), 1);
      nodeLayer.removeChild(n.g);
      if (selected === n) selected = null;
      drawLinks();
      syncPalette();
      clearResult();
    }
    function clearAll() {
      placed.slice().forEach(removeNode);
      H = M * 2 + (Math.ceil(maxY) + 1) * rowh;
      canvas.setAttribute("viewBox", "0 0 " + W + " " + H);
    }
    function clearResult() {
      resultList.innerHTML = "";
      placed.forEach(function (n) { n.rect.setAttribute("class", "dg-box" + (n === selected ? " ex-sel" : "")); });
    }

    box.querySelector(".ex-del").addEventListener("click", function () { if (selected) removeNode(selected); });
    box.querySelector(".ex-clear").addEventListener("click", clearAll);
    box.querySelector(".ex-show").addEventListener("click", function () {
      clearAll();
      var made = {};
      graph.nodes.forEach(function (gn) {
        made[gn.id] = addNode(gn.label, M + gn.x * colw + 10, M + gn.y * rowh + (rowh - NH) / 2);
        made[gn.id].rect.setAttribute("class", "dg-ok");
      });
      graph.edges.forEach(function (e) { links.push({ a: made[e[0]], b: made[e[1]], dash: e[2] }); });
      drawLinks();
      resultList.innerHTML = '<li>正解の構成です(点線は補足的なつながり)。「すべて消す」で、もう一度組み立てられます。</li>';
    });

    box.querySelector(".ex-judge").addEventListener("click", function () {
      var need = {}, out = [], ok = true;
      graph.nodes.forEach(function (n) { need[n.label] = true; });
      var have = {};
      placed.forEach(function (n) {
        have[n.label] = true;
        n.rect.setAttribute("class", need[n.label] ? "dg-ok" : "dg-ng");
      });
      graph.nodes.forEach(function (n) {
        if (!have[n.label]) { ok = false; out.push(["ng", "「" + n.label + "」が足りません"]); }
      });
      placed.forEach(function (n) {
        if (!need[n.label]) { ok = false; out.push(["ng", "「" + n.label + "」はこの要件では使いません"]); }
      });
      var userLinks = {};
      links.forEach(function (l) { userLinks[l.a.label + "→" + l.b.label] = true; });
      var known = {};
      graph.edges.forEach(function (e) {
        var a = byId[e[0]].label, b = byId[e[1]].label;
        known[a + "→" + b] = true;
        if (e[2] || e[3]) known[b + "→" + a] = true;
        if (e[2]) return;  // 点線(補足的なつながり)は、なくてもよい
        if (userLinks[a + "→" + b] || (e[3] && userLinks[b + "→" + a])) return;
        ok = false;
        out.push(["ng", userLinks[b + "→" + a]
          ? "「" + a + "」と「" + b + "」の矢印の向きが逆です"
          : "「" + a + "」から「" + b + "」へのつながりが足りません"]);
      });
      links.forEach(function (l) {
        var k = l.a.label + "→" + l.b.label;
        if (known[k] || known[l.b.label + "→" + l.a.label]) return;
        if (!need[l.a.label] || !need[l.b.label]) return;  // 不要な部品のつながりは、部品の指摘だけにする
        ok = false;
        out.push(["ng", "「" + l.a.label + "」から「" + l.b.label + "」へのつながりは不要です"]);
      });
      if (ok) out.push(["ok", "正解です。部品もつながりも、要件を満たしています。"]);
      resultList.innerHTML = out.map(function (o) {
        return '<li class="' + o[0] + '"><span class="ex-mark ' + o[0] + '">' + (o[0] === "ok" ? "○" : "×") + "</span>" + o[1] + "</li>";
      }).join("");
      var prev = store(FREE_KEY + slug);
      store(FREE_KEY + slug, { ok: ok || !!(prev && prev.ok), date: today() });
    });
  }

  // ---- ページの準備 ----
  var items = document.querySelectorAll(".ex-item");
  document.documentElement.classList.add("ex-js");
  if (!items.length) { markIndex(); return; }
  var slug = slugOf(location.pathname);
  var section = items[0].closest("section");
  var fill = el("div", "ex-fill");
  var kids = Array.prototype.slice.call(section.children);
  for (var i = 0; i < kids.length; i++) if (kids[i].tagName !== "H2") fill.appendChild(kids[i]);
  section.appendChild(fill);
  setupFill(items, slug, fill);

  var graphEl = document.getElementById("ex-graph");
  if (!graphEl) return;
  var graph = JSON.parse(graphEl.textContent);
  var tabs = el("div", "ex-tabs",
    '<button type="button" class="ex-tab" aria-pressed="true">穴埋めで解く</button>'
    + '<button type="button" class="ex-tab" aria-pressed="false">自由に組み立てる</button>');
  var free = el("div", "ex-free");
  free.hidden = true;
  section.insertBefore(tabs, fill);
  section.appendChild(free);
  var built = false;
  var buttons = tabs.querySelectorAll(".ex-tab");
  for (var t = 0; t < 2; t++) {
    buttons[t].addEventListener("click", (function (t) {
      return function () {
        buttons[0].setAttribute("aria-pressed", t === 0);
        buttons[1].setAttribute("aria-pressed", t === 1);
        fill.hidden = t !== 0;
        free.hidden = t !== 1;
        if (t === 1 && !built) { setupFree(graph, slug, free); built = true; }
      };
    })(t));
  }
})();
