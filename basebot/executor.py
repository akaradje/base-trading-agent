"""ชั้น Execution — แยก paper ออกจาก live เพื่อให้ต่อ Base ทีหลังได้โดยไม่รื้อ engine.

PaperExecutor  : เทรดบนพอร์ตจำลอง (ใช้ตอนนี้)
LiveExecutor   : เทรดจริงบน Base chain ผ่าน Base MCP
  - ทุกธุรกรรมต้องได้รับการอนุมัติจากผู้ใช้ก่อนเสมอ (human-in-the-loop)
  - รองรับ swap ETH/USDC ↔ Target Tokens
  - จัดการ exception: network timeout, gas spike, slippage
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .portfolio import Portfolio, Trade


# ──────────────────────────────────────────────
# อินเทอร์เฟซกลาง — engine เรียกผ่านนี้เท่านั้น
# ──────────────────────────────────────────────

class Executor:
    """อินเทอร์เฟซกลาง — engine เรียกผ่านนี้เท่านั้น."""

    def buy(self, symbol: str, usd_amount: float, price: float, reason: str) -> Trade | None:
        raise NotImplementedError

    def sell(self, symbol: str, price: float, reason: str, fraction: float = 1.0) -> Trade | None:
        raise NotImplementedError


# ──────────────────────────────────────────────
# ส่วนที่ 1: Paper Executor (จำลอง — ไม่ใช้เงินจริง)
# ──────────────────────────────────────────────

class PaperExecutor(Executor):
    def __init__(self, portfolio: Portfolio):
        self.pf = portfolio

    def buy(self, symbol, usd_amount, price, reason):
        return self.pf.buy(symbol, usd_amount, price, reason)

    def sell(self, symbol, price, reason, fraction=1.0):
        return self.pf.sell(symbol, price, reason, fraction)


# ──────────────────────────────────────────────
# ส่วนที่ 2: Live Executor — Base MCP Integration
# ──────────────────────────────────────────────

# ── ค่าคงที่ของ Base chain ──────────────────────
_BASE_CHAIN_ID = 8453
_NATIVE_ETH = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"  # sentinel สำหรับ native ETH
_DECIMALS: dict[str, int] = {
    # token address (lowercase) -> decimals
    "0x4200000000000000000000000000000000000006": 18,  # WETH on Base
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": 6,   # USDC on Base
    "0x940181a94a35a4569e4529a3cdfb74e38fd98631": 18,  # AERO on Base
    "0x4ed4e862860bed51a9570b96d89af5e1b0efefed": 18,  # DEGEN on Base
}
_DEFAULT_DECIMALS = 18

# CoinGecko coin ID -> ticker symbol mapping (สำหรับ resolve_token)
_COINGECKO_TO_TICKER: dict[str, str] = {
    "ethereum": "ETH",
    "aerodrome-finance": "AERO",
    "degen-base": "DEGEN",
}


# ── Exception hierarchy สำหรับข้อผิดพลาดเฉพาะของ live trading ──

class LiveExecutionError(Exception):
    """ฐาน exception สำหรับข้อผิดพลาดทั้งหมดของ LiveExecutor."""


class UserRejectionError(LiveExecutionError):
    """ผู้ใช้ปฏิเสธหรือไม่อนุมัติธุรกรรมภายในเวลาที่กำหนด."""


class GasSpikeError(LiveExecutionError):
    """ค่า gas สูงเกินขีดจำกัดที่ตั้งไว้ — ป้องกันการจ่ายค่า gas แพงเกินไป."""


class SlippageExceededError(LiveExecutionError):
    """ราคาที่ได้เลวกว่า slippage tolerance ที่ตั้งไว้."""


class NetworkTimeoutError(LiveExecutionError):
    """RPC หรือ MCP server ไม่ตอบกลับภายในเวลาที่กำหนด."""


class MCPProtocolError(LiveExecutionError):
    """MCP server ตอบกลับมาด้วย error หรือรูปแบบข้อมูลไม่ถูกต้อง."""


class InsufficientBalanceError(LiveExecutionError):
    """ยอด token ไม่เพียงพอสำหรับทำธุรกรรม."""


# ── โครงสร้างข้อมูลสำหรับ swap quote ──────────────

@dataclass
class SwapQuote:
    """ผลลัพธ์จาก MCP get_quote — ข้อมูลที่ใช้ตัดสินใจก่อนส่งธุรกรรม."""
    from_token: str         # ที่อยู่ token ต้นทาง
    to_token: str           # ที่อยู่ token ปลายทาง
    from_amount: int        # จำนวน token ต้นทาง (raw, ยังไม่หาร decimals)
    to_amount: int          # จำนวน token ปลายทาง (raw) — หลังหัก fee
    min_amount: int         # จำนวนขั้นต่ำที่ยอมรับได้ (หลัง apply slippage)
    price_impact: float     # เปอร์เซ็นต์ผลกระทบต่อราคา (0.01 = 1%)
    gas_estimate: int       # ประมาณการ gas units
    gas_price: int          # gas price (wei)
    route: list[str]        # เส้นทาง swap ที่ MCP เลือก (เช่น [WETH, USDC, AERO])
    expires_at: float       # timestamp ที่ quote หมดอายุ


# ──────────────────────────────────────────────
# MCP Client — เชื่อม Base MCP server ผ่าน JSON-RPC
# ──────────────────────────────────────────────

class BaseMCPClient:
    """เชื่อมต่อ Base MCP server ผ่าน JSON-RPC 2.0 (HTTP POST).

    Base MCP ให้บริการ tools สำหรับ on-chain operations:
    - get_quote      — ขอราคา swap
    - build_tx       — สร้าง transaction payload
    - send_tx        — ส่ง signed transaction
    - get_balance    — ดูยอด token
    - get_allowance  — ดูค่า allowance ของ token

    ใช้ urllib แทน requests เพื่อลด dependency (ไม่ต้องเพิ่มใน requirements.txt)
    """

    def __init__(self, server_url: str, chain_id: int = _BASE_CHAIN_ID,
                 timeout_sec: int = 30, log=print) -> None:
        self.server_url = server_url.rstrip("/")
        self.chain_id = chain_id
        self.timeout_sec = timeout_sec
        self.log = log
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """เรียก MCP tool ผ่าน JSON-RPC. คืน result dict หรือ raise MCPProtocolError."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        req = Request(
            url=self.server_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.timeout_sec) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise NetworkTimeoutError(
                f"MCP call '{tool_name}' ล้มเหลว: {exc}"
            ) from exc

        if "error" in body:
            err = body["error"]
            raise MCPProtocolError(
                f"MCP error {err.get('code', '?')}: {err.get('message', 'unknown')}"
            )
        return body.get("result", {})

    def get_quote(self, from_token: str, to_token: str, amount: int,
                  slippage_bps: int) -> SwapQuote:
        """ขอราคา swap จาก MCP — คืน SwapQuote สำหรับใช้ตัดสินใจ."""
        result = self.call_tool("get_quote", {
            "chainId": self.chain_id,
            "fromToken": from_token,
            "toToken": to_token,
            "amount": str(amount),
            "slippageBps": slippage_bps,
        })
        return SwapQuote(
            from_token=from_token,
            to_token=to_token,
            from_amount=int(result.get("fromAmount", amount)),
            to_amount=int(result.get("toAmount", 0)),
            min_amount=int(result.get("minAmount", 0)),
            price_impact=float(result.get("priceImpact", 0)),
            gas_estimate=int(result.get("gasEstimate", 200_000)),
            gas_price=int(result.get("gasPrice", 1_000_000_000)),
            route=result.get("route", []),
            expires_at=float(result.get("expiresAt", time.time() + 60)),
        )

    def build_transaction(self, quote: SwapQuote, from_address: str) -> dict[str, Any]:
        """สร้าง transaction payload จาก quote — ยังไม่ส่ง แค่เตรียมข้อมูล."""
        return self.call_tool("build_tx", {
            "chainId": self.chain_id,
            "fromToken": quote.from_token,
            "toToken": quote.to_token,
            "fromAmount": str(quote.from_amount),
            "minToAmount": str(quote.min_amount),
            "fromAddress": from_address,
            "route": quote.route,
        })

    def get_balance(self, token_address: str, wallet_address: str) -> int:
        """ดูยอด token ของ wallet (raw amount, ยังไม่หาร decimals)."""
        result = self.call_tool("get_balance", {
            "chainId": self.chain_id,
            "token": token_address,
            "wallet": wallet_address,
        })
        return int(result.get("balance", 0))


# ──────────────────────────────────────────────
# Gas Oracle — Base L1 data fee estimation
# ──────────────────────────────────────────────

# GasPriceOracle predeploy บน Base — 0x4200...000F
# https://docs.base.org/base-chain/building-with-base/gas-price-oracle
_GAS_ORACLE_ADDR = "0x420000000000000000000000000000000000000F"
# Function selector for getL1Fee(bytes) = keccak256("getL1Fee(bytes)")[:4]
_GET_L1_FEE_SEL = "0x939e1e40"
# Function selector for gasPrice() = keccak256("gasPrice()")[:4]
_GAS_PRICE_SEL = "0x49b46676"


class GasOracle:
    """Base GasPriceOracle client — ใช้ estimate L1 data fee สำหรับ transactions บน Base.

    Base เก็บค่า L1 data cost แยกจาก L2 execution gas.
    GasPriceOracle predeploy ให้ getL1Fee(encoded_tx) สำหรับค่า L1 ที่แม่นยำ
    แทนที่จะ estimate จาก byte length เอง (ซึ่งคลาดเคลื่อนได้ ~20%)
    """

    def __init__(self, rpc_url: str = "https://mainnet.base.org", timeout_sec: int = 10) -> None:
        self.rpc_url = rpc_url
        self.timeout_sec = timeout_sec
        self._gas_price_cache: float = 0
        self._gas_price_ts: float = 0
        self._cache_ttl = 12  # cache gas price 12 วินาที (1 block)

    def _eth_call(self, to: str, data: str) -> str | None:
        """Raw eth_call ผ่าน JSON-RPC — คืน hex result หรือ None."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": to, "data": data}, "latest"],
        }
        req = Request(
            url=self.rpc_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.timeout_sec) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            result = body.get("result")
            return result if isinstance(result, str) else None
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return None

    def get_l1_fee(self, tx_bytes: bytes) -> int:
        """เรียก GasPriceOracle.getL1Fee(encoded_tx) สำหรับ L1 data cost ที่แม่น.

        คืน fee ใน wei. คืน 0 ถ้า RPC ไม่ตอบ (graceful fallback).
        """
        # ABI encode: getL1Fee(bytes) → uint256
        # data = selector + offset(32) + length(32) + padded_bytes
        hex_bytes = tx_bytes.hex()
        padded_len = (len(tx_bytes) + 31) // 32 * 32
        calldata = (
            _GET_L1_FEE_SEL
            + "0000000000000000000000000000000000000000000000000000000000000020"  # offset
            + format(len(tx_bytes), "064x")  # length
            + hex_bytes.ljust(padded_len * 2, "0")  # padded bytes
        )
        result = self._eth_call(_GAS_ORACLE_ADDR, calldata)
        if result and isinstance(result, str) and result.startswith("0x"):
            try:
                return int(result, 16)
            except ValueError:
                pass
        return 0

    def get_gas_price(self) -> int:
        """ดู current L2 gas price จาก GasPriceOracle (cache 12 วินาที).

        คืน gas price ใน wei. fallback เป็น 1 gwei ถ้า RPC ไม่ตอบ.
        """
        now = time.time()
        if now - self._gas_price_ts < self._cache_ttl and self._gas_price_cache > 0:
            return int(self._gas_price_cache)

        result = self._eth_call(_GAS_ORACLE_ADDR, _GAS_PRICE_SEL)
        if result and isinstance(result, str) and result.startswith("0x"):
            try:
                price = int(result, 16)
                self._gas_price_cache = price
                self._gas_price_ts = now
                return price
            except ValueError:
                pass
        return 1_000_000_000  # fallback: 1 gwei

    def estimate_total_cost(self, gas_units: int, tx_bytes: bytes | None = None) -> dict[str, float]:
        """ประมาณการ gas cost รวม (L2 execution + L1 data).

        คืน dict:
        {
            "l2_fee_eth": float,     # L2 execution cost (ETH)
            "l1_fee_eth": float,     # L1 data cost (ETH)
            "total_fee_eth": float,  # รวม (ETH)
            "gas_price_gwei": float, # L2 gas price (gwei)
        }
        """
        gas_price = self.get_gas_price()
        l2_fee = gas_units * gas_price

        l1_fee = 0
        if tx_bytes:
            l1_fee = self.get_l1_fee(tx_bytes)

        total = l2_fee + l1_fee
        return {
            "l2_fee_eth": l2_fee / 1e18,
            "l1_fee_eth": l1_fee / 1e18,
            "total_fee_eth": total / 1e18,
            "gas_price_gwei": gas_price / 1e9,
        }


# ──────────────────────────────────────────────
# Multicall3 — Batch on-chain reads
# ──────────────────────────────────────────────

# Multicall3 บน Base (ที่อยู่เดียวกันทุก EVM chain)
# https://www.multicall3.com/
_MULTICALL3_ADDR = "0xcA11bde05977b3631167028862bE2a173976CA11"
# Function selector for aggregate3((address,bool,bytes)[]) -> (bool,bytes)[]
_AGGREGATE3_SEL = "0x82ad56cb"
# ERC-20 balanceOf(address) selector
_BALANCE_OF_SEL = "0x70a08231"


class Multicall3Client:
    """Batch on-chain reads ผ่าน Multicall3 contract.

    รวม eth_call หลายตัวเป็น call เดียว — ลด RPC overhead และ latency
    เหมาะสำหรับดึง balance หลาย token พร้อมกัน

    ใช้ urllib แทน web3.py เพื่อลด dependency
    """

    def __init__(self, rpc_url: str = "https://mainnet.base.org", timeout_sec: int = 10) -> None:
        self.rpc_url = rpc_url
        self.timeout_sec = timeout_sec

    def _eth_call(self, to: str, data: str) -> str | None:
        """Raw eth_call ผ่าน JSON-RPC."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": to, "data": data}, "latest"],
        }
        req = Request(
            url=self.rpc_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.timeout_sec) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            result = body.get("result")
            return result if isinstance(result, str) else None
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return None

    def _encode_aggregate3(self, calls: list[tuple[str, str]]) -> str:
        """Encode aggregate3((address,bool,bytes)[]) calldata.

        calls: list of (target_address, call_data_hex)
        คืน hex string ของ calldata ที่พร้อมส่ง eth_call
        """
        # ABI encode: aggregate3(Call3[])
        # Call3 = (address target, bool allowFailure, bytes calldata)
        # offset สำหรับ array = 0x20
        # แต่ละ element: target(32) + allowFailure(32) + calldata_offset(32) + calldata_length(32) + calldata_padded
        n = len(calls)
        # offset สำหรับ array data
        array_offset = 0x20
        # แต่ละ element มี: target(32) + allowFailure(32) + offset_to_data(32) + length(32) + padded_data
        # element offset เริ่มที่ array_offset + n * 32 (แต่ละ element offset 32 bytes)
        element_offsets = []
        current_offset = array_offset + n * 32
        for _, call_data_hex in calls:
            element_offsets.append(current_offset)
            data_bytes = bytes.fromhex(call_data_hex.replace("0x", ""))
            padded_len = (len(data_bytes) + 31) // 32 * 32
            # target(32) + allowFailure(32) + data_offset(32) + data_length(32) + padded_data
            current_offset += 32 + 32 + 32 + 32 + padded_len

        # Build calldata
        result = _AGGREGATE3_SEL
        result += format(array_offset, "064x")  # offset to array

        # Array element offsets
        for offset in element_offsets:
            result += format(offset, "064x")

        # Array elements
        for target, call_data_hex in calls:
            data_bytes = bytes.fromhex(call_data_hex.replace("0x", ""))
            padded_len = (len(data_bytes) + 31) // 32 * 32
            result += target.lower().replace("0x", "").zfill(64)  # target address
            result += format(1, "064x")  # allowFailure = true
            result += format(0x60, "064x")  # offset to data (relative: 3 words after this)
            result += format(len(data_bytes), "064x")  # data length
            result += data_bytes.hex().ljust(padded_len * 2, "0")  # padded data

        return result

    def _decode_aggregate3(self, result_hex: str, n: int) -> list[bytes | None]:
        """Decode aggregate3 result — list of (success, returnData)."""
        if not result_hex or not result_hex.startswith("0x"):
            return [None] * n
        data = bytes.fromhex(result_hex.replace("0x", ""))
        # ABI decode: (bool success, bytes returnData)[]
        # offset สำหรับ array
        if len(data) < 32:
            return [None] * n
        array_offset = int.from_bytes(data[:32], "big")
        results = []
        pos = array_offset
        for _ in range(n):
            if pos + 64 > len(data):
                results.append(None)
                continue
            # success flag
            success = int.from_bytes(data[pos:pos + 32], "big") != 0
            # offset to returnData (relative)
            ret_offset = int.from_bytes(data[pos + 32:pos + 64], "big")
            ret_pos = pos + 32 + ret_offset
            if ret_pos + 32 > len(data):
                results.append(None)
                continue
            ret_len = int.from_bytes(data[ret_pos:ret_pos + 32], "big")
            ret_data = data[ret_pos + 32:ret_pos + 32 + ret_len]
            results.append(ret_data if success else None)
            # advance to next element: success(32) + ret_offset(32) + ret_len(32) + padded_ret
            padded_len = (ret_len + 31) // 32 * 32
            pos += 32 + 32 + 32 + padded_len
        return results

    def batch_balance_of(self, wallet: str, token_addresses: list[str]) -> dict[str, int | None]:
        """ดึง ERC-20 balance หลาย token พร้อมกัน — 1 RPC call.

        คืน dict: token_address -> balance (raw) หรือ None ถ้า fail
        """
        if not token_addresses:
            return {}
        if len(token_addresses) == 1:
            # single token — ไม่ต้อง multicall
            addr = token_addresses[0]
            wallet_padded = wallet.lower().replace("0x", "").zfill(64)
            calldata = _BALANCE_OF_SEL + wallet_padded
            result = self._eth_call(addr, calldata)
            if result and result.startswith("0x") and len(result) >= 66:
                return {addr: int(result, 16)}
            return {addr: None}

        # batch ผ่าน Multicall3
        wallet_padded = wallet.lower().replace("0x", "").zfill(64)
        calls = []
        for token_addr in token_addresses:
            calldata = _BALANCE_OF_SEL + wallet_padded
            calls.append((token_addr, calldata))

        agg_calldata = self._encode_aggregate3(calls)
        raw_result = self._eth_call(_MULTICALL3_ADDR, agg_calldata)
        decoded = self._decode_aggregate3(raw_result, len(calls))

        results = {}
        for i, token_addr in enumerate(token_addresses):
            ret = decoded[i]
            if ret is not None and len(ret) >= 32:
                results[token_addr] = int.from_bytes(ret[:32], "big")
            else:
                results[token_addr] = None
        return results


# ──────────────────────────────────────────────
# Transaction Builder — เตรียม swap payloads
# ──────────────────────────────────────────────

class TransactionBuilder:
    """สร้างและตรวจสอบ swap transaction payloads.

    ไม่ส่งธุรกรรมเอง — แค่เตรียมข้อมูลให้ LiveExecutor
    นำไปแสดงผลและขออนุมัติจากผู้ใช้ก่อน

    Phase 5: ใช้ GasOracle สำหรับ estimate L1 data fee ที่แม่นยำ
    """

    def __init__(self, mcp: BaseMCPClient, config: dict[str, Any], log=print) -> None:
        self.mcp = mcp
        self.gas_config = config.get("gas", {})
        self.slippage_config = config.get("slippage", {})
        self.token_map = config.get("tokens", {})
        self.log = log
        # GasOracle สำหรับ L1 data fee estimation
        rpc_url = config.get("rpc_url", "https://mainnet.base.org")
        timeout = int(config.get("timeout_sec", 30))
        self._gas_oracle = GasOracle(rpc_url, timeout)

    def resolve_token(self, symbol: str) -> str:
        """แปลง ticker symbol หรือ CoinGecko ID เป็นที่อยู่ token บน Base.

        รองรับทั้ง:
        - Ticker: ETH, USDC, AERO, DEGEN
        - CoinGecko ID: ethereum, aerodrome-finance, degen-base
        """
        # ลองแปลง CoinGecko ID -> ticker ก่อน
        ticker = _COINGECKO_TO_TICKER.get(symbol.lower(), symbol)
        symbol_upper = ticker.upper()
        if symbol_upper == "ETH":
            return _NATIVE_ETH
        if symbol_upper in self.token_map:
            return self.token_map[symbol_upper]
        raise LiveExecutionError(f"ไม่รู้จัก token '{symbol}' — เพิ่มใน config.live.tokens")

    def get_decimals(self, token_address: str) -> int:
        """ดู decimals ของ token (ใช้ cache ก่อน, fallback เป็น 18)."""
        return _DECIMALS.get(token_address.lower(), _DEFAULT_DECIMALS)

    def to_raw(self, amount: float, token_address: str) -> int:
        """แปลงจำนวน token ที่มนุษย์อ่านได้ -> raw integer (ตาม decimals)."""
        decimals = self.get_decimals(token_address)
        return int(Decimal(str(amount)) * Decimal(10 ** decimals))

    def from_raw(self, raw_amount: int, token_address: str) -> float:
        """แปลง raw integer -> จำนวน token ที่มนุษย์อ่านได้."""
        decimals = self.get_decimals(token_address)
        return float(Decimal(str(raw_amount)) / Decimal(10 ** decimals))

    def compute_slippage_bps(self, from_token: str, to_token: str) -> int:
        """คำนวณ slippage tolerance (basis points) ตามชนิดคู่ token.

        - stablecoin pair (USDC↔USDT ฯลฯ) ใช้ slippage ต่ำ
        - คู่ทั่วไปใช้ค่า default
        """
        stablecoins = {"usdc", "usdt", "dai"}
        token_addrs = {v.lower(): k for k, v in self.token_map.items()}
        from_name = token_addrs.get(from_token.lower(), "").lower()
        to_name = token_addrs.get(to_token.lower(), "").lower()
        if from_name in stablecoins and to_name in stablecoins:
            return int(self.slippage_config.get("stablecoin_bps", 10))
        return int(self.slippage_config.get("default_bps", 50))

    def prepare_swap(self, action: str, symbol: str, usd_amount: float,
                     price: float, wallet_address: str) -> tuple[SwapQuote, dict]:
        """เตรียม swap payload ครบชุด — quote + transaction data.

        คืน (quote, tx_data) พร้อมนำไปแสดงผลและขออนุมัติ
        """
        # กำหนดทิศทาง swap: buy = USDC -> token, sell = token -> USDC
        to_token_addr = self.resolve_token(symbol)
        from_token_addr = self.token_map.get("USDC", self.token_map.get("WETH", _NATIVE_ETH))

        if action == "sell":
            from_token_addr, to_token_addr = to_token_addr, from_token_addr
            # สำหรับ sell: แปลงจากจำนวน token ที่ถือ
            token_amount = usd_amount / price if price > 0 else 0
            raw_amount = self.to_raw(token_amount, from_token_addr)
        else:
            raw_amount = self.to_raw(usd_amount, from_token_addr)

        slippage_bps = self.compute_slippage_bps(from_token_addr, to_token_addr)
        max_slippage = int(self.slippage_config.get("max_bps", 300))
        if slippage_bps > max_slippage:
            raise SlippageExceededError(
                f"slippage {slippage_bps} bps เกินขีดจำกัด {max_slippage} bps"
            )

        # ขั้นตอนที่ 1: ขอราคาจาก MCP
        self.log(f"[live] ขอราคา swap {action} {symbol}...")
        quote = self.mcp.get_quote(from_token_addr, to_token_addr, raw_amount, slippage_bps)

        # ตรวจสอบว่า quote ยังไม่หมดอายุ
        if quote.expires_at < time.time():
            raise LiveExecutionError("quote หมดอายุแล้ว — กรุณาลองใหม่")

        # ตรวจสอบ gas price ไม่เกินขีดจำกัด
        max_fee_gwei = float(self.gas_config.get("max_fee_gwei", 50))
        gas_price_gwei = quote.gas_price / 1e9
        if gas_price_gwei > max_fee_gwei:
            raise GasSpikeError(
                f"gas price {gas_price_gwei:.2f} Gwei สูงเกินขีดจำกัด {max_fee_gwei} Gwei"
            )

        # ตรวจสอบ price impact — ถ้าสูงเกิน 5% ถือว่าเสี่ยงเกินไป
        if quote.price_impact > 5.0:
            raise SlippageExceededError(
                f"price impact {quote.price_impact:.2f}% สูงเกินไป — อาจไม่คุ้ม"
            )

        # ขั้นตอนที่ 2: สร้าง transaction payload
        self.log(f"[live] สร้าง transaction payload...")
        tx_data = self.mcp.build_transaction(quote, wallet_address)

        # ขั้นตอนที่ 2.5: Gas-aware cost estimation — ใช้ GasOracle สำหรับ L1 data fee ที่แม่น
        raw_tx = tx_data.get("rawTransaction") or tx_data.get("data", "")
        tx_bytes = bytes.fromhex(raw_tx.replace("0x", "")) if isinstance(raw_tx, str) and raw_tx.startswith("0x") else b""
        if tx_bytes:
            gas_cost = self._gas_oracle.estimate_total_cost(quote.gas_estimate, tx_bytes)
            quote.gas_price = int(gas_cost["gas_price_gwei"] * 1e9)
            # บันทึก L1/L2 breakdown สำหรับแสดงผล
            tx_data["_gas_breakdown"] = gas_cost

        return quote, tx_data


# ──────────────────────────────────────────────
# Live Executor — เทรดจริงบน Base chain
# ──────────────────────────────────────────────

class LiveExecutor(Executor):
    """เทรดจริงบน Base chain ผ่าน Base MCP.

    หลักการออกแบบ:
    1. ทุกธุรกรรมต้องผ่านการอนุมัติจากผู้ใช้ก่อนเสมอ (human-in-the-loop)
    2. ไม่ส่งธุรกรรมอัตโนมัติ — แค่เตรียม payload และแสดงข้อมูลให้ผู้ใช้ตัดสินใจ
    3. จัดการ exception อย่างครอบคลุม: network, gas, slippage, user rejection
    4. ใช้ Portfolio เป็น single source of truth สำหรับ position tracking (เดียวกับ Paper)
    """

    def __init__(self, portfolio: Portfolio, config: dict[str, Any],
                 wallet_address: str | None = None, log=print) -> None:
        self.pf = portfolio
        self.config = config
        self.log = log
        self.wallet_address = wallet_address or os.environ.get("BASE_WALLET_ADDRESS", "")

        # โหมดจำลอง: ไม่ส่งธุรกรรมจริง — ใช้ quote จริงแต่ skip send_tx
        self.dry_run = config.get("dry_run", True)

        # สร้าง MCP client
        rpc_url = config.get("rpc_url", "https://mainnet.base.org")
        chain_id = int(config.get("chain_id", _BASE_CHAIN_ID))
        timeout = int(config.get("timeout_sec", 30))
        mcp_server = config.get("mcp_server", "https://mcp.base.org")
        self._mcp = BaseMCPClient(mcp_server, chain_id, timeout, log)

        # สร้าง transaction builder
        self._builder = TransactionBuilder(self._mcp, config, log)

        # ตั้งค่า approval flow
        approval_config = config.get("approval", {})
        self._require_approval = approval_config.get("require_user_confirmation", True)
        self._approval_timeout = int(approval_config.get("approval_timeout_sec", 300))
        self._show_preview = approval_config.get("show_tx_preview", True)

        # Phase 6: Flashbots Protect — submission RPC routing
        # Base sequencer มี MEV resistance ในตัว → ใช้ base_native สำหรับ DEX swaps
        # L1 bridge operations → ใช้ Flashbots Protect RPC เพื่อป้องกัน MEV บน L1
        sub_rpc = config.get("submission_rpc", {})
        self._rpc_base_native = sub_rpc.get("base_native", rpc_url)
        self._rpc_l1_bridge = sub_rpc.get("l1_bridge", "https://rpc.flashbots.net/fast")

    def _validate_wallet(self) -> None:
        """ตรวจสอบว่าตั้งค่า wallet address แล้ว."""
        if not self.wallet_address:
            raise LiveExecutionError(
                "ยังไม่ได้ตั้งค่า wallet address — "
                "ตั้งค่า BASE_WALLET_ADDRESS ใน .env หรือส่งเข้ามาตอนสร้าง LiveExecutor"
            )

    def _generate_dry_tx_hash(self) -> str:
        """สร้าง tx hash จำลองสำหรับ dry-run mode (ไม่ส่งจริง)."""
        return f"dry_run_{uuid.uuid4().hex[:16]}"

    def _format_quote_preview(self, quote: SwapQuote, action: str, symbol: str,
                               tx_data: dict | None = None) -> str:
        """สร้างข้อความแสดงตัวอย่างธุรกรรมสำหรับผู้ใช้."""
        from_amount = self._builder.from_raw(quote.from_amount, quote.from_token)
        to_amount = self._builder.from_raw(quote.to_amount, quote.to_token)
        min_amount = self._builder.from_raw(quote.min_amount, quote.to_token)

        # Phase 5: แสดง L1/L2 breakdown ถ้ามี
        gas_breakdown = (tx_data or {}).get("_gas_breakdown")
        if gas_breakdown:
            gas_line = (f"║  Gas (est.) : {gas_breakdown['total_fee_eth']:.6f} ETH "
                        f"(L2={gas_breakdown['l2_fee_eth']:.6f} + L1={gas_breakdown['l1_fee_eth']:.6f})")
        else:
            gas_cost_eth = (quote.gas_estimate * quote.gas_price) / 1e18
            gas_line = f"║  Gas (est.) : {gas_cost_eth:.6f} ETH ({quote.gas_estimate:,} units)"

        route_str = " → ".join(quote.route) if quote.route else "direct"
        lines = [
            "╔══════════════════════════════════════════════════════╗",
            "║          รายละเอียดธุรกรรม — ก่อนอนุมัติ             ║",
            "╠══════════════════════════════════════════════════════╣",
            f"║  Action     : {action.upper()} {symbol}",
            f"║  From       : {from_amount:.6f} ({quote.from_token[:10]}...)",
            f"║  To (est.)  : {to_amount:.6f} ({quote.to_token[:10]}...)",
            f"║  Min. recv  : {min_amount:.6f} (slippage protection)",
            f"║  Price imp. : {quote.price_impact:.2f}%",
            gas_line,
            f"║  Route      : {route_str}",
            "╚══════════════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)

    def _request_user_approval(self, quote: SwapQuote, tx_data: dict,
                               action: str, symbol: str) -> bool:
        """ขออนุมัติจากผู้ใช้ก่อนส่งธุรกรรม.

        ขั้นตอน:
        1. แสดงรายละเอียดธุรกรรม (quote preview)
        2. แสดง approval URL (ถ้ามี) ให้ผู้ใช้เปิดใน Base Account
        3. รอผู้ใช้ยืนยัน (timeout ตาม config)

        คืน True ถ้าผู้ใช้อนุมัติ, False ถ้าไม่อนุมัติหรือหมดเวลา
        """
        if not self._require_approval:
            return True

        # โหมดจำลอง: ข้ามการอนุมัติอัตโนมัติ (ไม่ต้องมี terminal)
        if self.dry_run:
            self.log("[live:dry] ข้ามการอนุมัติอัตโนมัติ (จำลอง)")
            return True

        # แสดงตัวอย่างธุรกรรม (Phase 5: ส่ง tx_data สำหรับ L1/L2 breakdown)
        if self._show_preview:
            preview = self._format_quote_preview(quote, action, symbol, tx_data)
            self.log(preview)

        # แสดง approval URL (ถ้า MCP ส่งมา)
        approval_url = tx_data.get("approvalUrl") or tx_data.get("signingUrl")
        if approval_url:
            self.log(f"\n🔗 ลิงก์อนุมัติธุรกรรม (เปิดใน Base Account):")
            self.log(f"   {approval_url}")
            self.log(f"   (หมดอายุใน {self._approval_timeout} วินาที)")

        # แสดง raw transaction data สำหรับผู้ใช้ที่ต้องการตรวจสอบเอง
        if tx_data.get("to") and tx_data.get("data"):
            self.log(f"\n📋 ข้อมูลธุรกรรม (สำหรับตรวจสอบ):")
            self.log(f"   To   : {tx_data['to']}")
            self.log(f"   Value: {tx_data.get('value', '0x0')}")
            self.log(f"   Data : {tx_data.get('data', '0x')[:66]}...")

        # รอการยืนยันจากผู้ใช้
        self.log(f"\n⏳ รอการอนุมัติ... (timeout {self._approval_timeout} วินาที)")
        try:
            response = input("   อนุมัติธุรกรรมนี้? (y/n): ").strip().lower()
            if response in ("y", "yes", "ยืนยัน"):
                self.log("✅ ผู้ใช้อนุมัติธุรกรรม")
                return True
            else:
                self.log("❌ ผู้ใช้ปฏิเสธธุรกรรม")
                return False
        except (EOFError, KeyboardInterrupt):
            self.log("❌ ผู้ใช้ยกเลิก (interrupt)")
            return False

    def _submit_transaction(self, tx_data: dict, operation: str = "swap") -> str:
        """ส่งธุรกรรมที่ผู้ใช้อนุมัติแล้วไปยัง chain ผ่าน MCP.

        Phase 6: Flashbots Protect — เลือก RPC ตามประเภท operation:
        - "swap" (Base DEX) → Base native sequencer (มี MEV resistance ในตัว)
        - "bridge" (L1 bridge) → Flashbots Protect RPC (ป้องกัน MEV บน L1)

        คืน transaction hash.
        """
        rpc_label = "Base native" if operation == "swap" else "Flashbots Protect"
        self.log(f"[live] กำลังส่งธุรกรรมไปยัง {rpc_label}...")
        result = self._mcp.call_tool("send_tx", {
            "chainId": int(self.config.get("chain_id", _BASE_CHAIN_ID)),
            "transaction": tx_data,
            "rpcUrl": self._rpc_l1_bridge if operation == "bridge" else self._rpc_base_native,
        })
        tx_hash = result.get("txHash") or result.get("hash")
        if not tx_hash:
            raise MCPProtocolError("MCP ไม่ส่ง txHash กลับมา — ไม่สามารถยืนยันธุรกรรมได้")
        return tx_hash

    def buy(self, symbol: str, usd_amount: float, price: float, reason: str) -> Trade | None:
        """ซื้อ token ด้วย USDC ผ่าน Base MCP.

        ขั้นตอน:
        1. ตรวจสอบ wallet
        2. เตรียม swap payload (quote + tx data)
        3. ขออนุมัติจากผู้ใช้ (human-in-the-loop) — dry-run: auto-approve
        4. ส่งธุรกรรม (dry-run: skip, ใช้ fake hash)
        5. บันทึก trade ผ่าน Portfolio (single source of truth)

        คืน Trade ถ้าสำเร็จ, None ถ้าล้มเหลวหรือถูกปฏิเสธ (ไม่ raise)
        """
        try:
            self._validate_wallet()

            # ขั้นตอนที่ 1-2: เตรียม swap
            quote, tx_data = self._builder.prepare_swap(
                "buy", symbol, usd_amount, price, self.wallet_address
            )

            # ขั้นตอนที่ 3: ขออนุมัติ
            approved = self._request_user_approval(quote, tx_data, "buy", symbol)
            if not approved:
                self.log(f"[live] BUY {symbol} ถูกปฏิเสธ — ข้าม")
                return None

            # ขั้นตอนที่ 4: ส่งธุรกรรม (dry-run: ใช้ hash จำลอง)
            if self.dry_run:
                tx_hash = self._generate_dry_tx_hash()
                self.log(f"[live:dry] SIMULATED — ไม่ได้ส่งธุรกรรมจริง  tx: {tx_hash}")
            else:
                tx_hash = self._submit_transaction(tx_data, operation="swap")

            # ขั้นตอนที่ 5: บันทึกผ่าน Portfolio (เหมือน PaperExecutor)
            trade = self.pf.buy(symbol, usd_amount, price, reason,
                                tx_hash=tx_hash, mode="live")
            if trade:
                self.log(f"[live] BUY {trade.qty:.6f} {symbol} @ ${price:,.2f}  tx: {tx_hash}")
            return trade

        except LiveExecutionError as exc:
            self.log(f"[live] BUY {symbol} ล้มเหลว: {exc}")
            return None
        except Exception as exc:
            self.log(f"[live] BUY {symbol} error ที่ไม่คาดคิด: {exc}")
            return None

    def sell(self, symbol: str, price: float, reason: str, fraction: float = 1.0) -> Trade | None:
        """ขาย token กลับเป็น USDC ผ่าน Base MCP.

        ขั้นตอนเดียวกับ buy แต่กลับทิศทาง swap.
        คืน Trade ถ้าสำเร็จ, None ถ้าล้มเหลวหรือถูกปฏิเสธ (ไม่ raise)
        """
        try:
            self._validate_wallet()

            # คำนวณมูลค่าที่จะขาย
            pos = self.pf.positions.get(symbol)
            if not pos:
                return None
            sell_qty = pos.qty * max(0.0, min(fraction, 1.0))
            if sell_qty <= 0:
                return None
            usd_amount = sell_qty * price

            # ขั้นตอนที่ 1-2: เตรียม swap (กลับทิศทาง)
            quote, tx_data = self._builder.prepare_swap(
                "sell", symbol, usd_amount, price, self.wallet_address
            )

            # ขั้นตอนที่ 3: ขออนุมัติ
            approved = self._request_user_approval(quote, tx_data, "sell", symbol)
            if not approved:
                self.log(f"[live] SELL {symbol} ถูกปฏิเสธ — ข้าม")
                return None

            # ขั้นตอนที่ 4: ส่งธุรกรรม (dry-run: ใช้ hash จำลอง)
            if self.dry_run:
                tx_hash = self._generate_dry_tx_hash()
                self.log(f"[live:dry] SIMULATED — ไม่ได้ส่งธุรกรรมจริง  tx: {tx_hash}")
            else:
                tx_hash = self._submit_transaction(tx_data, operation="swap")

            # ขั้นตอนที่ 5: บันทึกผ่าน Portfolio (เหมือน PaperExecutor)
            trade = self.pf.sell(symbol, price, reason, fraction,
                                 tx_hash=tx_hash, mode="live")
            if trade:
                self.log(f"[live] SELL {trade.qty:.6f} {symbol} @ ${price:,.2f}  tx: {tx_hash}")
            return trade

        except LiveExecutionError as exc:
            self.log(f"[live] SELL {symbol} ล้มเหลว: {exc}")
            return None
        except Exception as exc:
            self.log(f"[live] SELL {symbol} error ที่ไม่คาดคิด: {exc}")
            return None
