#!/usr/bin/env python3
# Copyright 2021 chris
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charm the service.

Refer to the following post for a quick-start guide that will help you
develop a new k8s charm using the Operator Framework:

    https://discourse.charmhub.io/t/4208
"""

import logging
import subprocess
import yaml

import charmhelpers.core.templating as ch_templating

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import BlockedStatus, MaintenanceStatus

logger = logging.getLogger(__name__)


class KingfisherCharm(CharmBase):
    """Charm the service."""

    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        # self.framework.observe(self.on.fortune_action, self._on_fortune_action)
        self.framework.observe(self.on.update_status, self._update_status)

    def _update_status(self, _):
        if self.credentials is None:
            no_creds_msg = 'missing credentials access; grant with: juju trust'
            # no creds provided
            self.unit.status = BlockedStatus(message=no_creds_msg)

    def _on_install(self, event):
        subprocess.check_call(['snap', 'install', '--classic', 'microk8s'])
        self.unit.status = MaintenanceStatus(message="Microk8s installed, waiting for ready.")

    @property
    def credentials(self):
        return self._get_credentials()

    def _get_credentials(self):
        try:
            result = subprocess.run(['credential-get'],
                                    check=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            creds_data = yaml.safe_load(result.stdout.decode('utf8'))
            logger.info('Using credentials-get for credentials')
            return creds_data
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
        ch_templating.render(
            'containerd-env',
            '/var/snap/microk8s/current/args/containerd-env',
            context={}
        )
        # doing stop and start as separate subprocess calls sometimes
        # has the start exit 1
        subprocess.check_call(['microk8s', 'stop'])
        try:
            subprocess.check_call(['microk8s', 'start'])
        except subprocess.CalledProcessError as e:
            # https://github.com/ubuntu/microk8s/issues/2363
            logger.warning("'microk8s start' failed: %s", e)
        subprocess.check_call(['microk8s', 'status', '--wait-ready'])
        self.unit.status = MaintenanceStatus(message="MicroK8s is configured.")

        if self.credentials is None:
            self._update_status(event)
            return
        ch_templating.render(
            'clouds.yaml', '/root/.config/openstack/clouds.yaml',
            context=self.credentials)
        self.unit.status = MaintenanceStatus(message="Ready to run benchmark.")
        self._update_status(event)

    # def _on_httpbin_pebble_ready(self, event):
    #     """Define and start a workload using the Pebble API.

    #     TEMPLATE-TODO: change this example to suit your needs.
    #     You'll need to specify the right entrypoint and environment
    #     configuration for your specific workload. Tip: you can see the
    #     standard entrypoint of an existing container using docker inspect

    #     Learn more about Pebble layers at https://github.com/canonical/pebble
    #     """
    #     # Get a reference the container attribute on the PebbleReadyEvent
    #     container = event.workload
    #     # Define an initial Pebble layer configuration
    #     pebble_layer = {
    #         "summary": "httpbin layer",
    #         "description": "pebble config layer for httpbin",
    #         "services": {
    #             "httpbin": {
    #                 "override": "replace",
    #                 "summary": "httpbin",
    #                 "command": "gunicorn -b 0.0.0.0:80 httpbin:app -k gevent",
    #                 "startup": "enabled",
    #                 "environment": {"thing": self.model.config["thing"]},
    #             }
    #         },
    #     }
    #     # Add intial Pebble config layer using the Pebble API
    #     container.add_layer("httpbin", pebble_layer, combine=True)
    #     # Autostart any services that were defined with startup: enabled
    #     container.autostart()
    #     # Learn more about statuses in the SDK docs:
    #     # https://juju.is/docs/sdk/constructs#heading--statuses
    #     self.unit.status = ActiveStatus()

    # def _on_fortune_action(self, event):
    #     """Just an example to show how to receive actions.

    #     TEMPLATE-TODO: change this example to suit your needs.
    #     If you don't need to handle actions, you can remove this method,
    #     the hook created in __init__.py for it, the corresponding test,
    #     and the actions.py file.

    #     Learn more about actions at https://juju.is/docs/sdk/actions
    #     """
    #     fail = event.params["fail"]
    #     if fail:
    #         event.fail(fail)
    #     else:
    #         event.set_results(
    #             {"fortune": "A bug in the code is worth two in the documentation."})


if __name__ == "__main__":
    main(KingfisherCharm)
