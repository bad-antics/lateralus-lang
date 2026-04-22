// ===============================================================
// POST /api/run — Lateralus Playground Execution Engine
// Lexes, parses, and evaluates Lateralus code server-side
// Rate-limited, sandboxed, output-capped
// ===============================================================

// -- Rate Limiter (per-isolate, resets on cold start) ----------
const attempts = new Map();
const RATE_LIMIT  = 30;           // requests per window
const RATE_WINDOW = 60 * 1000;    // 1 minute

function getIP(request) {
  return request.headers.get('cf-connecting-ip') ||
         request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
         'unknown';
}

function rateCheck(ip) {
  const now = Date.now();
  const rec = attempts.get(ip);
  if (!rec || now - rec.start > RATE_WINDOW) {
    attempts.set(ip, { count: 1, start: now });
    return true;
  }
  rec.count++;
  return rec.count <= RATE_LIMIT;
}

// -- Security Headers ------------------------------------------
const SEC = {
  'Content-Type': 'application/json; charset=utf-8',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Cache-Control': 'no-store',
  'Access-Control-Allow-Origin': 'https://lateralus.dev',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

function jsonResp(data, status = 200) {
  return Response.json(data, { status, headers: SEC });
}

// -- Lateralus Lexer -------------------------------------------
const KEYWORDS = new Set([
  'fn', 'let', 'mut', 'if', 'else', 'match', 'for', 'in', 'while',
  'return', 'import', 'struct', 'enum', 'impl', 'async', 'await',
  'spawn', 'try', 'recover', 'ensure', 'true', 'false', 'and',
  'or', 'not', 'pub', 'mod', 'use', 'type', 'const', 'break',
  'continue', 'loop', 'yield', 'self', 'super',
]);

const BUILTINS = new Set([
  'println', 'print', 'eprintln', 'len', 'push', 'pop', 'map',
  'filter', 'fold', 'reduce', 'sort', 'sort_by', 'reverse',
  'join', 'split', 'trim', 'contains', 'starts_with', 'ends_with',
  'replace', 'to_upper', 'to_lower', 'parse_int', 'parse_float',
  'to_string', 'type_of', 'range', 'enumerate', 'zip', 'any',
  'all', 'sum', 'min', 'max', 'abs', 'sqrt', 'pow', 'floor',
  'ceil', 'round', 'take', 'skip', 'first', 'last', 'flat_map',
  'keys', 'values', 'entries', 'insert', 'remove', 'get',
  'unwrap', 'unwrap_or', 'expect', 'is_some', 'is_none',
  'ok', 'err', 'assert', 'dbg', 'input', 'read_file', 'write_file',
  'capitalize', 'collect', 'average', 'avg', 'is_empty', 'div',
  'find', 'flatten', 'flat', 'count', 'group_by', 'map_err',
  'not_empty', 'clamp', 'sign',
]);

function tokenize(source) {
  const tokens = [];
  let i = 0;
  const src = source;
  const len = src.length;

  while (i < len) {
    // Whitespace
    if (src[i] === ' ' || src[i] === '\t' || src[i] === '\r') { i++; continue; }

    // Newline
    if (src[i] === '\n') { tokens.push({ type: 'NEWLINE' }); i++; continue; }

    // Single-line comment
    if (src[i] === '/' && src[i+1] === '/') {
      while (i < len && src[i] !== '\n') i++;
      continue;
    }

    // Multi-line comment
    if (src[i] === '/' && src[i+1] === '*') {
      i += 2;
      while (i < len - 1 && !(src[i] === '*' && src[i+1] === '/')) i++;
      i += 2;
      continue;
    }

    // String
    if (src[i] === '"') {
      i++;
      let s = '';
      let braceDepth = 0;
      while (i < len && (src[i] !== '"' || braceDepth > 0)) {
        if (src[i] === '\\' && i + 1 < len) {
          const c = src[i+1];
          if (c === 'n') s += '\n';
          else if (c === 't') s += '\t';
          else if (c === '\\') s += '\\';
          else if (c === '"') s += '"';
          else if (c === '{') s += '{';
          else s += c;
          i += 2;
        } else {
          if (src[i] === '{') braceDepth++;
          else if (src[i] === '}') braceDepth--;
          s += src[i]; i++;
        }
      }
      i++; // closing quote
      tokens.push({ type: 'STRING', value: s });
      continue;
    }

    // Number
    if ((src[i] >= '0' && src[i] <= '9') || (src[i] === '-' && i + 1 < len && src[i+1] >= '0' && src[i+1] <= '9' && (tokens.length === 0 || ['OP','LPAREN','COMMA','LBRACE','LBRACKET','NEWLINE','PIPE'].includes(tokens[tokens.length-1]?.type)))) {
      let num = '';
      if (src[i] === '-') { num += '-'; i++; }
      while (i < len && ((src[i] >= '0' && src[i] <= '9') || (src[i] === '.' && src[i+1] !== '.') || src[i] === '_')) {
        if (src[i] !== '_') num += src[i];
        i++;
      }
      tokens.push({ type: 'NUMBER', value: num.includes('.') ? parseFloat(num) : parseInt(num, 10) });
      continue;
    }

    // Identifier / keyword
    if ((src[i] >= 'a' && src[i] <= 'z') || (src[i] >= 'A' && src[i] <= 'Z') || src[i] === '_') {
      let id = '';
      while (i < len && ((src[i] >= 'a' && src[i] <= 'z') || (src[i] >= 'A' && src[i] <= 'Z') || (src[i] >= '0' && src[i] <= '9') || src[i] === '_')) {
        id += src[i]; i++;
      }
      if (KEYWORDS.has(id)) tokens.push({ type: 'KEYWORD', value: id });
      else if (id === 'None') tokens.push({ type: 'NONE' });
      else if (id === 'Some') tokens.push({ type: 'SOME' });
      else tokens.push({ type: 'IDENT', value: id });
      continue;
    }

    // Pipeline operator
    if (src[i] === '|' && src[i+1] === '>') { tokens.push({ type: 'PIPE' }); i += 2; continue; }

    // Arrow
    if (src[i] === '-' && src[i+1] === '>') { tokens.push({ type: 'ARROW' }); i += 2; continue; }

    // Fat arrow
    if (src[i] === '=' && src[i+1] === '>') { tokens.push({ type: 'FAT_ARROW' }); i += 2; continue; }

    // Comparison ops
    if (src[i] === '=' && src[i+1] === '=') { tokens.push({ type: 'OP', value: '==' }); i += 2; continue; }
    if (src[i] === '!' && src[i+1] === '=') { tokens.push({ type: 'OP', value: '!=' }); i += 2; continue; }
    if (src[i] === '<' && src[i+1] === '=') { tokens.push({ type: 'OP', value: '<=' }); i += 2; continue; }
    if (src[i] === '>' && src[i+1] === '=') { tokens.push({ type: 'OP', value: '>=' }); i += 2; continue; }
    if (src[i] === '&' && src[i+1] === '&') { tokens.push({ type: 'OP', value: '&&' }); i += 2; continue; }
    if (src[i] === '|' && src[i+1] === '|') { tokens.push({ type: 'OP', value: '||' }); i += 2; continue; }

    // Range operator ..
    if (src[i] === '.' && src[i+1] === '.') { tokens.push({ type: 'RANGE_OP' }); i += 2; continue; }

    // Double-colon ::
    if (src[i] === ':' && src[i+1] === ':') { tokens.push({ type: 'DOUBLE_COLON' }); i += 2; continue; }

    // Single-char tokens
    const SINGLES = {
      '(': 'LPAREN', ')': 'RPAREN', '{': 'LBRACE', '}': 'RBRACE',
      '[': 'LBRACKET', ']': 'RBRACKET', ',': 'COMMA', ':': 'COLON',
      ';': 'SEMI', '.': 'DOT',
    };
    if (SINGLES[src[i]]) { tokens.push({ type: SINGLES[src[i]] }); i++; continue; }

    // Operators
    if ('+-*/%<>=!&|^~'.includes(src[i])) {
      tokens.push({ type: 'OP', value: src[i] }); i++; continue;
    }

    // Skip unknown
    i++;
  }

  return tokens;
}

// -- Lateralus Interpreter -------------------------------------

const MAX_OUTPUT_LINES = 200;
const MAX_OUTPUT_BYTES = 16384;
const MAX_STEPS = 50000;
const MAX_STACK_DEPTH = 256;

class LateralusError extends Error {
  constructor(msg) { super(msg); this.name = 'LateralusError'; }
}

class Environment {
  constructor(parent = null) {
    this.vars = new Map();
    this.parent = parent;
  }
  get(name) {
    if (this.vars.has(name)) return this.vars.get(name);
    if (this.parent) return this.parent.get(name);
    return undefined;
  }
  set(name, val) { this.vars.set(name, val); }
  has(name) {
    if (this.vars.has(name)) return true;
    if (this.parent) return this.parent.has(name);
    return false;
  }
}

function interpret(tokens, limits) {
  const output = [];
  let outputBytes = 0;
  let steps = 0;
  let stackDepth = 0;

  function addOutput(text) {
    if (output.length >= limits.maxLines) throw new LateralusError('Output limit exceeded (max ' + limits.maxLines + ' lines)');
    const line = String(text);
    outputBytes += line.length;
    if (outputBytes > limits.maxBytes) throw new LateralusError('Output size limit exceeded');
    output.push(line);
  }

  function step() {
    steps++;
    if (steps > limits.maxSteps) throw new LateralusError('Execution limit exceeded (max ' + limits.maxSteps + ' steps — possible infinite loop)');
  }

  // -- Parser (tokens → AST) --
  let pos = 0;

  function peek() { while (pos < tokens.length && tokens[pos].type === 'NEWLINE') pos++; return tokens[pos]; }
  function peekRaw() { return tokens[pos]; }
  function advance() { const t = tokens[pos]; pos++; return t; }
  function skipNewlines() { while (pos < tokens.length && tokens[pos].type === 'NEWLINE') pos++; }
  function expect(type) {
    skipNewlines();
    const t = advance();
    if (!t || t.type !== type) throw new LateralusError("Expected " + type + ", got " + (t ? t.type : 'EOF'));
    return t;
  }

  function parseProgram() {
    const stmts = [];
    while (pos < tokens.length) {
      skipNewlines();
      if (pos >= tokens.length) break;
      stmts.push(parseStatement());
    }
    return { type: 'program', body: stmts };
  }

  function parseStatement() {
    step();
    skipNewlines();
    const t = peek();
    if (!t) return { type: 'noop' };

    if (t.type === 'KEYWORD') {
      switch (t.value) {
        case 'let': case 'const': return parseLet();
        case 'fn': return parseFn();
        case 'if': return parseIf();
        case 'for': return parseFor();
        case 'while': return parseWhile();
        case 'return': advance(); return { type: 'return', value: parseExpr() };
        case 'import': return parseImport();
        case 'struct': return parseStruct();
        case 'enum': return parseEnum();
        case 'impl': return parseImpl();
        case 'match': return parseMatchStmt();
        case 'async': return parseFn();
        case 'pub': advance(); return parseStatement();
        case 'type': advance(); advance(); if (peek()?.type === 'OP' && peek()?.value === '=') { advance(); parseTypeAnnotation(); } return { type: 'noop' };
        case 'try': return parseTryCatch();
      }
    }

    return parseExpr();
  }

  function parseLet() {
    const kw = advance(); // let/const
    skipNewlines();
    const name = expect('IDENT').value;
    skipNewlines();

    // Optional type annotation
    if (peek()?.type === 'COLON') { advance(); parseTypeAnnotation(); }

    skipNewlines();
    if (peek()?.type === 'OP' && peek()?.value === '=') {
      advance();
      skipNewlines();
      const value = parseExpr();
      return { type: 'let', name, value, mutable: kw.value === 'let' };
    }
    return { type: 'let', name, value: { type: 'literal', value: null }, mutable: kw.value === 'let' };
  }

  function parseTypeAnnotation() {
    // Consume type tokens loosely
    skipNewlines();
    if (peek()?.type === 'IDENT' || peek()?.type === 'KEYWORD') advance();
    if (peek()?.type === 'OP' && peek()?.value === '<') {
      advance();
      let depth = 1;
      while (pos < tokens.length && depth > 0) {
        if (tokens[pos].type === 'OP' && tokens[pos].value === '<') depth++;
        if (tokens[pos].type === 'OP' && tokens[pos].value === '>') depth--;
        pos++;
      }
    }
  }

  function parseFn() {
    let isAsync = false;
    if (peek()?.value === 'async') { advance(); isAsync = true; }
    advance(); // fn
    skipNewlines();
    const name = peek()?.type === 'IDENT' ? advance().value : null;
    expect('LPAREN');
    const params = [];
    while (peek()?.type !== 'RPAREN' && pos < tokens.length) {
      skipNewlines();
      if (peek()?.type === 'RPAREN') break;
      // Accept KEYWORD tokens too (e.g. 'self')
      const pname = (peek()?.type === 'IDENT' || peek()?.type === 'KEYWORD') ? advance().value : expect('IDENT').value;
      if (peek()?.type === 'COLON') { advance(); parseTypeAnnotation(); }
      params.push(pname);
      if (peek()?.type === 'COMMA') advance();
    }
    expect('RPAREN');
    // Optional return type
    if (peek()?.type === 'ARROW') { advance(); parseTypeAnnotation(); }
    const body = parseBlock();
    return { type: 'fn', name, params, body, isAsync };
  }

  function parseBlock() {
    expect('LBRACE');
    const stmts = [];
    skipNewlines();
    while (peek()?.type !== 'RBRACE' && pos < tokens.length) {
      stmts.push(parseStatement());
      skipNewlines();
    }
    expect('RBRACE');
    return { type: 'block', body: stmts };
  }

  function parseIf() {
    advance(); // if
    skipNewlines();
    const cond = parseExpr();
    const then = parseBlock();
    skipNewlines();
    let els = null;
    if (peek()?.type === 'KEYWORD' && peek()?.value === 'else') {
      advance();
      skipNewlines();
      if (peek()?.type === 'KEYWORD' && peek()?.value === 'if') {
        els = parseIf();
      } else {
        els = parseBlock();
      }
    }
    return { type: 'if', cond, then, else: els };
  }

  function parseFor() {
    advance(); // for
    skipNewlines();
    let forVar, forTupleVars = null;
    if (peek()?.type === 'LPAREN') {
      advance(); // (
      forTupleVars = [];
      while (peek()?.type !== 'RPAREN' && pos < tokens.length) {
        if (peek()?.type === 'IDENT') forTupleVars.push(advance().value);
        else if (peek()?.type === 'KEYWORD') forTupleVars.push(advance().value);
        if (peek()?.type === 'COMMA') advance();
      }
      advance(); // )
      forVar = '__tuple_item';
    } else {
      forVar = expect('IDENT').value;
    }
    skipNewlines();
    expect('KEYWORD'); // 'in'
    skipNewlines();
    const iter = parseExpr();
    const body = parseBlock();
    return { type: 'for', var: forVar, tupleVars: forTupleVars, iter, body };
  }

  function parseWhile() {
    advance(); // while
    skipNewlines();
    const cond = parseExpr();
    const body = parseBlock();
    return { type: 'while', cond, body };
  }

  function parseImport() {
    advance(); // import
    skipNewlines();
    const parts = [];
    while (peek()?.type === 'IDENT') {
      parts.push(advance().value);
      if (peek()?.type === 'DOT') advance(); else break;
    }
    // Handle { named } imports
    if (peek()?.type === 'LBRACE') {
      advance();
      while (peek()?.type !== 'RBRACE' && pos < tokens.length) {
        if (peek()?.type === 'IDENT') advance();
        if (peek()?.type === 'COMMA') advance();
        skipNewlines();
      }
      if (peek()?.type === 'RBRACE') advance();
    }
    return { type: 'import', module: parts.join('.') };
  }

  function parseStruct() {
    advance(); // struct
    const name = expect('IDENT').value;
    expect('LBRACE');
    const fields = [];
    skipNewlines();
    while (peek()?.type !== 'RBRACE' && pos < tokens.length) {
      skipNewlines();
      if (peek()?.type === 'RBRACE') break;
      const fname = expect('IDENT').value;
      expect('COLON');
      parseTypeAnnotation();
      fields.push(fname);
      if (peek()?.type === 'COMMA') advance();
      skipNewlines();
    }
    expect('RBRACE');
    return { type: 'struct', name, fields };
  }

  function parseEnum() {
    advance(); // enum
    const name = expect('IDENT').value;
    expect('LBRACE');
    const variants = [];
    skipNewlines();
    while (peek()?.type !== 'RBRACE' && pos < tokens.length) {
      skipNewlines();
      if (peek()?.type === 'RBRACE') break;
      const vname = expect('IDENT').value;
      const vfields = [];
      if (peek()?.type === 'LPAREN') {
        advance();
        while (peek()?.type !== 'RPAREN' && pos < tokens.length) {
          parseTypeAnnotation();
          vfields.push('_');
          if (peek()?.type === 'COMMA') advance();
        }
        expect('RPAREN');
      }
      variants.push({ name: vname, arity: vfields.length });
      if (peek()?.type === 'COMMA') advance();
      skipNewlines();
    }
    expect('RBRACE');
    return { type: 'enum', name, variants };
  }

  function parseImpl() {
    advance(); // impl
    const typeName = expect('IDENT').value;
    // Skip trait syntax: impl Trait for Type
    if (peek()?.type === 'KEYWORD' && peek()?.value === 'for') { advance(); advance(); }
    expect('LBRACE');
    const methods = [];
    skipNewlines();
    while (peek()?.type !== 'RBRACE' && pos < tokens.length) {
      skipNewlines();
      if (peek()?.type === 'RBRACE') break;
      // skip pub
      if (peek()?.type === 'KEYWORD' && peek()?.value === 'pub') advance();
      if (peek()?.type === 'KEYWORD' && (peek()?.value === 'fn' || peek()?.value === 'async')) {
        const fn = parseFn();
        methods.push(fn);
      } else {
        advance(); // skip unknown tokens
      }
      skipNewlines();
    }
    expect('RBRACE');
    return { type: 'impl', typeName, methods };
  }

  function parseTryCatch() {
    advance(); // try
    const body = parseBlock();
    let recoverVar = null;
    let recoverBody = null;
    let ensureBody = null;
    skipNewlines();
    if (peek()?.type === 'KEYWORD' && peek()?.value === 'recover') {
      advance();
      skipNewlines();
      if (peek()?.type === 'IDENT') recoverVar = advance().value;
      recoverBody = parseBlock();
    }
    skipNewlines();
    if (peek()?.type === 'KEYWORD' && peek()?.value === 'ensure') {
      advance();
      ensureBody = parseBlock();
    }
    return { type: 'try_catch', body, recoverVar, recoverBody, ensureBody };
  }

  function parseMatchStmt() {
    advance(); // match
    skipNewlines();
    const subject = parseExpr();
    expect('LBRACE');
    const arms = [];
    skipNewlines();
    while (peek()?.type !== 'RBRACE' && pos < tokens.length) {
      skipNewlines();
      if (peek()?.type === 'RBRACE') break;
      let pattern = parsePattern();
      // Collect or-alternatives: 1 | 2 | 3
      while (peek()?.type === 'OP' && peek()?.value === '|') {
        advance(); // consume '|'
        const alt = parsePattern();
        if (pattern.type === 'or_pattern') {
          pattern.alternatives.push(alt);
        } else {
          pattern = { type: 'or_pattern', alternatives: [pattern, alt] };
        }
      }
      let guard = null;
      skipNewlines();
      if (peek()?.type === 'KEYWORD' && peek()?.value === 'if') {
        advance();
        guard = parseExpr();
      }
      expect('FAT_ARROW');
      skipNewlines();
      let body;
      if (peek()?.type === 'LBRACE') {
        body = parseBlock();
      } else {
        body = parseExpr();
      }
      arms.push({ pattern, guard, body });
      if (peek()?.type === 'COMMA') advance();
      skipNewlines();
    }
    expect('RBRACE');
    return { type: 'match', subject, arms };
  }

  function parsePattern() {
    skipNewlines();
    const t = peek();
    if (t?.type === 'OP' && t?.value === '_') { advance(); return { type: 'wildcard' }; }
    if (t?.type === 'IDENT' && t?.value === '_') { advance(); return { type: 'wildcard' }; }
    if (t?.type === 'STRING') { advance(); return { type: 'literal', value: t.value }; }
    if (t?.type === 'NUMBER') { advance(); return { type: 'literal', value: t.value }; }
    if (t?.type === 'KEYWORD' && (t?.value === 'true' || t?.value === 'false')) { advance(); return { type: 'literal', value: t.value === 'true' }; }
    if (t?.type === 'NONE') { advance(); return { type: 'literal', value: null }; }
    if (t?.type === 'SOME') {
      advance(); // Some
      if (peek()?.type === 'LPAREN') {
        advance(); // (
        const binding = parsePattern();
        expect('RPAREN');
        return { type: 'some_pattern', binding };
      }
      return { type: 'some_pattern', binding: null };
    }
    
    if (t?.type === 'LPAREN') {
      advance();
      const elems = [];
      while (peek()?.type !== 'RPAREN') {
        elems.push(parsePattern());
        if (peek()?.type === 'COMMA') advance();
      }
      expect('RPAREN');
      return { type: 'tuple_pattern', elems };
    }
    if (t?.type === 'IDENT') {
      const name = advance().value;
      if (peek()?.type === 'LPAREN') {
        advance();
        const bindings = [];
        while (peek()?.type !== 'RPAREN') {
          bindings.push(parsePattern());
          if (peek()?.type === 'COMMA') advance();
        }
        expect('RPAREN');
        return { type: 'variant_pattern', variant: name, bindings };
      }
      return { type: 'binding', name };
    }
    advance();
    return { type: 'wildcard' };
  }

  // -- Expression Parsing --
  function parseExpr() { return parseOr(); }

  function parsePipeline() {
    let left = parseAddSub();
    while (peek()?.type === 'PIPE') {
      step();
      advance();
      skipNewlines();
      const fn = parseUnary();
      left = { type: 'pipe', left, fn };
    }
    return left;
  }

  function parseOr() {
    let left = parseAnd();
    while ((peek()?.type === 'KEYWORD' && peek()?.value === 'or') || (peek()?.type === 'OP' && peek()?.value === '||')) {
      advance(); left = { type: 'binop', op: 'or', left, right: parseAnd() };
    }
    return left;
  }
  function parseAnd() {
    let left = parseEquality();
    while ((peek()?.type === 'KEYWORD' && peek()?.value === 'and') || (peek()?.type === 'OP' && peek()?.value === '&&')) {
      advance(); left = { type: 'binop', op: 'and', left, right: parseEquality() };
    }
    return left;
  }
  function parseEquality() {
    let left = parseComparison();
    while (peek()?.type === 'OP' && (peek()?.value === '==' || peek()?.value === '!=')) {
      const op = advance().value; left = { type: 'binop', op, left, right: parseComparison() };
    }
    return left;
  }
  function parseComparison() {
    let left = parsePipeline();
    while (peek()?.type === 'OP' && (peek()?.value === '<' || peek()?.value === '>' || peek()?.value === '<=' || peek()?.value === '>=')) {
      const op = advance().value; left = { type: 'binop', op, left, right: parsePipeline() };
    }
    return left;
  }
  function parseAddSub() {
    let left = parseMulDiv();
    while (peek()?.type === 'OP' && (peek()?.value === '+' || peek()?.value === '-')) {
      const op = advance().value; left = { type: 'binop', op, left, right: parseMulDiv() };
    }
    return left;
  }
  function parseMulDiv() {
    let left = parseUnary();
    while (peek()?.type === 'OP' && (peek()?.value === '*' || peek()?.value === '/' || peek()?.value === '%')) {
      const op = advance().value; left = { type: 'binop', op, left, right: parseUnary() };
    }
    return left;
  }
  function parseUnary() {
    if (peek()?.type === 'OP' && peek()?.value === '!') { advance(); return { type: 'unary', op: '!', operand: parseUnary() }; }
    if (peek()?.type === 'KEYWORD' && peek()?.value === 'not') { advance(); return { type: 'unary', op: '!', operand: parseUnary() }; }
    if (peek()?.type === 'OP' && peek()?.value === '-') {
      // Negative number vs subtraction: only negate if previous token isn't a value
      advance();
      return { type: 'unary', op: '-', operand: parseUnary() };
    }
    return parsePostfix();
  }

  function parsePostfix() {
    let node = parsePrimary();
    while (true) {
      if (peek()?.type === 'DOT') {
        advance();
        const field = expect('IDENT').value;
        if (peek()?.type === 'LPAREN') {
          advance();
          const args = parseArgList();
          expect('RPAREN');
          node = { type: 'method_call', object: node, method: field, args };
        } else {
          node = { type: 'field', object: node, field };
        }
      } else if (peek()?.type === 'DOUBLE_COLON' && node.type === 'ident') {
        advance(); // consume ::
        const staticMethod = expect('IDENT').value;
        if (peek()?.type === 'LPAREN') {
          advance();
          const scArgs = parseArgList();
          expect('RPAREN');
          node = { type: 'static_call', typeName: node.name, method: staticMethod, args: scArgs };
        } else {
          node = { type: 'static_ref', typeName: node.name, method: staticMethod };
        }
    } else if (peek()?.type === 'LPAREN' && node.type === 'ident') {
        advance();
        const args = parseArgList();
        expect('RPAREN');
        node = { type: 'call', fn: node.name, args };
    } else if (peek()?.type === 'RANGE_OP') {
        advance();
        const rangeEnd = parseUnary();
        node = { type: 'range_expr', start: node, end: rangeEnd };
        break;
      } else if (peek()?.type === 'LBRACKET') {
        advance();
        const idx = parseExpr();
        expect('RBRACKET');
        node = { type: 'index', object: node, index: idx };
      } else {
        break;
      }
    }
    return node;
  }

  function parseArgList() {
    const args = [];
    skipNewlines();
    while (peek()?.type !== 'RPAREN' && pos < tokens.length) {
      skipNewlines();
      if (peek()?.type === 'RPAREN') break;
      args.push(parseExpr());
      skipNewlines();
      if (peek()?.type === 'COMMA') advance();
      skipNewlines();
    }
    return args;
  }

  function parsePrimary() {
    step();
    skipNewlines();
    const t = peek();
    if (!t) throw new LateralusError('Unexpected end of input');

    // Literals
    if (t.type === 'NUMBER') {
      advance();
      // Check for range: 0..n
      if (peek()?.type === 'RANGE_OP') {
        advance();
        const end = parsePrimary();
        return { type: 'range_expr', start: { type: 'literal', value: t.value }, end };
      }
      return { type: 'literal', value: t.value };
    }
    if (t.type === 'STRING') { advance(); return { type: 'string_interp', raw: t.value }; }
    if (t.type === 'KEYWORD' && t.value === 'true') { advance(); return { type: 'literal', value: true }; }
    if (t.type === 'KEYWORD' && t.value === 'false') { advance(); return { type: 'literal', value: false }; }
    if (t.type === 'NONE') { advance(); return { type: 'literal', value: null }; }

    // Lambda: |params| body
    if (t.type === 'OP' && t.value === '|') {
      advance();
      const params = [];
      while (!(peek()?.type === 'OP' && peek()?.value === '|') && pos < tokens.length) {
        if (peek()?.type === 'LPAREN') {
          // Tuple-destructuring param: (i, w)
          advance(); // (
          const names = [];
          while (peek()?.type !== 'RPAREN' && pos < tokens.length) {
            if (peek()?.type === 'IDENT') names.push(advance().value);
            else if (peek()?.type === 'KEYWORD') names.push(advance().value);
            if (peek()?.type === 'COMMA') advance();
          }
          advance(); // )
          params.push({ __tuple_param: true, names });
        } else if (peek()?.type === 'IDENT') {
          params.push(advance().value);
        } else if (peek()?.type === 'KEYWORD') {
          params.push(advance().value);
        }
        if (peek()?.type === 'COMMA') advance();
        skipNewlines();
      }
      advance(); // closing |
      skipNewlines();
      let body;
      if (peek()?.type === 'LBRACE') {
        body = parseBlock();
      } else {
        body = parseExpr();
      }
      return { type: 'lambda', params, body };
    }

    // Grouped / tuple
    if (t.type === 'LPAREN') {
      advance();
      if (peek()?.type === 'RPAREN') { advance(); return { type: 'literal', value: null }; }
      const first = parseExpr();
      if (peek()?.type === 'COMMA') {
        const elems = [first];
        while (peek()?.type === 'COMMA') { advance(); skipNewlines(); elems.push(parseExpr()); }
        expect('RPAREN');
        return { type: 'tuple', elems };
      }
      expect('RPAREN');
      return first;
    }

    // List
    if (t.type === 'LBRACKET') {
      advance();
      const elems = [];
      skipNewlines();
      while (peek()?.type !== 'RBRACKET' && pos < tokens.length) {
        elems.push(parseExpr());
        skipNewlines();
        if (peek()?.type === 'COMMA') advance();
        skipNewlines();
      }
      expect('RBRACKET');
      return { type: 'list', elems };
    }

    // Map literal { "key": value }
    if (t.type === 'LBRACE') {
      advance();
      const entries = [];
      skipNewlines();
      while (peek()?.type !== 'RBRACE' && pos < tokens.length) {
        const key = parseExpr();
        expect('COLON');
        const value = parseExpr();
        entries.push({ key, value });
        skipNewlines();
        if (peek()?.type === 'COMMA') advance();
        skipNewlines();
      }
      expect('RBRACE');
      return { type: 'map', entries };
    }

    // Identifier (could be struct constructor or enum variant)
    if (t.type === 'IDENT') {
      const name = advance().value;
      // Struct constructor: Name { field: value }
      if (peek()?.type === 'LBRACE' && name[0] >= 'A' && name[0] <= 'Z') {
        advance();
        const fields = {};
        skipNewlines();
        while (peek()?.type !== 'RBRACE' && pos < tokens.length) {
          skipNewlines();
          if (peek()?.type === 'RBRACE') break;
          const fname = expect('IDENT').value;
          if (peek()?.type === 'COLON') {
            advance();
            fields[fname] = parseExpr();
          } else {
            // Shorthand: { x } means { x: x }
            fields[fname] = { type: 'ident', name: fname };
          }
          skipNewlines();
          if (peek()?.type === 'COMMA') advance();
          skipNewlines();
        }
        expect('RBRACE');
        return { type: 'struct_init', name, fields };
      }
      return { type: 'ident', name };
    }

    if (t.type === 'SOME') {
      advance();
      expect('LPAREN');
      const val = parseExpr();
      expect('RPAREN');
      return { type: 'some', value: val };
    }

    // 'self' and 'super' as identifiers inside impl methods
    if (t.type === 'KEYWORD' && (t.value === 'self' || t.value === 'super')) {
      advance();
      return { type: 'ident', name: t.value };
    }

    // Keyword expressions
    if (t.type === 'KEYWORD') {
      if (t.value === 'await') { advance(); return { type: 'await', expr: parseExpr() }; }
      if (t.value === 'spawn') { advance(); return { type: 'spawn', expr: parseExpr() }; }
      if (t.value === 'if') return parseIf();
      if (t.value === 'match') return parseMatchStmt();
      if (t.value === 'fn') return parseFn();
    }

    // Skip unknown token
    advance();
    return { type: 'literal', value: null };
  }

  // -- Evaluator --
  function evaluate(node, env) {
    step();
    if (!node) return null;

    switch (node.type) {
      case 'program':
        let lastVal = null;
        for (const stmt of node.body) {
          lastVal = evaluate(stmt, env);
          if (lastVal?.__return) return lastVal;
        }
        return lastVal;

      case 'noop': return null;
      case 'literal': return node.value;

      case 'string_interp': {
        return node.raw.replace(/\{([^}]+)\}/g, (_, expr) => {
          // Split off format specifier like :.2
          const colonIdx = expr.search(/:[^:}]/);
          let varPart = colonIdx !== -1 ? expr.slice(0, colonIdx).trim() : expr.trim();
          const fmtSpec = colonIdx !== -1 ? expr.slice(colonIdx + 1).trim() : null;
          // Evaluate the variable part
          let val = undefined;
          if (env.has(varPart)) {
            val = env.get(varPart);
          } else if (!varPart.includes('(') && !varPart.includes('[') && !varPart.includes(' ')) {
            // Simple field access: obj.field.subfield (no calls)
            const parts = varPart.split('.');
            if (parts.length >= 2 && env.has(parts[0])) {
              let obj = env.get(parts[0]);
              for (let pi = 1; pi < parts.length; pi++) {
                obj = obj?.[parts[pi]] ?? null;
              }
              val = obj;
            }
          }
          if (val === undefined) {
            // Full expression evaluation (method calls, arithmetic, etc.)
            try {
              const savedTokens = tokens; const savedPos = pos;
              tokens = tokenize(varPart); pos = 0;
              const ast2 = parseExpr();
              tokens = savedTokens; pos = savedPos;
              val = evaluate(ast2, env);
            } catch(e) { return '{' + expr + '}'; }
          }
          if (fmtSpec && typeof val === 'number') {
            const m = fmtSpec.match(/^\.(\d+)$/);
            if (m) return val.toFixed(parseInt(m[1]));
          }
          return formatValue(val);
        });
      }
            case 'list': return node.elems.map(e => evaluate(e, env));
      case 'tuple': return { __tuple: true, elems: node.elems.map(e => evaluate(e, env)) };
      case 'map': {
        const m = {};
        for (const e of node.entries) {
          m[evaluate(e.key, env)] = evaluate(e.value, env);
        }
        return m;
      }

      case 'ident': {
        const val = env.get(node.name);
        if (val !== undefined) return val;
        if (BUILTINS.has(node.name)) return { __builtin: node.name };
        return null;
      }

      case 'let': {
        const val = evaluate(node.value, env);
        env.set(node.name, val);
        return val;
      }

      case 'fn': {
        const closure = { __fn: true, name: node.name, params: node.params, body: node.body, env };
        if (node.name) env.set(node.name, closure);
        return closure;
      }

      case 'lambda': {
        return { __fn: true, name: null, params: node.params, body: node.body, env };
      }

      case 'call': {
        const fn = env.get(node.fn);
        const args = node.args.map(a => evaluate(a, env));

        // Builtins
        if (BUILTINS.has(node.fn) || fn?.__builtin) {
          return callBuiltin(fn?.__builtin || node.fn, args, env);
        }

        if (fn?.__fn) return callFn(fn, args);
        if (fn?.__enum_variant) return { __variant: fn.__enum_variant, values: args };

        throw new LateralusError("'" + node.fn + "' is not a function");
      }

      case 'method_call': {
        const obj = evaluate(node.object, env);
        const args = node.args.map(a => evaluate(a, env));
        return callMethod(obj, node.method, args, env);
      }

      case 'pipe': {
        const val = evaluate(node.left, env);
        // If the RHS is a call, prepend the piped value as the first argument
        // (handles both builtins and user-defined/impl methods)
        if (node.fn.type === 'call') {
          const pipeArgs = [val, ...node.fn.args.map(a => evaluate(a, env))];
          const pfn = env.get(node.fn.fn);
          if (BUILTINS.has(node.fn.fn) || pfn?.__builtin) return callBuiltin(pfn?.__builtin || node.fn.fn, pipeArgs, env);
          if (pfn?.__fn) return callFn(pfn, pipeArgs);
          // Try as a method call on the piped value
          return callMethod(val, node.fn.fn, pipeArgs.slice(1), env);
        }
        const fn = evaluate(node.fn, env);
        if (fn?.__fn) return callFn(fn, [val]);
        if (fn?.__builtin) return callBuiltin(fn.__builtin, [val], env);
        if (typeof fn === 'function') return fn(val);
        throw new LateralusError("Pipeline target is not callable");
      }

      case 'field': {
        const obj = evaluate(node.object, env);
        if (obj && typeof obj === 'object') return obj[node.field] ?? null;
        return null;
      }

      case 'index': {
        const obj = evaluate(node.object, env);
        const idx = evaluate(node.index, env);
        if (Array.isArray(obj)) return obj[idx] ?? null;
        if (typeof obj === 'object' && obj) return obj[idx] ?? null;
        return null;
      }

      case 'binop': return evalBinop(node, env);
      case 'unary': {
        const val = evaluate(node.operand, env);
        if (node.op === '!') return !val;
        if (node.op === '-') return -val;
        return val;
      }

      case 'if': {
        const cond = evaluate(node.cond, env);
        if (cond) return evaluate(node.then, env);
        if (node.else) return evaluate(node.else, env);
        return null;
      }

      case 'for': {
        const iter = evaluate(node.iter, env);
        if (!Array.isArray(iter)) throw new LateralusError("for-in requires an iterable");
        let last = null;
        for (const item of iter) {
          step();
          const loopEnv = new Environment(env);
          if (node.tupleVars) {
            const elems = item?.__tuple ? item.elems : (Array.isArray(item) ? item : [item]);
            node.tupleVars.forEach((v, i) => loopEnv.set(v, elems[i] ?? null));
          } else {
            loopEnv.set(node.var, item);
          }
          last = evaluate(node.body, loopEnv);
          if (last?.__return) return last;
          if (last?.__break) break;
        }
        return last;
      }

      case 'while': {
        let last = null;
        while (evaluate(node.cond, env)) {
          step();
          last = evaluate(node.body, env);
          if (last?.__return) return last;
          if (last?.__break) break;
        }
        return last;
      }

      case 'return': {
        const val = evaluate(node.value, env);
        return { __return: true, value: val };
      }

      case 'block': {
        const blockEnv = new Environment(env);
        let last = null;
        for (const stmt of node.body) {
          last = evaluate(stmt, blockEnv);
          if (last?.__return) return last;
        }
        return last;
      }

      case 'match': {
        const subject = evaluate(node.subject, env);
        for (const arm of node.arms) {
          const bindings = matchPattern(arm.pattern, subject);
          if (bindings !== null) {
            const matchEnv = new Environment(env);
            for (const [k, v] of Object.entries(bindings)) matchEnv.set(k, v);
            // Check optional guard
            if (arm.guard && !evaluate(arm.guard, matchEnv)) continue;
            return evaluate(arm.body, matchEnv);
          }
        }
        throw new LateralusError("Non-exhaustive match");
      }

      case 'struct': {
        env.set(node.name, { __struct_def: true, name: node.name, fields: node.fields });
        return null;
      }

      case 'struct_init': {
        const inst = { __struct: node.name };
        for (const [k, v] of Object.entries(node.fields)) {
          inst[k] = evaluate(v, env);
        }
        // Attach impl methods
        const implEntry = implRegistry.get(node.name);
        if (implEntry) {
          for (const [mname, fn] of implEntry.instance) inst['__method_' + mname] = fn;
        }
        return inst;
      }

      case 'impl': {
        const entry = implRegistry.get(node.typeName) || { static: new Map(), instance: new Map() };
        implRegistry.set(node.typeName, entry);
        for (const fn of node.methods) {
          const closure = { __fn: true, __impl: true, name: fn.name, params: fn.params, body: fn.body, env };
          if (fn.params.length > 0 && fn.params[0] === 'self') {
            entry.instance.set(fn.name, closure);
          } else {
            entry.static.set(fn.name, closure);
          }
          if (fn.name) env.set(fn.name, closure);
        }
        return null;
      }

      case 'static_call': {
        const args = node.args.map(a => evaluate(a, env));
        // Check impl registry
        const implE = implRegistry.get(node.typeName);
        if (implE?.static.has(node.method)) return callFn(implE.static.get(node.method), args);
        if (implE?.instance.has(node.method)) return callFn(implE.instance.get(node.method), args);
        // Check env for TypeName__method or TypeName as namespace object
        const ns = env.get(node.typeName);
        if (ns && typeof ns === 'object' && ns[node.method] !== undefined) {
          const m = ns[node.method];
          if (m?.__fn) return callFn(m, args);
          return m;
        }
        // Built-in namespaces
        if (node.typeName === 'math' || node.typeName === 'Math') {
          const mathFns = { sqrt: Math.sqrt, abs: Math.abs, pow: Math.pow, floor: Math.floor, ceil: Math.ceil, round: Math.round, pi: Math.PI, e: Math.E, sin: Math.sin, cos: Math.cos, tan: Math.tan, log: Math.log, log2: Math.log2 };
          if (node.method in mathFns) { const f = mathFns[node.method]; return typeof f === 'function' ? f(args[0]) : f; }
        }
        throw new LateralusError(node.typeName + '::' + node.method + ' is not defined');
      }

      case 'static_ref': {
        const implE = implRegistry.get(node.typeName);
        if (implE?.static.has(node.method)) return implE.static.get(node.method);
        const ns = env.get(node.typeName);
        if (ns && typeof ns === 'object') return ns[node.method] ?? null;
        if (node.typeName === 'math' || node.typeName === 'Math') {
          const mathConsts = { pi: Math.PI, e: Math.E, tau: Math.PI * 2, infinity: Infinity };
          if (node.method.toLowerCase() in mathConsts) return mathConsts[node.method.toLowerCase()];
        }
        return null;
      }

      case 'range_expr': {
        const start = evaluate(node.start, env);
        const end = evaluate(node.end, env);
        const arr = [];
        for (let ri = start; ri < end; ri++) arr.push(ri);
        return arr;
      }

      case 'try_catch': {
        let result = null;
        try {
          result = evaluate(node.body, env);
        } catch(e) {
          if (node.recoverBody) {
            const recEnv = new Environment(env);
            if (node.recoverVar) recEnv.set(node.recoverVar, e?.message || String(e));
            result = evaluate(node.recoverBody, recEnv);
          }
        } finally {
          if (node.ensureBody) evaluate(node.ensureBody, env);
        }
        return result;
      }

      case 'enum': {
        for (const v of node.variants) {
          if (v.arity === 0) {
            env.set(v.name, { __variant: v.name, values: [] });
          } else {
            env.set(v.name, { __enum_variant: v.name, arity: v.arity });
          }
        }
        return null;
      }

      case 'some': {
        return { __some: true, value: evaluate(node.value, env) };
      }

      case 'import': return null; // imports are acknowledged but stdlib is pre-loaded
      case 'await': return evaluate(node.expr, env);
      case 'spawn': return evaluate(node.expr, env);

      default: return null;
    }
  }

  function evalBinop(node, env) {
    const l = evaluate(node.left, env);
    const r = evaluate(node.right, env);
    switch (node.op) {
      case '+': return (typeof l === 'string' || typeof r === 'string') ? String(l) + String(r) : l + r;
      case '-': return l - r;
      case '*': return l * r;
      case '/': if (r === 0) throw new LateralusError('Division by zero'); return l / r;
      case '%': return l % r;
      case '==': return l === r;
      case '!=': return l !== r;
      case '<': return l < r;
      case '>': return l > r;
      case '<=': return l <= r;
      case '>=': return l >= r;
      case 'and': return l && r;
      case 'or': return l || r;
      default: return null;
    }
  }

  function callFn(fn, args) {
    stackDepth++;
    if (stackDepth > MAX_STACK_DEPTH) throw new LateralusError('Stack overflow (recursion depth > ' + MAX_STACK_DEPTH + ')');
    const callEnv = new Environment(fn.env);
    fn.params.forEach((p, i) => {
      const arg = args[i] ?? null;
      if (p && p.__tuple_param) {
        // Destructure tuple: |(i, w)| -> bind i and w
        const elems = arg?.__tuple ? arg.elems : (Array.isArray(arg) ? arg : [arg]);
        p.names.forEach((name, ni) => callEnv.set(name, elems[ni] ?? null));
      } else {
        callEnv.set(p, arg);
      }
    });
    const result = evaluate(fn.body, callEnv);
    stackDepth--;
    return result?.__return ? result.value : result;
  }

  function callBuiltin(name, args, env) {
    step();
    switch (name) {
      case 'println': addOutput(args.map(formatValue).join(' ')); return null;
      case 'print': {
        const text = args.map(formatValue).join(' ');
        if (output.length > 0) {
          output[output.length - 1] += text;
        } else {
          output.push(text);
        }
        return null;
      }
      case 'eprintln': addOutput('[stderr] ' + args.map(formatValue).join(' ')); return null;
      case 'len': {
        const v = args[0];
        if (typeof v === 'string') return v.length;
        if (Array.isArray(v)) return v.length;
        if (v && typeof v === 'object') return Object.keys(v).length;
        return 0;
      }
      case 'push': { if (Array.isArray(args[0])) args[0].push(args[1]); return args[0]; }
      case 'pop': { if (Array.isArray(args[0])) return args[0].pop(); return null; }
      case 'map': {
        const arr = Array.isArray(args[0]) ? args[0] : [];
        const fn = args[1];
        if (fn?.__fn) return arr.map(item => callFn(fn, [item]));
        if (fn?.__builtin) return arr.map(item => callBuiltin(fn.__builtin, [item], env));
        return arr;
      }
      case 'filter': {
        const arr = Array.isArray(args[0]) ? args[0] : [];
        const fn = args[1];
        if (fn?.__fn) return arr.filter(item => callFn(fn, [item]));
        return arr;
      }
      case 'fold': case 'reduce': {
        const arr = Array.isArray(args[0]) ? args[0] : [];
        const fn = args[1];
        const init = args.length > 2 ? args[2] : (arr.length > 0 ? arr[0] : null);
        const startArr = args.length > 2 ? arr : arr.slice(1);
        if (fn?.__fn) return startArr.reduce((acc, item) => callFn(fn, [acc, item]), init);
        return init;
      }
      case 'sort': {
        const arr = Array.isArray(args[0]) ? [...args[0]] : [];
        return arr.sort((a, b) => a < b ? -1 : a > b ? 1 : 0);
      }
      case 'sort_by': {
        const arr = Array.isArray(args[0]) ? [...args[0]] : [];
        const fn = args[1];
        if (fn?.__fn) return arr.sort((a, b) => { const ka = callFn(fn, [a]); const kb = callFn(fn, [b]); return ka < kb ? -1 : ka > kb ? 1 : 0; });
        return arr;
      }
      case 'reverse': return Array.isArray(args[0]) ? [...args[0]].reverse() : args[0];
      case 'join': return Array.isArray(args[0]) ? args[0].map(formatValue).join(args[1] ?? '') : '';
      case 'split': return typeof args[0] === 'string' ? args[0].split(args[1] ?? '') : [];
      case 'trim': return typeof args[0] === 'string' ? args[0].trim() : args[0];
      case 'contains': {
        if (typeof args[0] === 'string') return args[0].includes(args[1]);
        if (Array.isArray(args[0])) return args[0].includes(args[1]);
        return false;
      }
      case 'starts_with': return typeof args[0] === 'string' ? args[0].startsWith(args[1]) : false;
      case 'ends_with': return typeof args[0] === 'string' ? args[0].endsWith(args[1]) : false;
      case 'replace': return typeof args[0] === 'string' ? args[0].replaceAll(args[1], args[2]) : args[0];
      case 'to_upper': return typeof args[0] === 'string' ? args[0].toUpperCase() : args[0];
      case 'to_lower': return typeof args[0] === 'string' ? args[0].toLowerCase() : args[0];
      case 'parse_int': return parseInt(args[0], 10) || 0;
      case 'parse_float': return parseFloat(args[0]) || 0.0;
      case 'to_string': return formatValue(args[0]);
      case 'type_of': return typeOf(args[0]);
      case 'range': {
        const start = args.length === 1 ? 0 : args[0];
        const end = args.length === 1 ? args[0] : args[1];
        const step = args[2] || 1;
        const arr = [];
        for (let i = start; i < end; i += step) arr.push(i);
        return arr;
      }
      case 'enumerate': return (Array.isArray(args[0]) ? args[0] : []).map((v, i) => ({ __tuple: true, elems: [i, v] }));
      case 'zip': {
        const a = Array.isArray(args[0]) ? args[0] : [];
        const b = Array.isArray(args[1]) ? args[1] : [];
        return a.slice(0, Math.min(a.length, b.length)).map((v, i) => ({ __tuple: true, elems: [v, b[i]] }));
      }
      case 'any': {
        const arr = Array.isArray(args[0]) ? args[0] : [];
        const fn = args[1];
        if (fn?.__fn) return arr.some(item => callFn(fn, [item]));
        return false;
      }
      case 'all': {
        const arr = Array.isArray(args[0]) ? args[0] : [];
        const fn = args[1];
        if (fn?.__fn) return arr.every(item => callFn(fn, [item]));
        return true;
      }
      case 'sum': return (Array.isArray(args[0]) ? args[0] : []).reduce((a, b) => a + b, 0);
      case 'min': return Array.isArray(args[0]) ? Math.min(...args[0]) : Math.min(...args);
      case 'max': return Array.isArray(args[0]) ? Math.max(...args[0]) : Math.max(...args);
      case 'abs': return Math.abs(args[0]);
      case 'sqrt': return Math.sqrt(args[0]);
      case 'pow': return Math.pow(args[0], args[1]);
      case 'floor': return Math.floor(args[0]);
      case 'ceil': return Math.ceil(args[0]);
      case 'round': return Math.round(args[0]);
      case 'take': return Array.isArray(args[0]) ? args[0].slice(0, args[1]) : args[0];
      case 'skip': return Array.isArray(args[0]) ? args[0].slice(args[1]) : args[0];
      case 'first': return Array.isArray(args[0]) ? (args[0][0] ?? null) : null;
      case 'last': return Array.isArray(args[0]) ? (args[0][args[0].length - 1] ?? null) : null;
      case 'flat_map': {
        const arr = Array.isArray(args[0]) ? args[0] : [];
        const fn = args[1];
        if (fn?.__fn) return arr.flatMap(item => callFn(fn, [item]));
        return arr;
      }
      case 'keys': return args[0] && typeof args[0] === 'object' ? Object.keys(args[0]) : [];
      case 'values': return args[0] && typeof args[0] === 'object' ? Object.values(args[0]) : [];
      case 'entries': return args[0] && typeof args[0] === 'object' ? Object.entries(args[0]).map(([k, v]) => ({ __tuple: true, elems: [k, v] })) : [];
      case 'insert': {
        if (args[0] && typeof args[0] === 'object') return { ...args[0], [args[1]]: args[2] };
        return args[0];
      }
      case 'remove': {
        if (args[0] && typeof args[0] === 'object') { const o = { ...args[0] }; delete o[args[1]]; return o; }
        return args[0];
      }
      case 'get': {
        if (Array.isArray(args[0])) return args[0][args[1]] ?? null;
        if (args[0] && typeof args[0] === 'object') return args[0][args[1]] ?? null;
        return null;
      }
      case 'unwrap': return args[0]?.__some ? args[0].value : args[0];
      case 'unwrap_or': return (args[0] != null && args[0] !== false) ? args[0] : args[1];
      case 'expect': { if (args[0] == null) throw new LateralusError(args[1] || 'Expected a value'); return args[0]; }
      case 'is_some': return args[0] != null;
      case 'is_none': return args[0] == null;
      case 'ok': return { __result: 'ok', value: args[0] };
      case 'err': return { __result: 'err', value: args[0] };
      case 'assert': { if (!args[0]) throw new LateralusError('Assertion failed: ' + (args[1] || '')); return true; }
      case 'dbg': { addOutput('[dbg] ' + formatValue(args[0])); return args[0]; }
      case 'input': return ''; // no stdin in playground
      case 'read_file': throw new LateralusError('Filesystem access is disabled in the playground');
      case 'write_file': throw new LateralusError('Filesystem access is disabled in the playground');
      case 'capitalize': {
        const s = String(args[0] ?? '');
        return s.length === 0 ? s : s[0].toUpperCase() + s.slice(1);
      }
      case 'collect': return args[0]; // identity — arrays are already collected
      case 'average': case 'avg': {
        const arr = Array.isArray(args[0]) ? args[0] : [];
        if (arr.length === 0) return 0;
        return arr.reduce((a, b) => a + b, 0) / arr.length;
      }
      case 'is_empty': {
        const v = args[0];
        if (typeof v === 'string') return v.length === 0;
        if (Array.isArray(v)) return v.length === 0;
        if (v && typeof v === 'object') return Object.keys(v).length === 0;
        return v == null;
      }
      case 'not_empty': {
        const v = args[0];
        if (typeof v === 'string') return v.length > 0;
        if (Array.isArray(v)) return v.length > 0;
        return v != null;
      }
      case 'div': {
        if (args[1] === 0) throw new LateralusError('Division by zero');
        return args[0] / args[1];
      }
      case 'find': {
        const arr = Array.isArray(args[0]) ? args[0] : [];
        const fn = args[1];
        if (fn?.__fn) return arr.find(item => callFn(fn, [item])) ?? null;
        return null;
      }
      case 'flatten': case 'flat': {
        const arr = Array.isArray(args[0]) ? args[0] : [];
        return arr.flat(args[1] ?? 1);
      }
      case 'count': {
        const arr = Array.isArray(args[0]) ? args[0] : [];
        const fn = args[1];
        if (fn?.__fn) return arr.filter(item => callFn(fn, [item])).length;
        return arr.length;
      }
      case 'group_by': {
        const arr = Array.isArray(args[0]) ? args[0] : [];
        const fn = args[1];
        const result = {};
        for (const item of arr) {
          const key = fn?.__fn ? String(callFn(fn, [item])) : String(item);
          if (!result[key]) result[key] = [];
          result[key].push(item);
        }
        return result;
      }
      case 'map_err': return args[0]; // simplified: pass through
      case 'clamp': return Math.min(Math.max(args[0], args[1]), args[2]);
      case 'sign': return args[0] > 0 ? 1 : args[0] < 0 ? -1 : 0;
      default: return null;
    }
  }

  function callMethod(obj, method, args, env) {
    // User-defined impl instance methods attached to struct
    if (obj && typeof obj === 'object' && obj.__struct) {
      const implE = implRegistry.get(obj.__struct);
      if (implE?.instance.has(method)) return callFn(implE.instance.get(method), [obj, ...args]);
    }
    // String methods
    if (typeof obj === 'string') {
      switch (method) {
        case 'len': return obj.length;
        case 'contains': return obj.includes(args[0]);
        case 'starts_with': return obj.startsWith(args[0]);
        case 'ends_with': return obj.endsWith(args[0]);
        case 'split': return obj.split(args[0] ?? '');
        case 'trim': return obj.trim();
        case 'to_upper': return obj.toUpperCase();
        case 'to_lower': return obj.toLowerCase();
        case 'replace': return obj.replaceAll(args[0], args[1]);
        case 'slice': return obj.slice(args[0], args[1]);
        case 'chars': return [...obj];
        case 'repeat': return obj.repeat(args[0]);
        case 'index_of': return obj.indexOf(args[0]);
      }
    }
    // List methods
    if (Array.isArray(obj)) {
      switch (method) {
        case 'len': return obj.length;
        case 'push': obj.push(args[0]); return obj;
        case 'pop': return obj.pop();
        case 'map': if (args[0]?.__fn) return obj.map(i => callFn(args[0], [i])); return obj;
        case 'filter': if (args[0]?.__fn) return obj.filter(i => callFn(args[0], [i])); return obj;
        case 'contains': return obj.includes(args[0]);
        case 'reverse': return [...obj].reverse();
        case 'sort': return [...obj].sort((a, b) => a < b ? -1 : a > b ? 1 : 0);
        case 'join': return obj.map(formatValue).join(args[0] ?? '');
        case 'first': return obj[0] ?? null;
        case 'last': return obj[obj.length - 1] ?? null;
        case 'slice': return obj.slice(args[0], args[1]);
        case 'flat': return obj.flat();
      }
    }
    // Map / struct methods
    if (obj && typeof obj === 'object') {
      if (method in obj && typeof obj[method] === 'object' && obj[method]?.__fn) {
        return callFn(obj[method], args);
      }
      switch (method) {
        case 'keys': return Object.keys(obj).filter(k => !k.startsWith('__'));
        case 'values': return Object.values(obj);
        case 'contains': return args[0] in obj;
        case 'get': return obj[args[0]] ?? null;
        case 'len': return Object.keys(obj).length;
      }
    }
    throw new LateralusError("No method '" + method + "' on " + typeOf(obj));
  }

  function matchPattern(pattern, value) {
    switch (pattern.type) {
      case 'wildcard': return {};
      case 'literal': return pattern.value === value ? {} : null;
      case 'binding': return { [pattern.name]: value };
      case 'or_pattern': {
        for (const alt of pattern.alternatives) {
          const b = matchPattern(alt, value);
          if (b !== null) return b;
        }
        return null;
      }
      case 'some_pattern': {
        if (!value?.__some) return null;
        if (pattern.binding === null) return {};
        return matchPattern(pattern.binding, value.value) ?? null;
      }
      case 'variant_pattern': {
        if (!value || value.__variant !== pattern.variant) return null;
        if (pattern.bindings.length !== (value.values?.length || 0)) return null;
        const bindings = {};
        for (let i = 0; i < pattern.bindings.length; i++) {
          const sub = matchPattern(pattern.bindings[i], value.values[i]);
          if (sub === null) return null;
          Object.assign(bindings, sub);
        }
        return bindings;
      }
      case 'tuple_pattern': {
        if (!value?.__tuple) return null;
        if (pattern.elems.length !== value.elems.length) return null;
        const bindings = {};
        for (let i = 0; i < pattern.elems.length; i++) {
          const sub = matchPattern(pattern.elems[i], value.elems[i]);
          if (sub === null) return null;
          Object.assign(bindings, sub);
        }
        return bindings;
      }
      default: return {};
    }
  }

  function formatValue(v) {
    if (v === null || v === undefined) return 'None';
    if (v === true) return 'true';
    if (v === false) return 'false';
    if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(2);
    if (typeof v === 'string') return v;
    if (v?.__tuple) return '(' + v.elems.map(formatValue).join(', ') + ')';
    if (v?.__variant) return v.values.length ? v.__variant + '(' + v.values.map(formatValue).join(', ') + ')' : v.__variant;
    if (v?.__some) return 'Some(' + formatValue(v.value) + ')';
    if (v?.__result) return v.__result === 'ok' ? 'Ok(' + formatValue(v.value) + ')' : 'Err(' + formatValue(v.value) + ')';
    if (v?.__struct) {
      const fields = Object.entries(v).filter(([k]) => k !== '__struct').map(([k, val]) => k + ': ' + formatValue(val)).join(', ');
      return v.__struct + ' { ' + fields + ' }';
    }
    if (Array.isArray(v)) return '[' + v.map(formatValue).join(', ') + ']';
    if (typeof v === 'object') {
      const entries = Object.entries(v).filter(([k]) => !k.startsWith('__'));
      if (entries.length === 0) return '{}';
      return '{ ' + entries.map(([k, val]) => '"' + k + '": ' + formatValue(val)).join(', ') + ' }';
    }
    return String(v);
  }

  function typeOf(v) {
    if (v === null || v === undefined) return 'None';
    if (typeof v === 'boolean') return 'bool';
    if (typeof v === 'number') return Number.isInteger(v) ? 'int' : 'float';
    if (typeof v === 'string') return 'str';
    if (v?.__tuple) return 'tuple';
    if (v?.__variant) return 'enum';
    if (v?.__struct) return v.__struct;
    if (v?.__fn) return 'fn';
    if (Array.isArray(v)) return 'list';
    if (typeof v === 'object') return 'map';
    return 'unknown';
  }

  // -- Run --
  const ast = parseProgram();
  const implRegistry = new Map();

  const globalEnv = new Environment();

  // Pre-populate stdlib stubs
  globalEnv.set('PI', 3.14159265358979);
  globalEnv.set('E', 2.71828182845905);
  globalEnv.set('TAU', 6.28318530717959);
  globalEnv.set('INFINITY', Infinity);
  globalEnv.set('NEG_INFINITY', -Infinity);
  globalEnv.set('math', { pi: Math.PI, e: Math.E, tau: Math.PI * 2, sqrt: Math.sqrt, abs: Math.abs, pow: Math.pow, floor: Math.floor, ceil: Math.ceil, round: Math.round, sin: Math.sin, cos: Math.cos, tan: Math.tan, log: Math.log });
  globalEnv.set('Math', globalEnv.get('math'));

  evaluate(ast, globalEnv);

  // Auto-call main() if defined
  const mainFn = globalEnv.get('main');
  if (mainFn && mainFn.__fn) {
    callFn(mainFn, []);
  }

  return {
    output,
    steps,
  };
}

// -- HTTP Handler ----------------------------------------------

export async function onRequestPost(context) {
  const ip = getIP(context.request);

  if (!rateCheck(ip)) {
    return jsonResp({ error: 'Rate limit exceeded. Max 30 executions per minute.' }, 429);
  }

  // Payload size guard
  const cl = parseInt(context.request.headers.get('content-length') || '0', 10);
  if (cl > 32768) {
    return jsonResp({ error: 'Code too large (max 32KB)' }, 413);
  }

  let body;
  try {
    const text = await context.request.text();
    if (text.length > 32768) return jsonResp({ error: 'Code too large (max 32KB)' }, 413);
    body = JSON.parse(text);
  } catch {
    return jsonResp({ error: 'Invalid JSON' }, 400);
  }

  const code = body?.code;
  if (!code || typeof code !== 'string') {
    return jsonResp({ error: 'Missing "code" field' }, 400);
  }

  if (code.length > 32768) {
    return jsonResp({ error: 'Code too large (max 32KB)' }, 413);
  }

  const startTime = Date.now();

  try {
    const tokens = tokenize(code);
    const result = interpret(tokens, {
      maxLines: MAX_OUTPUT_LINES,
      maxBytes: MAX_OUTPUT_BYTES,
      maxSteps: MAX_STEPS,
    });

    const elapsed = Date.now() - startTime;

    return jsonResp({
      success: true,
      output: result.output,
      stats: {
        steps: result.steps,
        elapsed_ms: elapsed,
        lines: result.output.length,
      },
    });
  } catch (err) {
    const elapsed = Date.now() - startTime;
    const isLtlError = err instanceof LateralusError;

    return jsonResp({
      success: false,
      error: {
        type: isLtlError ? 'LateralusError' : 'InternalError',
        message: isLtlError ? err.message : 'Internal execution error',
      },
      output: [],
      stats: { elapsed_ms: elapsed },
    }, isLtlError ? 200 : 500);
  }
}

export async function onRequestGet() {
  return jsonResp({
    endpoint: '/api/run',
    method: 'POST',
    description: 'Execute Lateralus code in a sandboxed environment',
    body: { code: 'string — Lateralus source code' },
    limits: {
      max_code_size: '32KB',
      max_output_lines: MAX_OUTPUT_LINES,
      max_output_bytes: MAX_OUTPUT_BYTES + ' bytes',
      max_steps: MAX_STEPS,
      rate_limit: RATE_LIMIT + ' requests/minute',
    },
    example: {
      code: 'let nums = [1, 2, 3, 4, 5]\nnums |> map(|x| x * x) |> filter(|x| x > 5) |> println()',
    },
  }, 200);
}

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: { ...SEC, 'Access-Control-Max-Age': '86400' } });
}
export async function onRequestPut() { return jsonResp({ error: 'Method not allowed' }, 405); }
export async function onRequestDelete() { return jsonResp({ error: 'Method not allowed' }, 405); }
