#!/bin/bash
# Copyright 2019 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

CAPO_SCRIPT=env.rc
CAPO_CLOUDS_PATH=".config/openstack/clouds.yaml"
export CAPO_CLOUD="{{ cloud_name }}"

CAPO_YQ_TYPE=$(file "$(which yq)")
if [[ ${CAPO_YQ_TYPE} == *"Python script"* ]]; then
  echo "Wrong version of 'yq' installed, please install the one from https://github.com/mikefarah/yq"
  echo ""
  exit 1
fi

CAPO_CLOUDS_PATH=${CAPO_CLOUDS_PATH:-""}
CAPO_OPENSTACK_CLOUD_YAML_CONTENT=$(cat "${CAPO_CLOUDS_PATH}")

CAPO_YQ_VERSION=$(yq -V)
yqNavigating(){
        if [[ ${CAPO_YQ_VERSION} == *"version 1"* || ${CAPO_YQ_VERSION} == *"version 2"* || ${CAPO_YQ_VERSION} == *"version 3"* ]]; then
                yq r $1 $2
        else
                yq e .$2 $1
        fi
}

# Just blindly parse the cloud.yaml here, overwriting old vars.
CAPO_AUTH_URL=$(echo "$CAPO_OPENSTACK_CLOUD_YAML_CONTENT" | yqNavigating - clouds.${CAPO_CLOUD}.auth.auth_url)
CAPO_USERNAME=$(echo "$CAPO_OPENSTACK_CLOUD_YAML_CONTENT" | yqNavigating - clouds.${CAPO_CLOUD}.auth.username)
CAPO_PASSWORD=$(echo "$CAPO_OPENSTACK_CLOUD_YAML_CONTENT" | yqNavigating - clouds.${CAPO_CLOUD}.auth.password)
CAPO_REGION=$(echo "$CAPO_OPENSTACK_CLOUD_YAML_CONTENT" | yqNavigating - clouds.${CAPO_CLOUD}.region_name)
CAPO_PROJECT_ID=$(echo "$CAPO_OPENSTACK_CLOUD_YAML_CONTENT" | yqNavigating - clouds.${CAPO_CLOUD}.auth.project_id)
CAPO_PROJECT_NAME=$(echo "$CAPO_OPENSTACK_CLOUD_YAML_CONTENT" | yqNavigating - clouds.${CAPO_CLOUD}.auth.project_name)
CAPO_DOMAIN_NAME=$(echo "$CAPO_OPENSTACK_CLOUD_YAML_CONTENT" | yqNavigating - clouds.${CAPO_CLOUD}.auth.user_domain_name)
CAPO_APPLICATION_CREDENTIAL_NAME=$(echo "$CAPO_OPENSTACK_CLOUD_YAML_CONTENT" | yqNavigating - clouds.${CAPO_CLOUD}.auth.application_credential_name)
CAPO_APPLICATION_CREDENTIAL_ID=$(echo "$CAPO_OPENSTACK_CLOUD_YAML_CONTENT" | yqNavigating - clouds.${CAPO_CLOUD}.auth.application_credential_id)
CAPO_APPLICATION_CREDENTIAL_SECRET=$(echo "$CAPO_OPENSTACK_CLOUD_YAML_CONTENT" | yqNavigating - clouds.${CAPO_CLOUD}.auth.application_credential_secret)
if [[ "$CAPO_DOMAIN_NAME" = "" || "$CAPO_DOMAIN_NAME" = "null" ]]; then
  CAPO_DOMAIN_NAME=$(echo "$CAPO_OPENSTACK_CLOUD_YAML_CONTENT" | yqNavigating - clouds.${CAPO_CLOUD}.auth.domain_name)
fi
CAPO_DOMAIN_ID=$(echo "$CAPO_OPENSTACK_CLOUD_YAML_CONTENT" | yqNavigating - clouds.${CAPO_CLOUD}.auth.user_domain_id)
if [[ "$CAPO_DOMAIN_ID" = "" || "$CAPO_DOMAIN_ID" = "null" ]]; then
  CAPO_DOMAIN_ID=$(echo "$CAPO_OPENSTACK_CLOUD_YAML_CONTENT" | yqNavigating - clouds.${CAPO_CLOUD}.auth.domain_id)
fi
CAPO_CACERT_ORIGINAL=$(echo "$CAPO_OPENSTACK_CLOUD_YAML_CONTENT" | yqNavigating - clouds.${CAPO_CLOUD}.cacert)

export OPENSTACK_CLOUD="${CAPO_CLOUD}"

# Build OPENSTACK_CLOUD_YAML_B64
if [[ ${CAPO_YQ_VERSION} == *"version 1"* || ${CAPO_YQ_VERSION} == *"version 2"* || ${CAPO_YQ_VERSION} == *"version 3"* ]]; then
    CAPO_OPENSTACK_CLOUD_YAML_SELECTED_CLOUD_B64=$(echo "${CAPO_OPENSTACK_CLOUD_YAML_CONTENT}" | yq r - clouds.${CAPO_CLOUD} | yq p - clouds.${CAPO_CLOUD} | base64 --wrap=0)
else
    CAPO_OPENSTACK_CLOUD_YAML_SELECTED_CLOUD_B64=$(echo "${CAPO_OPENSTACK_CLOUD_YAML_CONTENT}" | yq e .clouds.${CAPO_CLOUD} - | yq eval '{"clouds": {"'${CAPO_CLOUD}'": . }}' - | base64 --wrap=0)
fi
export OPENSTACK_CLOUD_YAML_B64="${CAPO_OPENSTACK_CLOUD_YAML_SELECTED_CLOUD_B64}"

# Build OPENSTACK_CLOUD_PROVIDER_CONF_B64
# Basic cloud.conf, no LB configuration as that data is not known yet.
CAPO_CLOUD_PROVIDER_CONF_TMP=$(mktemp /tmp/cloud.confXXX)
cat >> ${CAPO_CLOUD_PROVIDER_CONF_TMP} << EOF
[Global]
auth-url=${CAPO_AUTH_URL}
EOF

if [[ "$CAPO_USERNAME" != "" && "$CAPO_USERNAME" != "null" ]]; then
  echo "username=\"${CAPO_USERNAME}\"" >> ${CAPO_CLOUD_PROVIDER_CONF_TMP}
fi

if [[ "$CAPO_PASSWORD" != "" && "$CAPO_PASSWORD" != "null" ]]; then
  echo "password=\"${CAPO_PASSWORD}\"" >> ${CAPO_CLOUD_PROVIDER_CONF_TMP}
fi

if [[ "$CAPO_PROJECT_ID" != "" && "$CAPO_PROJECT_ID" != "null" ]]; then
  echo "tenant-id=\"${CAPO_PROJECT_ID}\"" >> ${CAPO_CLOUD_PROVIDER_CONF_TMP}
fi
if [[ "$CAPO_PROJECT_NAME" != "" && "$CAPO_PROJECT_NAME" != "null" ]]; then
  echo "tenant-name=\"${CAPO_PROJECT_NAME}\"" >> ${CAPO_CLOUD_PROVIDER_CONF_TMP}
fi
if [[ "$CAPO_DOMAIN_NAME" != "" && "$CAPO_DOMAIN_NAME" != "null" ]]; then
  echo "domain-name=\"${CAPO_DOMAIN_NAME}\"" >> ${CAPO_CLOUD_PROVIDER_CONF_TMP}
fi
if [[ "$CAPO_DOMAIN_ID" != "" && "$CAPO_DOMAIN_ID" != "null" ]]; then
  echo "domain-id=\"${CAPO_DOMAIN_ID}\"" >> ${CAPO_CLOUD_PROVIDER_CONF_TMP}
fi

if [[ "$CAPO_CACERT_ORIGINAL" != "" && "$CAPO_CACERT_ORIGINAL" != "null" ]]; then
  echo "ca-file=\"/etc/certs/cacert\"" >> ${CAPO_CLOUD_PROVIDER_CONF_TMP}
fi
if [[ "$CAPO_REGION" != "" && "$CAPO_REGION" != "null" ]]; then
  echo "region=\"${CAPO_REGION}\"" >> ${CAPO_CLOUD_PROVIDER_CONF_TMP}
fi
if [[ "$CAPO_APPLICATION_CREDENTIAL_NAME" != "" && "$CAPO_APPLICATION_CREDENTIAL_NAME" != "null" ]]; then
  echo "application-credential-name=\"${CAPO_APPLICATION_CREDENTIAL_NAME}\"" >> ${CAPO_CLOUD_PROVIDER_CONF_TMP}
fi

if [[ "$CAPO_APPLICATION_CREDENTIAL_ID" != "" && "$CAPO_APPLICATION_CREDENTIAL_ID" != "null" ]]; then
  echo "application-credential-id=\"${CAPO_APPLICATION_CREDENTIAL_ID}\"" >> ${CAPO_CLOUD_PROVIDER_CONF_TMP}
fi

if [[ "$CAPO_APPLICATION_CREDENTIAL_SECRET" != "" && "$CAPO_APPLICATION_CREDENTIAL_SECRET" != "null" ]]; then
  echo "application-credential-secret=\"${CAPO_APPLICATION_CREDENTIAL_SECRET}\"" >> ${CAPO_CLOUD_PROVIDER_CONF_TMP}
fi
export OPENSTACK_CLOUD_PROVIDER_CONF_B64="$(cat ${CAPO_CLOUD_PROVIDER_CONF_TMP} | base64 --wrap=0)"

# Build OPENSTACK_CLOUD_CACERT_B64
OPENSTACK_CLOUD_CACERT_B64=$(echo "" | base64 --wrap=0)
if [[ "$CAPO_CACERT_ORIGINAL" != "" && "$CAPO_CACERT_ORIGINAL" != "null" ]]; then
  OPENSTACK_CLOUD_CACERT_B64=$(cat "$CAPO_CACERT_ORIGINAL"  | base64 --wrap=0)
fi
export OPENSTACK_CLOUD_CACERT_B64
