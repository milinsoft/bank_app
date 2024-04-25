import os
import pathlib
import unittest
from decimal import Decimal
from logging import getLogger
from typing import TYPE_CHECKING, Optional

import settings
from app.cli import BankAppCli
from app.database import Database
from app.domain_classes import AccountType
from app.models import Base

if TYPE_CHECKING:
    from datetime import date

    from app.domain_classes import TransactionData
    from app.models import BankApp


# Done this way to make sure CI works
test_directory = pathlib.Path(__file__).parent.absolute().resolve() / "data"
# Paths to data folders
correct_test_files_dir = f"{test_directory}/correct"
incorrect_test_files_dir = f"{test_directory}/incorrect"

_logger = getLogger(__name__)


def convert_to_decimal(amount: float, rounding: str) -> Decimal:
    return Decimal(amount).quantize(Decimal("0.00"), rounding=rounding)


class TestBankAppCommon(unittest.TestCase):
    """Test cases for the BankAppCli class."""

    # TODO: try change to SetUpClass
    def setUp(self) -> None:
        """Set up the test environment."""
        self.db: "Database" = Database(settings.TEST_DB_URL)
        self.bank_app: "BankApp" = BankAppCli(self.db)
        self.credit_acc_id: int = self.bank_app.acc_service.create_one(self.bank_app.uow, AccountType.DEBIT)
        self.debit_acc_id: int = self.bank_app.acc_service.create_one(self.bank_app.uow, AccountType.CREDIT)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.db.engine)

    # noinspection PyPep8Naming
    @classmethod
    def tearDownClass(cls) -> None:
        """Remove sqlite database (if applicable) after all tests run."""
        try:
            os.remove(settings.TEST_DB_URL.replace("sqlite:///", ""))
        except FileNotFoundError:
            pass
        except OSError as e:
            _logger.error(e)

    # HELPER METHODS
    def parse_data(self, file_path: str) -> list["TransactionData"]:
        return self.bank_app.parser.parse_data(file_path)

    def get_balance(self, account_id: int, trx_date: Optional["date"] = None) -> Decimal:
        return self.bank_app.acc_service.get_balance(self.bank_app.uow, account_id, trx_date)

    def create_transactions(self, account_id: int, data: list["TransactionData"]) -> tuple[list[int], "Decimal"]:
        return self.bank_app.trx_service.create(self.bank_app.uow, account_id, data)

    def _test_credit_limit(
        self, account_id: int, transactions: list["TransactionData"], expect_error: bool
    ) -> tuple[list[int], Decimal] | None:
        new_transactions: list[int] = []
        balance: Decimal = Decimal(0)
        if not expect_error:
            new_transactions, balance = self.create_transactions(account_id, transactions)
        else:
            with self.assertRaisesRegex(ValueError, "Impossible to import data"):
                new_transactions, balance = self.create_transactions(account_id, transactions)
        return new_transactions, balance