import json
import os
import random
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

"""  
  - product_quality
  - shipment_location
  - shipment_time
  - shipment_price
  - shipment_package
  - shipment_return
  - shipment_insurance
  - shipment_company
  - shipment_info
  - shipment_destination
  - invoice
  - discount
  - discount_lottery
  - human_service
"""

file_root = os.path.dirname(__file__)
yunjing_info = json.load(open(os.path.join(file_root, 'kb/yunjing_response.json'), mode='r', encoding='utf-8'))
planet_info = json.load(open(os.path.join(file_root, 'kb/planet_response.json'), mode='r', encoding='utf-8'))

class ActionProductQuality(Action):
    def name(self) -> Text:
        return "action_product_quality"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(response='utter_product_quality')

        return []

class ActionSlocation(Action):
    def name(self) -> Text:
        return "action_shipment_location"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(response='utter_shipment_location')

        return []

class ActionStime(Action):
    def name(self) -> Text:
        return "action_shipment_time"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(response='utter_shipment_time')

        return []

class ActionSpackage(Action):
    def name(self) -> Text:
        return "action_shipment_package"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(response='utter_shipment_package')

        return []

class ActionSprice(Action):
    def name(self) -> Text:
        return "action_shipment_price"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(response='utter_shipment_price')

        return []

class ActionSreturn(Action):
    def name(self) -> Text:
        return "action_shipment_return"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(response='utter_shipment_return')

        return []

class ActionSinsurance(Action):
    def name(self) -> Text:
        return "action_shipment_insurance"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(response='utter_shipment_insurance')

        return []

class ActionScompany(Action):
    def name(self) -> Text:
        return "action_shipment_company"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(response='utter_shipment_company')

        return []

class ActionSinfo(Action):
    def name(self) -> Text:
        return "action_shipment_info"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(response='utter_shipment_info')

        return []

class ActionSdestination(Action):
    def name(self) -> Text:
        return "action_shipment_destination"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(response='utter_shipment_destination')

        return []

class ActionSinvoice(Action):
    def name(self) -> Text:
        return "action_invoice"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(response='utter_invoice')

        return []

class ActionDlottery(Action):
    def name(self) -> Text:
        return "action_discount_lottery"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(response='utter_discount_lottery')

        return []

class ActionDiscount(Action):
    def name(self) -> Text:
        return "action_discount"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        sender_id = tracker.sender_id
        shop_id = sender_id.split(':')[0]
        res = ''
        if shop_id.lower() == 'yunjing':
            res = get_prod_utter(yunjing_info, 'utter_discount')
        elif shop_id.lower() == 'planet':
            res = get_prod_utter(planet_info, 'utter_discount')
        if res:
            dispatcher.utter_message(text=res)
        else:
            dispatcher.utter_message(response='utter_discount')

        return []


class ActionHservice(Action):
    def name(self) -> Text:
        return "action_human_service"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        sender_id = tracker.sender_id
        shop_id = sender_id.split(':')[0]
        res = ''
        if shop_id.lower() == 'yunjing':
            res = get_prod_utter(yunjing_info, 'utter_human_service')
        elif shop_id.lower() == 'planet':
            res = get_prod_utter(planet_info, 'utter_human_service')
        if res:
            dispatcher.utter_message(text=res)
        else:
            dispatcher.utter_message(response='utter_human_service')

        return []

def get_prod_utter(data_dict, utter_key):
    res = data_dict.get(utter_key, [])
    res = random.choice(res) if res else ''
    return res