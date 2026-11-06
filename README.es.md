# cortex9-rust-regex-empty-repetition-size-limit-model

[English](README.md) · [Guía práctica](PRACTICE.md) · [CI](https://github.com/federiconbaez/cortex9-rust-regex-empty-repetition-size-limit-model/actions/workflows/ci.yml)

Modelo en Python de cómo el crate `regex` 1.5.4 de Rust contabiliza el tamaño
del programa compilado, **antes y después del fix de CVE-2022-24713**
(commit `ae70b41`; el GHSA indica 1.5.5 como primera versión corregida). Antes del fix, una subexpresión
vacía no generaba instrucciones ni sumaba tamaño, así que
`(?:){4294967295}` nunca alcanzaba el límite y el compilador solo iteraba.
El fix cobra `size_of::<Inst>()` bytes por cada subexpresión vacía.

**Todos los contadores se calculan ejecutando la lógica portada; no hay
veredictos fijos.** Cada llamada a `c()` se cuenta contra un presupuesto
externo y al agotarse el estado es `MODEL_LIMIT`. No corre código Rust ni el
crate `regex`, no hay servicios y los patrones tienen como máximo 256
caracteres. Ver [LIMITATIONS.md](LIMITATIONS.md).

- **Qué se porta:**
  - de `compile.rs` (b92ffd5 y ae70b41): `compile_one`, `c`, `c_capture`,
    `c_concat`, `c_alternate`, todas las `c_repeat_*` y `check_size`;
  - de `re_builder.rs`: el `size_limit` por defecto;
  - un parser propio que produce las formas de HIR de regex-syntax 0.6.25.
    No es un port.
- **Tamaño de `Inst`:** se toma 32 bytes. Es lo que mide `tools/inst_size.rs`,
  una copia aislada de las definiciones de `prog.rs`, con rustc 1.99.1 en
  x86_64. Rust no garantiza el layout y no se usó el compilador de 2022.
- **Casos a mano:** tabla en el [README en inglés](README.md#hand-derived-cases-fixturescasesjson).
  Con el límite por defecto, el fix se detiene tras exactamente 327.680
  vacíos contabilizados (límite / 32).
- **Progresión:** con `(?:){N}`, `pre` hace `2N + 1` llamadas y su tamaño
  queda fijo en 96 bytes. `fix` se corta en 655.362 llamadas a partir del
  umbral.
- **Observación no validada:** en el modelo, `(?:|){N}` ya falla con
  `COMPILED_TOO_BIG` antes del fix por las instrucciones Split. No se
  verificó contra el crate real.

## Uso

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m regex_size_model '(?:){4294967295}' --size-limit 4096 --budget 100000
python3 scripts/gen_results.py /tmp/out && diff -r results /tmp/out
```

Python ≥ 3.10, solo biblioteca estándar. Licencia: Apache-2.0.
