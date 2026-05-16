export interface ParagraphDiff {
  type: 'keep' | 'add' | 'remove';
  text: string;
}

export function computeParagraphDiff(original: string, result: string): ParagraphDiff[] {
  const a = original.split(/\n{2,}/).map(s => s.trim()).filter(Boolean);
  const b = result.split(/\n{2,}/).map(s => s.trim()).filter(Boolean);
  const m = a.length, n = b.length;

  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? 1 + dp[i + 1][j + 1] : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const diffs: ParagraphDiff[] = [];
  let i = 0, j = 0;
  while (i < m || j < n) {
    if (i < m && j < n && a[i] === b[j]) {
      diffs.push({ type: 'keep', text: a[i++] }); j++;
    } else if (i < m && (j >= n || dp[i + 1][j] >= dp[i][j + 1])) {
      diffs.push({ type: 'remove', text: a[i++] });
    } else {
      diffs.push({ type: 'add', text: b[j++] });
    }
  }
  return diffs;
}
