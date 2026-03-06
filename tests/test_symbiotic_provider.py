"""
Tests for SymbioticProvider.

Unit tests use mocked httpx responses.
Live test (marked @pytest.mark.live) hits DefiLlama directly.
"""

import json
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from wrdata.providers.symbiotic_provider import SymbioticProvider


# =============================================================================
# Fixtures
# =============================================================================


MOCK_PROTOCOL_DATA = {
    "name": "Symbiotic",
    "tvl": [
        {"date": 1709251200, "totalLiquidityUSD": 1_000_000_000},
        {"date": 1709337600, "totalLiquidityUSD": 1_050_000_000},
        {"date": 1709424000, "totalLiquidityUSD": 1_080_000_000},
    ],
    "currentChainTvls": {
        "Ethereum": 900_000_000,
        "Arbitrum": 180_000_000,
    },
    "tokensInUsd": [
        {
            "date": 1709424000,
            "tokens": {
                "WETH": 500_000_000,
                "wstETH": 300_000_000,
                "sfrxETH": 150_000_000,
                "cbETH": 130_000_000,
            },
        }
    ],
    "chainTvls": {},
}

MOCK_VAULTS_RESPONSE = {
    "data": {
        "vaults": [
            {
                "id": "0xabc123",
                "collateral": "0xweth",
                "activeStake": "5000000000000000000000",
                "slasher": "0xslash",
                "epochDuration": "604800",
                "depositWhitelist": False,
                "isDepositLimit": False,
                "createdTimestamp": "1709251200",
                "createdBlockNumber": "19000000",
            }
        ]
    }
}

MOCK_OPERATORS_RESPONSE = {
    "data": {
        "operators": [
            {
                "id": "0xop1",
                "networkOptInsCount": "3",
                "vaultOptInsCount": "5",
                "createdTimestamp": "1709251200",
                "createdBlockNumber": "19000000",
            }
        ]
    }
}


@pytest.fixture
def provider():
    """Create a SymbioticProvider with no API keys."""
    p = SymbioticProvider()
    yield p
    p.close()


# =============================================================================
# Unit tests — initialization
# =============================================================================


@pytest.mark.unit
class TestInit:
    def test_provider_name(self, provider):
        assert provider.name == "symbiotic"

    def test_no_keys_by_default(self, provider):
        assert provider._alchemy_key is None
        assert provider._thegraph_key is None

    def test_with_keys(self):
        p = SymbioticProvider(
            alchemy_api_key="alchemy-key", thegraph_api_key="graph-key"
        )
        assert p._alchemy_key == "alchemy-key"
        assert p._thegraph_key == "graph-key"
        p.close()

    def test_lazy_client(self, provider):
        assert provider._client is None
        client = provider.client
        assert client is not None

    def test_options_not_supported(self, provider):
        expirations = provider.get_available_expirations("ANYTHING")
        assert expirations == []

    def test_options_chain_returns_error(self, provider):
        from wrdata.models.schemas import OptionsChainRequest

        request = OptionsChainRequest(symbol="SYMBIOTIC")
        result = provider.fetch_options_chain(request)
        assert result.success is False
        assert "restaking" in result.error.lower()
        assert result.calls == []
        assert result.puts == []


# =============================================================================
# Unit tests — DefiLlama data
# =============================================================================


@pytest.mark.unit
class TestDefiLlamaData:
    @patch.object(SymbioticProvider, "_get_protocol_data")
    def test_fetch_timeseries_tvl(self, mock_proto, provider):
        mock_proto.return_value = MOCK_PROTOCOL_DATA

        result = provider.fetch_timeseries(
            symbol="TVL",
            start_date="2024-02-29",
            end_date="2024-03-03",
        )

        assert result.success is True
        assert result.provider == "symbiotic"
        assert len(result.data) > 0
        assert "tvl" in result.data[0]
        assert "date" in result.data[0]

    @patch.object(SymbioticProvider, "_get_protocol_data")
    def test_fetch_timeseries_flows(self, mock_proto, provider):
        mock_proto.return_value = MOCK_PROTOCOL_DATA

        result = provider.fetch_timeseries(
            symbol="TVL",
            start_date="2024-02-29",
            end_date="2024-03-03",
            data_type="flows",
        )

        assert result.success is True
        for row in result.data:
            assert "net_flow" in row
            assert "deposit" in row
            assert "withdrawal" in row

    @patch.object(SymbioticProvider, "_query_subgraph")
    @patch.object(SymbioticProvider, "_get_protocol_data")
    def test_fetch_protocol_summary(self, mock_proto, mock_subgraph, provider):
        mock_proto.return_value = MOCK_PROTOCOL_DATA
        mock_subgraph.side_effect = [
            {"vaults": []},
            {"vaultCounter": {"count": "10"}},
            {"operators": []},
            {"operatorCounter": {"count": "5"}},
        ]

        summary = provider.fetch_protocol_summary()

        assert summary["tvl"] == 1_080_000_000
        assert summary["change_24h"] == 30_000_000
        assert summary["vault_count"] == 10
        assert summary["operator_count"] == 5
        assert "tvl_formatted" in summary
        assert "last_updated" in summary

    @patch.object(SymbioticProvider, "_get_protocol_data")
    def test_collateral_breakdown(self, mock_proto, provider):
        mock_proto.return_value = MOCK_PROTOCOL_DATA

        breakdown = provider.fetch_collateral_breakdown()

        assert len(breakdown) == 4
        assert breakdown[0]["token"] == "WETH"
        assert breakdown[0]["tvl_usd"] == 500_000_000
        total_share = sum(t["share_pct"] for t in breakdown)
        assert abs(total_share - 100.0) < 0.1

    @patch.object(SymbioticProvider, "_get_protocol_data")
    def test_daily_flows(self, mock_proto, provider):
        mock_proto.return_value = MOCK_PROTOCOL_DATA

        flows = provider.fetch_daily_flows("2024-02-29", "2024-03-03")

        assert len(flows) == 2
        # First delta: 1.05B - 1B = +50M deposit
        assert flows[0]["deposit"] == 50_000_000
        assert flows[0]["withdrawal"] == 0
        # Second delta: 1.08B - 1.05B = +30M deposit
        assert flows[1]["net_flow"] == 30_000_000

    def test_fetch_timeseries_error_handling(self, provider):
        """Bad date format should return error response."""
        result = provider.fetch_timeseries(
            symbol="TVL",
            start_date="bad-date",
            end_date="2024-03-03",
        )
        assert result.success is False
        assert result.error is not None


# =============================================================================
# Unit tests — subgraph
# =============================================================================


@pytest.mark.unit
class TestSubgraph:
    def test_subgraph_url_no_key(self, provider):
        url = provider._get_subgraph_url()
        assert "studio.thegraph.com" in url

    def test_subgraph_url_with_key(self):
        p = SymbioticProvider(thegraph_api_key="my-key")
        url = p._get_subgraph_url()
        assert "my-key" in url
        assert "gateway.thegraph.com" in url
        p.close()

    @patch.object(SymbioticProvider, "_query_subgraph")
    def test_fetch_vaults(self, mock_query, provider):
        # First call: vault list, second call: count
        mock_query.side_effect = [
            {"vaults": MOCK_VAULTS_RESPONSE["data"]["vaults"]},
            {"vaultCounter": {"count": "42"}},
        ]

        result = provider.fetch_vaults(limit=10)

        assert result["total_count"] == 42
        assert len(result["vaults"]) == 1
        vault = result["vaults"][0]
        assert vault["address"] == "0xabc123"
        assert vault["active_stake_eth"] == 5000.0

    @patch.object(SymbioticProvider, "_query_subgraph")
    def test_fetch_operators(self, mock_query, provider):
        mock_query.side_effect = [
            {"operators": MOCK_OPERATORS_RESPONSE["data"]["operators"]},
            {"operatorCounter": {"count": "15"}},
        ]

        result = provider.fetch_operators(limit=10)

        assert result["total_count"] == 15
        assert len(result["operators"]) == 1
        op = result["operators"][0]
        assert op["address"] == "0xop1"
        assert op["network_opt_ins"] == 3

    @patch.object(SymbioticProvider, "_query_subgraph")
    def test_subgraph_error_fallback(self, mock_query, provider):
        mock_query.side_effect = RuntimeError("Subgraph unavailable")

        result = provider.fetch_vaults()

        assert result["vaults"] == []
        assert result["source"] == "unavailable"
        assert "error" in result


# =============================================================================
# Unit tests — formatting
# =============================================================================


@pytest.mark.unit
class TestFormatting:
    def test_format_usd_billions(self):
        assert SymbioticProvider._format_usd(1_500_000_000) == "$1.50B"

    def test_format_usd_millions(self):
        assert SymbioticProvider._format_usd(42_000_000) == "$42.00M"

    def test_format_usd_thousands(self):
        assert SymbioticProvider._format_usd(5_500) == "$5.5K"

    def test_format_usd_small(self):
        assert SymbioticProvider._format_usd(99.50) == "$99.50"


# =============================================================================
# Unit tests — validate_connection
# =============================================================================


@pytest.mark.unit
class TestValidation:
    def test_validate_connection_success(self, provider):
        mock_response = MagicMock()
        mock_response.status_code = 200
        provider._client = MagicMock()
        provider._client.is_closed = False
        provider._client.get.return_value = mock_response

        assert provider.validate_connection() is True

    def test_validate_connection_failure(self, provider):
        provider._client = MagicMock()
        provider._client.is_closed = False
        provider._client.get.side_effect = Exception("Network error")

        assert provider.validate_connection() is False


# =============================================================================
# Live integration test — hits DefiLlama (no API key needed)
# =============================================================================


@pytest.mark.live
class TestLiveDefiLlama:
    """Tests that hit the real DefiLlama API. Run with: pytest -m live"""

    def test_validate_connection_live(self):
        p = SymbioticProvider()
        assert p.validate_connection() is True
        p.close()

    def test_fetch_protocol_summary_live(self):
        p = SymbioticProvider()
        summary = p.fetch_protocol_summary()
        assert summary["tvl"] > 0
        assert summary["tvl_formatted"].startswith("$")
        p.close()

    def test_fetch_tvl_history_live(self):
        p = SymbioticProvider()
        result = p.fetch_timeseries(
            symbol="TVL",
            start_date="2024-06-01",
            end_date="2024-12-31",
        )
        assert result.success is True
        assert len(result.data) > 0
        p.close()

    def test_collateral_breakdown_live(self):
        p = SymbioticProvider()
        breakdown = p.fetch_collateral_breakdown()
        assert len(breakdown) > 0
        assert "token" in breakdown[0]
        assert "tvl_usd" in breakdown[0]
        p.close()

    def test_data_source_status_live(self):
        p = SymbioticProvider()
        status = p.get_data_source_status()
        assert status["defillama"] is True
        assert "subgraph" in status
        p.close()
