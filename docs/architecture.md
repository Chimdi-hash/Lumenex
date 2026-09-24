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
GenLayer's Optimistic Democracy requires Validators to independently verify the Leader's proposal. The Validator executes `validator_fn(leader_result)`.
In traditional non-deterministic patterns, requiring strict `==` equality on raw LLM outputs is brittle because natural language output varies stochastically across models and runs.

## 3. The Equivalence Principle & Actionable Result Binding

Lumenex implements the **Equivalence Principle** while maintaining strict cryptographic and operational safety:

1. **Independent Verification of All Actionable Results:**
   Downstream protocols and smart contracts rely on both `status` (`COMPLIANT`, `VIOLATION`, `UNRESOLVED`) and `severity` (`NONE`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) to make automated state transitions, pause queues, or trigger multisigs. Therefore, `validator_fn` independently runs its own non-deterministic evaluation and enforces that both `status` and `severity` are identical between the Leader and the Validator:
   ```python
   if leader_data["status"] != independent["status"]:
       return False
   if leader_data["severity"] != independent["severity"]:
       return False
   ```
2. **Equivalence on Explanatory Reasoning:**
   The `reason` field is a natural language explanation providing human-readable transparency for developers and auditors. Because this text is explanatory rather than an operational trigger, Lumenex accepts semantic variance in the reason string without demanding character-for-character equality, perfectly utilizing the Equivalence Principle.
3. **Defense Against Unbound State Manipulation:**
   Any attempt by a Leader to introduce inconsistent severities (e.g. `severity != NONE` when `status == COMPLIANT`, or an unvetted `CRITICAL` flag) causes validators to reject the proposal, ensuring every actionable result committed to on-chain state is independently validated and bound.

## 4. Prompt Engineering & Data Formatting

To defend against Prompt Injections and assure strict adherence, Lumenex formats its prompt using official GenLayer techniques:

1. **Role Boundary:** The engine asserts its identity ("You are the Lumenex semantic policy engine").
2. **Untrusted Data Isolation:** The user-supplied `invariants`, `context`, and `proposed_change` are strictly encapsulated within `BEGIN_UNTRUSTED_...` and `END_UNTRUSTED_...` tags.
3. **Defense-in-Depth:** The prompt explicitly instructs the model to ignore embedded system commands, URLs, or markdown instructions found within the untrusted blocks.
4. **JSON Enforcement:** Output is strictly constrained to a JSON format, and the contract parser rejects extraneous keys or markdown blocks via `json.loads(..., object_pairs_hook=_unique_object)`.
