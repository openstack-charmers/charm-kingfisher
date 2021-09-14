# kingfisher

## Description

TODO: Describe your charm in a few paragraphs of Markdown

## Usage

It is required to do a bit of setup on the cloud prior to running a
benchmark with kingfisher, specifically it is required to 
[build a ClusterAPI compaible image](https://image-builder.sigs.k8s.io/capi/providers/openstack.html)]
and configure the charm to use that image, by name. A brief summary of the
previous link that can help guide a deployer is below:

    apt install qemu-kvm libvirt-daemon-system libvirt-clients virtinst cpu-checker libguestfs-tools libosinfo-bin unzip python3-pip
    pip install ansible
    git clone https://github.com/kubernetes-sigs/image-builder.git
    cd image-builder/images/capi

    cat >~/build-config.json <<EOL
    {
        "http_proxy": "http://squid.internal:3128",
        "https_proxy": "http://squid.internal:3128"
    }
    EOL
    export PACKER_VAR_FILES="/root/build-config.json"
    export PATH="$PATH:/root/image-builder/images/capi/.local/bin"
    make deps-qemu
    make build-qemu-ubuntu-2004
    openstack image create --disk-format=qcow2 --container-format=bare --file ~/ubuntu-2004-kube-v1.20.9 cluster-api

In addition to the customised image, it is necessary to create an SSH key and then
configure this charm to refer to it.

    openstack keypair create --public-key ~/.ssh/id_rsa.pub cluster-api

Once you're ready to deploy a workload cluster, you can do so with the `deploy` action:

    juju deploy kingfisher --constraints mem=4G --trust
    juju run-action -m kingfisher --wait kingfisher/0 deploy

This action will take a while to finish or timeout (configurable), and then the
workload cluster can be cleaned up with the `destroy` action:

    juju run-action -m kingfisher --wait kingfisher/0 destroy

### Troubleshooting

When a deployment fails, it's usually due to resource errors on the cloud. Kingfisher
requires that Octavia is deployed in the cloud, and that an SSH key has been uploaded
in the tenant that's being used for testing. To follow along with what ClusterAPI is
doing, it's possible to tail the logs on the kingfisher node:

    kubectl  -n capo-system logs -l control-plane=capo-controller-manager -c manager --follow

In the event that one machine has been created but then the deployment has stopped, it
is possible to add security group rules to allow SSH, and add a route to the tenant's
router, at which point the deployed SSH key can be used to connect to the control plane
instance. The thing to look at on the instance is the cloud-init-output.log in /var/log.

## Developing

Create and activate a virtualenv with the development requirements:

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements-dev.txt
    charmcraft build
    juju deploy --resource kind=../kind --resource clusterctl=../clusterctl ./kingfisher.charm --constraints mem=4G --trust

## Testing

The Python operator framework includes a very nice harness for testing
operator behaviour without full deployment. Just `run_tests`:

    ./run_tests
