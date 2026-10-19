import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, override

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import quotes  # noqa: E402

PRINTED = "the quick brown fox jumps over the lazy dog and then keeps running for a while"


def answering(text: str) -> Any:
    class Answered:
        stdout = text

    def reader(*rest: object, **named: object) -> Answered:
        return Answered()

    return reader


def refuse(*rest: object, **named: object) -> None:
    raise FileNotFoundError("pdftotext")


class FlattenTest(unittest.TestCase):
    def test_punctuation_and_spacing_stop_mattering(self) -> None:
        # Arrange
        text = "A, b.  C!"

        # Act
        found = quotes.flatten(text)

        # Assert
        self.assertEqual(found, "abc")

    def test_a_typographic_dash_reads_as_a_plain_one(self) -> None:
        # Arrange
        text = f"a{chr(0x2014)}b"

        # Act
        found = quotes.flatten(text)

        # Assert
        self.assertEqual(found, "ab")

    def test_a_curly_quote_reads_as_a_straight_one(self) -> None:
        # Arrange
        text = f"it{chr(0x2019)}s"

        # Act
        found = quotes.flatten(text)

        # Assert
        self.assertEqual(found, "its")

    def test_and_a_typographic_double_quote_does_too(self) -> None:
        # Arrange
        text = f"{chr(0x201C)}x{chr(0x201D)}"

        # Act
        found = quotes.flatten(text)

        # Assert
        self.assertEqual(found, "x")


class WindowTest(unittest.TestCase):
    def test_a_quote_shorter_than_the_window_is_one_window(self) -> None:
        # Arrange
        text = "a b c"

        # Act
        found = quotes.windows(text)

        # Assert
        self.assertEqual(found, ["abc"])

    def test_a_longer_one_is_scored_on_overlapping_runs(self) -> None:
        # Arrange
        text = PRINTED

        # Act
        found = quotes.windows(text)

        # Assert
        self.assertEqual(len(found), 16 - quotes.WINDOW + 1)


class ReadingTest(unittest.TestCase):
    def test_a_quote_is_found_where_it_sits(self) -> None:
        # Arrange
        record = {"quote": "hello"}

        # Act
        found = quotes.said(record, "here")

        # Assert
        self.assertEqual(found, [("here.quote", "hello")])

    def test_a_key_that_merely_ends_in_quote_is_read_too(self) -> None:
        # Arrange
        record = {"unusedBitsQuote": "hello"}

        # Act
        found = quotes.said(record)

        # Assert
        self.assertEqual(found, [("unusedBitsQuote", "hello")])

    def test_a_list_of_quotes_is_read_item_by_item(self) -> None:
        # Arrange
        record = {"quotes": ["one", "two"]}

        # Act
        found = quotes.said(record)

        # Assert
        self.assertEqual(found, [("quotes[0]", "one"), ("quotes[1]", "two")])

    def test_a_list_entry_that_is_not_a_sentence_is_left_alone(self) -> None:
        # Arrange
        record = {"quotes": ["one", 2]}

        # Act
        found = quotes.said(record)

        # Assert
        self.assertEqual(found, [("quotes[0]", "one")])

    def test_a_plural_key_of_its_own_name_holds_several(self) -> None:
        # Arrange
        record = {"aboutQuotes": ["one", "two"]}

        # Act
        found = quotes.said(record)

        # Assert
        self.assertEqual(found, [("aboutQuotes[0]", "one"), ("aboutQuotes[1]", "two")])

    def test_and_a_numbered_map_of_them_keeps_the_number_printed_beside_each(self) -> None:
        # Arrange
        record = {"noteQuotes": {"1": "first", "14": "fourteenth"}}

        # Act
        found = quotes.said(record)

        # Assert
        self.assertEqual(found, [("noteQuotes.1", "first"), ("noteQuotes.14", "fourteenth")])

    def test_a_numbered_map_carrying_something_that_is_not_a_passage_skips_it(self) -> None:
        # Arrange
        record = {"noteQuotes": {"1": "first", "2": 2}}

        # Act
        found = quotes.said(record)

        # Assert
        self.assertEqual(found, [("noteQuotes.1", "first")])

    def test_a_quote_inside_a_list_of_objects_is_reached(self) -> None:
        # Arrange
        record = [{"quote": "hello"}]

        # Act
        found = quotes.said(record)

        # Assert
        self.assertEqual(found, [("[0].quote", "hello")])

    def test_a_table_flattened_into_prose_is_left_out(self) -> None:
        # Arrange
        record = {"quote": "Table 21", "assembled": True}

        # Act
        found = quotes.said(record)

        # Assert
        self.assertEqual(found, [])

    def test_the_records_hold_quotes_to_look_for(self) -> None:
        # Arrange
        records = quotes.loaded()

        # Act
        found = quotes.quoted(records)

        # Assert
        self.assertGreater(len(found), 0)

    def test_a_quote_the_recording_made_is_not_one_to_look_for(self) -> None:
        # Arrange
        records = [("made-up.json", {"referenceDoes": {"quote": "hello"}})]

        # Act
        found = quotes.quoted(records)

        # Assert
        self.assertEqual(found, [])

    def test_but_one_the_manufacturer_made_is(self) -> None:
        # Arrange
        records = [("made-up.json", {"documentSays": {"quote": "hello"}})]

        # Act
        found = quotes.quoted(records)

        # Assert
        self.assertEqual(found, [("made-up.json.documentSays.quote", "hello")])

    def test_and_none_of_them_comes_from_the_recording(self) -> None:
        # Arrange
        records = quotes.loaded()

        # Act
        found = quotes.quoted(records)

        # Assert
        self.assertEqual([where for where, _ in found if "referenceDoes" in where], [])

    def test_left_to_itself_it_reads_the_records_beside_it(self) -> None:
        # Arrange
        expected = quotes.quoted(quotes.loaded())

        # Act
        found = quotes.quoted()

        # Assert
        self.assertEqual(found, expected)


class LibraryTest(unittest.TestCase):
    def test_a_machine_with_no_documents_has_an_empty_library(self) -> None:
        # Arrange
        folder = ROOT / "no such folder"

        # Act
        found = quotes.library(folder)

        # Assert
        self.assertEqual(found, {})

    def test_a_folder_of_documents_is_read_once_each(self) -> None:
        # Arrange
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (folder / "one.pdf").write_bytes(b"not really a pdf")

        # Act
        found = quotes.library(folder)

        # Assert
        self.assertEqual(list(found), ["one.pdf"])

    def test_something_that_cannot_be_read_yields_no_text(self) -> None:
        # Arrange
        path = ROOT / "no such file.pdf"

        # Act
        found = quotes.readable(path)

        # Assert
        self.assertEqual(found, "")

    def test_and_a_machine_with_no_reader_installed_checks_nothing(self) -> None:
        # Arrange
        path = ROOT / "anything.pdf"

        # Act
        found = quotes.readable(path, refuse)

        # Assert
        self.assertEqual(found, "")

    def test_a_reader_that_answers_gives_back_what_it_read(self) -> None:
        # Arrange
        reader = answering("Hello, World.")

        # Act
        found = quotes.readable(ROOT / "anything.pdf", reader)

        # Assert
        self.assertEqual(found, "helloworld")

    def test_a_reading_left_beside_the_document_is_pooled_with_it(self) -> None:
        # Arrange
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (folder / "one.pdf").write_bytes(b"")
        (folder / "one.txt").write_text("from the pages")

        # Act
        found = quotes.readable(folder / "one.pdf", answering("from the layer"))

        # Assert
        self.assertEqual(found, "fromthelayerfromthepages")

    def test_and_nothing_is_pooled_when_nobody_has_read_the_pages(self) -> None:
        # Arrange
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (folder / "one.pdf").write_bytes(b"")

        # Act
        found = quotes.readable(folder / "one.pdf", answering("only the layer"))

        # Assert
        self.assertEqual(found, "onlythelayer")

    def test_the_answering_reader_takes_whatever_it_is_handed(self) -> None:
        # Arrange
        reader = answering("said")

        # Act
        found = reader("one", two=2)

        # Assert
        self.assertEqual(found.stdout, "said")


class VerdictTest(unittest.TestCase):
    def test_a_quote_that_places_enough_windows_is_found(self) -> None:
        # Arrange
        verdict = quotes.Verdict("a", "b", "doc", 5, 10)

        # Act
        found = verdict.found

        # Assert
        self.assertEqual(found, True)

    def test_one_that_places_too_few_is_not(self) -> None:
        # Arrange
        verdict = quotes.Verdict("a", "b", "doc", 1, 10)

        # Act
        found = verdict.found

        # Assert
        self.assertEqual(found, False)

    def test_and_a_quote_with_no_windows_at_all_is_not(self) -> None:
        # Arrange
        verdict = quotes.Verdict("a", "b", None, 0, 0)

        # Act
        found = verdict.found

        # Assert
        self.assertEqual(found, False)


class VerifyTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.books = {"real.pdf": quotes.flatten(PRINTED)}

    def test_a_sentence_the_document_carries_is_located(self) -> None:
        # Arrange
        held = [("here", PRINTED)]

        # Act
        found = quotes.verify(held, self.books)

        # Assert
        self.assertEqual((found[0].found, found[0].document), (True, "real.pdf"))

    def test_a_sentence_it_does_not_is_reported(self) -> None:
        # Arrange
        held = [("here", "nothing at all like the printed page here")]

        # Act
        found = quotes.verify(held, self.books)

        # Assert
        self.assertEqual((found[0].found, found[0].document), (False, None))

    def test_the_best_of_several_documents_is_the_one_named(self) -> None:
        # Arrange
        books = {"poor.pdf": quotes.flatten("the quick brown"), **self.books}

        # Act
        found = quotes.verify([("here", PRINTED)], books)

        # Assert
        self.assertEqual(found[0].document, "real.pdf")


class ReportTest(unittest.TestCase):
    def test_a_run_with_no_documents_says_it_checked_nothing(self) -> None:
        # Arrange
        found = [quotes.Verdict("a", "b", None, 0, 3)]

        # Act
        said = quotes.report(found, 0)

        # Assert
        self.assertIn("none was checked", said)

    def test_a_clean_run_still_says_how_much_it_checked(self) -> None:
        # Arrange
        found = [quotes.Verdict("a", "b", "doc", 3, 3)]

        # Act
        said = quotes.report(found, 1)

        # Assert
        self.assertIn("1 quotes against 1 documents, 1 located, 0 not", said)

    def test_a_missing_quote_is_named_with_its_score(self) -> None:
        # Arrange
        found = [quotes.Verdict("here", "text", "doc", 1, 9)]

        # Act
        said = quotes.report(found, 1)

        # Assert
        self.assertIn("placed 1 of 9 windows (best in doc)", said)

    def test_and_one_no_document_could_place_names_none(self) -> None:
        # Arrange
        found = [quotes.Verdict("here", "text", None, 0, 9)]

        # Act
        said = quotes.report(found, 1)

        # Assert
        self.assertIn("placed 0 of 9 windows", said)


def run_with(books: dict[str, str], held: list[tuple[str, str]]) -> tuple[int, str]:
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        status = quotes.main(books, held)
    return status, printed.getvalue()


class EntryPointTest(unittest.TestCase):
    def test_with_no_documents_it_asks_for_nothing(self) -> None:
        # Arrange
        held = [("here", PRINTED)]

        # Act
        status, said = run_with({}, held)

        # Assert
        self.assertEqual((status, "none was checked" in said), (0, True))

    def test_with_documents_and_every_quote_placed_it_passes(self) -> None:
        # Arrange
        books = {"real.pdf": quotes.flatten(PRINTED)}

        # Act
        status, said = run_with(books, [("here", PRINTED)])

        # Assert
        self.assertEqual((status, "0 not" in said), (0, True))

    def test_a_sentence_no_document_carries_asks_for_a_person(self) -> None:
        # Arrange
        books = {"real.pdf": quotes.flatten(PRINTED)}

        # Act
        status, said = run_with(books, [("here", "absent")])

        # Assert
        self.assertEqual((status, "1 not" in said), (1, True))


if __name__ == "__main__":
    unittest.main()
