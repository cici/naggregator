import asyncio
import coloredlogs
import os
import uuid
from datetime import date, timedelta
from dotenv import load_dotenv
from flask import Flask, current_app, render_template, request
from logging import getLogger
from newsfeed_workflow import NewsfeedWorkflow
from news_data import NewsfeedInput, NEWS_TASK_QUEUE
from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError
from typing import List, Dict
import hashlib
import json
from pathlib import Path

from temporal_client import NewTemporalClient

logger = getLogger(__name__)
coloredlogs.install(level='INFO')

load_dotenv()

NEWS_TOPIC = os.getenv("NEWS_TOPIC", "bitoin Apple OpenAI")

# Store workflow ID mappings in a JSON file for persistence between app restarts
WORKFLOW_MAPPINGS_FILE = 'workflow_mappings.json'

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


# Function to load existing workflow mappings
def load_workflow_mappings():
    if os.path.exists(WORKFLOW_MAPPINGS_FILE):
        try:
            with open(WORKFLOW_MAPPINGS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading workflow mappings: {e}")
    return {}


# Function to save workflow mappings
def save_workflow_mappings(mappings):
    try:
        with open(WORKFLOW_MAPPINGS_FILE, 'w') as f:
            json.dump(mappings, f)
    except Exception as e:
        logger.error(f"Error saving workflow mappings: {e}")


# Create a unique ID for a search query
def create_query_id(topic_string):
    # Create a hash of the topic string to use as a consistent ID
    return hashlib.md5(topic_string.encode()).hexdigest()[:8]


@app.route('/newsfeed', methods=['POST'])
async def get_newsfeed():
    """
    Handle requests for newsfeed results.
    This is a simplified implementation focused on reliability.
    """
    # Get topic string from form
    topicString = request.form.get('topicString')
    if not topicString:
        logger.warning("No topic string provided in request")
        return render_template('index.html', title="Newsfeed Aggregator")
    
    # Create a consistent query ID
    query_id = create_query_id(topicString)
    
    # Get today's date
    dt = str(date.today())
    logger.info(f"NEWSFEED REQUEST: topic='{topicString}', date={dt}, query_id={query_id}")
    
    # Initialize client and results container
    client = await NewTemporalClient()
    articles = []
    workflow_id = None
    
    # Load existing workflow mappings
    workflow_mappings = load_workflow_mappings()
    existing_workflow_id = workflow_mappings.get(query_id)
    
    # STEP 1: Try to get results from an existing workflow
    if existing_workflow_id:
        logger.info(f"Found existing workflow: {existing_workflow_id}")
        
        try:
            # Get handle to existing workflow and query for results
            handle = client.get_workflow_handle(existing_workflow_id)
            articles = await handle.query(NewsfeedWorkflow.get_current_results)
            
            # Send a signal to ensure it keeps running
            try:
                await handle.signal(NewsfeedWorkflow.is_running)
                logger.info(f"Signal sent to existing workflow, got {len(articles)} articles")
            except Exception as e:
                logger.warning(f"Failed to send signal: {e}")
            
            # If we got results, use the existing workflow
            if articles:
                logger.info(f"SUCCESS: Using existing workflow with {len(articles)} results")
                
                # Return results to the frontend
                unique_dates = set(article.get('date', '') for article in articles if 'date' in article)
                logger.info(f"Dates in results: {unique_dates}")
                
                return render_template(
                    'index.html',
                    title="Newsfeed Aggregator",
                    topic=topicString,
                    articles=articles,
                    dates=list(unique_dates),
                    query_id=query_id
                )
        
        except Exception as e:
            logger.error(f"ERROR accessing existing workflow: {e}")
            # Will continue to create a new workflow
    
    # STEP 2: Create a new workflow (either no existing one or it failed)
    # Get any existing results if we had a workflow
    existing_results = []
    if existing_workflow_id:
        try:
            handle = client.get_workflow_handle(existing_workflow_id)
            existing_results = await handle.query(NewsfeedWorkflow.get_current_results)
            logger.info(f"Retrieved {len(existing_results)} results from previous workflow")
        except Exception as e:
            logger.warning(f"Could not get existing results: {e}")
    
    # Create a new workflow with a unique ID
    workflow_id = f"newsfeed-{query_id}-{uuid.uuid4().hex[:8]}"
    logger.info(f"Creating new workflow: {workflow_id}")
    
    try:
        # Start the workflow
        newsfeedInput = NewsfeedInput(dt, topicString, existing_results)
        workflow = await client.start_workflow(
            NewsfeedWorkflow.run,
            newsfeedInput,
            id=workflow_id,
            task_queue=NEWS_TASK_QUEUE,
        )
        
        # Save the new workflow ID
        workflow_mappings[query_id] = workflow_id
        save_workflow_mappings(workflow_mappings)
        logger.info(f"New workflow started and mapping saved")
        
        # Wait for initial results with a timeout
        logger.info("Waiting for initial results...")
        wait_time = 0
        max_wait = 30  # Maximum seconds to wait
        
        while wait_time < max_wait:
            try:
                articles = await workflow.query(NewsfeedWorkflow.get_current_results)
                if articles:
                    logger.info(f"Got {len(articles)} initial results after {wait_time}s")
                    break
                
                # Wait a bit before trying again
                await asyncio.sleep(3)
                wait_time += 3
                logger.info(f"Waiting... ({wait_time}/{max_wait}s)")
            except Exception as e:
                logger.warning(f"Error querying workflow: {e}")
                await asyncio.sleep(3)
                wait_time += 3
        
        logger.info(f"Final result count: {len(articles)}")
    
    except WorkflowAlreadyStartedError as e:
        # Handle the case where the workflow was already started
        logger.warning(f"Workflow was already started: {workflow_id}")
        handle = e.get_existing_workflow_handle()
        
        try:
            articles = await handle.query(NewsfeedWorkflow.get_current_results)
            logger.info(f"Retrieved {len(articles)} articles from existing workflow")
        except Exception as query_error:
            logger.error(f"Failed to query existing workflow: {query_error}")
    
    except Exception as e:
        logger.error(f"Error starting workflow: {str(e)}", exc_info=True)
    
    # Extract unique dates for the template
    unique_dates = set(article.get('date', '') for article in articles if 'date' in article)
    logger.info(f"Dates in results: {unique_dates}")
    
    # Return results to the frontend
    logger.info(f"Rendering template with {len(articles)} articles")
    return render_template(
        'index.html',
        title="Newsfeed Aggregator",
        topic=topicString,
        articles=articles,
        dates=list(unique_dates),
        query_id=query_id
    )


@app.route('/api/newsfeed/<query_id>', methods=['GET'])
async def get_newsfeed_updates(query_id):
    """API endpoint to fetch latest newsfeed results for auto-refresh functionality"""
    logger.info(f"API request for updates on query_id: {query_id}")
    
    # Load workflow mappings
    workflow_mappings = load_workflow_mappings()
    workflow_id = workflow_mappings.get(query_id)
    
    if not workflow_id:
        logger.warning(f"No workflow found for query_id: {query_id}")
        return json.dumps({
            "status": "error",
            "message": "No workflow found for this query",
            "articles": [],
            "dates": []
        }), 404, {'ContentType': 'application/json'}
    
    # Connect to Temporal client
    client = await NewTemporalClient()
    
    try:
        # Get workflow handle and query for results
        handle = client.get_workflow_handle(workflow_id)
        articles = await handle.query(NewsfeedWorkflow.get_current_results)
        
        # Extract unique dates
        unique_dates = sorted(list(set(article.get('date', '') for article in articles if 'date' in article)))
        
        logger.info(f"API: Returning {len(articles)} articles with dates: {unique_dates}")
        
        return json.dumps({
            "status": "success",
            "articles": articles,
            "dates": unique_dates
        }), 200, {'ContentType': 'application/json'}
        
    except Exception as e:
        logger.error(f"Error fetching updates: {str(e)}")
        return json.dumps({
            "status": "error", 
            "message": f"Error: {str(e)}",
            "articles": [],
            "dates": []
        }), 500, {'ContentType': 'application/json'}


if __name__ == "__main__":
    asyncio.run(connect_temporal(app))
    app.run(debug=True, port=3000)
