.DEFAULT_GOAL := help

## [For users] Setup and installation
.PHONY: install
install: ## Install Python dependencies
	pip install -r requirements.txt

## [For users] Start the server
.PHONY: main
main: ## Run the main server
	python app.py 

.PHONY: vm-server
vm-server: ## Run the server for a VM (Runpod or similar)
	python app.py --host 0.0.0.0 --port 8000

## [For users] Start an Audio AI service from the 'models' directory, with its own venv
.PHONY: chatterbox-service
chatterbox-service: ## Start the chatterbox service
	python run_model.py chatterbox

.PHONY: dia-service
dia-service: ## Start the dia service
	python run_model.py dia

.PHONY: higgs-service
higgs-service: ## Start the higgs service
	python run_model.py higgs

.PHONY: vibevoice-service
vibevoice-service: ## Start the vibevoice service
	python run_model.py vibevoice

.PHONY: vibevoice-large-service
vibevoice-large-service: ## Start the vibevoice large (7B) service
	python run_model.py vibevoice --large

## [For developers] Run locally with hot reload

.PHONY: local
local: ## Run the backend server in development mode with hot reload
	python app.py --dev

.PHONY: local-testing-ui
local-testing-ui: ## Run the backend server with TESTING_UI=true for UI testing without GPU 
	TESTING_UI=true python app.py --dev

.PHONY: mock-service
mock-service: ## Start the mock service
	python run_model.py mock 

.PHONY: mock-service-fast
mock-service-fast: ## Start the mock service, with a faster delay (used in `make test`)
	python run_model.py mock --fast-delay

## [For developers] Frontend
.PHONY: frontend
frontend: ## Start the frontend development server with live reloading
	cd frontend && REACT_APP_API_URL='http://localhost:8000' npm start && cd .. 

.PHONY: frontend-build
frontend-build: ## Build the frontend, which is served in `make main`
	cd frontend && REACT_APP_API_URL='no_port' npm run build && cd .. 

.PHONY: generate-ts-types
generate-ts-types: ## Generate TypeScript types from backend OpenAPI schema
	# Note: have to use npx, otherwise dependency issues.
	npx openapi-typescript http://localhost:8000/openapi.json -o frontend/src/types/backendTypes.ts

## [For developers] Testing
.PHONY: test
test: ## Run the fast tests
	@if lsof -i:8999 -t >/dev/null 2>&1; then echo "Port 8999 is in use, cancelling test"; exit 1; fi
	@if lsof -i:8001 -t >/dev/null 2>&1; then echo "Port 8001 is in use, cancelling test"; exit 1; fi
	@if lsof -i:8000 -t >/dev/null 2>&1; then echo "Port 8000 is in use, cancelling test"; exit 1; fi
	@echo "Starting mock service for concurrency test..."
	@setsid python run_model.py mock --delay=3 & echo $$! > /tmp/mock_service_pid
	@sleep 2
	@echo "Running concurrency test..."
	@TESTING=true python -m pytest /home/nick/Documents/aai-studio/backend/core/tests/test_concurrency.py -v --tb=short; \
	CONCURRENCY_EXIT_CODE=$$?; \
	kill -TERM -`cat /tmp/mock_service_pid` 2>/dev/null || true; \
	rm -f /tmp/mock_service_pid; \
	if [ $$CONCURRENCY_EXIT_CODE -ne 0 ]; then exit $$CONCURRENCY_EXIT_CODE; fi
	@echo "Stopping first mock service..."
	@sleep 1
	@echo "Starting fast mock service..."
	@setsid python run_model.py mock --fast-delay & echo $$! > /tmp/mock_service_fast_pid
	@sleep 2
	@echo "Running remaining tests..."
	@TESTING=true python -m pytest backend/core/tests/ -v --tb=short --ignore=/home/nick/Documents/aai-studio/backend/core/tests/test_concurrency.py; \
	REMAINING_EXIT_CODE=$$?; \
	kill -TERM -`cat /tmp/mock_service_fast_pid` 2>/dev/null || true; \
	rm -f /tmp/mock_service_fast_pid; \
	if [ $$REMAINING_EXIT_CODE -ne 0 ]; then exit $$REMAINING_EXIT_CODE; fi
	@echo "Stopping fast mock service..."
	@echo "All tests completed successfully!"

## [For developers] LAN debugging. Useful if running on unix but debugging windows
LAN_IP = $(shell ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+' || hostname -I | awk '{print $$1}' || echo "127.0.0.1")

.PHONY: local-expose-host
local-expose-host: ## Expose the backend server for LAN access + debugging
	@echo "🔧 Starting backend server exposed to LAN..."
	echo "🌐 Backend will be available at: http://$(LAN_IP):8000"; \
	echo "⚠️  SECURITY WARNING: Server is exposed to your local network!"; \
	echo "   - Only run this on trusted networks"; \
	echo "   - Stop the server when done debugging"; \
	echo "   - Consider using 'make local' for localhost-only development"; \
	echo ""; \
	python app.py --dev --host 0.0.0.0 --port 8000

.PHONY: main-expose-host
main-expose-host: ## Builds frontend with LAN IP and runs the main server in non-dev mode
	@REACT_APP_API_URL="http://$(LAN_IP):8000" make frontend-build && python app.py --host 0.0.0.0 --port 8000

.PHONY: frontend-expose-host
frontend-expose-host: ## Expose the frontend for LAN access + debugging
	@cd frontend && HOST=0.0.0.0 REACT_APP_API_URL="http://$(LAN_IP):8000" npm start

.PHONY: expose-help
expose-help: ## Show instructions for LAN debugging
	@echo "LAN Debugging Setup Instructions:"; \
	echo ""; \
	echo "1. Set up firewall:"; \
	echo "   sudo ufw allow 8000"; \
	echo "   sudo ufw allow 3000"; \
	echo "2. Terminal 1: make local-expose-host"; \
	echo "3. Terminal 2: make frontend-expose-host"; \
	echo "4. From Windows: visit http://$(LAN_IP):3000"; \
	echo ""; \
	echo "Alternative:"; \
	echo "1. make main-expose-host (builds frontend with LAN IP)"; \
	echo "2. From Windows: visit http://$(LAN_IP):8000"; \
	echo ""; \
	echo "⚠️  Remember to stop all servers when done!"

## Help
.PHONY: help
help: ## Show this help message. Also runs if you just run 'make' on its own
	@echo ""
	@echo "\033[1mBookForge Studio - Available Commands\033[0m"
	@echo ""
	@echo "(All commands prefixed with 'make', for example 'make local')"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@awk 'BEGIN { \
		FS = ":.*?## "; \
		section = ""; \
		in_section = 0; \
		commands_printed = 0; \
	} \
	/^##[^#]/ { \
		if (commands_printed > 0) print ""; \
		section = substr($$0, 4); \
		gsub(/^[ \t]+|[ \t]+$$/, "", section); \
		print "\033[1;34m" section "\033[0m"; \
		underline = ""; \
		for (i = 1; i <= length(section) + 4; i++) underline = underline "─"; \
		print "\033[34m" underline "\033[0m"; \
		in_section = 1; \
		next; \
	} \
	/^[a-zA-Z_][a-zA-Z0-9_-]*:.*##/ { \
		if (!in_section) { \
			print "\033[1;34mGeneral Commands\033[0m"; \
			print "\033[34m────────────────────\033[0m"; \
			in_section = 1; \
		} \
		printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2; \
		commands_printed++; \
	}' $(MAKEFILE_LIST)
	@echo ""