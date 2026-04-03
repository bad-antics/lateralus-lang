/**
 * LATERALUS Markup Language — Browser Renderer (ltlml.js)
 * ═══════════════════════════════════════════════════════
 * Client-side parser + renderer for .ltlml files.
 * Understands both {block}-based and Markdown-based LTLML syntax.
 *
 * Usage (polyglot .ltlml file):
 *   The file is valid HTML that loads this script, which reads the
 *   <ltlml-source> element and renders the document in-place.
 *
 * Usage (standalone):
 *   const html = LTLML.render(sourceText);
 *   document.body.innerHTML = html;
 */
(function (root) {
  "use strict";

  /* ────────────────────────────────────────────────────── */
  /*  Helpers                                                */
  /* ────────────────────────────────────────────────────── */

  function escapeHTML(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function inlineFormat(text) {
    var t = escapeHTML(text);
    // Bold  {strong ...}  or **...**
    t = t.replace(/\{strong\s+([^}]+)\}/g, "<strong>$1</strong>");
    t = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    t = t.replace(/__(.+?)__/g, "<strong>$1</strong>");
    // Italic  {em ...}  or _..._
    t = t.replace(/\{em\s+([^}]+)\}/g, "<em>$1</em>");
    t = t.replace(/(?<!\w)_(.+?)_(?!\w)/g, "<em>$1</em>");
    // Inline code  {code ...}  or `...`
    t = t.replace(/\{code\s+([^}]+)\}/g, "<code>$1</code>");
    t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Links  [text](url)
    t = t.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
    // Cross-refs @ref{id}
    t = t.replace(/@ref\{([^}]+)\}/g, '<a class="crossref" href="#$1">$1</a>');
    // Citations @cite{id}
    t = t.replace(/@cite\{([^}]+)\}/g, "<cite>[$1]</cite>");
    // Inline math $...$
    t = t.replace(/(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)/g,
      '<span class="math-inline">\\($1\\)</span>');
    // Rewrite .ltlml links -> .ltlml.html for browser navigation
    t = t.replace(/href="([^"]*?)\.ltlml"/g, 'href="$1.ltlml"');
    return t;
  }

  /* ────────────────────────────────────────────────────── */
  /*  {block} Parser                                         */
  /* ────────────────────────────────────────────────────── */

  /**
   * Parse a {block}-format LTLML source into an array of block objects.
   * Each block: { type: string, attrs: {}, text: string, children: [] }
   */
  function parseBlocks(source) {
    var lines = source.split("\n");
    var blocks = [];
    var i = 0;
    var n = lines.length;

    while (i < n) {
      var line = lines[i];
      var trimmed = line.trim();

      // Skip empty lines
      if (!trimmed) { i++; continue; }

      // {document ... }  — metadata block
      var m = trimmed.match(/^\{document\b/);
      if (m) {
        var attrs = {};
        i++;
        while (i < n) {
          var dl = lines[i].trim();
          if (dl === "}" || dl === "") { i++; break; }
          var kv = dl.match(/^(\w+)\s*:\s*(.+)/);
          if (kv) {
            var val = kv[2].trim();
            if (val.charAt(0) === '"' && val.charAt(val.length-1) === '"')
              val = val.slice(1, -1);
            attrs[kv[1]] = val;
          }
          i++;
        }
        blocks.push({ type: "document", attrs: attrs, text: "", children: [] });
        continue;
      }

      // {h1 ...}, {h2 ...}, etc.
      m = trimmed.match(/^\{h([1-6])\s+(.+)\}$/);
      if (m) {
        blocks.push({ type: "heading", attrs: { level: parseInt(m[1]) }, text: m[2], children: [] });
        i++;
        continue;
      }

      // {separator} / {hr}
      if (trimmed === "{separator}" || trimmed === "{hr}") {
        blocks.push({ type: "hr", attrs: {}, text: "", children: [] });
        i++;
        continue;
      }

      // {toc}
      if (trimmed === "{toc}") {
        blocks.push({ type: "toc", attrs: {}, text: "", children: [] });
        i++;
        continue;
      }

      // {code lang="..." ... }  — multi-line code block
      m = trimmed.match(/^\{code(?:\s+lang="([^"]*)")?/);
      if (m) {
        var lang = m[1] || "";
        var codeLines = [];
        // If the opening line has content after the tag
        var restOfLine = trimmed.replace(/^\{code(?:\s+lang="[^"]*")?\s*/, "");
        if (restOfLine && restOfLine !== "}") {
          // Check if single-line code block
          if (restOfLine.endsWith("}")) {
            codeLines.push(restOfLine.slice(0, -1));
            blocks.push({ type: "code", attrs: { language: lang }, text: codeLines.join("\n"), children: [] });
            i++;
            continue;
          }
          codeLines.push(restOfLine);
        }
        i++;
        while (i < n) {
          var cl = lines[i];
          if (cl.trimEnd() === "}") { i++; break; }
          codeLines.push(cl);
          i++;
        }
        blocks.push({ type: "code", attrs: { language: lang }, text: codeLines.join("\n"), children: [] });
        continue;
      }

      // {math ... }  — display math
      m = trimmed.match(/^\{math/);
      if (m) {
        var mathLines = [];
        i++;
        while (i < n) {
          if (lines[i].trim() === "}") { i++; break; }
          mathLines.push(lines[i]);
          i++;
        }
        blocks.push({ type: "math", attrs: {}, text: mathLines.join("\n"), children: [] });
        continue;
      }

      // {note ...} / {warning ...} / {tip ...} / {info ...}  — admonitions
      m = trimmed.match(/^\{(note|warning|tip|info|danger|important)(?:\s+"([^"]*)")?\s*$/);
      if (m) {
        var admType = m[1];
        var admTitle = m[2] || m[1];
        var admLines = [];
        i++;
        while (i < n) {
          if (lines[i].trim() === "}") { i++; break; }
          admLines.push(lines[i]);
          i++;
        }
        blocks.push({ type: "admonition", attrs: { adm_type: admType, title: admTitle }, text: admLines.join("\n").trim(), children: [] });
        continue;
      }

      // {theorem ...} / {proof ...} / {definition ...} / {lemma ...}
      m = trimmed.match(/^\{(theorem|proof|definition|lemma|corollary|proposition)(?:\s+"([^"]*)")?\s*$/);
      if (m) {
        var thmType = m[1];
        var thmTitle = m[2] || "";
        var thmLines = [];
        i++;
        while (i < n) {
          if (lines[i].trim() === "}") { i++; break; }
          thmLines.push(lines[i]);
          i++;
        }
        blocks.push({ type: "theorem", attrs: { thm_type: thmType, title: thmTitle }, text: thmLines.join("\n").trim(), children: [] });
        continue;
      }

      // {table ... }  — data table
      m = trimmed.match(/^\{table/);
      if (m) {
        var tableLines = [];
        i++;
        while (i < n) {
          if (lines[i].trim() === "}") { i++; break; }
          tableLines.push(lines[i]);
          i++;
        }
        blocks.push({ type: "table", attrs: {}, text: tableLines.join("\n").trim(), children: [] });
        continue;
      }

      // {blockquote ... }
      m = trimmed.match(/^\{blockquote/);
      if (m) {
        var bqLines = [];
        i++;
        while (i < n) {
          if (lines[i].trim() === "}") { i++; break; }
          bqLines.push(lines[i]);
          i++;
        }
        blocks.push({ type: "blockquote", attrs: {}, text: bqLines.join("\n").trim(), children: [] });
        continue;
      }

      // {list ... }  — bullet list
      m = trimmed.match(/^\{(list|ol)\b/);
      if (m) {
        var listType = m[1] === "ol" ? "ol" : "ul";
        var listItems = [];
        i++;
        while (i < n) {
          var li = lines[i].trim();
          if (li === "}") { i++; break; }
          if (li.match(/^[-*+]\s/)) {
            listItems.push(li.replace(/^[-*+]\s+/, ""));
          } else if (li.match(/^\d+\.\s/)) {
            listItems.push(li.replace(/^\d+\.\s+/, ""));
          } else if (li) {
            listItems.push(li);
          }
          i++;
        }
        blocks.push({ type: listType, attrs: {}, text: "", children: listItems });
        continue;
      }

      // {p ... }  — paragraph (may span multiple lines)
      m = trimmed.match(/^\{p\b\s*/);
      if (m) {
        var pLines = [];
        // Check for single-line paragraph: {p Some text}
        var pRest = trimmed.replace(/^\{p\s*/, "");
        if (pRest.endsWith("}")) {
          pLines.push(pRest.slice(0, -1).trim());
        } else {
          if (pRest) pLines.push(pRest);
          i++;
          while (i < n) {
            var pl = lines[i];
            if (pl.trim() === "}") { i++; break; }
            pLines.push(pl);
            i++;
          }
        }
        blocks.push({ type: "paragraph", attrs: {}, text: pLines.join("\n").trim(), children: [] });
        if (!pRest.endsWith("}")) continue;
        i++;
        continue;
      }

      // {image src="..." alt="..."}
      m = trimmed.match(/^\{image\s+src="([^"]+)"(?:\s+alt="([^"]*)")?\s*\}$/);
      if (m) {
        blocks.push({ type: "image", attrs: { src: m[1], alt: m[2] || "" }, text: "", children: [] });
        i++;
        continue;
      }

      // Markdown-style headings
      m = trimmed.match(/^(#{1,6})\s+(.+)/);
      if (m) {
        blocks.push({ type: "heading", attrs: { level: m[1].length }, text: m[2], children: [] });
        i++;
        continue;
      }

      // Markdown-style HR
      if (trimmed.match(/^[-*_]{3,}\s*$/)) {
        blocks.push({ type: "hr", attrs: {}, text: "", children: [] });
        i++;
        continue;
      }

      // Markdown-style fenced code ```lang ... ```
      m = trimmed.match(/^```(\w*)/);
      if (m) {
        var mdLang = m[1] || "";
        var mdCode = [];
        i++;
        while (i < n) {
          if (lines[i].trim().match(/^```\s*$/)) { i++; break; }
          mdCode.push(lines[i]);
          i++;
        }
        blocks.push({ type: "code", attrs: { language: mdLang }, text: mdCode.join("\n"), children: [] });
        continue;
      }

      // Markdown-style blockquote
      m = trimmed.match(/^>\s*(.*)/);
      if (m) {
        var mdBQ = [m[1]];
        i++;
        while (i < n && lines[i].trim().match(/^>\s*/)) {
          mdBQ.push(lines[i].trim().replace(/^>\s*/, ""));
          i++;
        }
        blocks.push({ type: "blockquote", attrs: {}, text: mdBQ.join("\n"), children: [] });
        continue;
      }

      // Markdown-style unordered list
      m = trimmed.match(/^[-*+]\s+(.*)/);
      if (m) {
        var mdUL = [m[1]];
        i++;
        while (i < n) {
          var ulm = lines[i].trim().match(/^[-*+]\s+(.*)/);
          if (ulm) { mdUL.push(ulm[1]); i++; } else break;
        }
        blocks.push({ type: "ul", attrs: {}, text: "", children: mdUL });
        continue;
      }

      // Markdown-style ordered list
      m = trimmed.match(/^\d+\.\s+(.*)/);
      if (m) {
        var mdOL = [m[1]];
        i++;
        while (i < n) {
          var olm = lines[i].trim().match(/^\d+\.\s+(.*)/);
          if (olm) { mdOL.push(olm[1]); i++; } else break;
        }
        blocks.push({ type: "ol", attrs: {}, text: "", children: mdOL });
        continue;
      }

      // Markdown-style table  | ... |
      m = trimmed.match(/^\|(.+)\|$/);
      if (m) {
        var tblLines = [trimmed];
        i++;
        while (i < n && lines[i].trim().match(/^\|/)) {
          tblLines.push(lines[i].trim());
          i++;
        }
        blocks.push({ type: "md-table", attrs: {}, text: tblLines.join("\n"), children: [] });
        continue;
      }

      // Anything else — plain paragraph text (accumulate)
      var plainLines = [line];
      i++;
      while (i < n) {
        var next = lines[i].trim();
        if (!next || next.charAt(0) === "{" || next.charAt(0) === "#" ||
            next.match(/^[-*+]\s/) || next.match(/^\d+\.\s/) ||
            next.match(/^```/) || next.match(/^\|/) || next.match(/^>/) ||
            next.match(/^[-*_]{3,}$/)) break;
        plainLines.push(lines[i]);
        i++;
      }
      blocks.push({ type: "paragraph", attrs: {}, text: plainLines.join("\n").trim(), children: [] });
    }

    return blocks;
  }

  /* ────────────────────────────────────────────────────── */
  /*  Renderer — blocks → HTML                              */
  /* ────────────────────────────────────────────────────── */

  function renderBlocks(blocks) {
    var html = [];
    var title = "LATERALUS Document";
    var subtitle = "";
    var headings = [];

    // First pass — collect metadata & headings for TOC
    blocks.forEach(function (b) {
      if (b.type === "document") {
        title = b.attrs.title || title;
        subtitle = b.attrs.subtitle || "";
      }
      if (b.type === "heading") {
        headings.push({ level: b.attrs.level, text: b.text,
          id: b.text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-+$/, "") });
      }
    });

    // Second pass — render
    blocks.forEach(function (b) {
      switch (b.type) {
        case "document":
          // Rendered as title header
          break;

        case "heading":
          var hid = b.text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-+$/, "");
          html.push('<h' + b.attrs.level + ' id="' + hid + '">' +
            inlineFormat(b.text) + '</h' + b.attrs.level + '>');
          break;

        case "paragraph":
          html.push("<p>" + inlineFormat(b.text) + "</p>");
          break;

        case "code":
          var langCls = b.attrs.language ?
            ' class="language-' + escapeHTML(b.attrs.language) + '"' : "";
          html.push('<pre><code' + langCls + '>' + escapeHTML(b.text) + '</code></pre>');
          break;

        case "math":
          html.push('<div class="math-block">$$' + escapeHTML(b.text) + '$$</div>');
          break;

        case "hr":
          html.push("<hr>");
          break;

        case "toc":
          html.push('<nav class="ltlml-toc"><h3>Contents</h3><ul>');
          headings.forEach(function (h) {
            var indent = (h.level - 1) * 16;
            html.push('<li style="margin-left:' + indent + 'px">' +
              '<a href="#' + h.id + '">' + escapeHTML(h.text) + '</a></li>');
          });
          html.push("</ul></nav>");
          break;

        case "admonition":
          html.push('<div class="admonition ' + escapeHTML(b.attrs.adm_type) + '">' +
            '<div class="admonition-title">' + escapeHTML(b.attrs.title) + '</div>' +
            '<p>' + inlineFormat(b.text) + '</p></div>');
          break;

        case "theorem":
          var display = b.attrs.thm_type.charAt(0).toUpperCase() + b.attrs.thm_type.slice(1);
          if (b.attrs.title) display += " (" + escapeHTML(b.attrs.title) + ")";
          html.push('<div class="theorem ' + escapeHTML(b.attrs.thm_type) + '">' +
            '<div class="theorem-title">' + display + '</div>' +
            '<p>' + inlineFormat(b.text) + '</p></div>');
          break;

        case "blockquote":
          html.push("<blockquote><p>" + inlineFormat(b.text) + "</p></blockquote>");
          break;

        case "ul":
          html.push("<ul>");
          b.children.forEach(function (item) {
            html.push("<li>" + inlineFormat(item) + "</li>");
          });
          html.push("</ul>");
          break;

        case "ol":
          html.push("<ol>");
          b.children.forEach(function (item) {
            html.push("<li>" + inlineFormat(item) + "</li>");
          });
          html.push("</ol>");
          break;

        case "table":
          // Simple pipe-delimited table within {table}
          var tRows = b.text.split("\n").filter(function (r) { return r.trim(); });
          if (tRows.length > 0) {
            html.push('<table>');
            tRows.forEach(function (row, idx) {
              var cells = row.split("|").map(function (c) { return c.trim(); })
                .filter(function (c) { return c; });
              if (idx === 0) {
                html.push('<thead><tr>');
                cells.forEach(function (c) { html.push("<th>" + inlineFormat(c) + "</th>"); });
                html.push('</tr></thead><tbody>');
              } else if (!row.match(/^[\s|:-]+$/)) {
                html.push("<tr>");
                cells.forEach(function (c) { html.push("<td>" + inlineFormat(c) + "</td>"); });
                html.push("</tr>");
              }
            });
            html.push('</tbody></table>');
          }
          break;

        case "md-table":
          var mdRows = b.text.split("\n").filter(function (r) { return r.trim(); });
          if (mdRows.length > 0) {
            html.push('<table>');
            mdRows.forEach(function (row, idx) {
              var cells = row.replace(/^\|/, "").replace(/\|$/, "")
                .split("|").map(function (c) { return c.trim(); });
              if (idx === 0) {
                html.push('<thead><tr>');
                cells.forEach(function (c) { html.push("<th>" + inlineFormat(c) + "</th>"); });
                html.push('</tr></thead><tbody>');
              } else if (!row.match(/^[\s|:-]+$/)) {
                html.push("<tr>");
                cells.forEach(function (c) { html.push("<td>" + inlineFormat(c) + "</td>"); });
                html.push("</tr>");
              }
            });
            html.push('</tbody></table>');
          }
          break;

        case "image":
          html.push('<figure><img src="' + escapeHTML(b.attrs.src) +
            '" alt="' + escapeHTML(b.attrs.alt) + '"><figcaption>' +
            escapeHTML(b.attrs.alt) + '</figcaption></figure>');
          break;
      }
    });

    return { title: title, subtitle: subtitle, body: html.join("\n") };
  }

  /* ────────────────────────────────────────────────────── */
  /*  Full Render — source → complete HTML page              */
  /* ────────────────────────────────────────────────────── */

  function render(source) {
    var blocks = parseBlocks(source);
    var result = renderBlocks(blocks);
    return result;
  }

  /* ────────────────────────────────────────────────────── */
  /*  Auto-Init — run when DOM is ready                      */
  /* ────────────────────────────────────────────────────── */

  function autoInit() {
    // Look for <ltlml-source> element
    var sourceEl = document.getElementById("ltlml-source");
    if (!sourceEl) return;

    var source = sourceEl.textContent || sourceEl.innerText;
    var result = render(source);

    // Set page title
    document.title = result.title;

    // Find or create the render target
    var target = document.getElementById("ltlml-render");
    if (!target) {
      target = document.createElement("div");
      target.id = "ltlml-render";
      target.className = "ltlml-document";
      document.body.appendChild(target);
    }

    // Render title
    var headerHTML = '<h1>' + escapeHTML(result.title) +
      '<span class="ltl-badge">LTLML</span></h1>';
    if (result.subtitle) {
      headerHTML += '<p class="meta">' + escapeHTML(result.subtitle) + '</p>';
    }

    target.innerHTML = headerHTML + result.body;

    // Hide the source element
    sourceEl.style.display = "none";

    // Trigger KaTeX if loaded
    if (typeof renderMathInElement === "function") {
      renderMathInElement(target);
    }
  }

  // Run on DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoInit);
  } else {
    autoInit();
  }

  // Export
  root.LTLML = {
    parse: parseBlocks,
    render: render,
    renderBlocks: renderBlocks,
    inlineFormat: inlineFormat,
    escapeHTML: escapeHTML,
    autoInit: autoInit
  };

})(typeof window !== "undefined" ? window : this);
