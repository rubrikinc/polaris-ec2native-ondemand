#!/usr/bin/python
# USE - Uses the Rubrik Polaris API to take an on demand snapshot of the EC2 instance running this script
# expires oldest existing Polaris on demand snaps of this instance until # remaining <= snapcount

import requests
import json
import datetime
import getpass
import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('polaris_snap_script')
log.setLevel(logging.INFO)
requests.packages.urllib3.disable_warnings()
import os

#Auth parameters used to connect to Rubrik Polaris - consider retrieving these from a secrets manager instead - CONFIGURABLE
POLARIS_SUBDOMAIN = os.environ.get('POLARIS_SUBDOMAIN')
USERNAME = os.environ.get('POLARIS_USERNAME')
PASSWORD = os.environ.get('POLARIS_PASSWORD')
POLARIS_URL = 'https://{}.my.rubrik.com'.format(POLARIS_SUBDOMAIN)

#Number of snapshots to retain - CONFIGUREABLE
snapcount = 1

#Logging to console - CONFIGURABLE
logging = True

#Retrieve instance id of current AWS instance
instanceid = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document").json()['instanceId']

#Get access token
URI = POLARIS_URL + '/api/session'
HEADERS = {
    'Content-Type':'application/json',
    'Accept':'application/json'
    }
PAYLOAD = '{"username":"'+USERNAME+'","password":"'+PASSWORD+'"}'
RESPONSE = requests.post(URI, headers=HEADERS, verify=True, data=PAYLOAD)
if RESPONSE.status_code != 200:
        raise ValueError("Something went wrong with the request")
TOKEN = json.loads(RESPONSE.text)["access_token"]
TOKEN = "Bearer "+str(TOKEN)

#GraphQL endpoint and headers
URI = POLARIS_URL + '/api/graphql'
HEADERS = {
    'Content-Type':'application/json',
    'Accept':'application/json',
    'Authorization':TOKEN
    }

#Look up polaris UUID by EC2 instance ID
def get_ec2InstanceUUID(ec2InstanceId):
    if logging:
        log.info('geting Polaris UUID for instance: {}'.format(ec2InstanceId))
    GRAPH_VARS = '{{"sortBy":"EC2_INSTANCE_ID","sortOrder":"ASC","filters":[{{"field":"EC2_INSTANCE_NAME_OR_INSTANCE_ID","texts":["{}"]}},{{"field":"IS_ARCHIVED","texts":["0"]}}]}}'.format(ec2InstanceId)
    GRAPH_QUERY = '"query AWSInstancesList($first: Int, $after: String, $sortBy: HierarchySortByField, $sortOrder: HierarchySortOrder, $filters: [Filter!]) { ec2InstancesList: awsNativeEc2InstanceConnection(first: $first, after: $after, sortBy: $sortBy, sortOrder: $sortOrder, filter: $filters) { edges { node { id } } }}"'
    payload = '{{"operationName":"AWSInstancesList","variables":{},"query":{}}}'.format(GRAPH_VARS,GRAPH_QUERY)
    response = requests.post(URI, headers=HEADERS, verify=True, data=payload)
    if response.status_code != 200:
        raise ValueError("Something went wrong with the request")
    responsejson = json.loads(response.text)
    result = responsejson['data']['ec2InstancesList']['edges'][0]['node']['id']
    if logging:
        log.info('got UUID: {}'.format(result))
    return result

#Take a snapshot
def take_snapshot(ec2InstanceUUID):
    GRAPH_VARS = '{{"ec2InstanceIds":["{}"]}}'.format(ec2InstanceUUID)
    if logging:
        log.info('taking on demand snapshot of: {}'.format(ec2InstanceUUID))
    GRAPH_QUERY = '"mutation TakeAWSInstanceSnapshot($ec2InstanceIds: [UUID!]!) { createAwsNativeEc2InstanceSnapshots(ec2InstanceIds: $ec2InstanceIds) { taskchainUuids { ec2InstanceId taskchainUuid __typename } errors { error __typename } __typename }}"'
    payload = '{{"operationName":"TakeAWSInstanceSnapshot","variables":{},"query":{}}}'.format(GRAPH_VARS,GRAPH_QUERY)
    response = requests.post(URI, headers=HEADERS, verify=True, data=payload)
    if response.status_code != 200:
        raise ValueError("Something went wrong with the request")
    results = json.loads(response.text)
    if logging:
        log.info('API response for on demand snapshot: {}'.format(results))
    return results

#Get list of expired on demand snapshots for specific instance
def get_snapshot_list(ec2InstanceUUID, snapcount):
    if logging:
        log.info('looking for expired snapshots of  UUID: {}, max is {} snapshots'.format(ec2InstanceUUID, snapcount))
    GRAPH_VARS = '{{ "snappableFid": "{}", "isOnDemandSnapshot": true, "sortBy": "Date"}}'.format(ec2InstanceUUID)
    GRAPH_QUERY = '"query AWSInstanceSnapshotDetails($first: Int, $snappableFid: UUID!, $isOnDemandSnapshot: Boolean, $sortBy:PolarisSnapshotSortByEnum) { snappable: awsNativeEc2Instance(fid: $snappableFid) { id instanceId instanceName snapshotConnection(first: $first, filter: {isOnDemandSnapshot: $isOnDemandSnapshot}, sortBy:$sortBy) { nodes { id date isOnDemandSnapshot }} __typename }}"'
    payload = '{{"operationName":"AWSInstanceSnapshotDetails","variables":{},"query":{}}}'.format(GRAPH_VARS,GRAPH_QUERY)
    response = requests.post(URI, headers=HEADERS, verify=True, data=payload)
    if response.status_code != 200:
        raise ValueError("Something went wrong with the request")
    results = json.loads(response.text)['data']['snappable']['snapshotConnection']['nodes']
    if len(results) > snapcount:
        results = results[:-snapcount]
        if logging:
            log.info('got expired snapshots: {}'.format(results))
        return results
    else:
        return []

#delete all snapshots in list snapshots
def expire_on_demand_snapshots(snapshots):
    results = []
    if snapshots:
        if logging:
            log.info('expiring {} snapshots'.format(len(snapshots)))
        for snapshot in snapshots:
            if logging:
                log.info('expiring snapshot: {}'.format(snapshot['id']))
            GRAPH_VARS = '{{ "snapshotFid": "{}"}}'.format(snapshot['id'])    
            GRAPH_QUERY = '"mutation DeletePolarisSnapshot($snapshotFid: UUID!) { deletePolarisSnapshot(snapshotFid: $snapshotFid) }"'    
            payload = '{{"operationName":"DeletePolarisSnapshot","variables":{},"query":{}}}'.format(GRAPH_VARS,GRAPH_QUERY)    
            response = requests.post(URI, headers=HEADERS, verify=True, data=payload)
            if response.status_code != 200:
                raise ValueError("Something went wrong with the request")
            results.append(json.loads(response.text))
        if logging:
            log.info('snapshot expiration response codes: {}'.format(results))
        return results
    else:
        if logging:
            log.info('no snapshots to expire')
        return None

#Get the polaris UUID of our current instance
uuid = get_ec2InstanceUUID(instanceid)
if uuid:
    snapshot = take_snapshot(uuid)
    #if we have a UUID, check for on demand snapshots outside of the expiration window
    expired_snaps = get_snapshot_list(uuid,snapcount)
    #if we have expired snaps, delete them
    if expired_snaps:
        expire_on_demand_snapshots(expired_snaps)