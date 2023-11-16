import re

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse

import db_helper

app = FastAPI()

dict_of_orders = {}

@app.post("/")
async def handle_request(request: Request):
    payload = await request.json()

    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    output_context = payload['queryResult']['outputContexts']
    session_id = extract_session_id(output_context[0]['name'])
    intent_handler_dict = {
        'track.order - context: ongoing-tracking': track_order,
        'order.complete - context: ongoing-order': complete_order,
        'order.add - context: ongoing-order': add_to_order,
        'order.remove - context: ongoing-order': remove_from_order
    }
    if intent not in intent_handler_dict.keys():
        return
    return intent_handler_dict[intent](parameters, session_id)


def track_order(parameters: dict, session_id:str):
    order_id = int(parameters['number'])
    order_status = db_helper.get_order_status(order_id)

    if order_status is None:
        fulfillment_text = f"No order found with order id: {order_id}"
    else:
        fulfillment_text = f"The order status for order id: {order_id} is: {order_status}"
    return JSONResponse(content={"fulfillmentText": fulfillment_text})


def add_to_order(parameters: dict, session_id:str):
    food_items = parameters["Food-item"]
    quantities = parameters["number"]
    if len(food_items) != len(quantities):
        fulfillment_text = "Sorry I didn't understand. Can you specify food items and quantity,please"
    else:
        current_order = dict(zip(food_items, quantities))
        if session_id in dict_of_orders:
            dict_of_orders[session_id].update(current_order)
        else:
            dict_of_orders[session_id] = current_order
        fulfillment_text = " So, your order by now is: " + \
                        get_string_from_food_dict(dict_of_orders[session_id]) + \
                           ". Do you need anything else?"
    print(get_string_from_food_dict(dict_of_orders[session_id]))
    return JSONResponse(content={"fulfillmentText": fulfillment_text})


def remove_from_order(parameters: dict, session_id:str):
    food_items = parameters["food-item"]
    not_in_order_set = set()
    deleted_items = set()
    if session_id not in dict_of_orders:
        return "You haven't ordered yet"
    fulfillment_text = ""
    for food_item in food_items:
        try:
            del dict_of_orders[session_id][food_item]
            deleted_items.add(food_item)
        except KeyError as e:
            not_in_order_set.add(food_item)
    if not_in_order_set:
        fulfillment_text += "You didn't order the following items: " + \
                           set_to_string(not_in_order_set)
    else:
        fulfillment_text += "We removed the following items from your order " + \
                            set_to_string(deleted_items)
    fulfillment_text += " So, your order by now is: " + \
                        get_string_from_food_dict(dict_of_orders[session_id]) + \
                           ". Do you need anything else?"
    return JSONResponse(content={"fulfillmentText": fulfillment_text})


def complete_order(parameters: dict, session_id:str):
    if session_id not in dict_of_orders:
        fulfillment_text = "I'm having a trouble finding your order. Sorry! Can you " \
                           "place your order again?"
    else:
        order = dict_of_orders[session_id]
        order_id = db_helper.save_to_db(order)
        if order_id == 0:
            fulfillment_text = "Sorry, your order can't be placed due to the backend error. Try again! " \
                               "and we will try to fix the error."
        else:
            order_total = db_helper.get_total_order_price(order_id)
            fulfillment_text = f"Your order is placed. Here is your order id: {order_id}" + \
                               f". Your order total is {order_total} which you can pay at the time of delivery!"
    del dict_of_orders[session_id]
    return JSONResponse(content={"fulfillmentText": fulfillment_text})


def set_to_string(deleted_items):
    return ", ".join(map(str, deleted_items)) + " ."


def extract_session_id(session_str: str):
    match = re.search(r"/sessions/(.*?)/contexts/", session_str)
    if match:
        extracted_string = match.group(1)
        return extracted_string
    return ""


def get_string_from_food_dict(food_dict: dict):
    return ", ".join([f"{int(value)} {key}" for key, value in food_dict.items()])

