# -*- coding: utf-8 -*-
import re
import os
import openai
def start_chromadb(docker=False,collection_name="full",path="./chromadb_functions"):
    import chromadb
    if docker:
        #Initialize ChromaDB client and create a collection
        client = chromadb.HttpClient(host='localhost', port=8000)
    else:
        chroma_client = chromadb.PersistentClient(path=path)
        #chroma_client = chromadb.PersistentClient(path="/bio_context/chromabd_functions")
    
    collection = chroma_client.get_or_create_collection(name=collection_name)
    
    openai.api_key = os.environ['OPENAI_API_KEY']
    return collection

def count_words(s):
    """Count the number of words in a string. A word is denoted by a space."""
    if not s:
        return 0
    words = s.split(' ')
    return len(words)

def extract_json(text):
    pattern = r'```json'
    match = re.search(pattern, text)
    if match:
        json_starting_index = match.start()
    else:
        json_starting_index = -1
    text=text[json_starting_index:]

    pattern = r'```(?=(\s|$))'
    
    matches = list(re.finditer(pattern, text))
    indexes = [match.start() for match in matches]
    text=text[:indexes[-1]+3]
    return text


"""**Text Splitters** are classes for splitting text.


**Class hierarchy:**

.. code-block::

    BaseDocumentTransformer --> TextSplitter --> <name>TextSplitter  # Example: CharacterTextSplitter
                                                 RecursiveCharacterTextSplitter -->  <name>TextSplitter

Note: **MarkdownHeaderTextSplitter** and **HTMLHeaderTextSplitter do not derive from TextSplitter.


**Main helpers:**

.. code-block::

    Document, Tokenizer, Language, LineType, HeaderType

"""  # noqa: E501

import copy
import logging
from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Optional,
    TypeVar,
)


logger = logging.getLogger(__name__)

TS = TypeVar("TS", bound="TextSplitter")


def _make_spacy_pipeline_for_splitting(
    pipeline: str, *, max_length: int = 1_000_000
) -> Any:  # avoid importing spacy
    try:
        import spacy
    except ImportError:
        raise ImportError(
            "Spacy is not installed, please install it with `pip install spacy`."
        )
    if pipeline == "sentencizer":
        from spacy.lang.en import English

        sentencizer = English()
        sentencizer.add_pipe("sentencizer")
    else:
        sentencizer = spacy.load(pipeline, exclude=["ner", "tagger"])
        sentencizer.max_length = max_length
    return sentencizer


def _split_text_with_regex(
    text: str, separator: str, keep_separator: bool
) -> List[str]:
    # Now that we have the separator, split the text
    if separator:
        if keep_separator:
            # The parentheses in the pattern keep the delimiters in the result.
            _splits = re.split(f"({separator})", text)
            splits = [_splits[i] + _splits[i + 1] for i in range(1, len(_splits), 2)]
            if len(_splits) % 2 == 0:
                splits += _splits[-1:]
            splits = [_splits[0]] + splits
        else:
            splits = re.split(separator, text)
    else:
        splits = list(text)
    return [s for s in splits if s != ""]


class TextSplitter(ABC):
    """Interface for splitting text into chunks."""

    def __init__(
        self,
        chunk_size: int = 4000,
        chunk_overlap: int = 200,
        length_function: Callable[[str], int] = len,
        keep_separator: bool = False,
        add_start_index: bool = False,
        strip_whitespace: bool = True,
    ) -> None:
        """Create a new TextSplitter.

        Args:
            chunk_size: Maximum size of chunks to return
            chunk_overlap: Overlap in characters between chunks
            length_function: Function that measures the length of given chunks
            keep_separator: Whether to keep the separator in the chunks
            add_start_index: If `True`, includes chunk's start index in metadata
            strip_whitespace: If `True`, strips whitespace from the start and end of
                              every document
        """
        if chunk_overlap > chunk_size:
            raise ValueError(
                f"Got a larger chunk overlap ({chunk_overlap}) than chunk size "
                f"({chunk_size}), should be smaller."
            )
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._length_function = length_function
        self._keep_separator = keep_separator
        self._add_start_index = add_start_index
        self._strip_whitespace = strip_whitespace

    @abstractmethod
    def split_text(self, text: str) -> List[str]:
        """Split text into multiple components."""

    def create_documents(
        self, texts: List[str], metadatas: Optional[List[dict]] = None
    ) -> List[tuple]:
        """Create documents from a list of texts."""
        _metadatas = metadatas or [{}] * len(texts)
        documents = []
        for i, text in enumerate(texts):
            index = 0
            previous_chunk_len = 0
            for j,chunk in enumerate(self.split_text(text)):
                metadata = copy.deepcopy(_metadatas[i])
                metadata['chunk_number']=str(j)
                if self._add_start_index:
                    offset = index + previous_chunk_len - self._chunk_overlap
                    index = text.find(chunk, max(0, offset))
                    metadata["start_index"] = index
                    previous_chunk_len = len(chunk)
                new_doc = (chunk,metadata)
                documents.append(new_doc)
        return documents

    def split_documents(self, documents: List[tuple]) -> List[tuple]:
        """Split documents."""
        texts, metadatas = [], []
        for doc in documents:
            texts.append(doc[0])
            metadatas.append(doc[1])
        return self.create_documents(texts, metadatas=metadatas)

    def _join_docs(self, docs: List[str], separator: str) -> Optional[str]:
        text = separator.join(docs)
        if self._strip_whitespace:
            text = text.strip()
        if text == "":
            return None
        else:
            return text

    def _merge_splits(self, splits: Iterable[str], separator: str) -> List[str]:
        # We now want to combine these smaller pieces into medium size
        # chunks to send to the LLM.
        separator_len = self._length_function(separator)

        docs = []
        current_doc: List[str] = []
        total = 0
        for d in splits:
            _len = self._length_function(d)
            if (
                total + _len + (separator_len if len(current_doc) > 0 else 0)
                > self._chunk_size
            ):
                if total > self._chunk_size:
                    logger.warning(
                        f"Created a chunk of size {total}, "
                        f"which is longer than the specified {self._chunk_size}"
                    )
                if len(current_doc) > 0:
                    doc = self._join_docs(current_doc, separator)
                    if doc is not None:
                        docs.append(doc)
                    # Keep on popping if:
                    # - we have a larger chunk than in the chunk overlap
                    # - or if we still have any chunks and the length is long
                    while total > self._chunk_overlap or (
                        total + _len + (separator_len if len(current_doc) > 0 else 0)
                        > self._chunk_size
                        and total > 0
                    ):
                        total -= self._length_function(current_doc[0]) + (
                            separator_len if len(current_doc) > 1 else 0
                        )
                        current_doc = current_doc[1:]
            current_doc.append(d)
            total += _len + (separator_len if len(current_doc) > 1 else 0)
        doc = self._join_docs(current_doc, separator)
        if doc is not None:
            docs.append(doc)
        return docs

class RecursiveCharacterTextSplitter(TextSplitter):
    """Splitting text by recursively look at characters.

    Recursively tries to split by different characters to find one
    that works.
    """

    def __init__(
        self,
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
        is_separator_regex: bool = False,
        **kwargs: Any,
    ) -> None:
        """Create a new TextSplitter."""
        super().__init__(keep_separator=keep_separator, **kwargs)
        self._separators = separators or ["\n\n", "\n", " ", ""]
        self._is_separator_regex = is_separator_regex

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Split incoming text and return chunks."""
        final_chunks = []
        # Get appropriate separator to use
        separator = separators[-1]
        new_separators = []
        for i, _s in enumerate(separators):
            _separator = _s if self._is_separator_regex else re.escape(_s)
            if _s == "":
                separator = _s
                break
            if re.search(_separator, text):
                separator = _s
                new_separators = separators[i + 1 :]
                break

        _separator = separator if self._is_separator_regex else re.escape(separator)
        splits = _split_text_with_regex(text, _separator, self._keep_separator)

        # Now go merging things, recursively splitting longer texts.
        _good_splits = []
        _separator = "" if self._keep_separator else separator
        for s in splits:
            if self._length_function(s) < self._chunk_size:
                _good_splits.append(s)
            else:
                if _good_splits:
                    merged_text = self._merge_splits(_good_splits, _separator)
                    final_chunks.extend(merged_text)
                    _good_splits = []
                if not new_separators:
                    final_chunks.append(s)
                else:
                    other_info = self._split_text(s, new_separators)
                    final_chunks.extend(other_info)
        if _good_splits:
            merged_text = self._merge_splits(_good_splits, _separator)
            final_chunks.extend(merged_text)
        return final_chunks

    def split_text(self, text: str) -> List[str]:
        return self._split_text(text, self._separators)

    # @classmethod
    # def from_language(
    #     cls, language: Language, **kwargs: Any
    # ) -> RecursiveCharacterTextSplitter:
    #     separators = cls.get_separators_for_language(language)
    #     return cls(separators=separators, is_separator_regex=True, **kwargs)

    # @staticmethod
    # def get_separators_for_language(language: Language) -> List[str]:
    #     elif language == Language.RST:
    #         return [
    #             # Split along section titles
    #             "\n=+\n",
    #             "\n-+\n",
    #             "\n\\*+\n",
    #             # Split along directive markers
    #             "\n\n.. *\n\n",
    #             # Split by the normal type of lines
    #             "\n\n",
    #             "\n",
    #             " ",
    #             "",
    #         ]

    #     elif language == Language.MARKDOWN:
    #         return [
    #             # First, try to split along Markdown headings (starting with level 2)
    #             "\n#{1,6} ",
    #             # Note the alternative syntax for headings (below) is not handled here
    #             # Heading level 2
    #             # ---------------
    #             # End of code block
    #             "```\n",
    #             # Horizontal lines
    #             "\n\\*\\*\\*+\n",
    #             "\n---+\n",
    #             "\n___+\n",
    #             # Note that this splitter doesn't handle horizontal lines defined
    #             # by *three or more* of ***, ---, or ___, but this is not handled
    #             "\n\n",
    #             "\n",
    #             " ",
    #             "",
    #         ]