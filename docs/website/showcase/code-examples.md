# Lateralus Code Examples for Showcasing

## 1. The "Wow" One-Liner
```lateralus
// Count words in a file
read_file("book.txt") |> words() |> frequencies() |> top(10) |> println()
```

## 2. Real-World Data Pipeline
```lateralus
// ETL pipeline for log analysis
fn analyze_logs(date: Date) -> Report {
    glob("/var/log/app/*.log")
        |> flat_map(read_lines)
        |> filter(l -> l.date == date)
        |> map(parse_log_entry)
        |> partition(e -> e.level)
        |> {
            errors:   .errors   |> group_by(e -> e.source),
            warnings: .warnings |> count(),
            info:     .info     |> sample(100)
        }
        |> Report.new()
}
```

## 3. Async Web Scraper (Impressive)
```lateralus
async fn scrape_all(urls: [str]) -> [Article] {
    urls
        |> map(|url| async {
            fetch(url)
                |> await
                |> html.parse()
                |> extract_article()
        })
        |> await_all(concurrency: 10)
        |> filter(a -> a.word_count > 500)
        |> sort_by(a -> a.published_date)
}

// Usage
let articles = scrape_all(news_feeds) |> await
articles |> take(5) |> each(print_summary)
```

## 4. Pattern Matching Magic
```lateralus
enum Shape {
    Circle { radius: f64 }
    Rectangle { width: f64, height: f64 }
    Triangle { base: f64, height: f64 }
}

fn area(shape: Shape) -> f64 {
    match shape {
        Circle { radius }            => PI * radius * radius
        Rectangle { width, height }  => width * height
        Triangle { base, height }    => 0.5 * base * height
    }
}

// Exhaustive — compiler catches missing cases!
```

## 5. CLI Tool (Complete Program)
```lateralus
// A complete CLI tool in 25 lines
import cli { Command, Arg }
import fs
import json

fn main() {
    Command.new("jq-lite")
        .about("Query JSON files")
        .arg(Arg.new("file").required())
        .arg(Arg.new("query").required())
        .run(|args| {
            let data = args.file
                |> read_file()
                |> json.parse()
            
            args.query
                |> parse_query()
                |> apply(data)
                |> json.pretty()
                |> println()
        })
}
```

## 6. Struct with Methods
```lateralus
struct User {
    name: str
    email: str
    active: bool
    created_at: DateTime
}

impl User {
    fn new(name: str, email: str) -> User {
        User { name, email, active: true, created_at: DateTime.now() }
    }
    
    fn greet(self) -> str {
        "Hello, {self.name}!"
    }
    
    fn with_email(self, email: str) -> User {
        User { ...self, email }  // Spread operator
    }
}

// Usage
let user = User.new("Alice", "alice@example.com")
user.greet() |> println()  // Hello, Alice!
```

## 7. Error Handling (Result Type)
```lateralus
fn divide(a: f64, b: f64) -> Result<f64, str> {
    if b == 0.0 {
        Err("Division by zero")
    } else {
        Ok(a / b)
    }
}

fn calculate(values: [f64]) -> Result<f64, str> {
    values
        |> windows(2)
        |> map(|[a, b]| divide(a, b))
        |> collect_results()  // Fails fast on first error
        |> map(sum)
}

// Or use ? operator
fn safe_calc(a: f64, b: f64) -> Result<f64, str> {
    let x = divide(a, b)?
    let y = divide(x, 2.0)?
    Ok(y * 10.0)
}
```

## 8. Concurrency with Channels
```lateralus
fn parallel_process(items: [Item]) -> [Result] {
    let (tx, rx) = channel()
    
    // Spawn workers
    for i in 0..NUM_WORKERS {
        spawn(|| {
            for item in rx {
                process(item) |> tx.send()
            }
        })
    }
    
    // Send work
    items |> each(tx.send)
    tx.close()
    
    // Collect results
    rx |> collect()
}
```

## 9. HTTP Server with Routing
```lateralus
import net.http { Server, Router, json, html }
import db

fn main() {
    let router = Router.new()
        .get("/", |_| html(read_file("index.html")))
        .get("/api/users", |_| {
            db.query("SELECT * FROM users")
                |> json()
        })
        .post("/api/users", |req| {
            req.body
                |> json.parse::<CreateUser>()
                |> validate()
                |> db.insert("users")
                |> json()
        })
        .middleware(cors)
        .middleware(logger)
    
    Server.new()
        .bind("0.0.0.0:8080")
        .serve(router)
}
```

## 10. Macro for DSL
```lateralus
// Define a DSL for SQL queries
macro sql {
    (SELECT $cols:expr FROM $table:ident WHERE $cond:expr) => {
        Query.new()
            .select($cols)
            .from(stringify!($table))
            .where($cond)
    }
}

// Usage
let users = sql!(SELECT [name, email] FROM users WHERE active == true)
    |> db.execute()
    |> collect()
```

## 11. Testing Built-In
```lateralus
#[test]
fn test_pipeline_operations() {
    let result = [1, 2, 3, 4, 5]
        |> filter(n -> n % 2 == 0)
        |> map(n -> n * 2)
        |> sum()
    
    assert_eq(result, 12)
}

#[test]
fn test_user_creation() {
    let user = User.new("Test", "test@example.com")
    
    assert(user.active)
    assert_eq(user.name, "Test")
}

// Run with: lateralus test
```

## 12. The "LateralusOS" Teaser
```lateralus
// Yes, there's an OS written in Lateralus
// https://lateralus.dev/os/

fn kernel_main() {
    console.clear()
    console.println("LateralusOS v0.1.0")
    console.println("================")
    
    // Initialize subsystems
    [memory, interrupts, scheduler, filesystem]
        |> each(|sys| {
            sys.init() |> expect("Failed to init {sys.name}")
            console.println("[OK] {sys.name}")
        })
    
    // Start shell
    shell.run()
}
```
