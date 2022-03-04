import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Text, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.types import DomainDict
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import (
    SlotSet,
    UserUtteranceReverted,
    ConversationPaused,
    EventType,
)

from actions import config
from actions.api import community_events
from actions.api.algolia import AlgoliaAPI
from actions.api.discourse import DiscourseAPI
from actions.api.gdrive_service import GDriveService
from actions.api.mailchimp import MailChimpAPI
from actions.api.rasaxapi import RasaXAPI

USER_INTENT_OUT_OF_SCOPE = "out_of_scope"

logger = logging.getLogger(__name__)

INTENT_DESCRIPTION_MAPPING_PATH = "actions/intent_description_mapping.csv"


class TravelSlotValidation(FormValidationAction):
    @staticmethod
    def location_db() -> List[Text]:
        return ['copenhagen', 'vancouver', 'london', 'paris', 'lima', 'new york', 'milan']

    def validate_location(
        self,
        slot_value: Any,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> Dict[Text, Any]:
        if slot_value.lower() in self.location_db():
            return {"location": slot_value}
        else:
            return {"location": None}

    async def extract_has_booked(
        self,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> Dict[Text, Any]:
        location = tracker.get_slot("location")
        email_address = tracker.get_slot("email_address")
        if location and email_address:
            return {"has_booked": True}
        else:
            return {"has_booked": None}