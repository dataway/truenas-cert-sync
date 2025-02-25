#!/usr/local/share/truenas-cert-sync/bin/python
# Copyright 2025 Anthony Uk
# https://github.com/dataway/truenas-cert-sync
# SPDX-License-Identifier: MIT
import logging
import os
import re
import ssl
import sys
import time

from truenas_api_client import Client



__version__ = 'unset' # Will be set by docker build



logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



def read_file_by_env(env: str):
    fn = os.getenv(env)
    if fn is None:
        raise ValueError(f"Environment variable '{env}' unset")
    with open(fn, 'r') as f:
        return f.read()



def read_cert_by_env(env: str):
    fn = os.getenv(env)
    cert = read_file_by_env(env).strip()
    name = os.getenv(f"{env}_NAME")
    if name:
        return cert, name
    ssl_cert = ssl._ssl._test_decode_cert(fn)
    cn = [sattr[0][1] for sattr in ssl_cert['subject'] if sattr[0][0] == 'commonName'][0]
    name = re.sub(r'[^a-zA-Z0-9_-]', '_', cn)
    return cert, name



def wait_for_job(c, job):
    while True:
        r = c.call('core.get_jobs', [('id', '=', job)])
        state = r[0]['state']
        if state in ('SUCCESS', 'FAILED'):
            logger.info("job %d: %s", job, state)
            if state != 'SUCCESS':
                raise RuntimeError(f"Job {job} failed")
            return r[0]
        time.sleep(1)



def cert_sync(uri, apikey, username, password, force=False):
    ca, ca_name = read_cert_by_env('TRUENAS_SYNC_CA')
    cert, cert_name = read_cert_by_env('TRUENAS_SYNC_CERT')
    key = read_file_by_env('TRUENAS_SYNC_KEY').strip()

    with Client(uri=uri, verify_ssl=False) as c:
        logger.info("Connecting to %s", uri)
        # Authenticate
        if apikey is None:
            c.call('auth.login', username, password)
        else:
            c.call('auth.login_with_api_key', apikey)

        # Check if CA certificate already exists, if not create it
        existing_cacerts = c.call('certificateauthority.query')
        for existing_cacert in existing_cacerts:
            if existing_cacert['certificate'].strip() == ca:
                logger.info(f"CA certificate already exists under name '{existing_cacert['name']}'")
                break
        else:
            logger.info("Creating CA certificate '%s'", ca_name)
            r = c.call('certificateauthority.create', {
                'name': ca_name,
                'create_type': 'CA_CREATE_IMPORTED',
                'add_to_trusted_store': True,
                'certificate': ca,
            })

        # Check if certificate already exists.
        # If it does, do nothing.
        # If a different certificate exists under the same name, first change its name, then
        # create the new certificate and if that succeeds, delete the old one.
        existing_certs = c.call('certificate.query')
        previous_cert = None
        for existing_cert in existing_certs:
            if existing_cert['certificate'].strip() == cert and not force:
                logger.info(f"Certificate already exists under name '{existing_cert['name']}'")
                break
            if existing_cert['name'] == cert_name:
                logger.info(f"A different already exists under name '{cert_name}'. Rotating")
                previous_cert = existing_cert
                ts = int(time.time())
                job = c.call('certificate.update', existing_cert['id'], {
                    'name': f"{cert_name}_old_{ts}",
                })
                logger.info("Certificate rename job: %d", job)
                wait_for_job(c, job)
        else:
            logger.info("Creating certificate '%s'", cert_name)
            job = c.call('certificate.create', {
                'name': cert_name,
                'create_type': 'CERTIFICATE_CREATE_IMPORTED',
                'privatekey': key,
                'certificate': cert,
            })
            logger.info("Certificate creation job: %d", job)
            job_result = wait_for_job(c, job)
            logger.info("Setting UI certificate")
            r = c.call('system.general.update', {
                'ui_certificate': job_result['result']['id'],
            })
            if previous_cert:
                logger.info("Deleting previous certificate")
                job = c.call('certificate.delete', previous_cert['id'])
                logger.info("Certificate deletion job: %d", job)
                wait_for_job(c, job)
            logger.info("Restarting UI")
            job = c.call('system.general.ui_restart')
    return 0



def loop(oneshot=False, force=False):
    uri = os.getenv('TRUENAS_URL')
    apikey = os.getenv('TRUENAS_APIKEY')
    username = os.getenv('TRUENAS_USERNAME')
    password = os.getenv('TRUENAS_PASSWORD')
    if uri is None:
        raise ValueError("Environment variable 'TRUENAS_URL' unset")
    if apikey is None and (username is None or password is None):
        raise ValueError("Either 'TRUENAS_APIKEY' or both 'TRUENAS_USERNAME' and 'TRUENAS_PASSWORD' must be set")
    if apikey is not None and (username is not None or password is not None):
        raise ValueError("If 'TRUENAS_APIKEY' is set, 'TRUENAS_USERNAME' and 'TRUENAS_PASSWORD' must not be set")

    cert_sync(uri, apikey, username, password, force=force)
    if oneshot:
        return 0

    prev_mtime = 0.0
    while True:
        last_mtime = max(
            os.stat(os.getenv('TRUENAS_SYNC_CA')).st_mtime,
            os.stat(os.getenv('TRUENAS_SYNC_CERT')).st_mtime,
            os.stat(os.getenv('TRUENAS_SYNC_KEY')).st_mtime,
        )
        if prev_mtime > 0.0 and last_mtime != prev_mtime:
            logger.info("Certificate files changed, syncing")
            cert_sync(uri, apikey, username, password)
        time.sleep(60)
        prev_mtime = last_mtime



if __name__ == '__main__':
    logging.info("Starting truenas-cert-sync version %s", __version__)
    oneshot = '--oneshot' in sys.argv
    force = '--force' in sys.argv
    try:
        sys.exit(loop(oneshot=oneshot, force=force))
    except Exception as e:
        logger.error(e)
        sys.exit(1)
