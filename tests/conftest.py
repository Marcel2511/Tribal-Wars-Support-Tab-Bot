"""Pytest configuration and shared fixtures."""
import pytest
from datetime import datetime
from dataclasses import dataclass
from typing import Dict
import pytz


@dataclass
class MockDorf:
    """Mock village for testing."""
    dorf_name: str
    koordinaten: str
    truppen: Dict[str, int]
    rest_truppen: Dict[str, int] = None

    def __post_init__(self):
        if self.rest_truppen is None:
            self.rest_truppen = self.truppen.copy()


@dataclass
class MockAngriff:
    """Mock attack for testing."""
    ziel_koord: str
    ankunftszeit: datetime
    einheit: str = ""


@pytest.fixture
def berlin_tz():
    """Berlin timezone fixture."""
    return pytz.timezone("Europe/Berlin")


@pytest.fixture
def sample_doerfer():
    """Sample villages with troops for testing."""
    return [
        MockDorf(
            dorf_name="Dorf 1",
            koordinaten="500|500",
            truppen={
                "Speerträger": 1000,
                "Schwertkämpfer": 1000,
                "Axtkämpfer": 500,
                "Späher": 100,
                "Leichte Kavallerie": 200,
                "Schwere Kavallerie": 500,
                "Rammböcke": 50,
                "Katapulte": 100
            }
        ),
        MockDorf(
            dorf_name="Dorf 2",
            koordinaten="510|510",
            truppen={
                "Speerträger": 2000,
                "Schwertkämpfer": 1500,
                "Axtkämpfer": 1000,
                "Späher": 200,
                "Leichte Kavallerie": 300,
                "Schwere Kavallerie": 400,
                "Rammböcke": 100,
                "Katapulte": 150
            }
        ),
        MockDorf(
            dorf_name="Dorf 3",
            koordinaten="520|495",
            truppen={
                "Speerträger": 500,
                "Schwertkämpfer": 500,
                "Axtkämpfer": 250,
                "Späher": 50,
                "Leichte Kavallerie": 100,
                "Schwere Kavallerie": 200,
                "Rammböcke": 25,
                "Katapulte": 50
            }
        )
    ]


@pytest.fixture
def sample_angriffe(berlin_tz):
    """Sample attacks for testing."""
    return [
        MockAngriff(
            ziel_koord="505|505",
            ankunftszeit=berlin_tz.localize(datetime(2026, 1, 25, 12, 0, 0))
        ),
        MockAngriff(
            ziel_koord="515|515",
            ankunftszeit=berlin_tz.localize(datetime(2026, 1, 25, 13, 30, 0))
        ),
        MockAngriff(
            ziel_koord="525|500",
            ankunftszeit=berlin_tz.localize(datetime(2026, 1, 25, 14, 0, 0))
        )
    ]


@pytest.fixture
def standard_tabgroessen():
    """Standard tab sizes for testing."""
    return [
        {
            "Speerträger": 100,
            "Schwertkämpfer": 100,
            "Schwere Kavallerie": 100
        }
    ]


@pytest.fixture
def multiple_tabgroessen():
    """Multiple tab size configurations."""
    return [
        {
            "Speerträger": 100,
            "Schwertkämpfer": 100,
            "Schwere Kavallerie": 100
        },
        {
            "Speerträger": 200,
            "Schwertkämpfer": 200,
        },
        {
            "Schwere Kavallerie": 150
        }
    ]
