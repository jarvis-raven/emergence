/**
 * Simple markdown renderer
 * Converts basic markdown to HTML string
 * Handles: headers (h1-h3), bold, italic, lists, paragraphs, links
 */
export function renderMarkdown(text) {
  if (!text) return '';

  const lines = text.split('\n');
  const html = [];
  let inList = false;
  let listItems = [];

  const flushList = () => {
    if (listItems.length > 0) {
      html.push(`<ul class="list-disc pl-4 space-y-1">${listItems.join('')}</ul>`);
      listItems = [];
      inList = false;
    }
  };

  const processInline = (line) => {
    // Bold + italic
    line = line.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');
    // Bold
    line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic
    line = line.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Links [text](url)
    line = line.replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" class="text-primary hover:underline">$1</a>',
    );
    return line;
  };

  for (const line of lines) {
    const trimmed = line.trim();

    // Empty line - flush any list and add spacing
    if (!trimmed) {
      flushList();
      html.push('<div class="h-2"></div>');
      continue;
    }

    // H1
    if (trimmed.startsWith('# ')) {
      flushList();
      const content = processInline(trimmed.slice(2));
      html.push(`<h1 class="text-xl font-bold text-text mb-3 mt-4">${content}</h1>`);
      continue;
    }

    // H2
    if (trimmed.startsWith('## ')) {
      flushList();
      const content = processInline(trimmed.slice(3));
      html.push(`<h2 class="text-lg font-semibold text-text mb-2 mt-4">${content}</h2>`);
      continue;
    }

    // H3
    if (trimmed.startsWith('### ')) {
      flushList();
      const content = processInline(trimmed.slice(4));
      html.push(`<h3 class="text-base font-medium text-textMuted mb-2 mt-3">${content}</h3>`);
      continue;
    }

    // List items
    if (trimmed.match(/^[-•*] /)) {
      inList = true;
      const content = processInline(trimmed.slice(2));
      listItems.push(`<li class="text-textMuted">${content}</li>`);
      continue;
    }

    // Regular paragraph
    flushList();
    const content = processInline(trimmed);
    html.push(`<p class="text-textMuted leading-relaxed">${content}</p>`);
  }

  // Flush any remaining list
  flushList();

  return html.join('');
}

export default renderMarkdown;
