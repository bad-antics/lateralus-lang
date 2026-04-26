# Outreach Plan — Lateralus Distribution Channels

> Generated 2026-04-26 after the v3.2.0 multi-registry release.
> Purpose: maximise verified-publisher status and organic discovery.

---

## ✅ Currently published

| Registry | Package | Version | URL |
|---|---|---|---|
| PyPI | `lateralus-lang` | 3.2.0 | https://pypi.org/project/lateralus-lang/3.2.0/ |
| VS Marketplace | `lateralus.lateralus-lang` | 3.2.0 | https://marketplace.visualstudio.com/items?itemName=lateralus.lateralus-lang |
| Open VSX | `lateralus.lateralus-lang` | 3.2.0 | https://open-vsx.org/extension/lateralus/lateralus-lang |
| GHCR | `bad-antics/lateralus-lang` | 3.2.0 | https://github.com/bad-antics/lateralus-lang/pkgs/container/lateralus-lang |
| npm (grammar) | `lateralus-grammar` | 2.4.0 | https://www.npmjs.com/package/lateralus-grammar |
| GitHub Releases | `lateralus-lang` | v3.2.0 | https://github.com/bad-antics/lateralus-lang/releases/tag/v3.2.0 |

---

## 🔵 Verified-publisher / trust badges

### 1. VS Marketplace verified publisher (5 min)

Adds a ✓ checkmark next to the publisher name. Requires DNS proof of `lateralus.dev`.

1. Go to https://marketplace.visualstudio.com/manage/publishers/lateralus
2. Click "Verify Domain"
3. Marketplace gives you a TXT record like:
   ```
   Name:  _vsce.lateralus.dev   (or root @, depending on the prompt)
   Type:  TXT
   Value: vsce-domain-verification=<token>
   ```
4. Add the record at your DNS provider for `lateralus.dev`
5. Click "Verify" in the Marketplace UI
6. Propagation: usually <10 min, sometimes up to an hour

### 2. PyPI Trusted Publisher (3 min, no token rotation again)

1. https://pypi.org/manage/project/lateralus-lang/settings/publishing/
2. "Add a new pending publisher" → GitHub
3. Fill in:
   - PyPI Project Name: `lateralus-lang`
   - Owner: `bad-antics`
   - Repository: `lateralus-lang`
   - Workflow: `release.yml`
   - Environment: `pypi` (recommended for two-step approval)
4. Save
5. Existing `release.yml` already uses OIDC (`id-token: write`) so it just works

### 3. npm provenance (set up once, free verified badge)

For `lateralus-grammar` and any future npm packages, add to the publish workflow:
```yaml
- run: npm publish --provenance --access public
  env:
    NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```
Requires:
- `permissions: { id-token: write, contents: read }` on the job
- The repo set as the package's `repository` field in `package.json` (already correct)

### 4. Sigstore signing for GHCR images

Already wired up in `.github/workflows/container.yml` — fires automatically on tag pushes via cosign keyless OIDC.

---

## 📋 Awesome-list PRs (10 min each, batch them)

Submit one PR per list. Same template, slightly tailored bullet:

### Awesome lists to target

| List | Repo | Section | Priority |
|---|---|---|---|
| Awesome Programming Languages | aalhour/awesome-programming-languages | Statically Typed → New | P0 |
| Awesome Compilers | aalhour/awesome-compilers | Compilers built in | P0 |
| Awesome OS Dev | jubalh/awesome-os | Educational kernels | P1 (for LateralusOS) |
| Awesome Python | vinta/awesome-python | Distribution | P2 (since pip-installable) |
| Awesome WASM | mbasso/awesome-wasm | Languages compiling to WASM | P1 |
| Awesome LSP | autozimu/Awesome-LSP | Language servers | P2 |

### PR template

```markdown
## Add Lateralus

[Lateralus](https://lateralus.dev) is a statically-typed, pipeline-native programming language with Hindley–Milner inference, ADTs, and four compilation backends (C99, JavaScript, WebAssembly, Python).

- Repo: https://github.com/bad-antics/lateralus-lang
- Docs: https://lateralus.dev
- Released: 3+ years of public development, currently v3.2.0 (April 2026)
- Notable: ships with `LateralusOS`, a bare-metal companion OS written in the language

Suggested entry (alphabetical):

\`\`\`markdown
- [Lateralus](https://github.com/bad-antics/lateralus-lang) - Pipeline-native statically-typed language with multi-target codegen (C99/JS/WASM) and a companion OS.
\`\`\`
```

---

## 📝 Blog/article syndication

You have ~20 high-quality posts in `docs/blog/`. Cross-post the best to each platform with `<link rel="canonical">` pointing back to lateralus.dev. Suggested top 5 to syndicate first:

1. `pipelines-deep-dive.ltlml` → dev.to, Hashnode, r/ProgrammingLanguages
2. `building-lateralusos.ltlml` → dev.to, Lobste.rs (`os` tag), r/osdev
3. `designing-the-vm.ltlml` → dev.to, Lobste.rs (`compsci` tag), r/Compilers
4. `lateralus-on-bare-metal.ltlml` → r/osdev, Lobste.rs
5. `match-expressions-deep-dive.ltlml` → dev.to, r/ProgrammingLanguages

### Platforms

| Platform | URL | Setup | Notes |
|---|---|---|---|
| dev.to | dev.to/new | GitHub OAuth | Supports canonical URL header |
| Hashnode | hashnode.com/draft | GitHub OAuth | Has its own SEO authority |
| Medium | medium.com/new-story | Email | Lower compiler audience |
| Substack | substack.com | Email | "Lateralus Weekly" newsletter |
| Lobste.rs | lobste.rs | **Invite required** — DM @pushcx, @jcs, or post to /~tags/inviting | Higher signal than HN |
| r/ProgrammingLanguages | reddit.com/r/ProgrammingLanguages | reddit account | Welcoming to new langs, expect feedback |
| r/osdev | reddit.com/r/osdev | reddit account | LateralusOS angle |
| r/Compilers | reddit.com/r/Compilers | reddit account | Implementation posts |
| Hacker Newsletter | hackernewsletter.com | Auto-curated from HN | Free if you make front page |
| TLDR Newsletter | tldrnewsletter.com/submit | Free submission | ~250k devs |
| Console.dev | console.dev/contact | Email pitch | "Tool of the week" slot, dev-focused |
| Pointer.io | pointer.io/contact | Email pitch | Curated dev reading |
| Changelog podcast | changelog.com/contact | Email pitch | Aim for after the HN spike |

---

## 🎤 Conferences & talks

| Event | Format | Deadline | Notes |
|---|---|---|---|
| !!Con (next year) | 10-min lightning | spring | "I made an OS in a language I made!!" — perfect fit |
| LangDev meetup | Discord demo | monthly | Low friction, recorded |
| PWLConf | technical talk | varies | Strange Loop's spiritual successor |
| PLDI/POPL/ICFP | research paper | annual | Pull from your `docs/papers/` corpus |
| Compiler Construction (CC) | research paper | annual | Easier acceptance bar than POPL |

---

## 🔍 Discovery signal boosters

- **GitHub topics**: ensure every `bad-antics/*` repo with `.ltl` carries `programming-language`, `compiler`, `pipeline`, `lsp`, `wasm`, `osdev` (where applicable)
- **Linguist PR**: blocked on the 200-repo bar (current: 77). The 30 satellite repos in `seed-repos/manifest.yml` will close most of that gap.
- **Compiler Explorer (godbolt.org)**: submit a PR adding `lateralus` as a language. High prestige signal, viral with compiler nerds.
- **Rosetta Code**: add a Lateralus page. Solve 20–30 tasks. Each task = a backlink + SEO juice.
- **try.lateralus.dev**: a code-server instance with the Open VSX extension preinstalled. One-click "try in browser."
- **WebAssembly playground**: at lateralus.dev/play. Highest single conversion-to-trial lever.
- **Jupyter kernel for `.ltlnb`**: gets you listed on jupyter.org/try.

---

## 🚀 Show HN posting day (Tue/Wed)

1. **8:30am ET** — final smoke test: install on a fresh VM (homepage, pip install, vsce install, docker run)
2. **9:00–11:00am ET** — submit to HN, **don't share the link anywhere yet**
3. **+0–4 hours** — babysit comments, reply to everyone, especially critical ones
4. **+4 hours** — if alive, cross-post to r/ProgrammingLanguages with a different framing
5. **+24 hours** — if dead, email `hn@ycombinator.com` for second-chance pool consideration
6. **+1 week** — Lobste.rs (if invited)
7. **+2 weeks min** — only then post the next Show HN (GrugBot420)

---

## ⏭️ Action items right now

- [ ] DNS TXT for VS Marketplace verification
- [ ] PyPI Trusted Publisher form
- [ ] Make GHCR container public via web UI: https://github.com/users/bad-antics/packages/container/lateralus-lang/settings
- [ ] Submit awesome-list PRs (batch of 4)
- [ ] Cross-post pipelines-deep-dive to dev.to + Hashnode
- [ ] Linguist PR (blocked on 200-repo gate; finish satellite repos first)
- [ ] Apply final critique to SHOW_HN_DRAFTS (largely done)
