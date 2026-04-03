.PHONY: test test-all test-core test-engines test-tools test-c-backend lint format check bench health clean install release release-dry-run package

# ─── Installation ──────────────────────────────────────────────────────

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

# ─── Testing ───────────────────────────────────────────────────────────

test:
	pytest tests/ -v --tb=short

test-all:
	python scripts/run_all_tests.py --suite all_new -v

test-core:
	pytest tests/ -v --tb=short -k "not engine and not crypto and not markup and not bytecode"

test-engines:
	python scripts/run_all_tests.py --suite all_engines

test-tools:
	python scripts/run_all_tests.py --suite tools

test-science:
	pytest tests/test_science.py -v

test-math:
	pytest tests/test_math_engine.py -v

test-types:
	pytest tests/test_type_system.py -v

test-c-backend:
	pytest tests/test_c_backend.py -v --tb=short

# ─── Code Quality ─────────────────────────────────────────────────────

lint:
	python -m lateralus_lang.linter stdlib/ --strict

format:
	python -m lateralus_lang.formatter stdlib/

check:
	python -m lateralus_lang check examples/*.ltl

# ─── Benchmarks ────────────────────────────────────────────────────────

bench:
	python -m lateralus_lang.bench --suite math --iterations 100

bench-all:
	python -m lateralus_lang.bench --suite math --iterations 50
	python -m lateralus_lang.bench --suite crypto --iterations 50
	python -m lateralus_lang.bench --suite types --iterations 50

bench-json:
	python -m lateralus_lang.bench --suite math --iterations 100 --json > benchmark_results.json

# ─── Health ────────────────────────────────────────────────────────────

health:
	python scripts/health_check.py

# ─── Examples ──────────────────────────────────────────────────────────

run-examples:
	@echo "Running LATERALUS examples..."
	python -m lateralus_lang run examples/math_demo.ltl
	python -m lateralus_lang run examples/graph_demo.ltl
	python -m lateralus_lang run examples/statistics_demo.ltl

# ─── Documentation ────────────────────────────────────────────────────

docs:
	@echo "Building documentation..."
	python -c "from lateralus_lang.markup import compile_ltlml_file; \
		import glob; \
		[compile_ltlml_file(f) for f in glob.glob('docs/**/*.ltlml', recursive=True)]"

# ─── Package Management ───────────────────────────────────────────────

pkg-init:
	python -m lateralus_lang.package_manager init $(name)

# ─── VS Code Extension ────────────────────────────────────────────────

vscode-install:
	@echo "Installing Lateralus VS Code extension..."
	@rm -rf ~/.vscode/extensions/lateralus-lang.lateralus-1.5.0
	@cp -r vscode-lateralus ~/.vscode/extensions/lateralus-lang.lateralus-1.5.0
	@echo "Done. Reload VS Code (Ctrl+Shift+P → Developer: Reload Window)"

vscode-link:
	@echo "Symlinking Lateralus VS Code extension (dev mode)..."
	@rm -f ~/.vscode/extensions/lateralus-lang.lateralus-1.5.0
	@ln -s $(PWD)/vscode-lateralus ~/.vscode/extensions/lateralus-lang.lateralus-1.5.0
	@echo "Done. Reload VS Code (Ctrl+Shift+P → Developer: Reload Window)"

vscode-uninstall:
	@rm -rf ~/.vscode/extensions/lateralus-lang.lateralus-1.5.0
	@echo "Extension removed."

# ─── Clean ─────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.ltlc" -delete 2>/dev/null || true
	rm -rf .pytest_cache build dist *.egg-info
	rm -f benchmark_results.json

# ─── Version ───────────────────────────────────────────────────────────

version:
	python -m lateralus_lang --version

# ─── REPL ──────────────────────────────────────────────────────────────

repl:
	python -m lateralus_lang repl

# ─── Release ───────────────────────────────────────────────────────────

release:
	bash scripts/release.sh

release-dry-run:
	bash scripts/release.sh --dry-run

# ─── Package (for testers) ────────────────────────────────────────────

package:
	bash scripts/build_package.sh
