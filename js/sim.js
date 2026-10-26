// 構成演習の答え合わせ(build.py が構成演習のページと目次で読み込む。直接編集する)
// 本文の書き方:
//   <div class="ex-item" data-node="図のノードID(省略可)">
//     <p class="ex-q">問い</p>
//     <ul class="ex-choices">
//       <li data-ok data-short="図に出す短い名前">正解の選択肢<span class="ex-why">解説</span></li>
//       <li data-short="…">不正解の選択肢<span class="ex-why">解説</span></li>
//     </ul>
//   </div>
// 選択肢は表示のたびに並べ替える。結果は閲覧者のブラウザ(localStorage)にだけ保存する。
(function () {
  var KEY = "aws-textbook-ex:";

  function store(slug, value) {
    try {
      if (value === undefined) return JSON.parse(localStorage.getItem(KEY + slug) || "null");
      localStorage.setItem(KEY + slug, JSON.stringify(value));
    } catch (e) { return null; }
  }

  function slugOf(path) {
    var m = /([^\/]+)\.html$/.exec(path);
    return m ? m[1] : "";
  }

  // 目次:解いたことのある演習に結果を表示する
  function markIndex() {
    var links = document.querySelectorAll(".toc-category li a");
    for (var i = 0; i < links.length; i++) {
      var r = store(slugOf(links[i].getAttribute("href")));
      if (!r) continue;
      var badge = document.createElement("span");
      badge.className = "ex-badge" + (r.score === r.total ? " ex-badge-ok" : "");
      badge.textContent = r.score === r.total ? "全問正解" : r.score + "/" + r.total + "問正解";
      links[i].querySelector(".name").appendChild(badge);
    }
  }

  function shuffle(list) {
    for (var i = list.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = list[i]; list[i] = list[j]; list[j] = t;
    }
    return list;
  }

  function nodeOf(item) {
    var id = item.getAttribute("data-node");
    return id ? document.querySelector('svg g[data-node="' + id + '"]') : null;
  }

  function setNode(item, text, cls) {
    var g = nodeOf(item);
    if (!g) return;
    var label = g.querySelector("text");
    if (!label.hasAttribute("data-blank")) label.setAttribute("data-blank", label.textContent);
    label.textContent = text === null ? label.getAttribute("data-blank") : text;
    g.querySelector("rect").setAttribute("class", cls);
  }

  function setup(items) {
    var slug = slugOf(location.pathname);
    for (var i = 0; i < items.length; i++) {
      var ul = items[i].querySelector(".ex-choices");
      var lis = shuffle(Array.prototype.slice.call(ul.children));
      for (var j = 0; j < lis.length; j++) {
        var li = lis[j];
        ul.appendChild(li);
        var label = document.createElement("label");
        var input = document.createElement("input");
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
            var short = li.getAttribute("data-short") || li.querySelector("label").textContent;
            setNode(item, short, "dg-blank dg-filled");
          };
        })(items[i], li));
      }
    }

    var bar = document.createElement("div");
    bar.className = "ex-actions";
    bar.innerHTML = '<button type="button" class="ex-check">答え合わせ</button>'
      + '<button type="button" class="ex-reset" hidden>もう一度解く</button>'
      + '<p class="ex-result" role="status"></p>';
    items[items.length - 1].parentNode.insertBefore(bar, items[items.length - 1].nextSibling);
    var result = bar.querySelector(".ex-result");
    var prev = store(slug);
    if (prev) result.textContent = "前回の結果:" + prev.total + "問中" + prev.score + "問正解(" + prev.date + ")";

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
        if (chosenLi) chosenLi.classList.add("ex-chosen");
        var inputs = item.querySelectorAll("input");
        for (var k = 0; k < inputs.length; k++) inputs[k].disabled = true;
        setNode(item, answer.getAttribute("data-short") || answer.querySelector("label").textContent,
          ok ? "dg-ok" : "dg-ng");
      }
      var d = new Date();
      store(slug, { score: score, total: items.length,
        date: d.getFullYear() + "-" + (d.getMonth() + 1) + "-" + d.getDate() });
      result.textContent = items.length + "問中" + score + "問正解"
        + (score === items.length ? "。すべて正解です。解説で、ほかの選択肢が選ばれない理由も確かめましょう。"
          : "。色の付いた解説を読んで、正しい選択肢との違いを確かめましょう。");
      this.hidden = true;
      bar.querySelector(".ex-reset").hidden = false;
    });

    bar.querySelector(".ex-reset").addEventListener("click", function () {
      for (var i = 0; i < items.length; i++) {
        var item = items[i];
        item.classList.remove("is-ok", "is-ng");
        var lis = item.querySelectorAll("li");
        for (var k = 0; k < lis.length; k++) lis[k].classList.remove("ex-answer", "ex-chosen");
        var inputs = item.querySelectorAll("input");
        for (k = 0; k < inputs.length; k++) { inputs[k].disabled = false; inputs[k].checked = false; }
        setNode(item, null, "dg-blank");
      }
      result.textContent = "";
      this.hidden = true;
      bar.querySelector(".ex-check").hidden = false;
      items[0].scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }

  var items = document.querySelectorAll(".ex-item");
  document.documentElement.classList.add("ex-js");
  if (items.length) setup(items); else markIndex();
})();
