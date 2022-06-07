# -*- coding: utf-8 -*-

"""
@Time    : 2022/6/3 12:47 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""

from __future__ import annotations
import logging
import os
import glob
import shutil
import six
import unicodedata
from typing import Any, Dict, List, Optional, Text

from rasa.engine.graph import ExecutionContext
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage

from rasa.nlu.tokenizers.tokenizer import Token, Tokenizer
from rasa.shared.nlu.training_data.message import Message

from rasa.shared.nlu.training_data.training_data import TrainingData
from rasa.nlu.constants import TOKENS_NAMES, MESSAGE_ATTRIBUTES
from rasa.shared.nlu.constants import (
    INTENT,
    INTENT_RESPONSE_KEY,
    RESPONSE_IDENTIFIER_DELIMITER,
    ACTION_NAME,
)

logger = logging.getLogger(__name__)


@DefaultV1Recipe.register(DefaultV1Recipe.ComponentType.MESSAGE_TOKENIZER, is_trainable=True)
class MicroTokenizer(Tokenizer):
    provides = ["tokens"]

    @staticmethod
    def supported_languages() -> Optional[List[Text]]:
        """Supported languages (see parent class for full docstring)."""
        return ["zh"]

    @staticmethod
    def get_default_config() -> Dict[Text, Any]:
        """Returns default config (see parent class for full docstring)."""
        return {
            # default don't load custom dictionary
            "dictionary_path": None,
            # Flag to check whether to split intents
            "intent_tokenization_flag": False,
            # Symbol on which intent should be split
            "intent_split_symbol": "_",
            # Regular expression to detect tokens
            "token_pattern": None,
        }

    def __init__(
            self, config: Dict[Text, Any], model_storage: ModelStorage, resource: Resource,
    ) -> None:
        super().__init__(config)
        self._model_storage = model_storage
        self._resource = resource

    def process_training_data(self, training_data: TrainingData) -> TrainingData:
        """Tokenize all training data."""
        for example in training_data.training_examples:
            for attribute in MESSAGE_ATTRIBUTES:
                if (
                    example.get(attribute) is not None
                    and not example.get(attribute) == ""
                ):
                    if attribute in [INTENT, ACTION_NAME, INTENT_RESPONSE_KEY]:
                        tokens = self._split_name(example, attribute)
                    else:
                        tokens = self.tokenize(example, attribute)
                    example.set(TOKENS_NAMES[attribute], tokens)
        return training_data

    @classmethod
    def create(
            cls,
            config: Dict[Text, Any],
            model_storage: ModelStorage,
            resource: Resource,
            execution_context: ExecutionContext,
    ) -> MicroTokenizer:
        """Creates a new component (see parent class for full docstring)."""
        # Path to the dictionaries on the local filesystem.
        dictionary_path = config["dictionary_path"]

        if dictionary_path is not None:
            cls._load_custom_dictionary(dictionary_path)
        return cls(config, model_storage, resource)

    # @staticmethod
    # def _load_custom_dictionary(path: Text) -> None:
    #     import MicroTokenizer
    #
    #     userdicts = glob.glob(f"{path}/*")
    #     for userdict in userdicts:
    #         logger.info(f"Loading MicroTokenizer User Dictionary at {userdict}")
    #         MicroTokenizer.load_userdict(userdict)

    # @classmethod
    # def required_packages(cls) -> List[Text]:
    #     return ["MicroTokenizer"]

    def train(self, training_data: TrainingData) -> Resource:
        """Copies the dictionary to the model storage."""
        self.persist()
        return self._resource

    def tokenize(self, message: Message, attribute: Text) -> List[Token]:
        # import MicroTokenizer

        text = message.get(attribute)
        # import pdb;pdb.set_trace()
        # tokenized = MicroTokenizer.cut(text)
        # 单字切分
        tokenized = list(text.strip())

        tokens = []
        start = 0
        for word in tokenized:
            tokens.append(Token(word, start))
            start += len(word)

        return self._apply_token_pattern(tokens)

    def _apply_token_pattern(self, tokens: List[Token]) -> List[Token]:
        """Apply the token pattern to the given tokens.

        Args:
            tokens: list of tokens to split

        Returns:
            List of tokens.
        """
        if not self.token_pattern_regex:
            return tokens

        final_tokens = []
        for token in tokens:
            new_tokens = self.token_pattern_regex.findall(token.text)
            new_tokens = [t for t in new_tokens if t]

            if not new_tokens:
                final_tokens.append(token)

            running_offset = 0
            for new_token in new_tokens:
                word_offset = token.text.index(new_token, running_offset)
                word_len = len(new_token)
                running_offset = word_offset + word_len
                final_tokens.append(
                    Token(
                        new_token,
                        token.start + word_offset,
                        data=token.data,
                        lemma=token.lemma,
                    )
                )

        return final_tokens

    def _tokenize_on_split_symbol(self, text: Text) -> List[Text]:
        words = (
            text.split(self.intent_split_symbol)
            if self.intent_tokenization_flag
            else [text]
        )

        return words

    def _split_name(self, message: Message, attribute: Text = INTENT) -> List[Token]:
        text = message.get(attribute)

        # for INTENT_RESPONSE_KEY attribute,
        # first split by RESPONSE_IDENTIFIER_DELIMITER
        if attribute == INTENT_RESPONSE_KEY:
            intent, response_key = text.split(RESPONSE_IDENTIFIER_DELIMITER)
            words = self._tokenize_on_split_symbol(
                intent
            ) + self._tokenize_on_split_symbol(response_key)

        else:
            words = self._tokenize_on_split_symbol(text)

        return self._convert_words_to_tokens(words, text)

    @staticmethod
    def _convert_words_to_tokens(words: List[Text], text: Text) -> List[Token]:
        running_offset = 0
        tokens = []

        for word in words:
            word_offset = text.index(word, running_offset)
            word_len = len(word)
            running_offset = word_offset + word_len
            tokens.append(Token(word, word_offset))

        return tokens

    @classmethod
    def load(
            cls,
            config: Dict[Text, Any],
            model_storage: ModelStorage,
            resource: Resource,
            execution_context: ExecutionContext,
            **kwargs: Any,
    ) -> MicroTokenizer:
        """Loads a custom dictionary from model storage."""
        dictionary_path = config["dictionary_path"]

        # If a custom dictionary path is in the config we know that it should have
        # been saved to the model storage.
        if dictionary_path is not None:
            try:
                with model_storage.read_from(resource) as resource_directory:
                    cls._load_custom_dictionary(str(resource_directory))
            except ValueError:
                logger.debug(
                    f"Failed to load {cls.__name__} from model storage. "
                    f"Resource '{resource.name}' doesn't exist."
                )
        return cls(config, model_storage, resource)

    @staticmethod
    def _copy_files_dir_to_dir(input_dir: Text, output_dir: Text) -> None:
        # make sure target path exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        target_file_list = glob.glob(f"{input_dir}/*")
        for target_file in target_file_list:
            shutil.copy2(target_file, output_dir)

    def persist(self) -> None:
        """Persist the custom dictionaries."""
        dictionary_path = self._config["dictionary_path"]
        if dictionary_path is not None:
            with self._model_storage.write_to(self._resource) as resource_directory:
                self._copy_files_dir_to_dir(dictionary_path, str(resource_directory))


class BasicTokenizer(object):
  """Runs basic tokenization (punctuation splitting, lower casing, etc.)."""

  def __init__(self, do_lower_case=True):
    """Constructs a BasicTokenizer.
    Args:
      do_lower_case: Whether to lower case the input.
    """
    self.do_lower_case = do_lower_case

  def tokenize(self, text):
    """Tokenizes a piece of text."""
    text = self.convert_to_unicode(text)
    text = self._clean_text(text)

    # This was added on November 1st, 2018 for the multilingual and Chinese
    # models. This is also applied to the English models now, but it doesn't
    # matter since the English models were not trained on any Chinese data
    # and generally don't have any Chinese data in them (there are Chinese
    # characters in the vocabulary because Wikipedia does have some Chinese
    # words in the English Wikipedia.).
    text = self._tokenize_chinese_chars(text)

    orig_tokens = self.whitespace_tokenize(text)
    split_tokens = []
    for token in orig_tokens:
      if self.do_lower_case:
        token = token.lower()
        token = self._run_strip_accents(token)
      split_tokens.extend(self._run_split_on_punc(token))

    output_tokens = self.whitespace_tokenize(" ".join(split_tokens))
    return output_tokens

  def whitespace_tokenize(self, text):
      """Runs basic whitespace cleaning and splitting on a piece of text."""
      text = text.strip()
      if not text:
          return []
      tokens = text.split()
      return tokens

  def _run_strip_accents(self, text):
    """Strips accents from a piece of text."""
    text = unicodedata.normalize("NFD", text)
    output = []
    for char in text:
      cat = unicodedata.category(char)
      if cat == "Mn":
        continue
      output.append(char)
    return "".join(output)

  def _run_split_on_punc(self, text):
    """Splits punctuation on a piece of text."""
    chars = list(text)
    i = 0
    start_new_word = True
    output = []
    while i < len(chars):
      char = chars[i]
      if self._is_punctuation(char):
        output.append([char])
        start_new_word = True
      else:
        if start_new_word:
          output.append([])
        start_new_word = False
        output[-1].append(char)
      i += 1

    return ["".join(x) for x in output]

  def _tokenize_chinese_chars(self, text):
    """Adds whitespace around any CJK character."""
    output = []
    for char in text:
      cp = ord(char)
      if self._is_chinese_char(cp):
        output.append(" ")
        output.append(char)
        output.append(" ")
      else:
        output.append(char)
    return "".join(output)

  def _is_chinese_char(self, cp):
    """Checks whether CP is the codepoint of a CJK character."""
    # This defines a "chinese character" as anything in the CJK Unicode block:
    #   https://en.wikipedia.org/wiki/CJK_Unified_Ideographs_(Unicode_block)
    #
    # Note that the CJK Unicode block is NOT all Japanese and Korean characters,
    # despite its name. The modern Korean Hangul alphabet is a different block,
    # as is Japanese Hiragana and Katakana. Those alphabets are used to write
    # space-separated words, so they are not treated specially and handled
    # like the all of the other languages.
    if ((cp >= 0x4E00 and cp <= 0x9FFF) or  #
        (cp >= 0x3400 and cp <= 0x4DBF) or  #
        (cp >= 0x20000 and cp <= 0x2A6DF) or  #
        (cp >= 0x2A700 and cp <= 0x2B73F) or  #
        (cp >= 0x2B740 and cp <= 0x2B81F) or  #
        (cp >= 0x2B820 and cp <= 0x2CEAF) or
        (cp >= 0xF900 and cp <= 0xFAFF) or  #
        (cp >= 0x2F800 and cp <= 0x2FA1F)):  #
      return True

    return False

  def _clean_text(self, text):
    """Performs invalid character removal and whitespace cleanup on text."""
    output = []
    for char in text:
      cp = ord(char)
      if cp == 0 or cp == 0xfffd or self._is_control(char):
        continue
      if self._is_whitespace(char):
        output.append(" ")
      else:
        output.append(char)
    return "".join(output)

  def convert_to_unicode(self, text):
      """Converts `text` to Unicode (if it's not already), assuming utf-8 input."""
      if six.PY3:
          if isinstance(text, str):
              return text
          elif isinstance(text, bytes):
              return text.decode("utf-8", "ignore")
          else:
              raise ValueError("Unsupported string type: %s" % (type(text)))
      else:
          raise ValueError("Not running on Python 3?")

  def printable_text(self, text):
      """Returns text encoded in a way suitable for print or `tf.logging`."""

      # These functions want `str` for both Python2 and Python3, but in one case
      # it's a Unicode string and in the other it's a byte string.
      if six.PY3:
          if isinstance(text, str):
              return text
          elif isinstance(text, bytes):
              return text.decode("utf-8", "ignore")
          else:
              raise ValueError("Unsupported string type: %s" % (type(text)))
      else:
          raise ValueError("Not running on Python 3?")

  def _is_whitespace(self, char):
      """Checks whether `chars` is a whitespace character."""
      # \t, \n, and \r are technically contorl characters but we treat them
      # as whitespace since they are generally considered as such.
      if char == " " or char == "\t" or char == "\n" or char == "\r":
          return True
      cat = unicodedata.category(char)
      if cat == "Zs":
          return True
      return False

  def _is_control(self, char):
      """Checks whether `chars` is a control character."""
      # These are technically control characters but we count them as whitespace
      # characters.
      if char == "\t" or char == "\n" or char == "\r":
          return False
      cat = unicodedata.category(char)
      if cat in ("Cc", "Cf"):
          return True
      return False

  def _is_punctuation(self, char):
      """Checks whether `chars` is a punctuation character."""
      cp = ord(char)
      # We treat all non-letter/number ASCII as punctuation.
      # Characters such as "^", "$", and "`" are not in the Unicode
      # Punctuation class but we treat them as punctuation anyways, for
      # consistency.
      if ((cp >= 33 and cp <= 47) or (cp >= 58 and cp <= 64) or
              (cp >= 91 and cp <= 96) or (cp >= 123 and cp <= 126)):
          return True
      cat = unicodedata.category(char)
      if cat.startswith("P"):
          return True
      return False


@DefaultV1Recipe.register(DefaultV1Recipe.ComponentType.MESSAGE_TOKENIZER, is_trainable=True)
class MyBertTokenizer(Tokenizer):
    # bert实现分词功能，不加wordpiece分词
    provides = ["tokens"]

    @staticmethod
    def supported_languages() -> Optional[List[Text]]:
        """Supported languages (see parent class for full docstring)."""
        return ["zh"]

    @staticmethod
    def get_default_config() -> Dict[Text, Any]:
        """Returns default config (see parent class for full docstring)."""
        return {
            # default don't load custom dictionary
            "dictionary_path": None,
            # Flag to check whether to split intents
            "intent_tokenization_flag": False,
            # Symbol on which intent should be split
            "intent_split_symbol": "_",
            # Regular expression to detect tokens
            "token_pattern": None,
        }

    def __init__(
            self, config: Dict[Text, Any], model_storage: ModelStorage, resource: Resource,
    ) -> None:
        super().__init__(config)
        self._model_storage = model_storage
        self._resource = resource

    @classmethod
    def create(
            cls,
            config: Dict[Text, Any],
            model_storage: ModelStorage,
            resource: Resource,
            execution_context: ExecutionContext,
    ) -> MyBertTokenizer:
        """Creates a new component (see parent class for full docstring)."""
        # Path to the dictionaries on the local filesystem.
        dictionary_path = config["dictionary_path"]

        if dictionary_path is not None:
            cls._load_custom_dictionary(dictionary_path)
        return cls(config, model_storage, resource)

    @staticmethod
    def _load_custom_dictionary(path: Text) -> None:

        userdicts = glob.glob(f"{path}/*")
        for userdict in userdicts:
            logger.info(f"don't need to Load MyBertTokenizer User Dictionary at {userdict}")


    @classmethod
    def required_packages(cls) -> List[Text]:
        return ["BertTokenizer"]

    def train(self, training_data: TrainingData) -> Resource:
        """Copies the dictionary to the model storage."""
        self.persist()
        return self._resource

    def tokenize(self, message: Message, attribute: Text) -> List[Token]:
        bt = BasicTokenizer()
        text = message.get(attribute)

        tokenized = bt.tokenize(text)

        tokens = []
        start = 0
        for word in tokenized:
            tokens.append(Token(word, start))
            start += len(word)

        return self._apply_token_pattern(tokens)

    @classmethod
    def load(
            cls,
            config: Dict[Text, Any],
            model_storage: ModelStorage,
            resource: Resource,
            execution_context: ExecutionContext,
            **kwargs: Any,
    ) -> MyBertTokenizer:
        """Loads a custom dictionary from model storage."""
        dictionary_path = config["dictionary_path"]

        # If a custom dictionary path is in the config we know that it should have
        # been saved to the model storage.
        if dictionary_path is not None:
            try:
                with model_storage.read_from(resource) as resource_directory:
                    cls._load_custom_dictionary(str(resource_directory))
            except ValueError:
                logger.debug(
                    f"Failed to load {cls.__name__} from model storage. "
                    f"Resource '{resource.name}' doesn't exist."
                )
        return cls(config, model_storage, resource)

    @staticmethod
    def _copy_files_dir_to_dir(input_dir: Text, output_dir: Text) -> None:
        # make sure target path exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        target_file_list = glob.glob(f"{input_dir}/*")
        for target_file in target_file_list:
            shutil.copy2(target_file, output_dir)

    def persist(self) -> None:
        """Persist the custom dictionaries."""
        dictionary_path = self._config["dictionary_path"]
        if dictionary_path is not None:
            with self._model_storage.write_to(self._resource) as resource_directory:
                self._copy_files_dir_to_dir(dictionary_path, str(resource_directory))

if __name__ == '__main__':
    bt = BasicTokenizer()
    res = bt.tokenize("beijing shanghai是中国的首都，keras是一款好用的产品")
    print(res)