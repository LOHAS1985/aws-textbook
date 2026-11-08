// 参考書ページ(exams/{試験ID}/reference/)の本文を組み立てる(直接編集する)。
// 項目で参照しているページ(サービス・用語・運用シナリオ)の本文を読み込み、参考書の中で
// 見出し・リンク・図の id が重ならないように、取り込み元のページに合わせて直す。
// 読み込むのは同じサイトの HTML だけなので、Service Worker が保存していればオフラインでも動く。
(function () {
  var main = document.querySelector("main[data-incl]");
  if (!main || !window.fetch || !window.DOMParser) return;
  var included = (main.getAttribute("data-incl") || "").split(",").filter(Boolean);
  var boxes = main.querySelectorAll(".ref-body[data-src]");
  Array.prototype.forEach.call(boxes, load);

  function remove(el) {
    if (el.parentNode) el.parentNode.removeChild(el);
  }

  // 参考書に要らない部分(ページの見出し・目次・ページ送り・つながり・演習)を外す。冊子(print)と同じ範囲
  function trim(root) {
    Array.prototype.forEach.call(root.querySelectorAll(".page-head, nav, .to-top, script, style, noscript, .backlinks, .graph-chapter"), remove);
    Array.prototype.forEach.call(root.querySelectorAll(".ex-item"), function (el) {
      var sec = el.closest("section.chapter");
      remove(sec || el);
    });
  }

  // id を「元のページの slug-元のid」にして、参考書の中で重ならないようにする。参照している側も同じ名前にそろえる
  function renameIds(root, slug) {
    var map = {};
    Array.prototype.forEach.call(root.querySelectorAll("[id]"), function (el) {
      var id = el.getAttribute("id");
      map[id] = slug + "-" + id;
      el.setAttribute("id", map[id]);
    });
    return map;
  }

  // 元のページからの相対リンクを、参考書の中で正しく開けるように直す。
  // 項目の中にあるページへのリンクは、その節(#p-slug)へ移る。それ以外は元のページを開く
  function fixLinks(root, map, baseUrl) {
    var urlAttrs = ["href", "src", "xlink:href"];
    var refAttrs = ["fill", "stroke", "marker-start", "marker-mid", "marker-end", "clip-path", "mask", "filter", "style"];
    var idAttrs = ["aria-labelledby", "aria-describedby", "for"];
    Array.prototype.forEach.call(root.querySelectorAll("*"), function (el) {
      Array.prototype.forEach.call(Array.prototype.slice.call(el.attributes), function (a) {
        var name = a.name, value = a.value;
        if (urlAttrs.indexOf(name) >= 0) {
          if (value.charAt(0) === "#") {
            var local = value.slice(1);
            if (map[local]) el.setAttribute(name, "#" + map[local]);
            return;
          }
          var url = new URL(value, baseUrl);
          var m = url.pathname.match(/\/(services|terms|usecases)\/([\w-]+)\.html$/);
          if (m && !url.hash && included.indexOf(m[2]) >= 0) {
            el.setAttribute(name, "#p-" + m[2]);
          } else {
            el.setAttribute(name, url.href);
          }
        } else if (refAttrs.indexOf(name) >= 0) {
          el.setAttribute(name, value.replace(/url\(#([^)]+)\)/g, function (all, id) {
            return map[id] ? "url(#" + map[id] + ")" : all;
          }));
        } else if (idAttrs.indexOf(name) >= 0) {
          el.setAttribute(name, value.split(/\s+/).map(function (id) { return map[id] || id; }).join(" "));
        }
      });
    });
  }

  function load(box) {
    var slug = box.getAttribute("data-slug") || "";
    fetch(box.getAttribute("data-src")).then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.text().then(function (text) { return { text: text, url: res.url }; });
    }).then(function (r) {
      var doc = new DOMParser().parseFromString(r.text, "text/html");
      var src = doc.querySelector("main");
      if (!src) throw new Error("本文がありません");
      trim(src);
      var map = renameIds(src, slug);
      fixLinks(src, map, r.url);
      while (box.firstChild) box.removeChild(box.firstChild);  // noscript の案内を外してから本文を入れる
      Array.prototype.slice.call(src.childNodes).forEach(function (n) {
        box.appendChild(document.importNode(n, true));
      });
    }).catch(function () {
      // 読み込めなかったときは、元のページへのリンクを出す(noscript と同じ案内)
      while (box.firstChild) box.removeChild(box.firstChild);
      var p = document.createElement("p");
      p.className = "booklet-help";
      var a = document.createElement("a");
      a.href = box.getAttribute("data-src");
      a.textContent = "元のページ";
      p.appendChild(document.createTextNode("本文を読み込めませんでした。"));
      p.appendChild(a);
      p.appendChild(document.createTextNode("で読めます。"));
      box.appendChild(p);
    });
  }
})();
