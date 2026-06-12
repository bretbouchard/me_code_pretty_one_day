.PHONY: help train serve benchmark generate seed test format-data scrape clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:' Makefile | sed 's/://' | column -s:

train: ## Fine-tune model with MLX-LoRA (adapter-600, default 600 epochs)
	python scripts/train_lora.py --epochs 600 --adapter-path training/adapters-600

serve: ## Start Ollama serving (ensure model is created first)
	ollama run qwen2.5-coder:7b-instruct-q4_K_M

generate: ## Generate code with RAG (requires Ollama serving)
	python scripts/generate.py "$(PROMPT)" --domain python --verbose

generate-no-rag: ## Generate code without RAG
	python scripts/generate.py "$(PROMPT)" --no-rag --verbose

benchmark: ## Run all 3 benchmark suites
	@echo "=== HumanEval (2 problems) ==="
	python scripts/benchmark_humaneval.py --max-problems 2 --n-samples 2 --verbose
	@echo ""
	@echo "=== Latency ==="
	python scripts/benchmark-latency.py --variant all --iterations 3
	@echo ""
	@echo "=== Throughput ==="
	python scripts/benchmark-throughput.py --variant all --iterations 3

seed: ## Seed domain patterns into Confucius (15 patterns, 4 domains)
	python scripts/seed_patterns.py --domain all

test: ## Run all unit tests
	python -m pytest scripts/ -v -x -k "not integration"

test-integration: ## Run tests including Ollama integration
	python -m pytest scripts/ -v -x --run-integration

format-data: ## Prepare and validate training data (validate JSONL, fix formatting)
	python scripts/prepare_training_data.py

scrape: ## Scrape corpus from code repos
	python scripts/scrape_corpus.py --domains swift,python

clean: ## Remove cached files
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name ".pytest_cache" -type d -exec rm -rf {} +
