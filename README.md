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

## Developing

Create and activate a virtualenv with the development requirements:

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements-dev.txt

## Testing

The Python operator framework includes a very nice harness for testing
operator behaviour without full deployment. Just `run_tests`:

    ./run_tests
