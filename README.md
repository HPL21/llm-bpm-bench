# LLM BPM BENCH

Narzędzie, które służy do testowania LLMów uruchomionych lokalnie w różnych zastosowaniach biznesowych.

# Setup

0. Pobrać repo.
1. Zduplikować plik .env.example, zmienić nazwę kopii na .env.
2. Zainstalować [Taskfile](https://taskfile.dev/docs/installation).
3. Wykonać ```task up```.

Ewentualnie zamiast kroków 2 i 3 po prostu wpisać ```docker compose up -d```.

# Swagger

Po uruchomieniu można przetestować wszystkie endpointy na http://localhost:8000/docs.

