# Lateralus Social Media Posts

## Twitter/X Thread

### Tweet 1 (Hook)
```
🌀 What if your code read like a story?

users |> filter(active) |> map(name) |> sort() |> take(5)

No nesting. No callbacks. Just data flowing left to right.

Meet Lateralus — a language that spirals outward.

�� Thread:
```

### Tweet 2 (Problem)
```
The problem with modern languages:

• Python: Expressive but slow, types are lies
• Rust: Fast but compile times are brutal
• Go: Simple but verbose as hell
• TypeScript: Better, but still JavaScript underneath

What if we didn't have to choose?
```

### Tweet 3 (Solution)
```
Lateralus gives you:

✅ Pipeline operators (|>) baked in
✅ Type inference (no annotations 90% of time)
✅ Pattern matching with exhaustiveness
✅ Compiles to native via LLVM
✅ Sub-2-second builds
✅ Zero runtime dependencies

The sweet spot between expressiveness and speed.
```

### Tweet 4 (Code Comparison)
```
Nested function calls (JS):
take(sort(filter(map(users, getName), isActive)))

vs

Pipeline flow (Lateralus):
users |> map(get_name) |> filter(active) |> sort() |> take(5)

Same result. One is readable.
```

### Tweet 5 (Real World)
```
A real HTTP server in Lateralus:

serve(":8080", {
    "/api/users" => |req| {
        db.query("SELECT * FROM users")
            |> filter(active)
            |> json()
    }
})

12 lines. Type safe. Fast.
```

### Tweet 6 (CTA)
```
Get started in 30 seconds:

pip install lateralus-lang
echo 'fn main() { "Hello" |> println() }' > hello.ltl
lateralus run hello.ltl

📚 Docs: lateralus.dev
💻 GitHub: github.com/bad-antics/lateralus-lang
▶️ Try it now: lateralus.dev/playground
```

---

## Reddit Post (r/ProgrammingLanguages)

### Title
**Lateralus: A pipeline-first language with Rust's safety and Python's expressiveness**

### Body
```markdown
Hey r/ProgrammingLanguages!

I've been working on Lateralus for the past few years, and I'd love to get feedback from this community.

**The core idea**: What if pipelines weren't just an operator, but the foundation of how you think about data flow?

```lateralus
// Process a log file
read_file("/var/log/app.log")
    |> lines()
    |> filter(l -> l.contains("ERROR"))
    |> map(parse_log_entry)
    |> group_by(e -> e.level)
    |> to_report()
    |> save("errors.html")
```

**Key features:**
- Hindley-Milner type inference
- Algebraic data types + exhaustive pattern matching  
- Async/await with structured concurrency
- LLVM backend → native binaries
- Zero-dependency compiler (single binary)
- Ownership semantics (Rust-inspired, but simpler)

**What makes it different from Elixir/F#/etc?**
- Compiles to native code (not BEAM/CLR)
- Explicit ownership model
- No GC at runtime
- Built-in security tools (I come from a security research background)

**Try it:**
- Playground: https://lateralus.dev/playground/
- Install: `pip install lateralus-lang`
- Docs: https://lateralus.dev

I'm especially interested in:
- Syntax feedback
- Feature requests
- "Why not just use X?" questions (happy to discuss tradeoffs)

Thanks! 🌀
```

---

## Hacker News Show HN

### Title
```
Show HN: Lateralus – Pipeline-first programming language with Rust-like safety
```

### Body
```
I've been building Lateralus for the past few years as a side project that grew into something real.

The pitch: A language where data flows naturally left-to-right through pipelines, with type inference, pattern matching, and native compilation.

Quick example:

    users
        |> filter(u -> u.active)
        |> map(u -> u.email)
        |> unique()
        |> send_newsletter()

Technical details:
- Hindley-Milner type inference (like ML/Haskell)
- Compiles via LLVM to native code
- Ownership model inspired by Rust (but simpler)
- Sub-2-second incremental builds
- Single-binary compiler, no runtime deps

I use it for everything from CLI tools to a full web server (lateralus.dev is served by Lateralus code).

Try it: https://lateralus.dev/playground/

Source: https://github.com/bad-antics/lateralus-lang

Install: pip install lateralus-lang

Happy to answer questions about design decisions!
```

---

## LinkedIn Post

```
🚀 Excited to share Lateralus v3.0

After years of development, my programming language project has reached a milestone I'm proud of.

The idea: What if code read like a story? What if transformations flowed naturally from left to right?

// Process user data
users
    |> filter(active)
    |> map(extract_email)
    |> validate_all()
    |> send_welcome()

No nested function calls. No callback pyramids. Just data flowing through transformations.

Lateralus combines:
✅ Type inference (minimal annotations)
✅ Pattern matching
✅ Native compilation (LLVM)
✅ Memory safety without GC
✅ Fast builds (< 2 seconds)

Built for data engineers, security researchers, and anyone who's thought "there has to be a better way."

Try it free: lateralus.dev/playground

#programming #softwaredevelopment #opensource
```

---

## YouTube Video Script (100 Seconds of Lateralus)

```
[0:00 - Hook]
What if I told you there's a programming language where your code reads like a recipe? Where data flows left to right, just like you read?

[0:08 - Problem]
Every language makes you choose. Python is expressive but slow. Rust is fast but brutal to learn. Go is simple but verbose. TypeScript is... still JavaScript.

[0:18 - Solution]
Enter Lateralus. A compiled language with pipeline operators baked into its DNA.

[0:25 - Demo]
Look at this. Users, pipe to filter active, pipe to map names, pipe to sort, pipe to take five.

[Show code]
users |> filter(active) |> map(name) |> sort() |> take(5)

No nesting. No callbacks. Just flow.

[0:40 - Features]
You get type inference — the compiler figures out types 90% of the time. Pattern matching that's exhaustive — forget to handle a case? Won't compile. Compiles to native code via LLVM. No garbage collector. No VM.

[0:55 - Install]
pip install lateralus-lang. Write fn main, pipe hello to println. Run it. Done.

[1:05 - CTA]
Try the playground at lateralus.dev. Star it on GitHub. And remember: spiral out.

[1:12 - End card]
Bad-antics. Lateralus. Links in description.
```
