import boto3
import collections
import datetime

#Please mention your region name
#below line code is call cross region
ec = boto3.client('ec2', region_name='ap-southeast-1')

#begins lambda function
def lambda_handler(event, context):
    # mention your tag values below example "Backup-snap"
    reservations = ec.describe_instances(
        Filters=[
            {'Name': 'tag-key', 'Values': ['Backup', 'Yes']},
        ]
    ).get(
        'Reservations', []
    )

    instances = sum(
        [
            [i for i in r['Instances']]
            for r in reservations
        ], [])

    print "Number of the Instances : %d" % len(instances)

    to_tag = collections.defaultdict(list)

    for instance in instances:
        try:
            retention_days = [
                int(t.get('Value')) for t in instance['Tags']
                if t['Key'] == 'Retention'][0]
        except IndexError:
            # Please give your retention period day
            retention_days = 7

        for dev in instance['BlockDeviceMappings']:
            if dev.get('Ebs', None) is None:
                continue
            vol_id = dev['Ebs']['VolumeId']
            for name in instance['Tags']:
                # To store the instance tag value
                Instancename= name['Value']
                # To store the instance key value
                key= name['Key']
                # Below the code is create Snapshot name as instance Name 
                if key == 'Name' :
                    ins_name = Instancename
                    print "Found EBS volume %s on instance %s" % (
                    vol_id, instance['InstanceId'])
            
            #To get all the instance tags deatils
            for name in instance['Tags']:
                # To store the instance tag value
                Instancename= name['Value']
                # To store the instance key value
                key= name['Key']
                # Below the code is create Snapshot name as instance Name 
                if key == 'Name' :
                    snap = ec.create_snapshot(
                    VolumeId=vol_id,
                    Description=Instancename,
                    )
                    print "snap %s" %snap

            to_tag[retention_days].append(snap['SnapshotId'])

            print "Retaining snapshot %s of volume %s from instance %s for %d days" % (
                snap['SnapshotId'],
                vol_id,
                instance['InstanceId'],
                retention_days,
                
            )
            for retention_days in to_tag.keys():
                delete_date = datetime.date.today() + datetime.timedelta(days=retention_days)
                snap = snap['Description'] + str('_')
                # Here to get current date 
                snapshot = snap + str(datetime.date.today())   
                # to mention the current date formet
                delete_fmt = delete_date.strftime('%Y-%m-%d')
                print "Will delete %d snapshots on %s" % (len(to_tag[retention_days]), delete_fmt)
                # below code is create the name and current date as instance name
                ec.create_tags(
                Resources=to_tag[retention_days],
                Tags=[
                {'Key': 'DeleteOn', 'Value': delete_fmt},
                {'Key': 'Name', 'Value': snapshot },
                ]
                ) 
        to_tag.clear()
