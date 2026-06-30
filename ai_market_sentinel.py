# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

import json
import typing


class AIMarketSentinel(gl.Contract):
    # Single TreeMap — keys are prefixed strings:
    #   "owner"              -> contract owner address
    #   "counter"            -> alert counter (str int)
    #   "meta:{id}"          -> JSON metadata for alert
    #   "status:{id}"        -> "Active" | "Triggered" | "Cancelled"
    #   "history:{id}"       -> last AI evaluation result JSON
    state: TreeMap[str, str]

    def __init__(self):
        self.state = TreeMap()
        self.state["owner"]   = str(gl.message.sender_address)
        self.state["counter"] = "0"

    # ── helpers ────────────────────────────────────────────────────────

    def _counter(self) -> int:
        return int(self.state["counter"])

    def _meta_key(self, aid: int) -> str:
        return "meta:" + str(aid)

    def _status_key(self, aid: int) -> str:
        return "status:" + str(aid)

    def _history_key(self, aid: int) -> str:
        return "history:" + str(aid)

    def _alert_exists(self, aid: int) -> bool:
        return self._status_key(aid) in self.state

    # ── write methods ──────────────────────────────────────────────────

    @gl.public.write
    def create_intelligent_alert(
        self,
        asset: str,
        natural_language_intent: str,
    ) -> typing.Any:
        """
        Register a market watch alert in plain English.

        Args:
            asset:                   Token symbol or asset name (e.g. "BTC", "ETH").
            natural_language_intent: Trigger condition described in plain English
                                     (e.g. "Alert me if BTC dominance drops below 50%").

        Returns:
            The new alert's integer ID.
        """
        aid = self._counter()

        meta = json.dumps({
            "owner":  str(gl.message.sender_address),
            "asset":  asset,
            "intent": natural_language_intent,
        })

        self.state[self._meta_key(aid)]    = meta
        self.state[self._status_key(aid)]  = "Active"
        self.state[self._history_key(aid)] = json.dumps({
            "verdict":   "PENDING",
            "reasoning": "Initialized. Awaiting first sentinel check.",
        })
        self.state["counter"] = str(aid + 1)
        return aid

    @gl.public.write
    def process_sentinel_check(self, alert_id: u256) -> typing.Any:
        """
        Execute a real-time web fetch + multi-LLM consensus check for an alert.

        Five validator nodes independently fetch live market news and evaluate
        whether the alert's natural-language condition has been met. All nodes
        must agree on the verdict before state is committed.

        Args:
            alert_id: The alert to evaluate.

        Returns:
            True if the alert was triggered, False if still pending.
        """
        aid = int(alert_id)

        if not self._alert_exists(aid):
            raise gl.vm.UserError("Alert does not exist.")

        if self.state[self._status_key(aid)] != "Active":
            raise gl.vm.UserError("Alert is not active.")

        raw_meta = self.state[self._meta_key(aid)]
        meta     = json.loads(raw_meta)
        asset    = meta["asset"]
        intent   = meta["intent"]

        def run_ai_adjudication() -> typing.Any:
            # Fetch live market data — CoinGecko public endpoint
            cg_url = (
                "https://api.coingecko.com/api/v3/search/trending"
            )
            try:
                market_data = gl.nondet.web.render(cg_url, mode="text")[:2000]
            except Exception:
                market_data = "Market data unavailable."

            # Supplementary news feed
            news_url = "https://cryptopanic.com/api/v1/posts/?kind=news"
            try:
                news_data = gl.nondet.web.render(news_url, mode="text")[:1500]
            except Exception:
                news_data = "News feed unavailable."

            prompt = f"""
You are a GenLayer Decentralized Validator Node evaluating an intelligent market alert.

Asset Being Monitored: {asset}

Alert Condition (plain English):
{intent}

Live Market Data (CoinGecko trending):
{market_data}

Live News Feed (CryptoPanic):
{news_data}

Task: Determine whether the current live data confirms the alert condition has been met.

Respond with the following JSON format:
{{
    "verdict": str,      // "TRIGGERED" or "PENDING"
    "reasoning": str,    // one or two sentence explanation referencing the live data
    "confidence": int    // 0-100 confidence in this verdict
}}
It is mandatory that you respond only using the JSON format above,
nothing else. Don't include any other words or characters,
your output must be only JSON without any formatting prefix or suffix.
This result should be perfectly parsable by a JSON parser without errors.
"""
            result = (
                gl.nondet.exec_prompt(prompt)
                .replace("```json", "")
                .replace("```", "")
            )
            print(result)
            return json.loads(result)

        consensus = gl.eq_principle.strict_eq(run_ai_adjudication)

        verdict   = consensus.get("verdict", "PENDING")
        reasoning = consensus.get("reasoning", "")
        confidence= int(consensus.get("confidence", 0))

        self.state[self._history_key(aid)] = json.dumps({
            "verdict":    verdict,
            "reasoning":  reasoning,
            "confidence": confidence,
        })

        if verdict == "TRIGGERED":
            self.state[self._status_key(aid)] = "Triggered"
            return True

        return False

    @gl.public.write
    def cancel_alert(self, alert_id: u256) -> typing.Any:
        """
        Cancel an active alert. Only the alert owner can cancel.

        Args:
            alert_id: The alert to cancel.
        """
        aid = int(alert_id)

        if not self._alert_exists(aid):
            raise gl.vm.UserError("Alert does not exist.")

        meta = json.loads(self.state[self._meta_key(aid)])

        if str(gl.message.sender_address) != meta.get("owner", ""):
            raise gl.vm.UserError("Only the alert owner can cancel this alert.")

        if self.state[self._status_key(aid)] != "Active":
            raise gl.vm.UserError("Only active alerts can be cancelled.")

        self.state[self._status_key(aid)] = "Cancelled"
        return True

    # ── view methods ───────────────────────────────────────────────────

    @gl.public.view
    def inspect_alert_state(self, alert_id: u256) -> str:
        """Returns current status and last AI evaluation for an alert as JSON."""
        aid = int(alert_id)
        if not self._alert_exists(aid):
            return '{"error": "Alert not found."}'
        return json.dumps({
            "status":  self.state[self._status_key(aid)],
            "history": json.loads(self.state[self._history_key(aid)]),
        })

    @gl.public.view
    def get_alert_meta(self, alert_id: u256) -> str:
        """Returns the metadata JSON for an alert."""
        aid = int(alert_id)
        if not self._alert_exists(aid):
            return '{"error": "Alert not found."}'
        return self.state[self._meta_key(aid)]

    @gl.public.view
    def get_total_alerts(self) -> str:
        """Returns total number of alerts created."""
        return self.state["counter"]

    @gl.public.view
    def get_owner(self) -> str:
        """Returns the contract owner address."""
        return self.state["owner"]
