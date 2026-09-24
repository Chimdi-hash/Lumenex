# Lumenex Architecture

Lumenex is built natively for GenLayer, utilizing GenVM, Optimistic Democracy, and the Equivalence Principle to create a resilient, on-chain semantic policy engine.

## 1. GenVM Constraints & Deterministic Envelope

Lumenex operates within the strict boundaries of GenVM:
- **No Global Mutability:** Persistent state is only mutated via `TreeMap` instances within `@gl.public.write` functions.
- **Sandboxed Execution:** The contract avoids standard library calls (`os`, `sys`, `time`) that introduce unmanaged non-determinism. Time is deterministically derived from `gl.message.raw["datetime"]`.
- **Pre-flight Sizing:** Before invoking the LLM, Lumenex computes a hypothetical "worst-case" record size to ensure that no LLM response could ever cause the final serialization to exceed GenVM storage limits (`MAX_RECORD_BYTES`).

## 2. Optimistic Democracy and the Consensus Loop

When `check_change` is called, Lumenex transitions from a deterministic domain into a non-deterministic domain using GenLayer's consensus primitive:

```python
gl.vm.run_nondet(leader_fn, validator_fn)
```

### The Leader
The Leader node executes `leader_fn`, passing the compiled prompt to the LLM via `gl.nondet.exec_prompt`. The Leader receives a JSON object containing:
- `status`
- `severity`
- `reason`

### The Validator
GenLayer's Optimistic Democracy requires Validators to independently verify the Leader's work. The Validator executes `validator_fn(leader_result)`. 
In older patterns, validators might perform a strict `==` check on the `leader_result.calldata`. However, this is fundamentally flawed for Natural Language tasks because LLMs are stochastic.

## 3. The Equivalence Principle Implementation

Lumenex embraces the **Equivalence Principle**: *Validators accept non-identical outputs when they satisfy the Intelligent Contract's validation rule.*

Because Lumenex generates human-readable reasoning strings (`reason`), identical string matching is impossible. Instead, the `validator_fn`:
1. Receives the `leader_result`.
2. Runs its own independent `gl.nondet.exec_prompt`.
3. Asserts strict equivalence on the canonical `status` (e.g., if Leader says `VIOLATION`, Validator must also say `VIOLATION`).
4. Approves the transaction if the `status` matches, allowing the Leader's unique reasoning string to be written to state.

This pattern isolates the stochastic variance to the explanatory data while enforcing strict consensus on the actionable data, maximizing the contract's robustness on the GenLayer network.

## 4. Prompt Engineering & Data Formatting

To defend against Prompt Injections and assure strict adherence, Lumenex formats its prompt using official GenLayer techniques:

1. **Role Boundary:** The engine asserts its identity ("You are the Lumenex semantic policy engine").
2. **Untrusted Data Isolation:** The user-supplied `invariants`, `context`, and `proposed_change` are strictly encapsulated within `BEGIN_UNTRUSTED_...` and `END_UNTRUSTED_...` tags.
3. **Defense-in-Depth:** The prompt explicitly instructs the model to ignore embedded system commands, URLs, or markdown instructions found within the untrusted blocks.
4. **JSON Enforcement:** Output is strictly constrained to a JSON format, and the contract parser rejects extraneous keys or markdown blocks via `json.loads(..., object_pairs_hook=_unique_object)`.
