# Shunting-Yard Algorithm Tutorial: Infix to Postfix Parsing and RPN Evaluation

## Overview

Parsing mathematical and boolean expressions is one of the foundational challenges of compiler frontend and interpreter design. While human mathematical notation is predominantly **infix** (where operators sit between operands, e.g. $3 + 4 \times 2$), evaluating infix expressions directly requires tracking operator precedence, left/right associativity, and nested parentheses.

In 1961, Edsger W. Dijkstra invented the **Shunting-Yard algorithm** (named for its operational resemblance to a railroad shunting yard). The algorithm converts infix mathematical expressions into **postfix notation** (also called **Reverse Polish Notation**, or **RPN**).

In compiler construction and formula evaluation engines, Shunting-Yard provides:
- **Recursive-Free Parsing**: Translates complex nested arithmetic into linear token streams without requiring full recursive-descent grammar machinery.
- **Stack-Machine Bytecode Compilation**: Postfix RPN maps directly to virtual machine bytecode instructions (e.g. `PUSH 3`, `PUSH 4`, `PUSH 2`, `MUL`, `ADD`).
- **Spreadsheet and Rule Engines**: Evaluating dynamic user formulas (e.g. in financial models and SQL expression filters).

---

## Algorithm Mechanics

The Shunting-Yard algorithm processes an infix token stream from left to right using two primary structures:
1. **Output Queue**: Stores the generated postfix RPN tokens.
2. **Operator Stack**: Temporarily holds operators and open parentheses waiting for higher-precedence subexpressions to resolve.

### Precedence and Associativity Rules

Standard arithmetic operator hierarchy:
- Multiplication `*` and Division `/`: Precedence 2 (left-associative)
- Addition `+` and Subtraction `-`: Precedence 1 (left-associative)

### State Transitions

For each incoming token:
1. **Operand (Number)**: Immediately append to the output queue.
2. **Operator $O_1$**:
   - While the operator stack is non-empty, and its top operator $O_2$ has $\text{precedence}(O_2) \ge \text{precedence}(O_1)$, pop $O_2$ to the output queue.
   - Push $O_1$ onto the operator stack.
3. **Left Parenthesis `(`**: Push onto the operator stack.
4. **Right Parenthesis `)`**:
   - Pop operators from the stack to the output queue until a matching `(` is encountered.
   - Discard the `(`.
5. **End of Input**: Pop all remaining operators from the stack to the output queue.

### Postfix (RPN) Evaluation

Evaluating the output RPN stream takes linear $O(n)$ time:
- Iterate through tokens.
- If operand: push onto evaluation stack.
- If binary operator: pop operand $b$, pop operand $a$, apply operation $a \text{ op } b$, and push the result back onto the stack.
- The final value on the stack is the expression result.

---

## Lateralus Implementation

```lateralus
fn get_precedence(op: str) -> int {
    if op == "+" || op == "-" {
        return 1;
    }
    if op == "*" || op == "/" {
        return 2;
    }
    return 0;
}

fn is_operator(token: str) -> bool {
    if token == "+" || token == "-" || token == "*" || token == "/" {
        return true;
    }
    return false;
}

fn shunting_yard(tokens: list) -> list {
    let mut output = [];
    let mut op_stack = [];
    let mut i = 0;
    while i < len(tokens) {
        let tok = tokens[i];
        if is_operator(tok) {
            let mut prec = get_precedence(tok);
            let mut searching = true;
            while len(op_stack) > 0 && searching {
                let top_op = op_stack[len(op_stack) - 1];
                if is_operator(top_op) && get_precedence(top_op) >= prec {
                    output = output + [top_op];
                    op_stack = slice(op_stack, 0, len(op_stack) - 1);
                } else {
                    searching = false;
                }
            }
            op_stack = op_stack + [tok];
        } else {
            if tok == "(" {
                op_stack = op_stack + [tok];
            } else {
                if tok == ")" {
                    let mut found_paren = false;
                    while len(op_stack) > 0 && found_paren == false {
                        let top_op = op_stack[len(op_stack) - 1];
                        op_stack = slice(op_stack, 0, len(op_stack) - 1);
                        if top_op == "(" {
                            found_paren = true;
                        } else {
                            output = output + [top_op];
                        }
                    }
                } else {
                    output = output + [tok];
                }
            }
        }
        i = i + 1;
    }

    while len(op_stack) > 0 {
        let top_op = op_stack[len(op_stack) - 1];
        op_stack = slice(op_stack, 0, len(op_stack) - 1);
        if top_op != "(" && top_op != ")" {
            output = output + [top_op];
        }
    }

    return output;
}

fn rpn_eval(postfix: list) -> int {
    let mut val_stack = [];
    let mut i = 0;
    while i < len(postfix) {
        let tok = postfix[i];
        if is_operator(tok) {
            let n = len(val_stack);
            let b = val_stack[n - 1];
            let a = val_stack[n - 2];
            val_stack = slice(val_stack, 0, n - 2);

            let mut res = 0;
            if tok == "+" {
                res = a + b;
            } else {
                if tok == "-" {
                    res = a - b;
                } else {
                    if tok == "*" {
                        res = a * b;
                    } else {
                        if tok == "/" {
                            res = idiv(a, b);
                        }
                    }
                }
            }
            val_stack = val_stack + [res];
        } else {
            val_stack = val_stack + [to_int(tok)];
        }
        i = i + 1;
    }
    return val_stack[0];
}
```

---

## Verifying Golden Test Vectors

The test suite in `tests/stdlib_shunting_yard_tutorial.ltl` validates:

1. **Operator Precedence**:
   - `3 + 4 * 2` converts to postfix `3 4 2 * +` and evaluates to 11.
2. **Explicit Parentheses Precedence Overriding**:
   - `(3 + 4) * 2` converts to postfix `3 4 + 2 *` and evaluates to 14.
3. **Left-Associative Operations**:
   - Subtraction chain `10 - 4 - 2` evaluates to 4 (verifying $(10-4)-2$, not $10-(4-2)=8$).
4. **Deeply Nested Expressions**:
   - `((2 + 3) * (4 - 1)) / 5` evaluates to 3.
5. **Single-Operand Base Case**:
   - Single number `"42"` evaluates directly to 42.

Run verification suite:

```bash
python -m lateralus_lang check tests/stdlib_shunting_yard_tutorial.ltl
python -m lateralus_lang check examples/shunting_yard_tutorial.ltl
pytest tests/test_compiler.py
```
