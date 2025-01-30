import coloredlogs
import os
from logging import getLogger
from temporalio.client import Client, TLSConfig

# Create a logger object and use coloredlogs
logger = getLogger(__name__)
coloredlogs.install(level='INFO')


async def NewTemporalClient() -> Client:
    # Configure environment to connect to and necessary certs
    if (
        os.getenv('TEMPORAL_MTLS_TLS_CERT')
        and os.getenv('TEMPORAL_MTLS_TLS_KEY') is not None
    ):
        CLOUD_ADDR = os.getenv('TEMPORAL_CLI_ADDRESS')
        CLOUD_NS = os.getenv('TEMPORAL_CLI_NAMESPACE')
        CLOUD_CERT = os.getenv('TEMPORAL_MTLS_TLS_CERT')
        CLOUD_KEY = os.getenv('TEMPORAL_MTLS_TLS_KEY')

        clientcert = open(CLOUD_CERT, 'rb').read()
        clientprivatekey = open(CLOUD_KEY, 'rb').read()

        namespacename = CLOUD_NS
        targetdomain = namespacename + ".tmprl.cloud"
        targethost = CLOUD_ADDR

        # Client reference for mTLS / remote Temporal environment
        client = await Client.connect(target_host=targethost, namespace=namespacename,
                                      tls=TLSConfig(domain=targetdomain,
                                                    client_cert=clientcert,
                                                    client_private_key=clientprivatekey)
                                      )
        logger.info("Cloud Client started on " +
                    targethost)
    else:
        client = await Client.connect('localhost:7233')
        logger.info("Local Client started on localhost:7233")

    return client
