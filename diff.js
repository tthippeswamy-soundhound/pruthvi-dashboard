/**
 * Myers diff algorithm implementation for line-level and word-level diffing.
 */

const Diff = (() => {
  /**
   * Compute the longest common subsequence edit script using Myers' algorithm.
   * Returns an array of operations: { type: 'equal'|'insert'|'delete', value }
   */
  function myers(a, b) {
    const n = a.length;
    const m = b.length;
    const max = n + m;

    // Optimization: if one side is empty
    if (n === 0) return b.map(v => ({ type: 'insert', value: v }));
    if (m === 0) return a.map(v => ({ type: 'delete', value: v }));

    const vSize = 2 * max + 1;
    const v = new Array(vSize);
    v[max + 1] = 0;

    const trace = [];

    outer:
    for (let d = 0; d <= max; d++) {
      const snap = v.slice();
      trace.push(snap);

      for (let k = -d; k <= d; k += 2) {
        const idx = k + max;
        let x;
        if (k === -d || (k !== d && v[idx - 1] < v[idx + 1])) {
          x = v[idx + 1];
        } else {
          x = v[idx - 1] + 1;
        }
        let y = x - k;

        while (x < n && y < m && a[x] === b[y]) {
          x++;
          y++;
        }

        v[idx] = x;

        if (x >= n && y >= m) {
          break outer;
        }
      }
    }

    // Backtrack to build the edit script
    const ops = [];
    let x = n;
    let y = m;

    for (let d = trace.length - 1; d > 0; d--) {
      const snap = trace[d];
      const k = x - y;

      let prevK;
      if (k === -d || (k !== d && snap[k - 1 + max] < snap[k + 1 + max])) {
        prevK = k + 1;
      } else {
        prevK = k - 1;
      }

      const prevX = snap[prevK + max];
      const prevY = prevX - prevK;

      // Diagonal (equal)
      while (x > prevX && y > prevY) {
        x--;
        y--;
        ops.push({ type: 'equal', value: a[x] });
      }

      if (d > 0) {
        if (x === prevX) {
          // Insert
          y--;
          ops.push({ type: 'insert', value: b[y] });
        } else {
          // Delete
          x--;
          ops.push({ type: 'delete', value: a[x] });
        }
      }
    }

    // Remaining diagonal at d=0
    while (x > 0 && y > 0) {
      x--;
      y--;
      ops.push({ type: 'equal', value: a[x] });
    }

    ops.reverse();
    return ops;
  }

  /**
   * Diff two strings line by line.
   * Returns array of { type, value } where value is the line content.
   */
  function diffLines(textA, textB) {
    const linesA = textA.split('\n');
    const linesB = textB.split('\n');
    return myers(linesA, linesB);
  }

  /**
   * Diff two single lines word-by-word for inline highlighting.
   * Returns array of { type, value }.
   */
  function diffWords(lineA, lineB) {
    const tokenize = (str) => {
      const tokens = [];
      let buf = '';
      for (const ch of str) {
        if (/\s/.test(ch)) {
          if (buf) { tokens.push(buf); buf = ''; }
          tokens.push(ch);
        } else {
          buf += ch;
        }
      }
      if (buf) tokens.push(buf);
      return tokens;
    };
    return myers(tokenize(lineA), tokenize(lineB));
  }

  return { diffLines, diffWords };
})();
