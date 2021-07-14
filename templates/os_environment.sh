export OS_USERNAME={{ username }}
export OS_PASSWORD={{ password }}
export OS_PROJECT_DOMAIN_NAME={{ project_domain_name }}
export OS_DOMAIN_NAME={{ user_domain_name }}
export OS_USER_DOMAIN_NAME={{ user_domain_name }}
export OS_AUTH_URL={{ endpoint }}
export OS_REGION_NAME={{ region}}
export OS_AUTH_VERSION={{ version }}
export OS_IDENTITY_API_VERSION={{ version }}
export OS_TENANT_NAME={{ tenant_name }}

# Variables eneded to configure ClusterAPI
export OPENSTACK_CONTROL_PLANE_MACHINE_FLAVOR={{ config.control_plane_machine_flavor }}
export OPENSTACK_DNS_NAMESERVERS={{ config.dns_nameservers }}
export OPENSTACK_FAILURE_DOMAIN={{ config.availability_zones }}
export OPENSTACK_IMAGE_NAME={{ config.image_name }}
export OPENSTACK_NODE_MACHINE_FLAVOR={{ config.worker_machine_flavor }}
export OPENSTACK_SSH_KEY_NAME={{ config.ssh_key_name }}