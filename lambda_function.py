# Original code from:
# https://serverlesscode.com/post/lambda-schedule-ebs-snapshot-backups/
# http://blog.powerupcloud.com/2016/02/15/automate-ebs-snapshots-using-lambda-function/
# Rewritten to be configured on individual Volumes, not Instances.
# https://github.com/Brayyy/Lambda-EBS-Snapshot-Manager

import boto3
import datetime
import time
import os

# Manually configure EC2 region, account IDs, timezone
ec = boto3.client('ec2', region_name='us-east-1')
aws_account_ids = ['123456789012']
default_days_of_renention = 7
os.environ['TZ'] = 'US/Eastern'

# Nothing to configure below this line


def create_new_backups():

    # Current hour
    current_hour = int(datetime.datetime.now().strftime('%H'))

    # Find volumes tagged with key "Backup"
    volumes = ec.describe_volumes(
        Filters=[
            {'Name': 'tag-key', 'Values': ['Backup']},
        ]
    ).get(
       'Volumes', []
    )

    print 'Number of volumes with backup tag: %d' % len(volumes)

    for volume in volumes:
        vol_id = volume['VolumeId']
        vol_retention = default_days_of_renention
        snap_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        snap_desc = vol_id

        # Loop over all tags and grab out relevant keys
        for name in volume['Tags']:
            tag_key = name['Key']
            tag_val = name['Value']
            # print '...Found EBS volume key %s : %s ' % ( tag_key, tag_val );

            # Below the code is create Snapshot name as instance Name
            if tag_key == 'Name':
                snap_desc = vol_id + ' (' + tag_val + ')'

            if tag_key == 'Retention' and tag_val.isdigit():
                vol_retention = int(tag_val)

            if tag_key == 'Backup':
                backup_mod = False
                if tag_val == '' or tag_val == 'false':
                    backup_mod = False
                elif tag_val == 'true':
                    backup_mod = 24
                elif tag_val == 'daily':
                    backup_mod = 24
                elif tag_val == '1/day':
                    backup_mod = 24
                elif tag_val == '2/day':
                    backup_mod = 12
                elif tag_val == '4/day':
                    backup_mod = 6
                elif tag_val == '6/day':
                    backup_mod = 4
                elif tag_val == '8/day':
                    backup_mod = 3
                elif tag_val == '12/day':
                    backup_mod = 2
                elif tag_val == '24/day':
                    backup_mod = 1
                elif tag_val == 'hourly':
                    backup_mod = 1
                else:
                    print '%s unknown backup schedule %s' % (vol_id, tag_val)
                    continue

        snap_name = 'Backup of ' + snap_desc
        snap_desc = 'Lambda backup ' + snap_date + ' of ' + snap_desc
        delete_ts = '%.0f' % ((vol_retention * 86400) + time.time())

        # Only backup if scheduled to do so
        if backup_mod is False or current_hour % backup_mod != 0:
            print '%s is not scheduled this hour' % vol_id
            continue
        else:
            print '%s is scheduled this hour' % vol_id

        # Create snapshot
        snap = ec.create_snapshot(
          VolumeId=vol_id,
          Description=snap_desc,
        )

        print 'snap %s' % snap

        ec.create_tags(
          Resources=[snap['SnapshotId']],
          Tags=[
            {'Key': 'Name', 'Value': snap_name},
            {'Key': 'DeleteAfter', 'Value': str(delete_ts)}
          ]
        )


def destroy_old_backups():
    filters = [
        {'Name': 'tag-key', 'Values': ['DeleteAfter']}
    ]
    snapshot_response = ec.describe_snapshots(
      OwnerIds=aws_account_ids,
      Filters=filters
    )
    # print snapshot_response

    for snap in snapshot_response['Snapshots']:
        # Loop over all tags and grab out relevant keys
        for name in snap['Tags']:
            tag_key = name['Key']
            tag_val = name['Value']
            # print '...Found EBS volume key %s : %s ' % ( tag_key, tag_val );

            if tag_key == 'DeleteAfter':
                if int(tag_val) < time.time():
                    print '%s is being deleted' % snap['SnapshotId']
                    ec.delete_snapshot(SnapshotId=snap['SnapshotId'])
                else:
                    print '%s is safe.' % snap['SnapshotId']


def lambda_handler(event, context):
    create_new_backups()
    destroy_old_backups()
    return 'successful'
