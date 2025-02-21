import asyncio
import coloredlogs
import os
import uuid
from datetime import date, timedelta
from dotenv import load_dotenv
from flask import Flask, current_app, render_template, request
from logging import getLogger
from newsfeed_workflow import NewsfeedWorkflow
from news_data import TopicInput, NEWS_TASK_QUEUE
from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError
from typing import List, Dict

from temporal_client import NewTemporalClient

logger = getLogger(__name__)
coloredlogs.install(level='INFO')

load_dotenv()

NEWS_TOPIC = os.getenv("NEWS_TOPIC", "bitoin Apple OpenAI")

app = Flask(__name__, template_folder='./ui/templates',
            static_folder='./ui/static')
app.env = "development"


async def connect_temporal(app):
    client: Client = await NewTemporalClient()
    app.temporal_client = client


def get_client() -> Client:
    return current_app.temporal_client


@app.route('/', methods=['GET'])
async def index():
    search_id = str(uuid.uuid4().int)[:6]
    return render_template(template_name_or_list='index.html', title="Newsfeed Aggregator", search_id=search_id)


@app.route('/newsfeed', methods=['POST'])
async def get_newsfeed():
    # Initialize topic data from env
    topics = NEWS_TOPIC.split(",")
    dt = str(date.today())
    print("DATE")
    print(dt)
    topicString = request.form.get('topicString')
    topic = TopicInput(dt, topicString)

    # Get form data
    # topic = TopicInput(
    #     topicDate=request.form.get('topicDate'),
    #     topicString=request.form.get('topicString'),
    # )

    client = await NewTemporalClient()

    try:
        newsfeed_workflow = await client.start_workflow(
            NewsfeedWorkflow.run,
            topic,
            id="newsfeed-workflow",
            task_queue=NEWS_TASK_QUEUE,
        )

        await asyncio.sleep(2)

        # Retrieve the updated list of articles
        articles: List[Dict] = []
        while not articles:
            try:
                articles = await newsfeed_workflow.query(
                    NewsfeedWorkflow.newsfeed_details)
            except:
                pass

        # articles = await newsfeed_workflow.result()
        print("RETURNED ARTICLES")
        print(articles)
    except WorkflowAlreadyStartedError as e:
        logger.error(f"Workflow with ID '{id}' is already running.")
        # You can choose to return the existing workflow handle
        return e.get_existing_workflow_handle()
    return render_template(template_name_or_list='index.html', title="Newsfeed Aggregator", topic=topic, articles=articles)

if __name__ == "__main__":
    asyncio.run(connect_temporal(app))
    app.run(debug=True, port=3000)
