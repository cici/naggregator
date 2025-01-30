from temporalio.client import Client, TLSConfig
from typing import Optional
from logging import getLogger
import coloredlogs
import os

logger = getLogger(__name__)
coloredlogs.install(level='INFO')

async def get_client() -> Client:

    if (
        os.getenv("TEMPORAL_MTLS_TLS_CERT")
        and os.getenv("TEMPORAL_MTLS_TLS_KEY") is not None
    ):
        server_root_ca_cert: Optional[bytes] = None
        with open(os.getenv("TEMPORAL_MTLS_TLS_CERT"), "rb") as f:
            client_cert = f.read()

        with open(os.getenv("TEMPORAL_MTLS_TLS_KEY"), "rb") as f:
            client_key = f.read()

        # Start client
        client = await Client.connect(
            os.getenv("TEMPORAL_HOST_URL"),
            namespace=os.getenv("TEMPORAL_NAMESPACE"),
            tls=TLSConfig(
                server_root_ca_cert=server_root_ca_cert,
                client_cert=client_cert,
                client_private_key=client_key,
            ),
            # data_converter=dataclasses.replace(
            #     temporalio.converter.default(), payload_codec=EncryptionCodec()
            # ),
        )
        logger.info("Cloud Client started on " + os.getenv("TEMPORAL_HOST_URL"))
    else:
        client = await Client.connect(
            "localhost:7233",
        )
        logger.info("Local Client started on localhost:7233")

    return client
