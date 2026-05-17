//  Session stats (client-side) 
const session = { total: 0, correct: 0, scoreSum: 0 };

function updateStats() {
  document.getElementById('stat-total').textContent   = session.total;
  document.getElementById('stat-correct').textContent = session.correct;
  const avg = session.total > 0
    ? Math.round(session.scoreSum / session.total) + '%'
    : '—';
  document.getElementById('stat-score').textContent = avg;
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
let studyReveal = 'hide-def';

function setStudyOrder(order) {
  document.getElementById('study-order-hidden').value = order;
  document.getElementById('study-group-btn').classList.toggle('active', order === 'grouped');
  document.getElementById('study-mix-btn').classList.toggle('active',   order === 'mixed');
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

function revealAll() {
  document.querySelectorAll('#study-cards .study-field').forEach(el => el.classList.remove('blurred'));
}

function hideAll() {
  const sel = studyReveal === 'hide-def' ? '.study-def' : '.study-term';
  document.querySelectorAll(`#study-cards ${sel}`).forEach(el => el.classList.add('blurred'));
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
document.body.addEventListener('htmx:afterSettle', () => {
  const resultCard = document.getElementById('result-card');
  const hasResult  = resultCard?.classList.contains('show');

  if (hasResult && !resultCard.dataset.counted) {
    resultCard.dataset.counted = '1';
    if (!resultCard.dataset.aiRecheck) {
      const score     = parseInt(resultCard.dataset.score   || '0', 10);
      const isCorrect = resultCard.dataset.correct === '1';
      session.total++;
      if (isCorrect) session.correct++;
      session.scoreSum += score;
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
    } else {
      document.getElementById('answer-input')?.focus();
    }
  }
});
