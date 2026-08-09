#!/usr/bin/env python3

import logging
import threading
from typing import Optional
from zabbix_utils import ZabbixAPI
from dotenv import load_dotenv

from .config import EnvVars, parse_bool_env, parse_int_env, get_env, setup_logging

load_dotenv()

setup_logging(debug=parse_bool_env(EnvVars.DEBUG))
logger = logging.getLogger(__name__)

zabbix_api_client: Optional[ZabbixAPI] = None
_client_lock = threading.Lock()


def get_zabbix_client() -> ZabbixAPI:
    global zabbix_api_client

    if zabbix_api_client is not None:
        return zabbix_api_client

    with _client_lock:
        if zabbix_api_client is not None:
            return zabbix_api_client

        url = get_env(EnvVars.ZABBIX_URL)
        if not url:
            raise ValueError(f"{EnvVars.ZABBIX_URL} environment variable is required")

        logger.info(f"Initializing Zabbix API client for {url}")

        verify_ssl = parse_bool_env(EnvVars.VERIFY_SSL, default=True)
        if not verify_ssl:
            logger.warning(
                "SSL certificate verification is DISABLED. "
                "This should NEVER be used in production environments!"
            )

        skip_version_check = parse_bool_env(EnvVars.ZABBIX_SKIP_VERSION_CHECK)
        if skip_version_check:
            logger.info("Skipping Zabbix API version check")

        timeout = parse_int_env(EnvVars.ZABBIX_API_TIMEOUT, default=30)
        logger.info(f"API timeout set to {timeout} seconds")

        zabbix_api_client = ZabbixAPI(
            url=url,
            validate_certs=verify_ssl,
            skip_version_check=skip_version_check,
            timeout=timeout,
        )

        token = get_env(EnvVars.ZABBIX_TOKEN)
        if token:
            logger.info("Authenticating with API token")
            zabbix_api_client.login(token=token)
        else:
            user = get_env(EnvVars.ZABBIX_USER)
            password = get_env(EnvVars.ZABBIX_PASSWORD)
            if not user or not password:
                raise ValueError(
                    f"Either {EnvVars.ZABBIX_TOKEN} or "
                    f"{EnvVars.ZABBIX_USER}/{EnvVars.ZABBIX_PASSWORD} must be set"
                )
            logger.info("Authenticating with username/password")
            zabbix_api_client.login(user=user, password=password)

        logger.info("Successfully authenticated with Zabbix API")

        return zabbix_api_client
