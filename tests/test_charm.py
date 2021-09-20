# Copyright 2021 chris
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

import unittest
import unittest.mock as mock

from charm import KingfisherCharm
from ops.model import (
    BlockedStatus,
    MaintenanceStatus,
)
from ops.testing import Harness


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(KingfisherCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    @mock.patch('charm.KingfisherCharm.install_pkgs')
    @mock.patch('charm.ch_templating')
    @mock.patch('charm.subprocess')
    def test_install(self, mock_subprocess, mock_templating, mock_install_pkgs):
        self.harness.charm.on.install.emit()
        self.assertEqual(
            self.harness.model.unit.status,
            MaintenanceStatus(''))
        mock_subprocess.check_call.assert_has_calls([
            mock.call(['snap', 'install', '--classic', 'kubectl']),
            mock.call(['snap', 'install', 'yq']),
            mock.call(['snap', 'install', 'jq']),
        ])
        mock_install_pkgs.assert_called_once()

    @mock.patch('charm.subprocess')
    @mock.patch('charm.ch_templating')
    @mock.patch('charm.KingfisherCharm._get_credentials')
    def test_config_changed(self, mock_get_credentials, mock_templating, mock_subprocess):
        mock_get_credentials.return_value = None
        self.harness.update_config({})
        self.assertEqual(
            self.harness.model.unit.status,
            BlockedStatus('missing credentials access; grant with: juju trust')
        )
        mock_get_credentials.assert_called()
        mock_templating.render.assert_called_once_with(
            'http-proxy.conf',
            '/etc/systemd/system/docker.service.d/http-proxy.conf',
            context={
                'http_proxy': 'http://squid.internal:3128',
                'https_proxy': 'http://squid.internal:3128',
                'no_proxy': '10.5.0.0/16,10.245.160.0/21'})
        mock_subprocess.check_call.assert_has_calls([
            mock.call(['systemctl', 'daemon-reload']),
        ])

    @mock.patch('charm.KingfisherCharm._get_credentials')
    @mock.patch('charm.ch_templating')
    @mock.patch('charm.subprocess')
    def test_config_changed_with_trust(self, mock_subprocess, mock_templating,
                                       mock_get_credentials):
        mock_get_credentials.return_value = {'name': 'value'}
        self.harness.update_config({})
        self.assertEqual(
            self.harness.model.unit.status,
            MaintenanceStatus(message="")
        )
        expected_context = {
            'name': 'value',
            'config': {
                'kubernetes_version': '1.21.1',
                'kubernetes_controllers': 3, 'kubernetes_workers': 3,
                'control_plane_machine_flavor': 'm1.medium',
                'worker_machine_flavor': 'm1.medium',
                'dns_nameservers': '10.245.160.2', 'availability_zones': 'nova',
                'image_name': 'cluster-api', 'ssh_key_name': 'cluster-api',
                'source': None, 'key': None, 'ssl_ca': None, 'timeout': 60}}
        mock_templating.render.assert_has_calls([
            mock.call(
                'http-proxy.conf',
                '/etc/systemd/system/docker.service.d/http-proxy.conf',
                context={
                    'http_proxy': 'http://squid.internal:3128',
                    'https_proxy': 'http://squid.internal:3128',
                    'no_proxy': '10.5.0.0/16,10.245.160.0/21'}),
            mock.call(
                'clouds.yaml',
                '/root/.config/openstack/clouds.yaml',
                context=expected_context),
            mock.call(
                'os_environment.sh',
                '/etc/profile.d/os_environment.sh',
                context=expected_context),
            mock.call(
                'env.sh',
                '/etc/profile.d/env.sh',
                context=expected_context)
        ])

    @mock.patch('charm.KingfisherCharm._check_deploy_done')
    @mock.patch('charm.subprocess.check_output')
    def test_deploy_action(self, mock_check_output, mock_check_deploy_done):
        # the harness doesn't (yet!) help much with actions themselves
        action_event = mock.Mock(params={"fail": ""})
        mock_check_deploy_done.return_value = True
        mock_output = mock.MagicMock()
        mock_check_output.return_value = mock_output
        self.harness.charm._on_deploy_action(action_event)
        mock_check_deploy_done.assert_called_once()
        mock_check_output.assert_has_calls([
            mock.call([
                '/bin/bash', '-c',
                'source /etc/profile; None config cluster test-cluster '
                '--kubernetes-version 1.21.1 --control-plane-machine-count 3 '
                '--worker-machine-count 3'], cwd='/root'),
            mock.call(['kubectl', 'apply', '-f', '-'], input=mock_output, cwd='/root')])
        # self.assertTrue(action_event.set_results.called)

    @mock.patch('charm.subprocess.check_call')
    def test_destroy_action(self, mock_check_call):
        # the harness doesn't (yet!) help much with actions themselves
        action_event = mock.Mock(params={"fail": ""})
        self.harness.charm._on_destroy_action(action_event)
        mock_check_call.assert_called_once_with(
            ['kubectl', '--kubeconfig=/root/.kube/config',
             'delete', 'cluster', 'test-cluster'],
            cwd="/root"
        )

        # self.assertTrue(action_event.set_results.called)

    # def test_action_fail(self):
    #     action_event = Mock(params={"fail": "fail this"})
    #     self.harness.charm._on_fortune_action(action_event)

    #     self.assertEqual(action_event.fail.call_args, [("fail this",)])

    # def test_httpbin_pebble_ready(self):
    #     # Check the initial Pebble plan is empty
    #     initial_plan = self.harness.get_container_pebble_plan("httpbin")
    #     self.assertEqual(initial_plan.to_yaml(), "{}\n")
    #     # Expected plan after Pebble ready with default config
    #     expected_plan = {
    #         "services": {
    #             "httpbin": {
    #                 "override": "replace",
    #                 "summary": "httpbin",
    #                 "command": "gunicorn -b 0.0.0.0:80 httpbin:app -k gevent",
    #                 "startup": "enabled",
    #                 "environment": {"thing": "🎁"},
    #             }
    #         },
    #     }
    #     # Get the httpbin container from the model
    #     container = self.harness.model.unit.get_container("httpbin")
    #     # Emit the PebbleReadyEvent carrying the httpbin container
    #     self.harness.charm.on.httpbin_pebble_ready.emit(container)
    #     # Get the plan now we've run PebbleReady
    #     updated_plan = self.harness.get_container_pebble_plan("httpbin").to_dict()
    #     # Check we've got the plan we expected
    #     self.assertEqual(expected_plan, updated_plan)
    #     # Check the service was started
    #     service = self.harness.model.unit.get_container("httpbin").get_service("httpbin")
    #     self.assertTrue(service.is_running())
    #     # Ensure we set an ActiveStatus with no message
    #     self.assertEqual(self.harness.model.unit.status, ActiveStatus())
