(() => {
  // DOM elements
  const textLeft = document.getElementById('text-left');
  const textRight = document.getElementById('text-right');
  const fileLeft = document.getElementById('file-left');
  const fileRight = document.getElementById('file-right');
  const compareBtn = document.getElementById('compare-btn');
  const clearBtn = document.getElementById('clear-btn');
  const swapBtn = document.getElementById('swap-btn');
  const resultsSection = document.getElementById('results-section');
  const diffOutput = document.getElementById('diff-output');
  const diffStats = document.getElementById('diff-stats');
  const viewSide = document.getElementById('view-side');
  const viewInline = document.getElementById('view-inline');

  let currentView = 'side';
  let lastOps = null;

  // File upload handlers
  function readFile(file, textarea) {
    const reader = new FileReader();
    reader.onload = (e) => { textarea.value = e.target.result; };
    reader.readAsText(file);
  }

  fileLeft.addEventListener('change', (e) => {
    if (e.target.files[0]) readFile(e.target.files[0], textLeft);
  });

  fileRight.addEventListener('change', (e) => {
    if (e.target.files[0]) readFile(e.target.files[0], textRight);
  });

  // Swap
  swapBtn.addEventListener('click', () => {
    const tmp = textLeft.value;
    textLeft.value = textRight.value;
    textRight.value = tmp;
  });

  // Clear
  clearBtn.addEventListener('click', () => {
    textLeft.value = '';
    textRight.value = '';
    fileLeft.value = '';
    fileRight.value = '';
    resultsSection.hidden = true;
    diffStats.innerHTML = '';
    lastOps = null;
  });

  // View toggle
  viewSide.addEventListener('click', () => {
    currentView = 'side';
    viewSide.classList.add('active');
    viewInline.classList.remove('active');
    if (lastOps) render(lastOps);
  });

  viewInline.addEventListener('click', () => {
    currentView = 'inline';
    viewInline.classList.add('active');
    viewSide.classList.remove('active');
    if (lastOps) render(lastOps);
  });

  // Compare
  compareBtn.addEventListener('click', () => {
    const a = textLeft.value;
    const b = textRight.value;
    lastOps = Diff.diffLines(a, b);
    render(lastOps);
    resultsSection.hidden = false;
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  // Keyboard shortcut: Ctrl/Cmd+Enter to compare
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      compareBtn.click();
    }
  });

  /**
   * Escape HTML entities.
   */
  function esc(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  /**
   * Build word-level highlighted HTML for a changed line pair.
   */
  function highlightWords(lineA, lineB) {
    const wordOps = Diff.diffWords(lineA, lineB);

    let htmlA = '';
    let htmlB = '';

    for (const op of wordOps) {
      const escaped = esc(op.value);
      if (op.type === 'equal') {
        htmlA += escaped;
        htmlB += escaped;
      } else if (op.type === 'delete') {
        htmlA += `<span class="highlight-remove">${escaped}</span>`;
      } else {
        htmlB += `<span class="highlight-add">${escaped}</span>`;
      }
    }

    return { htmlA, htmlB };
  }

  /**
   * Group operations into aligned pairs for side-by-side display.
   * Pairs adjacent deletes with inserts for word-level diffing.
   */
  function buildPairs(ops) {
    const pairs = [];
    let i = 0;

    while (i < ops.length) {
      if (ops[i].type === 'equal') {
        pairs.push({ type: 'equal', value: ops[i].value });
        i++;
      } else if (ops[i].type === 'delete') {
        // Collect consecutive deletes
        const deletes = [];
        while (i < ops.length && ops[i].type === 'delete') {
          deletes.push(ops[i].value);
          i++;
        }
        // Collect consecutive inserts
        const inserts = [];
        while (i < ops.length && ops[i].type === 'insert') {
          inserts.push(ops[i].value);
          i++;
        }
        // Pair them up
        const maxLen = Math.max(deletes.length, inserts.length);
        for (let j = 0; j < maxLen; j++) {
          pairs.push({
            type: 'change',
            left: j < deletes.length ? deletes[j] : null,
            right: j < inserts.length ? inserts[j] : null,
          });
        }
      } else {
        // Insert without preceding delete
        pairs.push({ type: 'change', left: null, right: ops[i].value });
        i++;
      }
    }

    return pairs;
  }

  /**
   * Render the diff output.
   */
  function render(ops) {
    // Stats
    let added = 0;
    let removed = 0;
    for (const op of ops) {
      if (op.type === 'insert') added++;
      if (op.type === 'delete') removed++;
    }
    diffStats.innerHTML = `
      <span class="stat-added">+${added} added</span>
      <span class="stat-removed">−${removed} removed</span>
    `;

    // Check if identical
    if (added === 0 && removed === 0) {
      diffOutput.className = 'diff-output';
      diffOutput.innerHTML = `
        <div class="diff-identical">
          <div class="check">✓</div>
          <p>Files are identical</p>
        </div>`;
      return;
    }

    if (currentView === 'side') {
      renderSideBySide(ops);
    } else {
      renderInline(ops);
    }
  }

  function renderSideBySide(ops) {
    diffOutput.className = 'diff-output side-by-side';

    const pairs = buildPairs(ops);

    let leftNum = 0;
    let rightNum = 0;
    let leftHtml = '';
    let rightHtml = '';

    for (const pair of pairs) {
      if (pair.type === 'equal') {
        leftNum++;
        rightNum++;
        const escaped = esc(pair.value);
        leftHtml += diffLine('', leftNum, escaped);
        rightHtml += diffLine('', rightNum, escaped);
      } else {
        // Change pair
        const hasLeft = pair.left !== null;
        const hasRight = pair.right !== null;

        if (hasLeft && hasRight) {
          // Modified line — word-level highlight
          leftNum++;
          rightNum++;
          const { htmlA, htmlB } = highlightWords(pair.left, pair.right);
          leftHtml += diffLine('removed', leftNum, htmlA, true);
          rightHtml += diffLine('added', rightNum, htmlB, true);
        } else if (hasLeft) {
          leftNum++;
          leftHtml += diffLine('removed', leftNum, esc(pair.left));
          rightHtml += diffLine('empty-placeholder', '', '');
        } else {
          rightNum++;
          leftHtml += diffLine('empty-placeholder', '', '');
          rightHtml += diffLine('added', rightNum, esc(pair.right));
        }
      }
    }

    diffOutput.innerHTML = `
      <div class="diff-pane">
        <div class="diff-pane-header">Original</div>
        ${leftHtml}
      </div>
      <div class="diff-pane">
        <div class="diff-pane-header">Modified</div>
        ${rightHtml}
      </div>`;

    // Sync scrolling
    const panes = diffOutput.querySelectorAll('.diff-pane');
    if (panes.length === 2) {
      let syncing = false;
      panes[0].addEventListener('scroll', () => {
        if (syncing) return;
        syncing = true;
        panes[1].scrollTop = panes[0].scrollTop;
        panes[1].scrollLeft = panes[0].scrollLeft;
        syncing = false;
      });
      panes[1].addEventListener('scroll', () => {
        if (syncing) return;
        syncing = true;
        panes[0].scrollTop = panes[1].scrollTop;
        panes[0].scrollLeft = panes[1].scrollLeft;
        syncing = false;
      });
    }
  }

  function renderInline(ops) {
    diffOutput.className = 'diff-output inline-view';

    const pairs = buildPairs(ops);
    let leftNum = 0;
    let rightNum = 0;
    let html = '';

    for (const pair of pairs) {
      if (pair.type === 'equal') {
        leftNum++;
        rightNum++;
        html += inlineLine('', leftNum, rightNum, ' ', esc(pair.value));
      } else {
        const hasLeft = pair.left !== null;
        const hasRight = pair.right !== null;

        if (hasLeft && hasRight) {
          leftNum++;
          rightNum++;
          const { htmlA, htmlB } = highlightWords(pair.left, pair.right);
          html += inlineLine('removed', leftNum, '', '−', htmlA, true);
          html += inlineLine('added', '', rightNum, '+', htmlB, true);
        } else if (hasLeft) {
          leftNum++;
          html += inlineLine('removed', leftNum, '', '−', esc(pair.left));
        } else {
          rightNum++;
          html += inlineLine('added', '', rightNum, '+', esc(pair.right));
        }
      }
    }

    diffOutput.innerHTML = html;
  }

  function diffLine(cls, num, contentHtml, isRaw) {
    return `<div class="diff-line ${cls}">
      <span class="line-num">${num}</span>
      <span class="line-content">${contentHtml}</span>
    </div>`;
  }

  function inlineLine(cls, leftNum, rightNum, prefix, contentHtml, isRaw) {
    return `<div class="diff-line ${cls}">
      <span class="line-nums">
        <span class="line-num">${leftNum}</span>
        <span class="line-num">${rightNum}</span>
      </span>
      <span class="prefix">${esc(prefix)}</span>
      <span class="line-content">${contentHtml}</span>
    </div>`;
  }
})();
