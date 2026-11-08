// トップの全ページ検索の精度を測る(ビルド済みの book/ を Node で動かす)。
// 使い方: node tools/search_eval.js [book のフォルダ]   (既定: book)
//         node tools/search_eval.js book --show "検索語"   (その検索語の上位5件と根拠を表示)
// tools/search-eval.json の検索語ごとに、正解のページが何位に出たかを表示する。
// 指標: 上位5件に入った割合(recall@5)と、順位の逆数の平均(MRR)。
const fs = require("fs");
const path = require("path");

const bookDir = path.resolve(process.argv[2] || "book");
const html = fs.readFileSync(path.join(bookDir, "index.html"), "utf8").replace(/\r\n/g, "\n");
const start = html.indexOf("<script>\n(function () {\n  var pages =");
const end = html.indexOf("</script>", start);
const code = html.slice(start + "<script>".length, end);
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "search-eval.json"), "utf8"));

// 本文の全文は search.json から読む(ブラウザで初回の入力時に読むのと同じ動き)
global.fetch = () => Promise.resolve({
  json: () => Promise.resolve(JSON.parse(fs.readFileSync(path.join(bookDir, "search.json"), "utf8"))),
});

const els = {};
function mk(id) {
  return els[id] || (els[id] = {
    id, value: "", innerHTML: "", hidden: true, textContent: "", listeners: {},
    addEventListener(t, f) { this.listeners[t] = f; }, querySelectorAll() { return []; },
    setAttribute() {}, focus() {},
  });
}
global.document = { getElementById: mk, addEventListener() {} };
global.location = { hash: "" };
eval(code);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const q = els["site-q"];
  const showAt = process.argv.indexOf("--show");
  if (showAt > 0) {
    q.value = process.argv[showAt + 1];
    q.listeners.input();
    await sleep(30);
    const items = els["site-results"].innerHTML.split("<li>").slice(1, 6);
    console.log(`${q.value}  (${els["site-hits"].textContent})`);
    for (const it of items) {
      const name = (it.match(/class="name">([^<]*)</) || [])[1];
      const why = (it.match(/class="why">根拠: ([^<]*)</) || [])[1] || "";
      console.log(" -", name, "\n     ", why.replace(/&quot;/g, '"').replace(/&amp;/g, "&"));
    }
    return;
  }
  let hit5 = 0, rr = 0;
  const fails = [];
  for (const c of cases) {
    q.value = c.q;
    q.listeners.input();
    await sleep(30);
    const urls = [...els["site-results"].innerHTML.matchAll(/<li><a href="([^"]+)"/g)].map((m) => m[1]);
    const rank = urls.indexOf(c.want) + 1;
    if (rank >= 1 && rank <= 5) hit5++;
    rr += rank ? 1 / rank : 0;
    if (!(rank >= 1 && rank <= 5)) fails.push(`${c.q} → ${c.want} (${rank ? rank + "位" : "候補になし"})`);
  }
  const n = cases.length;
  console.log(`recall@5 ${hit5}/${n} = ${(100 * hit5 / n).toFixed(1)}%   MRR ${(rr / n).toFixed(3)}`);
  for (const f of fails) console.log("  外れ:", f);
})();
