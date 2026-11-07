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
        || record.best < 0 || record.best > record.total
        || (record.wrong !== undefined && !Array.isArray(record.wrong))) {
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
  var output = document.getElementById("quiz-result");
  var best = document.getElementById("quiz-best");
  var finishPanel = document.getElementById("quiz-finish");
  var returnButton = document.getElementById("quiz-return");
  var previous = showBest(slug, best);
  var activeQuestions = [];
  var currentIndex = 0;
  var mode = "random";
  var setup = document.createElement("section");
  var selection = document.createElement("div");
  var progress = document.createElement("p");
  var navigation = document.createElement("div");
  var back = document.createElement("button");
  var next = document.createElement("button");

  function makeButton(text, handler) {
    var button = document.createElement("button");
    button.type = "button";
    button.textContent = text;
    button.addEventListener("click", handler);
    return button;
  }

  function shuffled(items) {
    var result = items.slice();
    for (var i = result.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var temporary = result[i];
      result[i] = result[j];
      result[j] = temporary;
    }
    return result;
  }

  function setMode(value) {
    mode = value;
    selection.hidden = mode !== "choose";
    startButton.textContent = mode === "random" ? "ランダムに始める" : "選んだ問題を始める";
    setup.querySelectorAll("[name='quiz-mode']").forEach(function (radio) {
      radio.checked = radio.value === mode;
    });
  }

  function renderSelection() {
    var list = selection.querySelector(".quiz-selection-list");
    list.textContent = "";
    questions.forEach(function (question) {
      var label = document.createElement("label");
      var checkbox = document.createElement("input");
      var stem = question.querySelector(".quiz-stem").textContent;
      checkbox.type = "checkbox";
      checkbox.value = question.getAttribute("data-id");
      checkbox.checked = false;
      label.appendChild(checkbox);
      label.appendChild(document.createTextNode(
        " 問" + checkbox.value + " — " + (stem.length > 72 ? stem.slice(0, 72) + "…" : stem)
      ));
      list.appendChild(label);
    });
  }

  function showQuestion() {
    questions.forEach(function (question) { question.hidden = true; });
    var question = activeQuestions[currentIndex];
    if (question) question.hidden = false;
    progress.textContent = question
      ? "問題 " + (currentIndex + 1) + " / " + activeQuestions.length
      : "";
    back.hidden = currentIndex === 0;
    next.textContent = currentIndex === activeQuestions.length - 1 ? "結果を見る" : "次の問題";
  }

  function start() {
    var selected;
    if (mode === "random") {
      selected = shuffled(questions);
    } else {
      var ids = Array.prototype.slice.call(selection.querySelectorAll("input:checked"))
        .map(function (input) { return input.value; });
      selected = questions.filter(function (question) {
        return ids.indexOf(question.getAttribute("data-id")) !== -1;
      });
      if (!selected.length) {
        setupMessage.textContent = "解く問題を1問以上選んでください。";
        return;
      }
    }
    setupMessage.textContent = "";
    questions.forEach(function (question) {
      question.querySelectorAll("input").forEach(function (input) { input.checked = false; });
      question.querySelectorAll(".quiz-choices li").forEach(function (choice) {
        choice.classList.remove("quiz-choice-correct", "quiz-choice-wrong");
      });
      question.querySelector(".quiz-answer").open = false;
    });
    activeQuestions = selected;
    currentIndex = 0;
    setup.hidden = true;
    progress.hidden = false;
    navigation.hidden = false;
    finishPanel.hidden = true;
    showQuestion();
    document.querySelector(".quiz-page").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  setup.className = "quiz-setup";
  setup.innerHTML = '<h4>出題方法</h4>'
    + '<label><input type="radio" name="quiz-mode" value="random" checked> 全100問をランダムに解く</label>'
    + '<label><input type="radio" name="quiz-mode" value="choose"> 問題を選んで解く</label>';
  var setupMessage = document.createElement("p");
  setupMessage.className = "quiz-setup-message";
  setupMessage.setAttribute("role", "status");
  setupMessage.setAttribute("aria-live", "polite");
  selection.className = "quiz-selection";
  selection.hidden = true;
  selection.innerHTML = '<p>解く問題を選んでください。間違えた問題は保存され、ここからまとめて選べます。</p>'
    + '<div class="quiz-selection-actions"></div><div class="quiz-selection-list"></div>';
  var selectionActions = selection.querySelector(".quiz-selection-actions");
  selectionActions.appendChild(makeButton("すべて選択", function () {
    selection.querySelectorAll(".quiz-selection-list input").forEach(function (input) { input.checked = true; });
  }));
  selectionActions.appendChild(makeButton("すべて解除", function () {
    selection.querySelectorAll(".quiz-selection-list input").forEach(function (input) { input.checked = false; });
  }));
  selectionActions.appendChild(makeButton("間違えた問題を選択", function () {
    var wrong = previous && Array.isArray(previous.wrong) ? previous.wrong : [];
    selection.querySelectorAll(".quiz-selection-list input").forEach(function (input) {
      input.checked = wrong.indexOf(input.value) !== -1;
    });
  }));
  var startButton = makeButton("ランダムに始める", start);
  setup.appendChild(selection);
  setup.appendChild(setupMessage);
  setup.appendChild(startButton);
  form.insertBefore(setup, form.firstChild);
  renderSelection();
  setup.querySelectorAll("[name='quiz-mode']").forEach(function (radio) {
    radio.addEventListener("change", function () { setMode(radio.value); });
  });

  progress.className = "quiz-progress";
  progress.hidden = true;
  navigation.className = "quiz-navigation";
  navigation.hidden = true;
  back.type = "button";
  back.textContent = "前の問題";
  back.addEventListener("click", function () {
    if (currentIndex > 0) {
      currentIndex--;
      showQuestion();
    }
  });
  next.type = "button";
  next.addEventListener("click", function () {
    if (currentIndex < activeQuestions.length - 1) {
      currentIndex++;
      showQuestion();
    } else {
      finishStudy();
    }
  });
  navigation.appendChild(back);
  navigation.appendChild(next);
  navigation.appendChild(makeButton("勉強を終了する", finishStudy));
  form.insertBefore(progress, setup.nextSibling);
  form.querySelector(".quiz-actions").appendChild(navigation);
  form.classList.add("quiz-js");
  questions.forEach(function (question, index) {
    if (!question.hasAttribute("data-id")) question.setAttribute("data-id", String(index + 1));
    question.hidden = true;
  });

  function finishStudy() {
    if (!activeQuestions.length) return;
    var score = 0;
    var unanswered = 0;
    var wrongThisRun = 0;
    var wrong = new Set(previous && Array.isArray(previous.wrong) ? previous.wrong : []);
    activeQuestions.forEach(function (question) {
      var id = question.getAttribute("data-id");
      var expected = question.getAttribute("data-answer").split(",").sort();
      var selected = Array.prototype.slice.call(question.querySelectorAll("input:checked"))
        .map(function (input) { return input.value; }).sort();
      if (!selected.length) unanswered++;
      var correct = expected.length === selected.length
        && expected.every(function (answer, index) { return answer === selected[index]; });
      if (correct) {
        score++;
        wrong.delete(id);
      } else {
        wrong.add(id);
        wrongThisRun++;
      }
      question.querySelectorAll(".quiz-choices li").forEach(function (choice) {
        var input = choice.querySelector("input");
        choice.classList.remove("quiz-choice-correct", "quiz-choice-wrong");
        if (expected.indexOf(input.value) !== -1) choice.classList.add("quiz-choice-correct");
        else if (input.checked) choice.classList.add("quiz-choice-wrong");
      });
      question.querySelector(".quiz-answer").open = true;
      question.hidden = false;
    });
    progress.hidden = true;
    navigation.hidden = true;
    output.textContent = score + " / " + activeQuestions.length + "問正解です。不正解・未回答: "
      + wrongThisRun + "問 (未回答 " + unanswered + "問)。";
    try {
      var attempts = previous ? previous.attempts + 1 : 1;
      var better = !previous || score * previous.total > previous.best * activeQuestions.length;
      var record = {
        best: better ? score : previous.best,
        total: better ? activeQuestions.length : previous.total,
        attempts: attempts,
        wrong: Array.from(wrong)
      };
      localStorage.setItem(key(slug), JSON.stringify(record));
      previous = record;
      best.textContent = resultLabel(record);
      best.hidden = false;
      renderSelection();
    } catch (error) {
      output.textContent += " 成績を保存できませんでした: " + error.message;
    }
    setup.hidden = true;
    finishPanel.hidden = false;
    finishPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    finishStudy();
  });

  returnButton.addEventListener("click", function () {
    questions.forEach(function (question) {
      question.hidden = true;
      question.querySelectorAll("input").forEach(function (input) { input.checked = false; });
      question.querySelectorAll(".quiz-choices li").forEach(function (choice) {
        choice.classList.remove("quiz-choice-correct", "quiz-choice-wrong");
      });
      question.querySelector(".quiz-answer").open = false;
    });
    activeQuestions = [];
    setup.hidden = false;
    finishPanel.hidden = true;
    progress.hidden = true;
    navigation.hidden = true;
    setupMessage.textContent = "";
  });
})();
