import coloredlogs
import os
from dotenv import load_dotenv
from logging import getLogger
from newsfeed_workflow import NewsfeedWorkflow
from app.news_data import Topic
from quart import Quart, render_template, redirect, g
from quart_cors import cors
from temporalio.client import Client

from app.client import get_client
from config import get_config

logger = getLogger(__name__)
coloredlogs.install(level='INFO')

load_dotenv()

# Get the task queue name from the environment variable
NEWS_TASK_QUEUE = os.getenv("NEWS_TASK_QUEUE", "NewsTaskQueue")
NEWS_TOPIC = os.getenv("NEWS_TOPIC", "bitoin Apple OpenAI")
NEWS_DATE = os.getenv("NEWS_DATE", "December 23, 2024")
app = Quart(__name__, template_folder='../templates',
            static_folder='../static')
app = cors(app,
           allow_origin='*',
           allow_headers=['X-Namespace', 'Authorization', 'Accept'],
           # allow_credentials=True,
           allow_methods=['GET', 'PUT', 'POST',
                          'PATCH', 'OPTIONS', 'DELETE', 'HEAD'],
           expose_headers=['Content-Type', 'Authorization', 'X-Namespace'])
cfg = get_config()

app_info = dict({
    'name': 'Temporal Newsfeed Notification Demo'
})
app_info = {**app_info, **cfg}
app.app_info = app_info


@app.before_request
def apply_app_info():
    g.app_info = app_info


@app.context_processor
def view_app_info():
    return dict(app_info=g.app_info)


@app.route('/', methods=['GET'])
async def index():
    return redirect(location='/newsfeed')


@app.route('/newsfeed', methods=['GET'])
async def get_newsfeeds():
    client = await get_client()
    # form = await get_newsfeed_form()

    # If form input is null, get topics from ENV
    topics = NEWS_TOPIC.split(",")
    topic = Topic(NEWS_DATE, topics)

    newsfeed_workflow = await client.start_workflow(
        NewsfeedWorkflow.run,
        topic,
        id="newsfeed-workflow",
        task_queue=NEWS_TASK_QUEUE,
    )

    return await render_template(template_name_or_list='index.html')
