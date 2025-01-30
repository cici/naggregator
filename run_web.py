import asyncio
import coloredlogs
import os
import uuid
from dotenv import load_dotenv
from flask import Flask, current_app, render_template, request
from logging import getLogger
from newsfeed_workflow import NewsfeedWorkflow
from news_data import TopicInput, NEWS_TASK_QUEUE
from temporalio.client import Client

from temporal_client import NewTemporalClient

logger = getLogger(__name__)
coloredlogs.install(level='INFO')

load_dotenv()

NEWS_TOPIC = os.getenv("NEWS_TOPIC", "bitoin Apple OpenAI")
NEWS_DATE = os.getenv("NEWS_DATE", "December 23, 2024")

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
    topic = TopicInput(NEWS_DATE, topics)

    # Get form data
    topic = TopicInput(
        topicDate=request.form.get('topicDate'),
        topicString=request.form.get('topicString'),
    )

    client = await NewTemporalClient()

    newsfeed_workflow = await client.start_workflow(
        NewsfeedWorkflow.run,
        topic,
        id="newsfeed-workflow",
        task_queue=NEWS_TASK_QUEUE,
    )

    articles = await newsfeed_workflow.result()
    print(articles)
    return render_template(template_name_or_list='index.html', title="Newsfeed Aggregator", topic=topic, articles=articles)

if __name__ == "__main__":
    asyncio.run(connect_temporal(app))
    app.run(debug=True, port=3000)
