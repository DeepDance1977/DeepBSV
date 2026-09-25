# DeepBSV

DeepBSV ist eine eigenständige Solo-Mining-Plattform für Bitcoin SV (BSV), speziell optimiert für den Betrieb auf dedizierter Hardware (z. B. Raspberry Pi 5 unter 5tratumOS).

## Architektur-Fokus

Der zeitkritische Miningpfad (`BSV Node <-> Mining Engine <-> Stratum V1 <-> ASIC`) ist vollständig entkoppelt von Benutzeroberflächen, APIs und Datenbanken.

## Phase 1 Scope

- Asynchroner BSV RPC Client für `getminingcandidate`
- Typensicheres Pydantic-Datenmodell für Mining Candidates
- Mocks und automatisierte Testsuite

## Quickstart (Entwicklung)

1. Repository klonen
2. Virtuelle Umgebung erstellen und aktivieren:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
