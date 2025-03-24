from slack_sdk.errors import SlackApiError
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import coloredlogs
from slack_sdk import WebClient
import json
import os
import smtplib
import ssl
from logging import getLogger
from scrapegraphai.graphs import SearchGraph
from scrapegraphai.utils import prettify_exec_info
from scrapegraphai.utils.data_export import export_to_json
from serpapi import GoogleSearch
from temporalio import activity
from news_data import NewsfeedInput
from temporalio.exceptions import ActivityError, ApplicationError

SLACKAPI_KEY = os.getenv('SLACKAPI_KEY')
SERPAPI_KEY = os.getenv('SERPAPI_KEY')

# Create a logger object and use coloredlogs
logger = getLogger(__name__)
coloredlogs.install(level='INFO')


class NewsActivities:

    @activity.defn
    def search_news(activity_input: NewsfeedInput) -> dict:
        """Function to search and retrieve news based on query"""
        logger.info("Fetching the news")

        logger.info(activity_input.topicString)

        # Date filtering:
        # tbs: "qbr:h" -- hour
        #      "qbr:d" -- day
        #      "qbr:w" -- week
        params = {
            "engine": "google",
            "q": activity_input.topicString,
            "google_domain": "google.com",
            "tbs": "qdr:d",
            "tbm": "nws",
            "gl": "us",
            "hl": "en",
            "api_key": SERPAPI_KEY
        }

        search = GoogleSearch(params)
        search_results = search.get_dict()

        # Create result dictionary where the key is the date of the search
        result_dict = {}
        if search_results:
            result_dict[activity_input.topicDate] = search_results['news_results']
        logger.info("Returning articles from Activity")
        return result_dict

    @activity.defn
    async def notify_slack(newsfeed_results: list):
        logger.info("Sending Slack notification")

        # Initialize a WebClient instance with your OAuth token
        client = WebClient(
            token=SLACKAPI_KEY)

        # The channel ID or name where you want to send the message
        channel_id = "#newsfeed-demo"

        # The bot name
        bot_name = "NewsfeedDemo"

        # Send Slack with newsfeed results
        for entry in newsfeed_results:
            try:
                msg = entry['title']
                link = entry['link']
                response = client.chat_postMessage(
                    channel=channel_id, text=f"{msg} {link}", username=bot_name)
                logger.info("Message sent successfully!")
            except SlackApiError as e:
                logger.error(f"Error sending message: {e}")
