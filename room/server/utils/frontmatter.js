/**
 * Frontmatter Parser — YAML frontmatter parser for session files
 *
 * Parses markdown files with YAML frontmatter delimited by ---
 * Returns { frontmatter, body } structure.
 */

/**
 * Parse YAML frontmatter from markdown content
 *
 * @param {string} content - Full markdown content
 * @returns {object} { frontmatter: object, body: string }
 */
export function parseFrontmatter(content) {
  if (!content) {
    return { frontmatter: {}, body: '' };
  }

  // Match --- delimited frontmatter
  const match = content.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);

  if (!match) {
    // No frontmatter found
    return { frontmatter: {}, body: content.trim() };
  }

  const fmText = match[1];
  const body = match[2].trim();

  const frontmatter = parseYaml(fmText);

  return { frontmatter, body };
}

/**
 * Simple YAML parser for frontmatter
 * Handles basic key: value pairs, no nested objects
 *
 * @param {string} yaml - YAML content
 * @returns {object} Parsed object
 */
function parseYaml(yaml) {
  const result = {};

  const lines = yaml.split('\n');

  for (const line of lines) {
    const trimmed = line.trim();

    // Skip empty lines and comments
    if (!trimmed || trimmed.startsWith('#')) {
      continue;
    }

    // Parse key: value
    const colonIndex = trimmed.indexOf(':');
    if (colonIndex === -1) {
      continue;
    }

    const key = trimmed.slice(0, colonIndex).trim();
    let value = trimmed.slice(colonIndex + 1).trim();

    // Remove quotes if present
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }

    // Try to parse as number
    if (/^-?\d+$/.test(value)) {
      value = parseInt(value, 10);
    } else if (/^-?\d+\.\d+$/.test(value)) {
      value = parseFloat(value);
    } else if (value === 'true') {
      value = true;
    } else if (value === 'false') {
      value = false;
    } else if (value === 'null' || value === '~') {
      value = null;
    }

    result[key] = value;
  }

  return result;
}

/**
 * Format frontmatter back to YAML string
 *
 * @param {object} frontmatter - Frontmatter object
 * @returns {string} YAML string
 */
export function stringifyFrontmatter(frontmatter) {
  const lines = ['---'];

  for (const [key, value] of Object.entries(frontmatter)) {
    if (value === null) {
      lines.push(`${key}: null`);
    } else if (typeof value === 'boolean') {
      lines.push(`${key}: ${value}`);
    } else if (typeof value === 'number') {
      lines.push(`${key}: ${value}`);
    } else if (typeof value === 'string') {
      // Quote string if it contains special characters
      if (/[:#{}[\],&*?|<>=!%@`]/.test(value) || value.includes('\n')) {
        lines.push(`${key}: "${value.replace(/"/g, '\\"')}"`);
      } else {
        lines.push(`${key}: ${value}`);
      }
    }
  }

  lines.push('---');
  return lines.join('\n');
}

/**
 * Clean markdown for display (remove formatting)
 *
 * @param {string} text - Markdown text
 * @returns {string} Cleaned text
 */
export function cleanMarkdown(text) {
  return text
    .replace(/^---$/gm, '')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^\s*\n/gm, '\n')
    .trim();
}

/**
 * Extract summary from session body
 * Looks for ## Summary section
 *
 * @param {string} body - Session body
 * @returns {string} Summary text
 */
export function extractSummary(body) {
  const match = body.match(/## Summary\n(.+?)(?:\n## |\n*$)/s);
  if (match) {
    return cleanMarkdown(match[1])
      .split('\n')
      .filter((l) => l.trim())
      .slice(0, 2)
      .join(' ');
  }

  // Fallback: first few lines
  return cleanMarkdown(body)
    .split('\n')
    .filter((l) => l.trim())
    .slice(0, 3)
    .join(' ');
}
