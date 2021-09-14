#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charm the service.

Refer to the following post for a quick-start guide that will help you
develop a new k8s charm using the Operator Framework:

    https://discourse.charmhub.io/t/4208
"""

import json
import logging
from charmhelpers.core.hookenv import action_fail
import openstack
import os
import subprocess
import time
import yaml

from typing import (
    Optional,
)

import charmhelpers.core.templating as ch_templating
import charmhelpers.core.host as ch_host

from ops.framework import StoredState
from ops.main import main
from ops.model import (
    ActiveStatus,
    BlockedStatus,
    ModelError,
)
import ops_openstack.core

import timeout

logger = logging.getLogger(__name__)


class KingfisherCharm(ops_openstack.core.OSBaseCharm):
    """Charm the service."""

    PACKAGES = ["docker.io"]
    TEST_CLUSTER_KUBECONFIG_PATH = "/root/test-cluster-kubeconfig.yaml"
    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)
        super().register_status_check(self.status_check_trust)
        super().register_status_check(self.status_check_resources)
        self._stored.set_default(
            cluster_api_initialized=False)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.deploy_action, self._on_deploy_action)
        self.framework.observe(self.on.destroy_action, self._on_destroy_action)

    def status_check_trust(self):
        if self.credentials is None:
            no_creds_msg = 'missing credentials access; grant with: juju trust'
            # no creds provided
            return BlockedStatus(message=no_creds_msg)
        return ActiveStatus()

    def status_check_resources(self):
        if None in [self.kind_path, self.clusterctl_path]:
            msg = "Missing required resources for cluster-api."
            return BlockedStatus(message=msg)
        return ActiveStatus()

    def _on_install(self, event):
        subprocess.check_call(['snap', 'install', '--classic', 'kubectl'])
        subprocess.check_call(['snap', 'install', 'yq'])
        subprocess.check_call(['snap', 'install', 'jq'])

    @property
    def credentials(self):
        return self._get_credentials()

    @property
    def openstack_client(self):
        return openstack.connect()

    @property
    def kind_path(self):
        try:
            path = self.model.resources.fetch("kind")
            os.chmod(path, 0o755)
            return path
        except ModelError:
            return None

    @property
    def clusterctl_path(self):
        try:
            path = self.model.resources.fetch("clusterctl")
            os.chmod(path, 0o755)
            return path
        except ModelError:
            return None

    @property
    def timeout(self) -> int:
        """
        Timeout, in minutes, for a deploy
        """
        return self.model.config.get('timeout')

    def _get_credentials(self):
        try:
            result = subprocess.run(['credential-get'],
                                    check=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            raw_creds_data = yaml.safe_load(result.stdout.decode('utf8'))
            logger.info('Using credentials-get for credentials, got: %s' % raw_creds_data)
            creds_data = raw_creds_data['credential']['attributes']
            creds_data['endpoint'] = raw_creds_data['endpoint']
            creds_data['region'] = raw_creds_data['region']
            creds_data['cloud_name'] = raw_creds_data['name']
            return dict((k.replace('-', '_'), v) for k, v in creds_data.items())
        except subprocess.CalledProcessError as e:
            if 'permission denied' not in e.stderr.decode('utf8'):
                raise

    def _on_config_changed(self, event):
        """Just an example to show how to deal with changed configuration.

        TEMPLATE-TODO: change this example to suit your needs.
        If you don't need to handle config, you can remove this method,
        the hook created in __init__.py for it, the corresponding test,
        and the config.py file.

        Learn more about config at https://juju.is/docs/sdk/config
        """
        with ch_host.restart_on_change({
            '/etc/systemd/system/docker.service.d/http-proxy.conf': ['docker']
        }):
            ch_templating.render(
                'http-proxy.conf', '/etc/systemd/system/docker.service.d/http-proxy.conf',
                context={
                    'http_proxy': 'http://squid.internal:3128',
                    'https_proxy': 'http://squid.internal:3128',
                    'no_proxy': '10.5.0.0/16,10.245.160.0/21',
                }
            )
            subprocess.check_call(['systemctl', 'daemon-reload'])
        if self.credentials is None:
            self._update_status(event)
            return
        ctxt = self.credentials
        ctxt['config'] = dict((k.replace('-', '_'), v) for k, v in self.model.config.items())

        ch_templating.render(
            'clouds.yaml', '/root/.config/openstack/clouds.yaml',
            context=self.credentials)
        # This has to be run after the above as it relies on clouds.yaml being present
        if ctxt['config'].get('availability_zones') is None:
            ctxt['config']['availability_zones'] = ','.join(list([
                zone.name for zone in self.openstack_client.compute.availability_zones()]))
        ch_templating.render(
            'os_environment.sh', '/etc/profile.d/os_environment.sh',
            context=ctxt)
        ch_templating.render(
            'env.sh', '/etc/profile.d/env.sh',
            context=self.credentials)
        if None in [self.kind_path, self.clusterctl_path]:
            return
        self.enable_cluster_api()
        self._stored.is_started = True

    def enable_cluster_api(self):
        if self._stored.cluster_api_initialized:
            return
        subprocess.check_call([self.kind_path, 'create', 'cluster'],
                              cwd='/root')
        subprocess.check_call(
            [self.clusterctl_path, 'init', '--infrastructure', 'openstack'],
            cwd='/root')
        self._stored.cluster_api_initialized = True

    def _on_deploy_action(self, event):
        output = subprocess.check_output([
            '/bin/bash', '-c', "source /etc/profile; {}".format(" ".join([
                str(self.clusterctl_path), 'config', 'cluster', 'test-cluster',
                '--kubernetes-version', str(self.model.config.get('kubernetes-version')),
                '--control-plane-machine-count',
                str(self.model.config.get('kubernetes-controllers')),
                '--worker-machine-count', str(self.model.config.get('kubernetes-workers')),
            ]))
        ], cwd="/root")
        # The below uses check_output even though we do not care about it's
        # output because check_call doesn't accept an input keyword argument
        subprocess.check_output(
            ['kubectl', 'apply', '-f', '-'],
            input=output, cwd="/root")
        try:
            with timeout.Timeout(minutes=self.timeout):
                while not self._check_deploy_done():
                    time.sleep(1)
        except TimeoutError:
            action_fail("Deployment timed out after {}".format(self.timeout))

    def _test_cluster_kubectl(self) -> Optional[str]:
        if not os.path.exists(self.TEST_CLUSTER_KUBECONFIG_PATH):
            try:
                subprocess.check_call(
                    [
                        '/bin/bash', '-c',
                        'kubectl --kubeconfig=/root/.kube/config get '
                        'secrets test-cluster-kubeconfig -o json | '
                        "jq -r '.data.value' |"
                        "base64 -d > '{}'".format(self.TEST_CLUSTER_KUBECONFIG_PATH)
                    ], cwd="/root",
                    stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError as err:
                logging.warning("Could not retrieve config from kubectl: {}".format(err))
            try:
                if os.path.getsize(self.TEST_CLUSTER_KUBECONFIG_PATH) == 0:
                    os.remove(self.TEST_CLUSTER_KUBECONFIG_PATH)
                    return None
            except (FileNotFoundError, OSError,) as err:
                logging.warning("Could not store config: {}".format(err))
        return self.TEST_CLUSTER_KUBECONFIG_PATH

    def _kubectl_get_workload_nodes(self):
        kubeconfig = self._test_cluster_kubectl()
        if kubeconfig is None:
            return False
        try:
            output = subprocess.check_output(
                ['kubectl', '--kubeconfig', kubeconfig, 'get', 'nodes', '--output=json'],
                stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            return False
        nodes = json.loads(output)
        return len(nodes['items']) == (
            self.model.config.get('kubernetes-controllers') +
            self.model.config.get('kubernetes-workers'))
        return True

    def _kubectl_get_cluster(self):
        try:
            output = subprocess.check_output(
                ['kubectl', '--kubeconfig=/root/.kube/config',
                 'get', 'cluster', 'test-cluster'],
                cwd="/root",
                stderr=subprocess.DEVNULL)
            return b'Provisioned' in output
        except subprocess.CalledProcessError:
            return False

    def _check_deploy_done(self):
        return self._kubectl_get_cluster() and self._kubectl_get_workload_nodes()

    def _on_destroy_action(self, event):
        subprocess.check_call(
            ['kubectl', '--kubeconfig=/root/.kube/config',
             'delete', 'cluster', 'test-cluster'],
            cwd="/root")


if __name__ == "__main__":
    main(KingfisherCharm)
