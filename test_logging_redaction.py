"""Regression tests for credentials and wallet identifiers in logs."""

import logging
import sys
import unittest

from akitafolio.http_client import RedactingFormatter, SecretsFilter


TELEGRAM_TOKEN = "123456789:AAEexampleTokenValueThatMustNeverAppearInLogs"
INFURA_ID = "0123456789abcdef0123456789abcdef"
EVM_ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"
XPUB = "xpub" + "1" * 100


class LoggingRedactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.formatter = RedactingFormatter("%(levelname)s %(message)s")

    def render(self, message, args=(), exc_info=None) -> str:
        record = logging.LogRecord(
            "test",
            logging.ERROR,
            __file__,
            1,
            message,
            args,
            exc_info,
        )
        return self.formatter.format(record)

    def assert_redacted(self, output: str, *values: str) -> None:
        for value in values:
            self.assertNotIn(value, output)
        self.assertIn("***MASKED***", output)

    def test_redacts_telegram_and_infura_urls(self) -> None:
        output = self.render(
            "request https://api.telegram.org/bot%s/getUpdates and "
            "https://mainnet.infura.io/v3/%s",
            (TELEGRAM_TOKEN, INFURA_ID),
        )
        self.assert_redacted(output, TELEGRAM_TOKEN, INFURA_ID)

    def test_redacts_key_value_without_masking_regular_token_text(self) -> None:
        output = self.render("token=%s; token tracking enabled", (TELEGRAM_TOKEN,))
        self.assert_redacted(output, TELEGRAM_TOKEN)
        self.assertIn("token tracking enabled", output)

    def test_redacts_logging_arguments_and_wallet_identifiers(self) -> None:
        record = logging.LogRecord(
            "test", logging.WARNING, __file__, 1,
            "address=%s xpub=%s", (EVM_ADDRESS, XPUB), None,
        )
        self.assertTrue(SecretsFilter().filter(record))
        output = self.formatter.format(record)
        self.assert_redacted(output, EVM_ADDRESS, XPUB)

    def test_redacts_exception_text(self) -> None:
        try:
            raise RuntimeError(f"token={TELEGRAM_TOKEN}")
        except RuntimeError:
            output = self.render("upstream request failed", exc_info=sys.exc_info())
        self.assert_redacted(output, TELEGRAM_TOKEN)


if __name__ == "__main__":
    unittest.main()
