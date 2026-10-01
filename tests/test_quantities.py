from decimal import Decimal

from core.quantities import quantities


def test_indian_and_international_units_have_equivalent_values():
    assert quantities("8 lakh, 2.5 lakh, fifty thousand, 2,50,000") == {
        Decimal(800000),
        Decimal(250000),
        Decimal(50000),
    }
    assert quantities("8,000,000") != quantities("8 lakh")


def test_presentational_list_numbers_are_not_treated_as_facts():
    assert quantities("1. Register online.\n2. Upload documents.") == set()
    assert quantities("Step 3: submit") == set()
    assert quantities("first year, second year, SSC/10th") == {Decimal(1), Decimal(2), Decimal(10)}
