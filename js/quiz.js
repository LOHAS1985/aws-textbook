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
  var setup = document.createElement("section");
  var lobbyHeading = document.createElement("div");
  var modeIntro = document.createElement("div");
  var modeButtons = document.createElement("div");
  var selection = document.createElement("div");
  var randomButton = document.createElement("button");
  var chooseButton = document.createElement("button");
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

  function modeCard(button, icon, eyebrow, title, description, badge) {
    button.className = "quiz-mode-card";
    button.setAttribute("aria-label", title + "。 " + description);
    button.innerHTML = '<span class="quiz-mode-icon" aria-hidden="true">' + icon + '</span>'
      + '<span class="quiz-mode-copy"><span class="quiz-mode-eyebrow">' + eyebrow + '</span>'
      + '<span class="quiz-mode-title">' + title + '</span>'
      + '<span class="quiz-mode-description">' + description + '</span></span>'
      + '<span class="quiz-mode-bottom"><span class="quiz-mode-badge">' + badge + '</span>'
      + '<span class="quiz-mode-arrow" aria-hidden="true">→</span></span>';
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

  function renderSelection() {
    var list = selection.querySelector(".quiz-selection-list");
    list.textContent = "";
    questions.slice().sort(function (left, right) {
      return Number(left.getAttribute("data-id")) - Number(right.getAttribute("data-id"));
    }).forEach(function (question) {
      var label = document.createElement("label");
      var checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = question.getAttribute("data-id");
      checkbox.checked = false;
      label.appendChild(checkbox);
      label.appendChild(document.createTextNode(" 問" + checkbox.value + " — "
        + question.getAttribute("data-title")));
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

  function start(selected) {
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
  setup.setAttribute("aria-label", "問題の選択");
  lobbyHeading.className = "quiz-lobby-heading";
  lobbyHeading.innerHTML = '<p class="quiz-lobby-eyebrow">DEA-C01 <span>QUESTION BANK</span></p>'
    + '<h2>どのスタイルで挑戦しますか？</h2>'
    + '<p>目的に合わせて出題方法を選べます。</p>';
  var setupMessage = document.createElement("p");
  setupMessage.className = "quiz-setup-message";
  setupMessage.setAttribute("role", "status");
  setupMessage.setAttribute("aria-live", "polite");
  selection.className = "quiz-selection";
  selection.hidden = true;
  selection.innerHTML = '<div class="quiz-selection-heading"><span class="quiz-selection-step">STEP 02</span>'
    + '<h2>出題する問題を選択</h2>'
    + '<p>復習したい問題にチェックを入れてください。</p></div>'
    + '<p class="quiz-selection-count" aria-live="polite"></p>'
    + '<div class="quiz-selection-actions"></div><div class="quiz-selection-list"></div>';
  var selectionCount = selection.querySelector(".quiz-selection-count");
  function updateSelectionCount() {
    selectionCount.textContent = selection.querySelectorAll(".quiz-selection-list input:checked").length
      + " 問選択中";
  }
  var selectionActions = selection.querySelector(".quiz-selection-actions");
  selectionActions.appendChild(makeButton("すべて選択", function () {
    selection.querySelectorAll(".quiz-selection-list input").forEach(function (input) { input.checked = true; });
    updateSelectionCount();
  }));
  selectionActions.appendChild(makeButton("すべて解除", function () {
    selection.querySelectorAll(".quiz-selection-list input").forEach(function (input) { input.checked = false; });
    updateSelectionCount();
  }));
  selectionActions.appendChild(makeButton("間違えた問題を選択", function () {
    var wrong = previous && Array.isArray(previous.wrong) ? previous.wrong : [];
    selection.querySelectorAll(".quiz-selection-list input").forEach(function (input) {
      input.checked = wrong.indexOf(input.value) !== -1;
    });
    updateSelectionCount();
  }));
  randomButton.type = "button";
  randomButton.textContent = "ランダム";
  randomButton.addEventListener("click", function () { start(shuffled(questions)); });
  chooseButton.type = "button";
  chooseButton.textContent = "問題を選ぶ";
  chooseButton.addEventListener("click", function () {
    randomButton.hidden = true;
    chooseButton.hidden = true;
    modeIntro.hidden = true;
    selection.hidden = false;
    selection.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  var startButton = makeButton("選んだ問題を始める", function () {
    var ids = Array.prototype.slice.call(selection.querySelectorAll(".quiz-selection-list input:checked"))
      .map(function (input) { return input.value; });
    var selected = questions.filter(function (question) {
      return ids.indexOf(question.getAttribute("data-id")) !== -1;
    }).sort(function (left, right) {
      return Number(left.getAttribute("data-id")) - Number(right.getAttribute("data-id"));
    });
    if (!selected.length) {
      setupMessage.textContent = "解く問題を1問以上選んでください。";
      return;
    }
    start(selected);
  });
  var backToModes = makeButton("戻る", function () {
    selection.hidden = true;
    modeIntro.hidden = false;
    randomButton.hidden = false;
    chooseButton.hidden = false;
    setupMessage.textContent = "";
  });
  var selectionFooter = document.createElement("div");
  selectionFooter.className = "quiz-selection-footer";
  selectionFooter.appendChild(backToModes);
  selectionFooter.appendChild(startButton);
  selection.appendChild(selectionFooter);
  selection.hidden = true;
  randomButton = modeCard(randomButton,
    '<svg viewBox="0 0 48 48" focusable="false"><path d="M8 14h6c11 0 11 20 22 20h4M32 29l8 5-8 5M8 34h6c5 0 7-5 10-10s5-10 10-10h6M32 9l8 5-8 5"/></svg>',
    "模擬試験", "ランダム", "全200問からランダムに出題。試験のようにまとめて挑戦できます。", "200 問");
  chooseButton = modeCard(chooseButton,
    '<svg viewBox="0 0 48 48" focusable="false"><path d="M20 10h19v30H9V10h5M18 7h12v7H18zM16 23l3 3 6-7M29 24h5M16 33l3 3 6-7M29 34h5"/></svg>',
    "弱点を復習", "問題を選ぶ", "解きたい問題だけを選択。間違えた問題の復習にも使えます。", "自由に選択");
  modeButtons.className = "quiz-mode-cards";
  modeButtons.appendChild(randomButton);
  modeButtons.appendChild(chooseButton);
  modeIntro.className = "quiz-lobby-content";
  modeIntro.appendChild(lobbyHeading);
  modeIntro.appendChild(modeButtons);
  setup.appendChild(modeIntro);
  setup.appendChild(selection);
  setup.appendChild(setupMessage);
  form.insertBefore(setup, form.firstChild);
  renderSelection();
  selection.querySelectorAll(".quiz-selection-list input").forEach(function (input) {
    input.addEventListener("change", updateSelectionCount);
  });
  updateSelectionCount();

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
    selection.hidden = true;
    modeIntro.hidden = false;
    randomButton.hidden = false;
    chooseButton.hidden = false;
    setupMessage.textContent = "";
  });
})();
