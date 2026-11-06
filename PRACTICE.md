# Guía práctica / Practice guide

Ejercicios **offline**: se cuenta lo que haría el compilador, sin compilar
ningún regex real y sin servicios. Cada iteración de los bucles del
compilador pasa por `c()`, que cuenta contra el presupuesto. El parser no
cuenta pasos: lo acota el límite de 256 caracteres del patrón. (El chequeo
opcional `scripts/upstream_check.py` sí compila con los crates reales,
excepto los casos `MODEL_LIMIT` en 1.5.4.) *English
summary at the end.*

## Objetivos

1. Leer `Compiler::c` y las funciones `c_repeat_*` de regex 1.5.4 y ver
   cuándo devuelven `None` (ninguna instrucción).
2. Entender por qué el límite de tamaño, que mide instrucciones, no
   detecta trabajo que no genera instrucciones.
3. Medir con contadores (llamadas a `c()`, instrucciones, bytes extra) en
   lugar de cronómetros.
4. Diseñar límites que cuenten el trabajo y no solo el resultado.

## Prerrequisitos

Python ≥ 3.10. Lectura: diff de ae70b41, `compile.rs` en b92ffd5 (funciones
`c`, `c_concat`, `c_alternate`, `c_repeat_range`, `check_size`) y el GHSA (ver
[SOURCES.md](SOURCES.md)).

## Comandos locales

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m regex_size_model 'a{2,4}'
PYTHONPATH=src python3 -m regex_size_model '(?:){3}'
PYTHONPATH=src python3 -m regex_size_model '(?:){4294967295}' --size-limit 4096 --budget 100000
python3 scripts/gen_results.py /tmp/out && diff -r results /tmp/out
```

## Ejercicios graduados

**Nivel 1 — a mano.** Para `a{2,4}` escribe cada llamada a `c()` y cada
instrucción empujada (Save, Char, Split, Match). Debe darte 5 llamadas y 9
instrucciones.

**Nivel 2 — el vacío.** Para `(?:){3}` cuenta las llamadas a `c()` y los
vacíos. ¿Por qué el fix suma 4 × 32 = 128 bytes y no 96?

**Nivel 3 — el umbral.** Con límite 4096, deriva por qué el fix se corta en la
llamada 258 para `(?:){4294967295}` y en la 130 para `x{0}{4294967295}`.
¿Por qué los dos casos se detienen con 128 vacíos?

**Nivel 4 — progresión.** Con `results/progression.csv`, grafica `c_calls`
contra N para `pre` y `fix`. Explica por qué `size_at_stop` de `pre` queda en
96 bytes.

**Nivel 5 — alternativa vacía.** Deriva a mano por qué `(?:|){N}` con límite
4096 se corta en `pre` con 129 instrucciones y en `fix` con 44 instrucciones
y 2720 bytes extra.

**Nivel 6 — contraste con el crate real.** El modelo dice que `(?:|){N}` ya
falla antes del fix. Sigue `c_alternate` en `compile.rs` (b92ffd5) y señala
la línea que añade la instrucción aunque las dos ramas sean vacías. Luego
lee `review/upstream/hir.tsv` y `compile.tsv`. Comprobación: la HIR de
`(?:|)` es `Group(NC,Alt(Empty,Empty))` y la fila
`06_upstream_empty_alt_small_limit pre` es `COMPILED_TOO_BIG` en los dos
lados. Explica por qué eso no prueba que los recuentos de instrucciones
coincidan.

**Nivel 7 — defensa propia.** Para un compilador o intérprete propio, añade un
contador de trabajo (nodos visitados) con límite propio, independiente del
tamaño del resultado. Escribe un test con una repetición enorme de algo vacío.

## Vínculo modelo ↔ CVE

| Caso real | En el código |
|---|---|
| `Empty => Ok(None)` y `None => return Ok(None)` en `c_concat` | `Compiler.c_empty` / `_pre_empty_concat` con `version="pre"` |
| `c_empty()` suma `size_of::<Inst>()` (ae70b41) | `Compiler.c_empty` con `version="fix"` |
| `check_size` | `Compiler.check_size` |

## Aplicación defensiva

- Al aceptar regex de usuarios: limitar tamaño compilado **y** tiempo o
  trabajo, y usar versiones con el fix.
- En código propio, todo "atajo" que omite salida debe seguir contando
  trabajo.

---

## English summary

Offline exercises: only counts, no real regex compiled. Every compiler loop
iteration goes through the counted `c()`. The parser is bounded by the
256-char pattern limit, and the optional `upstream_check.py` uses the real
crates.
Levels:

1. Trace `a{2,4}` by hand.
2. Count the empties in `(?:){3}`.
3. Derive the thresholds at limit 4096.
4. Plot the progression.
5. Derive the empty-alternation case.
6. Trace the `c_alternate` split and read the real-crate check.
7. Add a work counter to your own compiler.
