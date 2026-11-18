# Getting Started with Lateralus in 10 Minutes

Welcome to **LATERALUS**! Lateralus is a modern, expressive programming language designed for data pipelines, robust type safety, and seamless polyglot interoperability.

This guide takes you from zero to running your first Lateralus programs in under 10 minutes.

---

## 1. Installation

Lateralus is distributed as a Python package and requires **Python 3.10+**.

Install the toolchain via `pip`:

```bash
pip install lateralus-lang
```

Verify your installation:

```bash
lateralus --version
```

You should see:
```text
Lateralus Language toolchain v3.2.0
```

---

## 2. Hello World

Let's write a classic first program. Create a file named `hello.ltl`:

```lateralus
// hello.ltl
import io

fn main() {
    let greeting = "Hello, Lateralus!"
    io.println(greeting)
}

main()
```

Run it using the Lateralus runner:

```bash
lateralus run hello.ltl
```

**Output:**
```text
Hello, Lateralus!
```

In Lateralus:
- Statements do not require semicolons.
- `let` declares local variables with optional type annotations (`let greeting: str = ...`).
- `import io` provides input/output functions such as `io.println()`.

---

## 3. Pipeline Operators (`|>` and `|>=`)

Lateralus treats data transformation as a first-class paradigm using pipeline operators.

### Forward Pipeline (`|>`)

The `|>` operator passes the result of the left-hand expression as the first argument to the right-hand function:

```lateralus
// pipeline.ltl
import io

fn square(x: int) -> int {
    return x * x
}

fn add_ten(x: int) -> int {
    return x + 10
}

fn main() {
    // 5 |> square |> add_ten is equivalent to add_ten(square(5))
    let result = 5 |> square |> add_ten
    io.println("Computed: " + str(result))
}

main()
```

**Output:**
```text
Computed: 35
```

### Pipeline Assignment (`|>=`)

The `|>=` operator updates a variable in-place by passing it through a pipeline transformation:

```lateralus
// pipeline_assign.ltl
import io

fn square(x: int) -> int {
    return x * x
}

fn add_ten(x: int) -> int {
    return x + 10
}

fn main() {
    let count = 10

    // In-place pipeline update (count = square(count))
    count |>= square
    count |>= add_ten

    io.println("Updated count: " + str(count))
}

main()
```

**Output:**
```text
Updated count: 110
```

---

## 4. Pattern Matching with `match`

Pattern matching in Lateralus provides exhaustive, expressive branch dispatch without messy `if-else` cascades.

```lateralus
// matching.ltl
import io

fn describe_status(code: int) -> str {
    let desc = match code {
        200 => "200 OK: Request succeeded",
        404 => "404 Not Found: Resource missing",
        500 => "500 Internal Error: Server failure",
        _   => "Unknown status code",
    }
    return desc
}

fn main() {
    io.println(describe_status(200))
    io.println(describe_status(404))
    io.println(describe_status(418))
}

main()
```

**Output:**
```text
200 OK: Request succeeded
404 Not Found: Resource missing
Unknown status code
```

---

## 5. Structs and Enums

Lateralus supports typed records (`struct`) with implementation blocks (`impl`), as well as algebraic enumerations (`enum`).

```lateralus
// models.ltl
import io

enum Role {
    Admin
    Member
    Guest
}

struct User {
    username: str
    active: bool
}

impl User {
    // Constructor function
    fn new(username: str) -> User {
        return User { username: username, active: true }
    }

    // Method with self receiver
    fn describe(self) -> str {
        return "User: " + self.username + " (Active: " + str(self.active) + ")"
    }
}

fn main() {
    let user = User.new("alice")
    io.println(user.describe())
}

main()
```

**Output:**
```text
User: alice (Active: True)
```

---

## 6. Building a Simple CLI Tool

Let's combine pipelines, functions, and string processing to build a word counter CLI tool:

```lateralus
// wordcount.ltl
import io

fn clean_word(word: str) -> str {
    return str_trim(word)
}

fn count_words(text: str) -> int {
    let parts = str_split(text, " ")
    return len(parts)
}

fn main() {
    let input_text = "  lateralus makes data pipelines elegant and fast  "
    
    // Process input data cleanly through pipeline
    let total = input_text
        |> clean_word
        |> count_words

    io.println("Input: '" + clean_word(input_text) + "'")
    io.println("Total word count: " + str(total))
}

main()
```

Run the CLI tool:

```bash
lateralus run wordcount.ltl
```

**Output:**
```text
Input: 'lateralus makes data pipelines elegant and fast'
Total word count: 7
```

---

## Next Steps

Now that you understand the core concepts:
- Explore the [Language Specification](../language-spec.ltlml) for comprehensive syntax rules.
- Review [Cookbook](../cookbook.ltlml) for real-world recipes across networking, data science, and web services.
- Check out the `examples/` directory for full applications built with Lateralus.
