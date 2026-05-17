//  Theme
function toggleTheme() {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  localStorage.setItem('theme', next);
}

//  Timer state
let timerMax      = parseInt(localStorage.getItem('timerMax') ?? '30', 10);
let timerInterval = null;
let timerStart    = null;

//  Session stats (client-side)
const session     = { total: 0, correct: 0, scoreSum: 0 };
const sessionTerms = new Set();

function updateStats() {
  document.getElementById('stat-total').textContent   = session.total;
  document.getElementById('stat-correct').textContent = session.correct;
  const avg = session.total > 0
    ? Math.round(session.scoreSum / session.total) + '%'
    : '—';
  document.getElementById('stat-score').textContent = avg;
}

function updateCoverage() {
  const qWrap    = document.getElementById('question-wrap');
  const poolSize = parseInt(qWrap?.dataset.poolSize || '0', 10);
  const el = document.getElementById('stat-coverage');
  if (!el) return;
  el.textContent = poolSize > 0 ? `${sessionTerms.size} / ${poolSize}` : '— / —';
}

//  Section switching 
function switchSection(section) {
  const isPractice = section === 'practice';
  document.getElementById('practice-section').style.display = isPractice ? '' : 'none';
  document.getElementById('study-section').style.display    = isPractice ? 'none' : '';
  document.getElementById('tab-practice').classList.toggle('active',  isPractice);
  document.getElementById('tab-study').classList.toggle('active', !isPractice);

  if (!isPractice) {
    reloadSection('study', document.getElementById('study-unit-hidden').value);
  }
}

//  Practice controls 
function setMode(mode) {
  document.getElementById('mode-hidden').value = mode;
  document.querySelectorAll('#mode-group .pill').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });
  document.getElementById('ollama-note').style.display =
    mode === 'term_to_def' ? 'block' : 'none';
}

//  Study controls 
let studyReveal     = 'hide-def';
let studyView       = 'grid';
let studySingleIndex = 0;

function setStudyOrder(order) {
  document.getElementById('study-order-hidden').value = order;
  document.getElementById('study-group-btn').classList.toggle('active',   order === 'grouped');
  document.getElementById('study-mix-btn').classList.toggle('active',    order === 'mixed');
  document.getElementById('study-shuffle-btn').classList.toggle('active', order === 'shuffle');
  reloadSection('study', document.getElementById('study-unit-hidden').value);
}

//  Unit multi-select 
function toggleUnit(section, unitNum, btn) {
  const hidden  = document.getElementById(section === 'practice' ? 'unit-hidden' : 'study-unit-hidden');
  const pillsId = section === 'practice' ? 'practice-unit-pills' : 'study-unit-pills';
  let current = hidden.value ? hidden.value.split(',').map(Number) : [];
  const idx = current.indexOf(unitNum);
  if (idx >= 0) current.splice(idx, 1);
  else current.push(unitNum);
  current.sort((a, b) => a - b);
  hidden.value = current.join(',');
  btn.classList.toggle('active', current.includes(unitNum));
  document.querySelector(`#${pillsId} [data-all]`).classList.toggle('active', current.length === 0);
  reloadSection(section, hidden.value);
}

function setAllUnits(section, btn) {
  const hidden  = document.getElementById(section === 'practice' ? 'unit-hidden' : 'study-unit-hidden');
  const pillsId = section === 'practice' ? 'practice-unit-pills' : 'study-unit-pills';
  hidden.value = '';
  document.querySelectorAll(`#${pillsId} .pill`).forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  reloadSection(section, '');
}

function reloadSection(section, unitValue) {
  if (section === 'practice') {
    const mode = document.getElementById('mode-hidden').value;
    htmx.ajax('GET', '/question', {
      target: '#question-wrap',
      swap: 'outerHTML',
      values: { mode, unit: unitValue },
    });
  } else {
    const order = document.getElementById('study-order-hidden').value;
    htmx.ajax('GET', '/study/cards', {
      target: '#study-cards',
      swap: 'innerHTML',
      values: { unit: unitValue, order },
    }).then(() => {
      document.querySelectorAll('#study-cards .study-def')
        .forEach(el => el.classList.toggle('blurred', studyReveal === 'hide-def'));
      document.querySelectorAll('#study-cards .study-term')
        .forEach(el => el.classList.toggle('blurred', studyReveal === 'hide-term'));
      studySingleIndex = 0;
      applyStudyView();
    });
  }
}

function setStudyReveal(mode) {
  studyReveal = mode;
  document.getElementById('study-hide-def-btn').classList.toggle('active',  mode === 'hide-def');
  document.getElementById('study-hide-term-btn').classList.toggle('active', mode === 'hide-term');
  document.querySelectorAll('#study-cards .study-term')
    .forEach(el => el.classList.toggle('blurred', mode === 'hide-term'));
  document.querySelectorAll('#study-cards .study-def')
    .forEach(el => el.classList.toggle('blurred', mode === 'hide-def'));
}

function setStudyView(view) {
  studyView = view;
  document.getElementById('study-grid-btn').classList.toggle('active', view === 'grid');
  document.getElementById('study-single-btn').classList.toggle('active', view === 'single');
  studySingleIndex = 0;
  applyStudyView();
}

function applyStudyView() {
  const cards = Array.from(document.querySelectorAll('#study-cards .study-card'));
  const nav   = document.getElementById('study-single-nav');
  if (!nav) return;
  if (studyView === 'single' && cards.length > 0) {
    if (studySingleIndex >= cards.length) studySingleIndex = cards.length - 1;
    cards.forEach((c, i) => { c.style.display = i === studySingleIndex ? '' : 'none'; });
    nav.style.display = '';
    document.getElementById('study-nav-index').textContent =
      `${studySingleIndex + 1} / ${cards.length}`;
    document.getElementById('study-nav-prev').disabled = studySingleIndex === 0;
    document.getElementById('study-nav-next').disabled = studySingleIndex >= cards.length - 1;
  } else {
    cards.forEach(c => { c.style.display = ''; });
    nav.style.display = 'none';
  }
}

function studyNavStep(delta) {
  const cards = document.querySelectorAll('#study-cards .study-card');
  studySingleIndex = Math.max(0, Math.min(studySingleIndex + delta, cards.length - 1));
  applyStudyView();
}

function revealAll() {
  document.querySelectorAll('#study-cards .study-field').forEach(el => el.classList.remove('blurred'));
}

function hideAll() {
  const sel = studyReveal === 'hide-def' ? '.study-def' : '.study-term';
  document.querySelectorAll(`#study-cards ${sel}`).forEach(el => el.classList.add('blurred'));
}

//  Timer
function startTimer() {
  const display = document.getElementById('timer-display');
  if (!display) return;
  stopTimer();
  timerStart = Date.now();
  if (timerMax <= 0) {
    display.textContent = '∞';
    display.className = 'timer-display timer-disabled';
    timerStart = null;
    return;
  }
  let remaining = timerMax;
  display.textContent = remaining;
  display.className = 'timer-display';
  timerInterval = setInterval(() => {
    remaining--;
    display.textContent = remaining;
    if (remaining / timerMax <= 0.3) display.classList.add('timer-urgent');
    if (remaining <= 0) { stopTimer(); expireQuestion(); }
  }, 1000);
}

function stopTimer() {
  clearInterval(timerInterval);
  timerInterval = null;
}

function getTimeTaken() {
  return timerStart ? Math.round((Date.now() - timerStart) / 1000) : 0;
}

function expireQuestion() {
  const expiredInput   = document.getElementById('expired-flag');
  const timeTakenInput = document.getElementById('time-taken-input');
  if (!expiredInput) return;
  expiredInput.value   = '1';
  if (timeTakenInput) timeTakenInput.value = timerMax;
  timerStart = null;
  document.getElementById('grade-form')?.requestSubmit();
}

function setTimerMax(val, btn) {
  timerMax = val;
  localStorage.setItem('timerMax', val);
  document.querySelectorAll('#timer-group .pill').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (!document.getElementById('result-card')?.classList.contains('show')) startTimer();
}

function resetProgress() {
  if (!confirm('Reset all progress? This cannot be undone.')) return;
  fetch('/api/reset', { method: 'POST' })
    .then(() => {
      session.total = 0; session.correct = 0; session.scoreSum = 0;
      updateStats();
    });
}

//  Keyboard shortcuts 
document.addEventListener('keydown', e => {
  if (document.activeElement?.id !== 'answer-input') return;

  const mode = document.getElementById('question-wrap')?.dataset.mode;
  const form = document.getElementById('grade-form');
  if (!form) return;

  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    form.requestSubmit();
  } else if (e.key === 'Enter' && !e.shiftKey && mode === 'def_to_term') {
    e.preventDefault();
    form.requestSubmit();
  }
}, true);

//  htmx lifecycle
document.body.addEventListener('htmx:beforeRequest', (e) => {
  if (e.detail.elt?.id === 'grade-form') {
    const expiredInput   = document.getElementById('expired-flag');
    const timeTakenInput = document.getElementById('time-taken-input');
    if (timeTakenInput && expiredInput?.value !== '1') {
      timeTakenInput.value = getTimeTaken();
    }
    stopTimer();
    timerStart = null;
  }
});

document.body.addEventListener('htmx:afterSettle', () => {
  const resultCard = document.getElementById('result-card');
  const hasResult  = resultCard?.classList.contains('show');

  if (hasResult && !resultCard.dataset.counted) {
    resultCard.dataset.counted = '1';
    stopTimer();
    if (!resultCard.dataset.aiRecheck) {
      const score     = parseInt(resultCard.dataset.score   || '0', 10);
      const isCorrect = resultCard.dataset.correct === '1';
      session.total++;
      if (isCorrect) session.correct++;
      session.scoreSum += score;
      updateStats();
      // Track unique terms seen
      const qWrap = document.getElementById('question-wrap');
      const term  = qWrap?.dataset.term;
      if (term) sessionTerms.add(term + '|' + (qWrap.dataset.mode || ''));
      updateCoverage();
    } else if (resultCard.dataset.correct === '1') {
      // AI recheck upgraded the answer — patch stats with the score delta
      const score     = parseInt(resultCard.dataset.score     || '0', 10);
      const prevScore = parseInt(resultCard.dataset.prevScore || '0', 10);
      session.correct++;
      session.scoreSum += score - prevScore;
      updateStats();
    }
    // Animate score bar (starts at 0 via CSS, trigger transition after paint)
    const bar = resultCard.querySelector('.score-bar');
    if (bar) {
      const target = bar.dataset.width;
      requestAnimationFrame(() => requestAnimationFrame(() => { bar.style.width = target; }));
    }
    document.getElementById('next-btn')?.focus();
  } else if (!hasResult) {
    // Apply study reveal mode to freshly loaded study cards
    if (document.getElementById('study-section')?.style.display !== 'none') {
      document.querySelectorAll('#study-cards .study-def')
        .forEach(el => el.classList.toggle('blurred', studyReveal === 'hide-def'));
      document.querySelectorAll('#study-cards .study-term')
        .forEach(el => el.classList.toggle('blurred', studyReveal === 'hide-term'));
      studySingleIndex = 0;
      applyStudyView();
    } else {
      startTimer();
      updateCoverage();
      document.getElementById('answer-input')?.focus();
    }
  }
});

//  Arrow key navigation in single-card study view
document.addEventListener('keydown', e => {
  if (studyView !== 'single') return;
  if (document.getElementById('study-section')?.style.display === 'none') return;
  if (e.key === 'ArrowLeft')  { e.preventDefault(); studyNavStep(-1); }
  if (e.key === 'ArrowRight') { e.preventDefault(); studyNavStep(1); }
  if (e.key === ' ') {
    e.preventDefault();
    const cards = document.querySelectorAll('#study-cards .study-card');
    const card  = cards[studySingleIndex];
    if (!card) return;
    const sel = studyReveal === 'hide-def' ? '.study-def' : '.study-term';
    card.querySelector(sel)?.classList.toggle('blurred');
  }
});

//  Initialization
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('#timer-group .pill').forEach(btn => {
    btn.classList.toggle('active', parseInt(btn.dataset.timer) === timerMax);
  });
  if (!document.getElementById('result-card')?.classList.contains('show')) {
    startTimer();
  }
  updateCoverage();
});
