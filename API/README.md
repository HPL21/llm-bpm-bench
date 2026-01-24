# LLM BPM BENCH

Projekt na zaliczenie przedmiotu Zaawansowane programowanie w języku Python.

Projekt jest pierwszą częścią narzędzia, które będzie służyło do testowania LLMów uruchomionych lokalnie w różnych zastosowaniach biznesowych.

# Co zostało zrobione

- Magazyn plików oparty na MinIO;
- 3 modele:
    - file_asset - plik wykorzystywany w testach;
    - test_case - pojedynczy test;
    - test_suite - zbiór testów z danej dziedziny biznesowej;
- połączenie z bazą Postgres, w której zostały utworzone tabele;
- serwisy i endpointy realizujące operacje CRUD na stworzonych tabelach;
- websocket wysyłający status aplikacji;
- testy integracyjne;
- plik docker compose do uruchomienia aplikacji;
- plik Taskfile do ułatwienia pracy z aplikacją.


# Setup

0. Pobrać repo.
1. Zduplikować plik .env.example, zmienić nazwę kopii na .env.
2. Zainstalować [Taskfile](https://taskfile.dev/docs/installation).
3. Wykonać ```task up```.

Ewentualnie zamiast kroków 2 i 3 po prostu wpisać ```docker compose up -d```.

# Swagger

Po uruchomieniu można przetestować wszystkie endpointy na http://localhost:8000/docs.

Websocket był testowany na stronie [PieHost](https://piehost.com/websocket-tester), wpisując ```ws://localhost:8000/api/v1/ws/status```.