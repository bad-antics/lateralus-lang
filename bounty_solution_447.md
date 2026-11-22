2. Code Patch / Fix

**File: `lateralus_lang/ir.py`**
```python
# In the IROp enum, add:
PIPE_OPT = "PIPE_OPT"

# In visit_BinOp, update op_map:
op_map = {
    # ... existing mappings ...
    TK.PIPE_OPT: IROp.PIPE_OPT,
}
```

**File: `lateralus_lang/codegen/bytecode.py`**
```python
def emit_ir(self, instr: IRInstruction):
    if instr.op == IROp.PIPE_OPT:
        # Desugar: if left is nil -> nil, else call right(left)
        # Assuming standard bytecode opcodes for nil check and call
        self.emit(BC.NIL_CHECK, instr.left)
        self.emit(BC.JUMP_IF_NIL, "nil_label")
        self.emit(BC.CALL, instr.right, [instr.left])
        self.emit(BC.JUMP, "end_label")
        self.emit_label("nil_label")
        self.emit(BC.LOAD_NIL)
        self.emit_label("end_label")
    else:
        # ... existing logic ...
```

**File: `lateralus_lang/codegen/c.py`**
```python
def emit_ir(self, instr: IRInstruction):
    if instr.op == IROp.PIPE_OPT:
        # Desugar to C ternary or if-else
        self.emit(f"({self.emit_expr(instr.left)} == NULL ? NULL : {self.emit_expr(instr.right)}({self.emit_expr(instr.left)}))")
    else:
        # ... existing logic ...
```

**File: `lateralus_lang/codegen/wasm.py`**
```python
def emit_ir(self, instr: IRInstruction):
    if instr.op == IROp.PIPE_OPT:
        # Desugar to WASM if-else with call
        self.emit_expr(instr.left)
        self.emit("if")
        self.emit("call", instr.right)
        self.emit("else")
        self.emit("drop")
        self.emit("i32.const", 0) # nil representation
        self.emit("end")
    else:
        # ... existing logic ...
```