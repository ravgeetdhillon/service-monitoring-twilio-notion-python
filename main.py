"""
Automated Monitoring of Web Services using Twilio, Notion, and Python.
by https://github.com/ravgeetdhillon
"""

import json
import os

import requests
from dotenv import load_dotenv
from requests.models import Response
from twilio.rest import Client
from twilio.rest.api.v2010.account.message import MessageInstance

load_dotenv()

NOTION_API_BASE_URL = 'https://api.notion.com/v1'
NOTION_API_TOKEN = os.getenv('NOTION_API_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')


def get_status(service: dict):
    """
    This function returns a status string based on the status code
    and presence of the identifier in the response.
    """

    response: Response = requests.get(service['url'])

    if response is not None:
        status_code: int = response.status_code
        response_body: str = response.text

        if status_code >= 200 and status_code < 400 and service['identifier'].lower() in response_body.lower():
            return 'Operational'
        elif status_code >= 200 and status_code < 400:
            return 'Doubtful'
        elif status_code >= 400 and status_code < 500:
            return 'Warning'
        elif status_code == 503:
            return 'Maintenance'
        else:
            return 'Down'


def get_services_to_monitor():
    """
    This function calls the notion API to get the services that we need to monitor
    and returns a list of the services.
    """

    headers: dict = {
        'Authorization': f'Bearer {NOTION_API_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2021-05-13',
    }

    # uses https://developers.notion.com/reference/post-database-query
    response: Response = requests.post(
        f'{NOTION_API_BASE_URL}/databases/{NOTION_DATABASE_ID}/query', headers=headers)

    if response.status_code == 200:
        json_response: dict = response.json()['results']
    else:
        return

    services: list = []

    for item in json_response:
        service: dict = {
            'id': item['id'],
            'url': item['properties']['URL']['title'][0]['text']['content'],
            'identifier': item['properties']['Identifier']['rich_text'][0]['text']['content'],
        }

        # since status of a service can be empty
        # we need to use try except block to get the last recorded status of a service
        try:
            service['last_recorded_status'] = item['properties']['Status']['select']['name']
        except KeyError:
            service['last_recorded_status'] = ''

        services.append(service)

    return services


def update_service_status(service: dict, status: str):
    """
    This function updates the service's status using Notion API.
    """

    payload: dict = {
        'properties': {
            'Status': {
                'select': {
                    'name': status
                }
            }
        }
    }

    headers: dict = {
        'Authorization': f'Bearer {NOTION_API_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2021-05-13',
    }

    # uses https://developers.notion.com/reference/patch-page
    requests.patch(
        f'{NOTION_API_BASE_URL}/pages/{service["id"]}', headers=headers, data=json.dumps(payload))


def send_notification(service: dict, status: str):
    """
    This function sends a whatsapp notification using the twilio whatsapp API
    """

    if service['last_recorded_status'] != status:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        from_whatsapp_number = 'whatsapp:+14155238886'
        to_whatsapp_number = 'whatsapp:+919780221904'
        body: str = f'Status for {service["url"]} is {status}.'

        message: MessageInstance = client.messages.create(body=body,
                                                          from_=from_whatsapp_number,
                                                          to=to_whatsapp_number)

        return message.sid


def main():
    """
    Main function for the app.
    """

    services: list = get_services_to_monitor()
    for service in services:
        status: str = get_status(service)
        update_service_status(service, status)
        send_notification(service, status)


if __name__ == '__main__':
    main()
