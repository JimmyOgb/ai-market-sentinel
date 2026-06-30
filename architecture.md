# Architecture — AI Market Sentinel v2

## What Was Fixed and Why

### Fix 1: gl.vm.UserError

GenVM's linter (genvm-lint) requires gl.vm.UserError for contract-level
validation failures, not bare Python Exception. The PredictionMarket
reference contract (the official GenLayer example) uses this pattern:

  raise gl.vm.UserError("Already resolved")

All three validation points in this contract now use it:

  raise gl.vm.UserError("Alert does not exist.")
  raise gl.vm.UserError("Alert is not active.")
  raise gl.vm.UserError("Only the alert owner can cancel this alert.")

### Fix 2: Nondet Structure

The original inner function returned a raw string from exec_prompt
and strict_eq compared the raw strings. The correct pattern — used
across every other contract in this project series — is to return a
parsed dict from the inner function:

  def run_ai_adjudication() -> typing.Any:
      market_data = gl.nondet.web.render(cg_url, mode="text")[:2000]
      news_data   = gl.nondet.web.render(news_url, mode="text")[:1500]
      result      = gl.nondet.exec_prompt(prompt)...
      return json.loads(result)   <- parsed dict

  consensus = gl.eq_principle.strict_eq(run_ai_adjudication)

strict_eq compares structured objects across all 5 validators.
This is more reliable than comparing raw strings because whitespace
and formatting differences in the LLM output can cause spurious
disagreements.

### Fix 3: Real genlayer-js Frontend

The v1 frontend used setTimeout and Math.random() to simulate
contract interactions. The v2 frontend uses genlayer-js loaded
from CDN (genlayer-js@latest) to make real calls to Studionet:

  client = GenLayerJS.createClient({ endpointUrl: rpc });

  // Read call (no signing needed)
  const result = await client.readContract({
    address: CONTRACT_ADDRESS,
    functionName: 'get_total_alerts',
    args: [],
  });

  // Write call (requires account with private key)
  const txHash = await client.writeContract({
    address:      CONTRACT_ADDRESS,
    functionName: 'process_sentinel_check',
    args:         [parseInt(id)],
    account,
  });
  const receipt = await client.waitForTransactionReceipt({ hash: txHash });

## Storage: Single TreeMap Pattern

  "owner"         -> contract owner address
  "counter"       -> total alerts created
  "meta:{id}"     -> JSON {owner, asset, intent}
  "status:{id}"   -> "Active" | "Triggered" | "Cancelled"
  "history:{id}"  -> JSON {verdict, reasoning, confidence}

## Two Web Sources Per Sentinel Check

Both fetches happen inside the same inner function passed to strict_eq,
so all 5 validator nodes independently fetch both sources in the same
execution context:

  gl.nondet.web.render(CoinGecko trending URL, mode="text")[:2000]
  gl.nondet.web.render(CryptoPanic news URL,   mode="text")[:1500]

This ensures cross-source evidence is available to every validator,
preventing a situation where different nodes see different data
combinations and produce divergent verdicts.

## Type Constraints

  Class annotations : TreeMap[str, str] only
  Method parameters  : str, u256         (NOT float, dict, Address)
  Write returns      : typing.Any
  View returns        : str
