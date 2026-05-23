#!/usr/bin/env python3
"""
Sprizen Bug Hunter v2.0 — ProviderRouter
Edge-device friendly AI provider routing with circuit breaker, exponential backoff, and fallback chain.
Sirf stdlib + requests use kiya gaya hai.
"""

import json
import random
import time
import threading
from enum import Enum
from typing import Optional, Dict, Any, List, Callable

import requests


class CircuitState(Enum):
    """Circuit breaker ke 3 states — CLOSED sab normal, OPEN fail ho gaya, HALF_OPEN test kar raha hai."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker pattern — 5 failures ke baad 60 sec ke liye provider block.
    Thread-safe hai, Termux pe bhi smooth chalega.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout_sec: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Function ko circuit breaker ke saath execute karega."""
        with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time >= self.recovery_timeout_sec:
                    self.state = CircuitState.HALF_OPEN
                    self.failure_count = 0
                else:
                    raise Exception(f"Circuit breaker OPEN — abhi {self.recovery_timeout_sec}s wait karo.")

        try:
            result = func(*args, **kwargs)
            with self._lock:
                self.failure_count = 0
                self.state = CircuitState.CLOSED
            return result
        except Exception as e:
            with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
            raise e

    def get_state(self) -> str:
        """Current circuit breaker state return karta hai."""
        with self._lock:
            return self.state.value


class ProviderRouter:
    """
    AI provider router — fallback chain, circuit breaker, exponential backoff, aur routing rules handle karta hai.
    """

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._init_circuit_breakers()

    def _load_config(self) -> Dict[str, Any]:
        """config.json load karta hai, nahi mili to default config return karta hai."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[WARNING] {self.config_path} nahi mila, default config use kar raha hoon.")
            return self._default_config()
        except json.JSONDecodeError as e:
            print(f"[ERROR] config.json parse fail: {e}")
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Default config jab file nahi mile."""
        return {
            "fallback_chain": ["groq", "kimi", "ollama"],
            "routing_rules": {
                "privacy_sensitive": "ollama",
                "high_reasoning": "groq"
            },
            "circuit_breaker": {
                "failure_threshold": 5,
                "recovery_timeout_sec": 60
            },
            "retry": {
                "max_retries": 3,
                "base_delay_sec": 2.0,
                "jitter": True
            },
            "providers": {
                "groq": {"enabled": False, "api_key": "", "model": "llama3-8b-8192", "timeout_seconds": 30},
                "kimi": {"enabled": False, "api_key": "", "model": "moonshot-v1-8k", "timeout_seconds": 30},
                "gemini": {"enabled": False, "api_key": "", "model": "gemini-pro", "timeout_seconds": 30},
                "ollama": {"enabled": True, "api_key": "", "model": "codellama", "timeout_seconds": 60, "base_url": "http://localhost:11434"},
                "llamacpp": {"enabled": False, "api_key": "", "model": "default", "timeout_seconds": 60, "base_url": "http://localhost:8080"}
            }
        }

    def _init_circuit_breakers(self):
        """Har provider ke liye circuit breaker initialize karta hai."""
        cb_config = self.config.get("circuit_breaker", {})
        threshold = cb_config.get("failure_threshold", 5)
        timeout = cb_config.get("recovery_timeout_sec", 60)

        for provider in self.config.get("providers", {}):
            self.circuit_breakers[provider] = CircuitBreaker(threshold, timeout)

    def _get_retry_config(self) -> Dict[str, Any]:
        """Retry configuration return karta hai."""
        return self.config.get("retry", {"max_retries": 3, "base_delay_sec": 2.0, "jitter": True})

    def _calculate_backoff(self, attempt: int) -> float:
        """Exponential backoff + jitter calculate karta hai: 2s -> 4s -> 8s, max 30s."""
        retry_config = self._get_retry_config()
        base = retry_config.get("base_delay_sec", 2.0)
        jitter = retry_config.get("jitter", True)

        delay = base * (2 ** attempt)
        delay = min(delay, 30.0)  # Max 30 sec

        if jitter:
            delay = delay * (0.5 + random.random() * 0.5)  # 50% to 100% of delay

        return delay

    def _handle_http_error(self, status_code: int, provider: str) -> str:
        """HTTP error codes ko human-readable message mein convert karta hai."""
        errors = {
            401: f"[{provider}] 401 Unauthorized — API key galat hai ya missing hai.",
            403: f"[{provider}] 403 Forbidden — Access denied, permissions check karo.",
            429: f"[{provider}] 429 Too Many Requests — Rate limit hit, thoda wait karo.",
            500: f"[{provider}] 500 Internal Server Error — Provider side issue hai.",
            502: f"[{provider}] 502 Bad Gateway — Provider temporarily down hai.",
            503: f"[{provider}] 503 Service Unavailable — Provider overloaded hai.",
        }
        return errors.get(status_code, f"[{provider}] HTTP {status_code} error aaya.")

    def _call_groq(self, prompt: str, system_prompt: str = "") -> str:
        """Groq API call — fast inference ke liye best hai."""
        cfg = self.config["providers"]["groq"]
        api_key = cfg.get("api_key", "")
        model = cfg.get("model", "llama3-8b-8192")
        timeout = cfg.get("timeout_seconds", 30)

        if not api_key:
            raise ValueError("Groq API key missing hai config mein.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 4096
        }

        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout
        )

        if resp.status_code != 200:
            raise Exception(self._handle_http_error(resp.status_code, "groq"))

        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _call_kimi(self, prompt: str, system_prompt: str = "") -> str:
        """Kimi (Moonshot AI) API call — Chinese LLM, strong reasoning."""
        cfg = self.config["providers"]["kimi"]
        api_key = cfg.get("api_key", "")
        model = cfg.get("model", "moonshot-v1-8k")
        timeout = cfg.get("timeout_seconds", 30)

        if not api_key:
            raise ValueError("Kimi API key missing hai config mein.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.1
        }

        resp = requests.post(
            "https://api.moonshot.cn/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout
        )

        if resp.status_code != 200:
            raise Exception(self._handle_http_error(resp.status_code, "kimi"))

        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _call_gemini(self, prompt: str, system_prompt: str = "") -> str:
        """Google Gemini API call — multimodal capabilities hain."""
        cfg = self.config["providers"]["gemini"]
        api_key = cfg.get("api_key", "")
        model = cfg.get("model", "gemini-pro")
        timeout = cfg.get("timeout_seconds", 30)

        if not api_key:
            raise ValueError("Gemini API key missing hai config mein.")

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.1}
        }

        resp = requests.post(url, json=payload, timeout=timeout)

        if resp.status_code != 200:
            raise Exception(self._handle_http_error(resp.status_code, "gemini"))

        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_ollama(self, prompt: str, system_prompt: str = "") -> str:
        """Ollama local API call — Termux pe bhi chal sakta hai, fully offline."""
        cfg = self.config["providers"]["ollama"]
        model = cfg.get("model", "codellama")
        timeout = cfg.get("timeout_seconds", 60)
        base_url = cfg.get("base_url", "http://localhost:11434")

        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt if system_prompt else "You are a code security expert.",
            "stream": False,
            "options": {"temperature": 0.1}
        }

        resp = requests.post(
            f"{base_url}/api/generate",
            json=payload,
            timeout=timeout
        )

        if resp.status_code != 200:
            raise Exception(self._handle_http_error(resp.status_code, "ollama"))

        data = resp.json()
        return data.get("response", "")

    def _call_llamacpp(self, prompt: str, system_prompt: str = "") -> str:
        """llama.cpp server API call — lightweight C++ inference."""
        cfg = self.config["providers"]["llamacpp"]
        timeout = cfg.get("timeout_seconds", 60)
        base_url = cfg.get("base_url", "http://localhost:8080")

        full_prompt = f"### System:\n{system_prompt}\n\n### User:\n{prompt}\n\n### Assistant:\n" if system_prompt else f"### User:\n{prompt}\n\n### Assistant:\n"

        payload = {
            "prompt": full_prompt,
            "temperature": 0.1,
            "n_predict": 4096,
            "stop": ["### User:", "### System:"]
        }

        resp = requests.post(
            f"{base_url}/completion",
            json=payload,
            timeout=timeout
        )

        if resp.status_code != 200:
            raise Exception(self._handle_http_error(resp.status_code, "llamacpp"))

        data = resp.json()
        return data.get("content", "")

    def _get_provider_call(self, provider: str) -> Callable:
        """Provider name se uska _call method return karta hai."""
        mapping = {
            "groq": self._call_groq,
            "kimi": self._call_kimi,
            "gemini": self._call_gemini,
            "ollama": self._call_ollama,
            "llamacpp": self._call_llamacpp,
        }
        return mapping.get(provider)

    def route(self, prompt: str, system_prompt: str = "", context: Optional[Dict[str, Any]] = None) -> str:
        """
        Prompt ko sahi provider pe bhejta hai — routing rules, fallback chain, circuit breaker sab handle karta hai.
        """
        context = context or {}
        routing_rules = self.config.get("routing_rules", {})

        # Privacy sensitive files ke liye direct ollama
        if context.get("privacy_sensitive") and routing_rules.get("privacy_sensitive"):
            target = routing_rules["privacy_sensitive"]
            if self._is_provider_available(target):
                return self._execute_with_retry(target, prompt, system_prompt)

        # High reasoning tasks ke liye groq prefer karo
        if context.get("high_reasoning") and routing_rules.get("high_reasoning"):
            target = routing_rules["high_reasoning"]
            if self._is_provider_available(target):
                return self._execute_with_retry(target, prompt, system_prompt)

        # Fallback chain try karo
        fallback_chain = self.config.get("fallback_chain", ["groq", "kimi", "ollama"])
        last_error = None

        for provider in fallback_chain:
            if not self._is_provider_available(provider):
                continue

            try:
                return self._execute_with_retry(provider, prompt, system_prompt)
            except Exception as e:
                last_error = e
                print(f"[FALLBACK] {provider} fail ho gaya: {e}")
                continue

        raise Exception(f"Saare providers fail ho gaye. Last error: {last_error}")

    def _is_provider_available(self, provider: str) -> bool:
        """Check karta hai ki provider enabled hai aur circuit breaker OPEN nahi hai."""
        providers = self.config.get("providers", {})
        if provider not in providers:
            return False
        if not providers[provider].get("enabled", False):
            return False

        cb = self.circuit_breakers.get(provider)
        if cb and cb.get_state() == "open":
            return False

        return True

    def _execute_with_retry(self, provider: str, prompt: str, system_prompt: str) -> str:
        """Provider call ko circuit breaker + retry ke saath execute karta hai."""
        cb = self.circuit_breakers.get(provider)
        call_func = self._get_provider_call(provider)

        if not call_func:
            raise ValueError(f"Provider {provider} ka call method nahi mila.")

        retry_config = self._get_retry_config()
        max_retries = retry_config.get("max_retries", 3)

        def wrapped_call():
            for attempt in range(max_retries):
                try:
                    return call_func(prompt, system_prompt)
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        delay = self._calculate_backoff(attempt)
                        print(f"[RETRY] {provider} timeout, {delay:.1f}s wait kar raha hoon... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                    else:
                        raise
                except requests.exceptions.ConnectionError as e:
                    if attempt < max_retries - 1:
                        delay = self._calculate_backoff(attempt)
                        print(f"[RETRY] {provider} connection error, {delay:.1f}s wait... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                    else:
                        raise
                except Exception:
                    raise  # HTTP errors ko retry mat karo, direct raise karo
            raise Exception(f"{provider} ne {max_retries} retries ke baad bhi fail kiya.")

        if cb:
            return cb.call(wrapped_call)
        return wrapped_call()

    def get_provider_health(self) -> Dict[str, Dict[str, Any]]:
        """Sab providers ka health status return karta hai — Termux pe monitoring ke liye useful."""
        health = {}
        providers = self.config.get("providers", {})

        for name, cfg in providers.items():
            cb = self.circuit_breakers.get(name)
            health[name] = {
                "enabled": cfg.get("enabled", False),
                "circuit_state": cb.get_state() if cb else "unknown",
                "model": cfg.get("model", "unknown"),
                "has_api_key": bool(cfg.get("api_key", "")),
                "base_url": cfg.get("base_url", "N/A")
            }

        return health


if __name__ == "__main__":
    # Quick test
    router = ProviderRouter()
    health = router.get_provider_health()
    print("=== Provider Health ===")
    for name, status in health.items():
        print(f"{name}: {status}")
