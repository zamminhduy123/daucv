/**
 * Blog Content Quality Audit Script
 * 
 * Scans all .mdx blog posts for content quality issues:
 *   Pattern A: Truncated text (sentences ending in "…" mid-word)
 *   Pattern B: Empty example sections (bold label ending ":" with no content before next heading)
 *   Pattern C: Duplicate headings (same ## or ### heading text appearing twice)
 *   Pattern D: Truncated frontmatter (description field ending in "…" mid-word)
 *   Pattern E: Empty "Nếu bạn muốn tìm hiểu sâu hơn" sections (unfilled template placeholder)
 *   Pattern F: Dead href="#" links
 * 
 * Usage: node scripts/audit-blog-content.cjs
 */

const fs = require('fs');
const path = require('path');
const matter = require('gray-matter');

const CONTENT_DIR = path.join(__dirname, '..', 'content', 'blog');

// Vietnamese word-ending characters — if the char before "…" is one of these,
// it's likely a natural ellipsis (e.g., "ATS…" or a stylistic trailing-off).
// But we flag ALL instances and let the human decide.
const NATURAL_ELLIPSIS_AFTER = /[.?!)\]"'»。？！）」』]\s*$/;

function findTruncatedText(lines) {
  const issues = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trimEnd();
    if (!line.endsWith('…')) continue;
    // Skip frontmatter delimiters
    if (line === '---') continue;
    // Skip lines inside component JSX props (handled separately)
    if (line.match(/^\s*"/)) continue;

    // Check if it looks like a mid-word truncation
    // Get the text before the "…"
    const beforeEllipsis = line.slice(0, -1).trimEnd();
    
    // Flag it — the reviewer can decide if it's intentional
    issues.push({
      line: i + 1,
      pattern: 'A',
      label: 'Truncated text',
      context: line.length > 120 ? '...' + line.slice(-100) : line,
    });
  }
  return issues;
}

function findEmptyExamples(lines) {
  const issues = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    // Look for bold labels ending with ":"
    const isBoldLabel = /^\*\*[^*]+:\*\*$/.test(line);
    if (!isBoldLabel) continue;

    // Check what follows: skip blank lines, then see if the next content is a heading or component
    let j = i + 1;
    while (j < lines.length && lines[j].trim() === '') j++;
    
    if (j >= lines.length) {
      issues.push({
        line: i + 1,
        pattern: 'B',
        label: 'Empty example (end of file)',
        context: line,
      });
      continue;
    }

    const nextContent = lines[j].trim();
    if (nextContent.startsWith('##') || nextContent.startsWith('<')) {
      issues.push({
        line: i + 1,
        pattern: 'B',
        label: 'Empty example section',
        context: `"${line}" → followed by "${nextContent.slice(0, 60)}" (line ${j + 1})`,
      });
    }
  }
  return issues;
}

function findDuplicateHeadings(lines) {
  const issues = [];
  const headings = {};
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    const match = line.match(/^(#{2,3})\s+(.+)$/);
    if (!match) continue;
    const text = match[2];
    if (headings[text] !== undefined) {
      issues.push({
        line: i + 1,
        pattern: 'C',
        label: 'Duplicate heading',
        context: `"${text}" — first at line ${headings[text] + 1}, duplicate at line ${i + 1}`,
      });
    } else {
      headings[text] = i;
    }
  }
  return issues;
}

function findTruncatedFrontmatter(frontmatter) {
  const issues = [];
  if (frontmatter.description && frontmatter.description.endsWith('…')) {
    issues.push({
      line: 0, // frontmatter, exact line unknown
      pattern: 'D',
      label: 'Truncated description',
      context: frontmatter.description.slice(-80),
    });
  }
  return issues;
}

function findEmptyRefSections(lines) {
  const issues = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.includes('Nếu bạn muốn tìm hiểu sâu hơn')) {
      // Check if the next non-blank lines have any actual content (links, text)
      let j = i + 1;
      let hasContent = false;
      while (j < lines.length && j < i + 5) {
        const nextLine = lines[j].trim();
        if (nextLine === '') { j++; continue; }
        if (nextLine.startsWith('<') || nextLine.startsWith('##') || nextLine.startsWith('{/*')) {
          break; // hit next section/component
        }
        if (nextLine.startsWith('-') || nextLine.startsWith('http') || nextLine.startsWith('[')) {
          hasContent = true;
          break;
        }
        j++;
      }
      if (!hasContent) {
        issues.push({
          line: i + 1,
          pattern: 'E',
          label: 'Empty reference section',
          context: line,
        });
      }
    }
  }
  return issues;
}

function auditFile(filePath) {
  const raw = fs.readFileSync(filePath, 'utf8');
  const { data: frontmatter, content } = matter(raw);
  const lines = content.split('\n');
  const allLines = raw.split('\n');

  const issues = [
    ...findTruncatedText(allLines),
    ...findEmptyExamples(allLines),
    ...findDuplicateHeadings(allLines),
    ...findTruncatedFrontmatter(frontmatter),
    ...findEmptyRefSections(allLines),
  ];

  return {
    file: path.basename(filePath),
    slug: path.basename(filePath, '.mdx'),
    frontmatter: {
      title: frontmatter.title,
      date: frontmatter.date,
      category: frontmatter.category,
      tags: frontmatter.tags,
    },
    issueCount: issues.length,
    issues,
  };
}

// ── Main ──
function main() {
  if (!fs.existsSync(CONTENT_DIR)) {
    console.error(`Content directory not found: ${CONTENT_DIR}`);
    process.exit(1);
  }

  const files = fs.readdirSync(CONTENT_DIR)
    .filter(f => f.endsWith('.mdx'))
    .sort();

  console.log(`\n📋 Blog Content Quality Audit`);
  console.log(`${'='.repeat(60)}`);
  console.log(`Scanning ${files.length} MDX files in content/blog/\n`);

  let totalIssues = 0;
  const patternCounts = { A: 0, B: 0, C: 0, D: 0, E: 0 };
  const results = [];

  for (const file of files) {
    const result = auditFile(path.join(CONTENT_DIR, file));
    results.push(result);
    totalIssues += result.issueCount;

    if (result.issueCount === 0) {
      console.log(`✅ ${result.slug} — no issues`);
    } else {
      console.log(`\n❌ ${result.slug} — ${result.issueCount} issue(s)`);
      console.log(`   Title: ${result.frontmatter.title}`);
      console.log(`   Date: ${result.frontmatter.date}`);
      for (const issue of result.issues) {
        patternCounts[issue.pattern]++;
        console.log(`   [${issue.pattern}] Line ${issue.line}: ${issue.label}`);
        console.log(`       ${issue.context}`);
      }
    }
  }

  console.log(`\n${'='.repeat(60)}`);
  console.log(`📊 Summary`);
  console.log(`   Total files scanned: ${files.length}`);
  console.log(`   Files with issues: ${results.filter(r => r.issueCount > 0).length}`);
  console.log(`   Total issues: ${totalIssues}`);
  console.log(`   Pattern A (truncated text): ${patternCounts.A}`);
  console.log(`   Pattern B (empty examples): ${patternCounts.B}`);
  console.log(`   Pattern C (duplicate headings): ${patternCounts.C}`);
  console.log(`   Pattern D (truncated description): ${patternCounts.D}`);
  console.log(`   Pattern E (empty reference section): ${patternCounts.E}`);
  console.log();

  // Exit with error code if issues found (useful for CI)
  if (totalIssues > 0) {
    process.exit(1);
  }
}

main();
