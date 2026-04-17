.PHONY: help venv install run test menu-test validate quickstart clean-runtime-dry clean-runtime

help:
	@echo "Cibles disponibles :"
	@echo "  make quickstart         - setup rapide dev"
	@echo "  make venv               - créer .venv"
	@echo "  make install            - installer requirements"
	@echo "  make run                - lancer l'application"
	@echo "  make test               - lancer pytest"
	@echo "  make menu-test          - lancer auto_menu_test.sh"
	@echo "  make validate           - validation complète"
	@echo "  make clean-runtime-dry  - aperçu nettoyage runtime"
	@echo "  make clean-runtime      - nettoyage runtime réel"

venv:
	python3 -m venv .venv

install:
	.venv/bin/pip install -r requirements.txt

run:
	.venv/bin/python -m ble_radar.app

test:
	.venv/bin/python -m pytest -q

menu-test:
	./auto_menu_test.sh

validate:
	./scripts/run_full_validation.sh

quickstart:
	./scripts/quickstart.sh

clean-runtime-dry:
	./scripts/clean_runtime_artifacts.sh --dry-run

clean-runtime:
	./scripts/clean_runtime_artifacts.sh --yes
