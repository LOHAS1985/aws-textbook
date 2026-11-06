(function () {
  var prefix = "aws-textbook-quiz:";
  var form = document.getElementById("quiz-form");
  var note = document.getElementById("quiz-storage-note");

  function key(slug) { return prefix + slug; }

  function readRecord(slug) {
    var value = localStorage.getItem(key(slug));
    if (!value) return null;
    var record = JSON.parse(value);
    if (!record || !Number.isInteger(record.best) || !Number.isInteger(record.total)
        || !Number.isInteger(record.attempts) || record.total < 1 || record.attempts < 1
        || record.best < 0 || record.best > record.total) {
      throw new Error("保存済みの成績データが正しくありません。");
    }
    return record;
  }

  function resultLabel(record) {
    return "最高得点 " + record.best + "/" + record.total + "問 (" + record.attempts + "回挑戦)";
  }

  function showBest(slug, target) {
    try {
      var record = readRecord(slug);
      if (record) {
        target.textContent = resultLabel(record);
        target.hidden = false;
      }
      return record;
    } catch (error) {
      target.textContent = "保存済みの成績を読み込めませんでした: " + error.message;
      target.hidden = false;
      return null;
    }
  }

  function showIndexResults() {
    var links = document.querySelectorAll(".toc-category a[href$='.html']");
    var failed = false;
    links.forEach(function (link) {
      var path = link.getAttribute("href");
      var slug = path.slice(path.lastIndexOf("/") + 1, -5);
      try {
        var record = readRecord(slug);
        if (!record) return;
        var badge = document.createElement("span");
        badge.className = "quiz-index-badge";
        badge.textContent = resultLabel(record);
        var name = link.querySelector(".name");
        (name || link).appendChild(badge);
      } catch (error) {
        failed = true;
      }
    });
    if (failed && note) {
      note.textContent = "保存済みの成績を読み込めませんでした。問題集の採点結果はこのブラウザーに保存されます。";
      note.hidden = false;
    }
  }

  if (!form) {
    showIndexResults();
    return;
  }

  var slug = form.getAttribute("data-quiz");
  var questions = Array.prototype.slice.call(form.querySelectorAll(".quiz-q"));
  var submit = document.getElementById("quiz-submit");
  var reset = document.getElementById("quiz-reset");
  var output = document.getElementById("quiz-result");
  var best = document.getElementById("quiz-best");
  var previous = showBest(slug, best);
  form.classList.add("quiz-js");
  submit.hidden = false;
  reset.hidden = false;

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var score = 0;
    questions.forEach(function (question) {
      var expected = question.getAttribute("data-answer").split(",").sort();
      var selected = Array.prototype.slice.call(question.querySelectorAll("input:checked"))
        .map(function (input) { return input.value; }).sort();
      var correct = expected.length === selected.length
        && expected.every(function (answer, index) { return answer === selected[index]; });
      if (correct) score++;
      question.querySelectorAll(".quiz-choices li").forEach(function (choice) {
        var input = choice.querySelector("input");
        choice.classList.remove("quiz-choice-correct", "quiz-choice-wrong");
        if (expected.indexOf(input.value) !== -1) choice.classList.add("quiz-choice-correct");
        else if (input.checked) choice.classList.add("quiz-choice-wrong");
      });
      question.querySelector(".quiz-answer").open = true;
    });

    output.textContent = score + " / " + questions.length + "問正解です。";
    try {
      var attempts = previous ? previous.attempts + 1 : 1;
      var record = {
        best: previous ? Math.max(previous.best, score) : score,
        total: questions.length,
        attempts: attempts
      };
      localStorage.setItem(key(slug), JSON.stringify(record));
      previous = record;
      best.textContent = resultLabel(record);
      best.hidden = false;
    } catch (error) {
      output.textContent += " 成績を保存できませんでした: " + error.message;
    }
    document.getElementById("c3").scrollIntoView({ behavior: "smooth", block: "start" });
  });

  form.addEventListener("reset", function () {
    window.setTimeout(function () {
      questions.forEach(function (question) {
        question.querySelectorAll(".quiz-choices li").forEach(function (choice) {
          choice.classList.remove("quiz-choice-correct", "quiz-choice-wrong");
        });
        question.querySelector(".quiz-answer").open = false;
      });
      output.textContent = "採点後に結果が表示されます。";
    }, 0);
  });
})();
