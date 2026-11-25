import pytest
from lateralus_lang.compiler import Compiler, Target

c = Compiler()

def test_tutorial_hello_world():
    code = """
import io

fn main() {
    let greeting = "Hello, Lateralus!"
    io.println(greeting)
}

main()
"""
    res = c.compile_source(code, target=Target.PYTHON, filename="test_hello.ltl")
    assert res.ok, f"Compile error: {res.errors}"
    exec_globals = {}
    exec(res.python_src, exec_globals)

def test_tutorial_pipeline_operators():
    code = """
import io

fn square(x: int) -> int {
    return x * x
}

fn add_ten(x: int) -> int {
    return x + 10
}

fn main() {
    let result = 5 |> square |> add_ten
    let count = 10
    count |>= square
    count |>= add_ten
}

main()
"""
    res = c.compile_source(code, target=Target.PYTHON, filename="test_pipeline.ltl")
    assert res.ok, f"Compile error: {res.errors}"
    exec_globals = {}
    exec(res.python_src, exec_globals)

def test_tutorial_pattern_matching():
    code = """
fn describe_status(code: int) -> str {
    let desc = match code {
        200 => "200 OK: Request succeeded",
        404 => "404 Not Found: Resource missing",
        _   => "Unknown status code",
    }
    return desc
}

fn main() {
    let a = describe_status(200)
    let b = describe_status(404)
}

main()
"""
    res = c.compile_source(code, target=Target.PYTHON, filename="test_match.ltl")
    assert res.ok, f"Compile error: {res.errors}"
    exec_globals = {}
    exec(res.python_src, exec_globals)

def test_tutorial_structs():
    code = """
struct User {
    username: str
    active: bool
}

impl User {
    fn new(username: str) -> User {
        return User { username: username, active: true }
    }

    fn describe(self) -> str {
        return "User: " + self.username
    }
}

fn main() {
    let user = User.new("alice")
}

main()
"""
    res = c.compile_source(code, target=Target.PYTHON, filename="test_structs.ltl")
    assert res.ok, f"Compile error: {res.errors}"
    exec_globals = {}
    exec(res.python_src, exec_globals)

def test_tutorial_cli_tool():
    code = """
fn clean_word(word: str) -> str {
    return str_trim(word)
}

fn count_words(text: str) -> int {
    let parts = str_split(text, " ")
    return len(parts)
}

fn main() {
    let input_text = "  lateralus makes data pipelines elegant and fast  "
    let total = input_text
        |> clean_word
        |> count_words
}

main()
"""
    res = c.compile_source(code, target=Target.PYTHON, filename="test_cli.ltl")
    assert res.ok, f"Compile error: {res.errors}"
    exec_globals = {}
    exec(res.python_src, exec_globals)
