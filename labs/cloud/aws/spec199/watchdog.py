#!/usr/bin/env python3
"""Frozen, exact-instance cloud stop plan; never a claim of a monetary hard cap."""
from datetime import datetime, timezone
import json
import re
import campaign as c


def stop_actions(account, region, prefix, deadline, instance_action='instance', stage=1):
    c.need(bool(re.fullmatch(r'\d{12}', account)), 'account_required')
    c.need(bool(re.fullmatch(r'nc199-[a-f0-9]{12}', prefix)), 'owned_prefix_required')
    c.need(bool(re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d', region)), 'region_required')
    c.stamp(deadline)
    c.need(type(stage) is int and stage in c.MAX_SECONDS, 'stage_required')
    tags = [{'Key':k,'Value':v} for k,v in {'netclaw-spec':'199','netclaw-run':prefix,
                                           'netclaw-stage':str(stage)}.items()]
    group = prefix + '-stop'
    role = prefix + '-stop'
    source_arn = f'arn:aws:scheduler:{region}:{account}:schedule-group/{group}'
    trust = {'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'scheduler.amazonaws.com'},
        'Action':'sts:AssumeRole','Condition':{'StringEquals':{'aws:SourceAccount':account},
                                           'ArnEquals':{'aws:SourceArn':source_arn}}}]}
    instance = {'$ref': instance_action + '.Instances.0.InstanceId'}
    resource = {'$join':[f'arn:aws:ec2:{region}:{account}:instance/',instance]}
    policy = {'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':['ec2:StopInstances'],'Resource':[resource]}]}
    expression = 'at(' + datetime.fromtimestamp(c.stamp(deadline), timezone.utc).strftime('%Y-%m-%dT%H:%M:%S') + ')'
    return [
        {'name':'stop-group','service':'scheduler','operation':'create-schedule-group','region':region,
         'request':{'Name':group,'ClientToken':prefix+'-group','Tags':tags}},
        {'name':'stop-role','service':'iam','operation':'create-role','region':region,
         'request':{'RoleName':role,'AssumeRolePolicyDocument':json.dumps(trust,separators=(',',':')),
                    'Description':'Spec199 exact-instance deadline stop only','MaxSessionDuration':3600,'Tags':tags}},
        {'name':'stop-policy','service':'iam','operation':'put-role-policy','region':region,
         'request':{'RoleName':role,'PolicyName':'StopOwnedInstance','PolicyDocument':{'$json':policy}}},
        {'name':'stop-schedule','service':'scheduler','operation':'create-schedule','region':region,
         'request':{'Name':prefix+'-deadline','GroupName':group,'ClientToken':prefix+'-schedule',
            'ScheduleExpression':expression,'ScheduleExpressionTimezone':'UTC','FlexibleTimeWindow':{'Mode':'OFF'},
            'ActionAfterCompletion':'DELETE','State':'ENABLED',
            'Target':{'Arn':'arn:aws:scheduler:::aws-sdk:ec2:stopInstances',
                'RoleArn':{'$ref':'stop-role.Role.Arn'},
                'Input':{'$json':{'InstanceIds':[instance],'Force':False}},
                'RetryPolicy':{'MaximumEventAgeInSeconds':60,'MaximumRetryAttempts':2}}}},
    ]


def verify_schedule(observed, expected, now):
    for key in ('Name','GroupName','ScheduleExpression','ScheduleExpressionTimezone','FlexibleTimeWindow','ActionAfterCompletion','State'):
        c.need(observed.get(key) == expected.get(key), 'schedule_binding_mismatch')
    for key in ('Arn','RoleArn','Input','RetryPolicy'):
        c.need(observed.get('Target',{}).get(key) == expected['Target'][key], 'schedule_target_mismatch')
    # The input is exact single-instance scope; observations do not prove future delivery.
    body=json.loads(observed['Target']['Input'])
    c.need(len(body.get('InstanceIds',[])) == 1 and body.get('Force') is False, 'exact_instance_stop_required')
    c.need(re.fullmatch(r'i-[0-9a-f]{8,17}', body['InstanceIds'][0]), 'valid_instance_required')
    expression = observed['ScheduleExpression']
    c.need(expression.startswith('at(') and expression.endswith(')'), 'one_time_schedule_required')
    expiry = c.stamp(expression[3:-1] + '+00:00')
    c.need(expiry > now + 120, 'stop_deadline_too_close_or_expired')
    return {'configured':True,'future_delivery_proven':False,'observed_at':now}
