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


@DefaultV1Recipe.register(
    DefaultV1Recipe.ComponentType.MESSAGE_TOKENIZER, is_trainable=True
)
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

    @staticmethod
    def _load_custom_dictionary(path: Text) -> None:
        import MicroTokenizer

        userdicts = glob.glob(f"{path}/*")
        for userdict in userdicts:
            logger.info(f"Loading MicroTokenizer User Dictionary at {userdict}")
            MicroTokenizer.load_userdict(userdict)

    @classmethod
    def required_packages(cls) -> List[Text]:
        return ["MicroTokenizer"]

    def train(self, training_data: TrainingData) -> Resource:
        """Copies the dictionary to the model storage."""
        self.persist()
        return self._resource

    def tokenize(self, message: Message, attribute: Text) -> List[Token]:
        import MicroTokenizer

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