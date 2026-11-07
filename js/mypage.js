// マイページ(book/mypage.html の #my-root)に、しおり・学習メモの一覧と書き出し・読み込みを描画する(直接編集する)。
// site.js が #my-root のあるページでだけ読み込む。保存先は site.js と同じ localStorage のキー。
// 表示はすべて要素を作って textContent に入れる(保存された文字列を HTML として解釈しない)。
(function () {
  var root = document.getElementById("my-root");
  if (!root) return;
  var BM_KEY = "aws-textbook-bookmarks", NOTE_KEY = "aws-textbook-notes";
  var FORMAT = "aws-textbook-my";  // 書き出しファイルの印
  var MAX_TEXT = 20000;
  var status = null;

  function readJSON(key, fallback) {
    try { var v = JSON.parse(localStorage.getItem(key) || "null"); return v === null ? fallback : v; } catch (e) { return fallback; }
  }
  function writeJSON(key, v) {
    try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) {}
  }
  function changed() { window.dispatchEvent(new Event("aws-textbook-change")); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  // 保存先のパスとして安全なものだけ使う(links や javascript: を防ぐ)
  function safeUrl(u) { return typeof u === "string" && u.length < 300 && /^\/?[\w\/.~%\-]+\.html$/.test(u) ? u : null; }
  function validBookmark(b) { return !!(b && safeUrl(b.url)); }
  function bookmarks() {
    var v = readJSON(BM_KEY, []);
    return Array.isArray(v) ? v.filter(validBookmark) : [];
  }
  function notes() {
    var v = readJSON(NOTE_KEY, {});
    return v && typeof v === "object" && !Array.isArray(v) ? v : {};
  }
  // 表示できるメモだけ(URL が安全で、本文がある)
  function validNotes() {
    var all = notes(), out = {};
    Object.keys(all).forEach(function (k) {
      var n = all[k];
      if (safeUrl(k) && n && typeof n.text === "string" && n.text.trim()) out[k] = n;
    });
    return out;
  }
  function msg(text) { if (status) status.textContent = text; }

  function listHead(text, count) {
    var h = el("h2", "", text + "(" + count + ")");
    h.tabIndex = -1;
    return h;
  }

  // ---- しおり ----
  function bookmarkSection() {
    var list = bookmarks();
    var sec = el("section", "my-section");
    sec.appendChild(listHead("しおり", list.length));
    if (!list.length) {
      sec.appendChild(el("p", "my-empty", "しおりはまだありません。各ページの「☆ しおり」ボタンで追加できます。"));
      return sec;
    }
    var ul = el("ul", "my-list");
    list.forEach(function (b) {
      var li = el("li", "my-item");
      var title = typeof b.title === "string" && b.title ? b.title : b.url;
      var a = el("a", "my-title", title);
      a.href = b.url;
      li.appendChild(a);
      if (typeof b.lead === "string" && b.lead) li.appendChild(el("p", "my-lead", b.lead));
      var del = el("button", "my-del", "削除");
      del.type = "button";
      del.setAttribute("aria-label", title + "のしおりを削除");
      del.addEventListener("click", function () {
        writeJSON(BM_KEY, bookmarks().filter(function (x) { return x.url !== b.url; }));
        changed();
        render("しおりを削除しました");
      });
      li.appendChild(del);
      ul.appendChild(li);
    });
    sec.appendChild(ul);
    return sec;
  }

  // ---- 学習メモ ----
  function noteSection() {
    var all = validNotes();
    var keys = Object.keys(all).sort();
    var sec = el("section", "my-section");
    sec.appendChild(listHead("学習メモ", keys.length));
    if (!keys.length) {
      sec.appendChild(el("p", "my-empty", "メモはまだありません。各ページの「✎ メモ」ボタンで書けます。"));
      return sec;
    }
    var ul = el("ul", "my-list");
    keys.forEach(function (k) {
      var n = all[k];
      var title = typeof n.title === "string" && n.title ? n.title : k;
      var li = el("li", "my-item");
      var a = el("a", "my-title", title);
      a.href = k;
      li.appendChild(a);
      li.appendChild(el("p", "my-note-text", n.text.slice(0, MAX_TEXT)));
      var del = el("button", "my-del", "削除");
      del.type = "button";
      del.setAttribute("aria-label", title + "のメモを削除");
      del.addEventListener("click", function () {
        var rest = validNotes();
        delete rest[k];
        writeJSON(NOTE_KEY, rest);
        changed();
        render("メモを削除しました");
      });
      li.appendChild(del);
      ul.appendChild(li);
    });
    sec.appendChild(ul);
    return sec;
  }

  // ---- 書き出し・読み込み ----
  function dataSection() {
    var sec = el("section", "my-section");
    sec.appendChild(el("h2", "", "書き出し・読み込み"));
    sec.appendChild(el("p", "my-empty",
      "しおりとメモは、この端末のブラウザにだけ保存されています。機種変更や閲覧データの削除の前に書き出しておくと、読み込みで戻せます。"));

    var exp = el("button", "my-btn", "書き出す(JSON)");
    exp.type = "button";
    exp.addEventListener("click", function () {
      var data = {
        format: FORMAT,
        version: 1,
        exportedAt: new Date().toISOString(),
        bookmarks: bookmarks(),
        notes: validNotes()
      };
      var blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      var url = URL.createObjectURL(blob);
      var a = el("a");
      a.href = url;
      a.download = "aws-textbook-" + new Date().toISOString().slice(0, 10) + ".json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      msg("書き出しました");
    });
    sec.appendChild(exp);

    var label = el("label", "my-file-label", "読み込む(書き出したJSONを選ぶ)");
    label.setAttribute("for", "my-import");
    var input = el("input");
    input.type = "file";
    input.id = "my-import";
    input.accept = ".json,application/json";
    input.addEventListener("change", function () {
      var file = input.files && input.files[0];
      if (!file) return;
      if (file.size > 2000000) { msg("ファイルが大きすぎます(2MBまで)"); input.value = ""; return; }
      var reader = new FileReader();
      reader.onload = function () { importText(String(reader.result)); input.value = ""; };
      reader.onerror = function () { msg("ファイルを読めませんでした"); input.value = ""; };
      reader.readAsText(file);
    });
    sec.appendChild(label);
    sec.appendChild(input);
    return sec;
  }

  // 読み込みは、同じページのしおり・メモが既にあれば残す(上書きしない)
  function importText(text) {
    var data;
    try { data = JSON.parse(text); } catch (e) { msg("JSON として読めませんでした"); return; }
    if (!data || typeof data !== "object" || data.format !== FORMAT) {
      msg("このサイトで書き出したファイルではありません");
      return;
    }
    var added = 0, addedNotes = 0;
    var list = bookmarks();
    (Array.isArray(data.bookmarks) ? data.bookmarks : []).forEach(function (b) {
      if (!validBookmark(b) || list.some(function (x) { return x.url === b.url; })) return;
      list.push({
        url: b.url,
        title: typeof b.title === "string" ? b.title.slice(0, 200) : b.url,
        lead: typeof b.lead === "string" ? b.lead.slice(0, 300) : ""
      });
      added++;
    });
    var all = notes();
    var src = data.notes && typeof data.notes === "object" && !Array.isArray(data.notes) ? data.notes : {};
    Object.keys(src).forEach(function (k) {
      var n = src[k];
      if (!safeUrl(k) || all[k] || !n || typeof n.text !== "string" || !n.text.trim()) return;
      all[k] = {
        title: typeof n.title === "string" ? n.title.slice(0, 200) : k,
        text: n.text.slice(0, MAX_TEXT)
      };
      addedNotes++;
    });
    writeJSON(BM_KEY, list);
    writeJSON(NOTE_KEY, all);
    changed();
    render("しおり" + added + "件、メモ" + addedNotes + "件を読み込みました");
  }

  // 一覧を描き直す(削除や読み込みのあと)。見出しにフォーカスを戻す
  function render(message) {
    root.textContent = "";
    root.appendChild(el("p", "my-empty", "しおりとメモは、この端末のブラウザにだけ保存されています。"));
    status = el("p", "my-status");
    status.setAttribute("role", "status");
    root.appendChild(status);
    var bm = bookmarkSection();
    var nt = noteSection();
    root.appendChild(bm);
    root.appendChild(nt);
    root.appendChild(dataSection());
    if (message) {
      msg(message);
      var h = bm.querySelector("h2");
      if (h) h.focus();
    }
  }

  render();
  // 別のページや別のタブで保存内容が変わったら、一覧も合わせる
  addEventListener("storage", function (e) { if (e.key === BM_KEY || e.key === NOTE_KEY) render(); });
})();
