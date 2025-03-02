# truenas-cert-sync

## Deploy certificates from a K8S cluster to TrueNAS

This is a simple script that will deploy a TLS certificate from a Kubernetes
cluster to a [TrueNAS](https://www.truenas.com/truenas-scale/) server to be used as the
web GUI certificate.

It is intended to be used with in-cluster private certificate issuers such as
[cert-manager](https://cert-manager.io/docs/)
with [step-ca](https://smallstep.com/docs/step-ca/).
It will not perform any certificate issuance itself, nor will it handle ACME challenges.

My setup is as follows:

* TrueNAS SCALE ElectricEel-24.10.2
* k3s v1.31.5+k3s1
* cert-manager v1.17.1
* step-ca v0.28.1
* step-issuer v0.9.7

I don't know how many people will find this useful as it applies
only to people with both a Kubernetes cluster running cert-manager
as well as a TrueNAS server.
I'm putting it out there in case someone else finds it useful.

## Usage

The script is packaged in a container image.
See `example-manifest.yaml` for an example of how to deploy the script in Kubernetes. You will need to modify the manifest to include the necessary environment variables.

The script will install the CA and GUI certificates on the TrueNAS server via the API.
It will then regularly check whether the certificates have changed and update them if necessary.

If you would rather run it as a cronjob, it can be run with the `--oneshot` flag to perform a single run and then exit.

## Environment Variables

| Variable | Description |
| -------- | ----------- |
| TRUENAS_URL | _Required_ - The API URL of the TrueNAS server, for example: `wss://truenas.example.com/websocket` |
| TRUENAS_USERNAME | The username to use when authenticating with the TrueNAS server. I recommend a dedicated user with the minimum necessary permissions. |
| TRUENAS_PASSWORD | If `TRUENAS_USERNAME` is set, this is the password for that user. |
| TRUENAS_APIKEY | If you prefer to use an API key instead of a username/password, you can set it here. |
| TRUENAS_SYNC_CERT | _Required_ - The path to the certificate to be installed on the TrueNAS server. This will be set to be the web GUI certificate. Defaults to `/certs/tls.crt`. |
| TRUENAS_SYNC_KEY  | _Required_ - The path to the private key to be installed on the TrueNAS server. Defaults to `/certs/tls.key`. |
| TRUENAS_SYNC_CA | _Required_ - The path to the CA certificate to be installed on the TrueNAS server as a trusted root. This should be the root CA certificate of the issuer that signed the certificates you want to deploy. Defaults to `/certs/ca.crt`. |
| TRUENAS_SYNC_CA_NAME | The name which should be used for the CA certificate on the TrueNAS server. Defaults to the common name of the CA certificate. |
| TRUENAS_SYNC_CERT_NAME | The name which should be used for the certificate on the TrueNAS server. Defaults to the common name of the certificate. |

Licensed under the [MIT License](LICENSE.md).
