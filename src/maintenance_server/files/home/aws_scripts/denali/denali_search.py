#! /usr/bin/env python

import os
import ast
import copy
import time
import fnmatch
import datetime

import denali
import denali_analytics
import denali_arguments
import denali_commands
import denali_history
import denali_location
import denali_types
import denali_utility
#import denali_sis

from denali_tty import colors


# columnData variable positions
cmdb_alias_name     = 0
cmdb_name_pos       = 1
column_name_pos     = 2
column_print_width  = 3


cmdb_defs = {
                'DeviceDao': [
                                # Base Device Information ("base") #
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['name',                        'name',                                     'Host Name',                                35],
                                ['model',                       'model.name',                               'Model Name',                               33],
                                ['model_category',              'model.model_category.full_name',           'Model Category',                           52],
                                ['asset_id',                    'asset_id',                                 'Asset ID',                                 10],
                                ['asset_tag',                   'asset_id',                                 'Asset Tag',                                10],
                                ['label',                       'label',                                    'Label',                                    20],
                                ['ownership',                   'ownership',                                'Ownership',                                11],
                                ['vendor_supplier',             'vendor_supplier.name',                     'Vendor Supplier',                          17],
                                ['vendor',                      'vendor_supplier.name',                     'Vendor Supplier',                          17],
                                ['vendor_supplier_id',          'vendor_supplier_id',                       'Vendor ID',                                11],
                                ['customer_id',                 'customer_id',                              'Customer ID',                              13],
                                ['device_group',                'device_group.name',                        'Device Group',                             50],
                                ['device_id',                   'device_id',                                'Device ID',                                11],
                                ['device_id_url',               'device_id',                                'Device ID URL',                            65],
                                ['device_service',              'device_service.full_name',                 'Device Service',                           55],
                                ['service',                     'device_service.full_name',                 'Device Service',                           55],
                                ['device_service_id',           'device_service.device_service_id',         'Device Service ID',                        19],
                                ['device_service_id_url',       'device_service.device_service_id',         'Device Service ID URL',                    80],
                                ['device_service_owner_id',     'device_service.owner.owner_type_id',       'Device Service Owner ID',                  25],
                                ['device_service_group_owners', 'device_service.owner.owner_type.name',     'Device Service Group Owners',              40],

                                # DeviceRoleDao field names (they mirror device service field names)
                                ['device_role',                 'device_role.full_name',                    'Device Role',                              55],
                                ['role',                        'device_role.full_name',                    'Device Role',                              55],
                                ['device_role_id',              'device_role.device_role_id',               'Device Role ID',                           19],
                                ['device_role_id_url',          'device_role.device_role_id',               'Device Role ID URL',                       80],
                                ['device_role_owner_id',        'device_role.owner.owner_type_id',          'Device Role Owner ID',                     25],
                                ['device_role_group_owners',    'device_role.owner.owner_type.name',        'Device Role Group Owners',                 40],

                                ['device_state',                'device_state.full_name',                   'Device State',                             35],
                                ['state',                       'device_state.full_name',                   'Device State',                             35],
                                ['device_state_notes',          'device_state_notes',                       'Device State Notes',                       20],
                                ['environment_id',              'device_environment_id',                    'Environment ID',                           16],
                                ['environment',                 'environment.full_name',                    'Environment Name',                         48],
                                ['env',                         'environment.full_name',                    'Environment Name',                         48],
                                ['environment_name',            'environment.name',                         'Environment',                              20],
                                ['env_name',                    'environment.name',                         'Environment',                              20],
                                ['notes',                       'notes',                                    'Device Notes',                             20],
                                ['po_number',                   'po_number',                                'PO Number',                                11],
                                ['order_id',                    'order_id',                                 'Order ID',                                 10],
                                ['sap_asset_number',            'sap_asset_number',                         'SAP Asset Number',                         18],
                                ['asset_cost',                  'asset_cost',                               'Asset Cost',                               12],
                                ['date_received',               'date_received',                            'Date Received',                            15],
                                ['actual_arrival_date',         'actual_arrival_date',                      'Actual Arrival Date',                      23],
                                ['install_date',                'install_date',                             'Install Date',                             15],
                                ['initial_kick_date',           'initial_kick_date',                        'Initial Kick Date',                        19],
                                ['last_imaged_date',            'last_imaged_date',                         'Last Imaged Date',                         18],
                                ['last_update_datetime',        'last_update_datetime',                     'Last Update Date/Time',                    23],
                                ['serial',                      'serial',                                   'Serial #',                                 27],
                                ['owner_subject',               'device_service.owner.owner_subject_id',    'Owner IDs',                                40],
                                ['owner_type',                  'device_service.owner.owner_subject_type',  'Owner Types',                              20],
                                # MRASEREQ-40973 - assigned_to
                                ['assigned_to',                 'assigned_to_user.full_name',               'Assigned To',                              30],
                                ['assigned_team',               'owner_team.full_name',                     'Assigned Team',                            23],

                                ['num_power_supplies',          'num_power_supplies',                       '# Power Supplies',                         18],
                                ['dc_power_supply_connection',  'device_power_connection.connected_to_device_power_connection.device.name', 'DC Power Supply Connections', 29],
                                ['dc_power_supply_connection_id', 'device_power_connection.connected_to_device_power_connection.device.device_id', 'DC Power Supply ID(s)', 23],
                                ['dc_power_supply_ports',       'device_power_connection.model_power_connection.name',         'Power Port',            12],
                                ['host_power_supply',           'device_power_connection.model_power_connection.name',         'Host Power Supply',     19],
                                ['power_supply_port',           'device_power_connection.model_power_connection.model_id',     'Power Supply Port',     19],

                                ['alert_state',                 'alert.last_alert_state',                   'Last Alert State',                         18],
                                ['alert_details',               'alert.last_alert_details',                 'Last Alert Details',                       50],
                                ['alert_time',                  'alert.last_alert_datetime',                'Last Alert Time',                          22],
                                ['alert_update',                'alert.updated_on',                         'Last Alert Update',                        22],
                                ['ticket_type',                 'alert.ticket_type',                        'Ticket Type',                              13],

                                # Device Components ("components") #
                                ['cpu',                         'cpu',                                      'CPU SPECs',                                51],
                                ['processor',                   'cpu',                                      'CPU SPECs',                                51],
                                ['cpu_cores',                   'cpu_cores',                                'CPU Cores',                                11],
                                ['disks',                       'disks',                                    'Disk Configuration',                       30],
                                ['memory',                      'memory',                                   'Memory',                                    8],
                                ['ram',                         'memory',                                   'Memory',                                    8],
                                ['num_attached_storage',        'num_attached_storage',                     '# Attached Storage',                       20],

                                # Device Location ("location") #
                                ['location',                    'location_id',                              'Site Location',                            15],
                                ['loc',                         'location_id',                              'Site Location',                            15],
                                ['location_id',                 'location_id',                              'Location ID',                              13],
                                ['location_notes',              'location_notes',                           'Location Notes',                           16],
                                ['location_status',             'location_status',                          'Location Status',                          23],
                                ['rack_facing',                 'rack_position',                            'Rack Facing',                              13],
                                ['rack_number',                 'rack_unit',                                'Rack #',                                    8],
                                ['cage_location',               'rack.cage.location.name',                  'Site Location',                            15],
                                ['cage',                        'rack.cage.name',                           'Cage Name',                                13],
                                ['cage_name',                   'rack.cage.name',                           'Cage Name',                                13],
                                ['rack',                        'rack.name',                                'Rack Name',                                16],
                                ['rack_name',                   'rack.name',                                'Rack Name',                                16],
                                ['rack_id',                     'rack_id',                                  'Rack ID',                                   9],
                                ['rack_id_url',                 'rack_id',                                  'Rack ID URL',                              65],
                                ['ru_size',                     'model.rack_units',                         'RU Size',                                   9],
                                ['chassis',                     'enclosure_device.name',                    'Chassis/Enclosure',                        20],
                                ['enclosure',                   'enclosure_device.name',                    'Enclosure',                                20],
                                ['enclosure_devices',           'enclosed_device.name',                     'Enclosure Devices',                        20],
                                ['enclosure_id',                'enclosure_device_id',                      'Enclosure ID',                             14],
                                ['enclosure_model',             'enclosure_device.model.name',              'Enclosure Model',                          33],
                                ['enclosure_slot',              'enclosure_slot',                           'Chassis Slot',                             14],
                                ['slot',                        'enclosure_slot',                           'Chassis Slot',                             14],

                                # Network Settings ("network") #
                                ['ip_address',                  'primary_ip_address.ip_address',            'IP Address (P)',                           16],
                                ['ip',                          'primary_ip_address.ip_address',            'IP Address (P)',                           16],
                                ['primary_ip_address',          'primary_ip_address.ip_address',            'IP Address (P)',                           16],
                                ['primary_ip',                  'primary_ip_address.ip_address',            'IP Address (P)',                           16],
                                ['secondary_ip_address',        'secondary_ip_address.ip_address',          'IP Address (S)',                           16],
                                ['secondary_ip',                'secondary_ip_address.ip_address',          'IP Address (S)',                           16],
                                ['mac',                         'mac_addr',                                 'MAC Address (P)',                          19],
                                ['mac_addr',                    'mac_addr',                                 'MAC Address (P)',                          19],
                                ['mac_cisco',                   'mac_addr',                                 'MAC Address (P)',                          19],
                                ['mac_dash',                    'mac_addr',                                 'MAC Address (P)',                          19],
                                ['mac_default',                 'mac_addr',                                 'MAC Address (P)',                          19],
                                ['secondary_mac',               'secondary_mac_addr',                       'MAC Address (S)',                          19],
                                ['secondary_mac_address',       'secondary_mac_addr',                       'MAC Address (S)',                          19],
                                ['secondary_mac_cisco',         'secondary_mac_addr',                       'MAC Address (S)',                          19],
                                ['secondary_mac_dash',          'secondary_mac_addr',                       'MAC Address (S)',                          19],
                                ['secondary_mac_default',       'secondary_mac_addr',                       'MAC Address (S)',                          19],
                                ['ilo_ip_address',              'ilo_ip_address.ip_address',                'iLO IP Address',                           16],
                                ['ilo',                         'ilo_ip_address.ip_address',                'iLO IP Address',                           16],
                                ['int_dns_name',                'int_dns_name',                             'Internal DNS Name',                        30],
                                ['ext_dns_name',                'ext_dns_name',                             'External DNS Name',                        30],
                                ['ad_domain',                   'ad_domain',                                'AD Domain',                                10],
                                ['device_interfaces',           'device_interface.name',                    'Server Int(s)',                            17],
                                ['switch_port_device',          'connected_to_device_interface.device.name','Switch Device Name',                       25],
                                ['switch_port_name',            'connected_to_device_interface.name',       'Switch Port',                              25],
                                ['switch_name',                 'device_interface.connected_to_device_interface.device.name', 'Switch Device Name',     25],
                                ['switch',                      'device_interface.connected_to_device_interface.device.name', 'Switch Device Name',     25],
                                ['default_gateway',             'primary_ip_address.ip_block.default_gateway','Default Gateway',                        17],
                                ['vlan',                        'primary_ip_address.ip_block.vlan.name',    'VLAN Name',                                25],
                                ['vlan_id',                     'primary_ip_address.ip_block.vlan.vlan_id', 'VLAN ID',                                  10],
                                ['vlan_number',                 'primary_ip_address.ip_block.vlan.vlan_number', 'VLAN #',                                8],
                                ['ip_block_id',                 'primary_ip_address.ip_block_id',           'IP Block ID',                              13],
                                ['ip_block_description',        'primary_ip_address.ip_block.description',  'IP Block Description',                     45],
                                ['ip_block_end_ip',             'primary_ip_address.ip_block.end_ip',       'IP Block End IP',                          17],
                                ['ip_block_prefix',             'primary_ip_address.ip_block.prefix',       'IP Block Prefix',                          17],
                                ['subnet',                      'primary_ip_address.ip_block.prefix',       'IP Address/Subnet',                        32],
                                ['cidr',                        'primary_ip_address.ip_block.prefix',       'IP Address/CIDR',                          19],
                                ['stovepipe_description',       'primary_ip_address.ip_block.stovepipe.description', 'Stovepipe Description',           23],
                                ['stovepipe_name',              'primary_ip_address.ip_block.stovepipe.name', 'Stovepipe Name',                         16],
                                ['stovepipe_id',                'primary_ip_address.ip_block.stovepipe.stovepipe_id', 'Stovepipe ID',                   14],
                                ['ip_utilization',              'primary_ip_address.ip_block.utilization',  'IP Util',                                   9],

                                # IP Address Allocation Dao (ip_address_allocation.<field>)
                                ['ip_id',                       'ip_address_allocation.ip_address_id',      'IP ID',                                    10],
                                ['ip_notes',                    'ip_address_allocation.notes',              'IP Notes',                                 30],
                                ['ip_subject',                  'ip_address_allocation.subject_id',         'IP Subject ID',                            15],
                                ['ip_type',                     'ip_address_allocation.subject_type',       'IP Subject Type',                          20],
                                ['ip_additional',               'ip_address_allocation.ip_address.ip_address',   'IP Address (A)',                      16],
                                #['ip_additional_bin',           'ip_address_allocation.ip_address.ip_address_binary',   'IP Address (b)',               30],

                                # Operating System Settings ("os") #
                                ['kernel',                      'kernel',                                   'Kernel',                                   30],
                                ['os_id',                       'operating_system_id',                      'OS ID',                                    10],
                                ['os_name',                     'operating_system.display_name',            'OS Name',                                  30],
                                ['operating_system',            'operating_system.display_name',            'OS Name',                                  30],

                                # Software ("software") #
                                ['software_version',            'software_version.version',                 'Software Version',                         47],
                                ['software_name',               'software_version.software.name',           'Software Name',                            20],
                                ['software_description',        'software_version.software.description',    'Software Description',                     25],
                                ['software_type',               'software_version.software.type',           'software_version.software.type',           15],

                                # Virtual Settings ("virtual") #
                                ['is_virtual_host',             'is_virtual_host',                          'Is Virtual Host',                          20],
                                ['virtual_group',               'virtual_group_name',                       'Virtual Group',                            20],
                                ['virtual_data_center',         'virtual_data_center_name',                 'Virtual Data Center',                      21],
                                ['virtual_instance_id',         'virtual_instance_id',                      'Virtual Instance ID',                      21],
                                ['virtual_cluster_group',       'virtual_cluster_device_group.name',        'Virtual Cluster Group',                    30],
                                ['virtual_cluster_group_url',   'virtual_cluster_device_group.device_group_id', 'Virtual Cluster Group URL',            80],
                                ['virtual_guest_toggle',        'virtual_guest_toggle',                     'Virtual Guest Assignment',                 31],

                                # Attribute Column Settings #
                                ['attribute_name',              'attribute_data.attribute.name',                 'Attribute Name',                      40],
                                ['attribute_value',             'attribute_data.value',                          'Attribute Value',                     52],
                                ['attribute_inheritance',       'attribute_data.inherited_from_attribute.value', 'Attribute Inheritance',               60],
                                ['attribute_inherited_id',      'attribute_data.inherited_attribute_data_id',    'Inherited?',                          12],
                                ['attribute_overrides_id',      'attribute_data.overrides_attribute_data_id',    'Overrides?',                          12],

                                # Source of record data
                                ['sor',                         'source_of_record.name',                    'DB Source',                                11],
                                ['source_name',                 'source_of_record.name',                    'DB Source',                                11],
                                ['source_description',          'source_of_record.description',             'DB Source Description',                    50],
                                ['source_id',                   'source_of_record.source_of_record_id',     'DB Source ID',                             14],

                                # Master/Slave relationship
                                ['master_slave',                'device_relationship.relationship_type_label.value', 'Master / Slave',                  16],
                                ['related_device',              'device_relationship.related_device.name',  'Related Device',                           20],

                                # JIRA ticket data
                                ['jira_ticket',                 'jira_issue.jira_key',                      'JIRA Ticket',                              17],
                                ['jira_url',                    'jira_issue.jira_key',                      'JIRA Ticket URL',                          55],
                                ['jira_status',                 'jira_issue.status',                        'JIRA Status',                              20],
                                ['jira_subject',                'jira_issue.subject',                       'JIRA Subject',                             40],
                                ['jira_devices',                'jira_issue.device_names',                  'JIRA Device Names',                        25],
                                ['jira_assignee',               'jira_issue.assignee_user.full_name',       'JIRA Assigned To',                         30],
                                ['jira_creator',                'jira_issue.reporter_user.full_name',       'JIRA Created By',                          30],
                                ['jira_created_on',             'jira_issue.created_on',                    'JIRA Created On',                          22],
                                ['jira_updated_on',             'jira_issue.updated_on',                    'JIRA Updated On',                          22],
                             ],

                'DeviceServiceDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['active',                      'active',                                   'Active?',                                   9],
                                ['alerts',                      'alerts',                                   'Alerts?',                                   9],
                                ['description',                 'description',                              'Description',                              30],
                                ['inherit_env',                 'inherit_environments',                     'Inherit Env?',                             14],
                                ['inherit_os',                  'inherit_operating_systems',                'Inherit OS?',                              13],
                                ['monitored',                   'monitored',                                'Monitored?',                               12],
                                ['node_type',                   'node_type',                                'Node Type',                                11],
                                ['group',                       'requires_device_group',                    'Group Req\'d?',                            14],
                                ['name',                        'full_name',                                'Device Service (full)',                    70],
                                ['short_name',                  'name',                                     'Device Service',                           25],
                                ['device_service_id',           'device_service_id',                        'Service ID',                               15],
                                ['owner_type',                  'owner.owner_type.name',                    'Owner Type',                               25],
                                ['owner_id',                    'owner.owner_subject_id',                   'Owner ID',                                 35],
                                ['owner_subject_type',          'owner.owner_subject_type',                 'Owner Subject Type',                       20],
                                ['device_name',                 'device.name',                              'Host Name',                                20],
                                ['owner_user',                  'owner_user.full_name',                     'Owner - User(s)',                          40],
                                ['owner_team',                  'owner_team.full_name',                     'Owner - Team(s)',                          21],
                                ['attribute_name',              'attribute_data.attribute.name',            'Attribute Name',                           40],
                                ['attribute_value',             'attribute_data.value',                     'Attribute Value',                          52],

                             ],

                'DeviceRoleDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['active',                      'active',                                   'Active?',                                   9],
                                ['alerts',                      'alerts',                                   'Alerts?',                                   9],
                                ['description',                 'description',                              'Description',                              30],
                                ['inherit_env',                 'inherit_environments',                     'Inherit Env?',                             14],
                                ['inherit_os',                  'inherit_operating_systems',                'Inherit OS?',                              13],
                                ['monitored',                   'monitored',                                'Monitored?',                               12],
                                ['node_type',                   'node_type',                                'Node Type',                                11],
                                ['group',                       'requires_device_group',                    'Group Req\'d?',                            14],
                                ['name',                        'full_name',                                'Device Role (full)',                       70],
                                ['short_name',                  'name',                                     'Device Role',                              25],
                                ['device_role_id',              'device_role_id',                           'Role ID',                                  15],
                                ['owner_type',                  'owner.owner_type.name',                    'Owner Type',                               25],
                                ['owner_id',                    'owner.owner_subject_id',                   'Owner ID',                                 35],
                                ['owner_subject_type',          'owner.owner_subject_type',                 'Owner Subject Type',                       20],
                                ['device_name',                 'device.name',                              'Host Name',                                20],
                                ['owner_user',                  'owner_user.full_name',                     'Owner - User(s)',                          40],
                                ['owner_team',                  'owner_team.full_name',                     'Owner - Team(s)',                          21],
                                ['attribute_name',              'attribute_data.attribute.name',            'Attribute Name',                           40],
                                ['attribute_value',             'attribute_data.value',                     'Attribute Value',                          52],

                             ],

                'DeviceStateDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['name',                        'full_name',                                'Device State Name',                        35],
                             ],

                'LocationDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['location_id',                 'location_id',                              'Location ID',                              15],
                                ['name',                        'name',                                     'Name',                                     10],
                             ],

                'TeamDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['active',                      'active',                                   'Active',                                    8],
                                ['description',                 'description',                              'Team Description',                         35],
                                ['members',                     'member_user.full_name',                    'Team Members',                             60],
                                ['team_id',                     'team_id',                                  'Team ID',                                   9],
                             ],

                'UserDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['full_name',                   'full_name',                                'User Name',                                30],
                                ['team_name',                   'member_of_team.full_name',                 'Team Name',                                30],
                                ['user_id',                     'user_id',                                  'User ID',                                   9],
                                ['email',                       'email',                                    'Email Address',                            25],
                                ['desk',                        'desk',                                     'Office',                                   12],
                                ['phone',                       'phone',                                    'Office Phone',                             20],
                                ['phone_ext',                   'phone_ext',                                'Extension',                                11],
                                ['mobile',                      'mobile',                                   'Mobile Phone',                             18],
                                ['alt_phone',                   'alternate_phone',                          'Alt. Phone',                               22],
                                ['alt_phone_2',                 'alternate_phone_2',                        'Alt. Phone 2',                             22],
                                ['position',                    'position_level',                           'Position Level',                           25],
                                ['time_zone',                   'time_zone',                                'Time Zone',                                17],
                                ['title',                       'title',                                    'Job Title',                                40],
                             ],

                'OwnerDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['owner_subject_id',            'owner_subject_id',                         'Owner ID',                                 20],
                                ['owner_subject_type',          'owner_subject_type',                       'Subject Type',                             14],
                                ['owner_type.name',             'owner_type.name',                          'Owner Type',                               12],
                             ],

                'OnCallDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['user_id',                     'user_id',                                  'User ID',                                   9],
                                ['user',                        'user.full_name',                           'User Name',                                30],
                                ['on_call_queue_id',            'on_call_queue_id',                         'Queue ID',                                 18],
                                ['queue_name',                  'on_call_queue.name',                       'Queue Name',                               20],
                                ['on_call_id',                  'on_call_id',                               'On Call ID',                               12],
                                ['start_datetime',              'start_datetime',                           'Start Date/Time',                          21],
                                ['end_datetime',                'end_datetime',                             'End Date/Time',                            21],
                                ['on_call_queue.full_name',     'on_call_queue.full_name',                  'Queue Full Name',                          20],
                             ],

                'OnCallQueueDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['queue_name',                  'full_name',                                'Queue Name (long)',                        20],
                                ['description',                 'description',                              'Queue Description',                        50],
                                ['active',                      'active',                                   'Active?',                                   9],
                                ['alternate_escalation',        'alternate_escalation',                     'Alternate Escalation',                     22],
                                ['alt_escalation_other',        'alternate_escalation_other',               'Alt. Escalation Info',                     30],
                                ['alt_queue_id',                'alternate_escalation_queue_id',            'Alt. Queue ID',                            15],
                                ['alt_user_id',                 'alternate_escalation_user_id',             'Alt. User ID',                             14],
                                ['enable_rotation',             'enable_rotation',                          'Enable Rotation',                          17],
                                ['name',                        'name',                                     'Queue Name',                               30],
                                ['queue_id',                    'on_call_queue_id',                         'Queue ID',                                 10],
                                ['parent_queue_id',             'parent_on_call_queue_id',                  'Par. Queue ID',                            15],
                                ['queue_type',                  'queue_type',                               'Queue Type',                               16],
                                ['start_time',                  'start_time',                               'Start Time',                               12],
                                ['time_zone',                   'time_zone',                                'Time Zone',                                11],
                             ],

                'OnCallQueueToUserDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['user_id',                     'user_id',                                  'User ID',                                   9],
                                ['queue_id',                    'on_call_queue_id',                         'Queue ID',                                 10],
                                ['user_name',                   'user.full_name',                           'User Name',                                30],
                             ],

                'AttributeDataDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['attribute_data_id',           'attribute_data_id',                        'Attribute Data ID',                        19],
                                ['attribute_id',                'attribute_id',                             'Attribute ID',                             14],
                                ['inherited_id',                'inherited_attribute_data_id',              'Inherited ID',                             14],
                                ['subject_id',                  'subject_id',                               'Subject ID',                               12],
                                ['subject_type',                'subject_type',                             'Subject Type',                             14],
                                ['value',                       'value',                                    'Attribute Value',                          52],
                                # switch to the Attribute dao
                                ['description',                 'attribute.description',                    'Description',                              30],
                                ['name',                        'attribute.name',                           'Attribute Name',                           40],
                             ],

                'SecretStoreDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['name',                        'name',                                     'SS Name',                                  20],
                                ['secret_store_id',             'secret_store_id',                          'SS ID',                                     7],
                                ['ss_id',                       'secret_store_id',                          'SS ID',                                     7],
                                ['description',                 'description',                              'SS Description',                           45],
                                ['owner_user',                  'owner_user.full_name',                     'User Owners',                              30],
                                ['user_owner',                  'owner_user.full_name',                     'User Owners',                              30],
                                ['owner_group',                 'owner_group.full_name',                    'Group Owners',                             20],
                                ['group_owner',                 'owner_group.full_name',                    'Group Owners',                             20],
                                ['secrets',                     'secret.name',                              'Secret Names',                             50],
                             ],

                'OrderDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['closed_on',                   'closed_on',                                'Closed On Date',                           21],
                                ['contract_end_date',           'contract_end_date',                        'Contract End Date',                        21],
                                ['currrency',                   'currency',                                 'Currency',                                 15],
                                ['description',                 'description',                              'Description',                              90],
                                ['draft_created_on',            'draft_created_on',                         'Draft Created On Date',                    23],
                                ['estimated_cost',              'estimated_total_cost',                     'Estimated Cost',                           16],
                                ['jira',                        'jira_ticket',                              'JIRA Ticket',                              20],
                                ['last_update',                 'last_update',                              'Last Update Date',                         21],
                                ['location',                    'location_id',                              'Location',                                 20],
                                ['location_id',                 'location_id',                              'Location ID',                              20],
                                ['manufacturer',                'manufacturer',                             'Manufacturer',                             30],
                                ['needed_by',                   'needed_by',                                'Needed By Date',                           16],
                                ['order_id',                    'order_id',                                 'Order ID',                                 10],
                                ['owner_user_id',               'owner_user_id',                            'Owner User ID',                            15],
                                ['project_id',                  'project_id',                               'Project ID',                               30],
                                ['project_title',               'project_title',                            'Project Title',                            30],
                                ['requestor_user',              'requestor_user.full_name',                 'Requestor User',                           30],
                                ['requestor_user_id',           'requestor_user_id',                        'Requestor User ID',                        20],
                                ['rt_instructions',             'rt_instructions',                          'RT Instructions',                          40],
                                ['special_instructions',        'special_instructions',                     'Special Instructions',                     40],
                                ['status',                      'status',                                   'Status',                                   45],
                                ['submitted_by_user_id',        'submitted_by_user_id',                     'Submitted User ID',                        20],
                                ['submitted_on',                'submitted_on',                             'Submitted On Date',                        21],
                                ['summary',                     'summary',                                  'Order Summary',                            60],
                                ['technical_user_id',           'technical_contact_user_id',                'Technical User ID',                        20],
                             ],

                'HistoryDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['device_id',                   'subject_id',                               'Device Name',                              20],
                                ['datetime',                    'history_datetime',                         'Date/Time',                                21],
                                ['details',                     'details',                                  'Details',                                  70],
                                ['old_value',                   'old_value',                                'Prior Value',                              40],
                                ['new_value',                   'new_value',                                'Current Value',                            40],
                                ['action',                      'action_label.value',                       'Action Performed',                         45],
                                ['field_label',                 'field_label',                              'Field Name',                               20],
                                ['field_name',                  'field_name',                               'CMDB Field Name',                          20],
                                ['user_id',                     'user_id',                                  'User ID',                                   9],
                                ['username',                    'user.full_name',                           'User Name',                                30],
                             ],

                'SkmsArchiveHistoryDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['device_id',                   'subject_id',                               'Device Name',                              20],
                                ['datetime',                    'history_datetime',                         'Date/Time',                                21],
                                ['details',                     'details',                                  'Details',                                  70],
                                ['old_value',                   'old_value',                                'Prior Value',                              40],
                                ['new_value',                   'new_value',                                'Current Value',                            40],
                                ['action',                      'action_label.value',                       'Action Performed',                         45],
                                ['field_label',                 'field_label',                              'Field Name',                               20],
                                ['field_name',                  'field_name',                               'CMDB Field Name',                          20],
                                ['user_id',                     'user_id',                                  'User ID',                                   9],
                                ['username',                    'user.full_name',                           'User Name',                                30],
                             ],


                'JiraIssueDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['status',                      'status',                                   'Issue Status',                             20],
                                ['subject',                     'subject',                                  'Subject',                                  40],
                                ['created_on',                  'created_on',                               'Created On',                               21],
                                ['updated_on',                  'updated_on',                               'Updated On',                               21],
                             ],

                'DeviceGroupDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['name',                        'name',                                     'Device Group Name',                        30],
                                ['group_type',                  'device_group_type',                        'Device Group Type',                        20],
                                ['device',                      'device.name',                              'Devices Assigned To The Group',            40],
                                ['device_state',                'device.device_state.full_name',            'Device State',                             35],
                                ['device_service',              'device.device_service.full_name',          'Device Service',                           50],
                                ['attribute_name',              'attribute_data.attribute.name',            'Attribute Name',                           40],
                                ['attribute_value',             'attribute_data.value',                     'Attribute Value',                          52],
                                ['location',                    'location_id',                              'Location ID',                              13],
                                ['location_id',                 'location_id',                              'Location ID',                              13],
                             ],

                'LdapGroupDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['name',                        'name',                                     'LDAP Group Name',                          35],
                                ['sudo_rule',                   'sudo_rule.name',                           'SUDO Rule Name',                           40],
                                ['access_role',                 'access_role.name',                         'Access Role Name',                         40],
                             ],

                'LbProfileDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['name',                        'lb_device.name',                           'LB Name',                                  25],
                                ['profile_name',                'name',                                     'Profile Name',                             50],
                                ['updated_on',                  'updated_on',                               'Last Update',                              21],
                                ['location',                    'location_id',                              'Location',                                 12],
                                ['location_id',                 'location_id',                              'Location',                                 12],
                                ['profile_id',                  'lb_profile_id',                            'Profile ID',                               12],
                                ['device_id',                   'lb_device_id',                             'Device ID',                                11],
                                ['device_id_url',               'lb_device_id',                             'Device ID URL',                            65],
                                ['active',                      'active',                                   'Active',                                    8],
                                ['vip_name',                    'lb_virtual_ip.name',                       'VIP Name',                                 47],
                                ['vip_port',                    'lb_virtual_ip.port',                       'VIP Port',                                 20],
                                ['vip_status',                  'lb_virtual_ip.active',                     'VIP Status',                               12],
                                ['vip_ip_address',              'lb_virtual_ip.ip_address.ip_address',      'VIP IP Address',                           40],
                                ['fpssl',                       'lb_virtual_ip.ip_address.fpssl',           'FPSSL?',                                    8],
                             ],

                'LbVirtualIpDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['vip_name',                    'name',                                     'VIP Name',                                 30],
                                ['vip_port',                    'port',                                     'VIP Port',                                 20],
                                ['vip_status',                  'active',                                   'VIP Status',                               12],
                                ['vip_ip_address',              'ip_address.ip_address',                    'VIP IP Address',                           40],
                                ['fpssl',                       'ip_address.fpssl',                         'FPSSL?',                                    8],
                                ['location',                    'location_id',                              'Location',                                 12],
                                ['location_id',                 'location_id',                              'Location',                                 12],
                                ['pool_name',                   'lb_pool.name',                             'Pool Name',                                35],
                                ['pool_status',                 'lb_pool.active',                           'Pool Status',                              13],
                                ['name',                        'lb_device.name',                           'LB Name',                                  25],
                                ['updated_on',                  'updated_on',                               'Last Update',                              21],
                             ],

                'LbPoolDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['pool_status',                 'active',                                   'Pool Status',                              13],
                                ['device_id',                   'lb_device_id',                             'Device ID',                                11],
                                ['device_id_url',               'lb_device_id',                             'Device ID',                                65],
                                ['pool_id',                     'lb_pool_id',                               'Pool ID',                                   9],
                                ['location',                    'location_id',                              'Location',                                 12],
                                ['location_id',                 'location_id',                              'Location',                                 12],
                                ['pool_name',                   'name',                                     'Pool Name',                                35],
                                ['name',                        'name',                                     'Pool Name',                                35],
                                ['updated_on',                  'updated_on',                               'Last Update',                              21],
                                ['members',                     'lb_pool_member',                           'Pool Members',                             30],
                             ],

                'ServiceDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['name',                        'name',                                     'Service Name',                             45],
                                ['full_name',                   'full_name',                                'Service Full Name',                       120],
                                ['marketing_name',              'marketing_name',                           'Marketing Name',                           25],
                                ['description',                 'description',                              'Service Description',                      25],
                                ['service_id',                  'service_id',                               'Service ID',                               12],
                                ['service_type_id',             'service_type_id',                          'Service Type ID',                          17],
                             ],

                'EnvironmentDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['active',                      'active',                                   'Active?',                                  11],
                                ['date',                        'active_datetime',                          'Active Date',                              21],
                                ['alerts',                      'alerts',                                   'Alerts?',                                   9],
                                ['description',                 'description',                              'Description',                              30],
                                ['id',                          'environment_id',                           'ID',                                       10],
                                ['full_name',                   'full_name',                                'Environment Full Name',                    50],
                                ['inactive_date',               'inactive_datetime',                        'Inactive Date',                            21],
                                ['marketing_name',              'marketing_name',                           'Marketing Name',                           30],
                                ['monitored',                   'monitored',                                'Monitored?',                               12],
                                ['name',                        'name',                                     'Environment Name',                         30],
                                ['node_type',                   'node_type',                                'Node Type',                                11],
                                ['service_id',                  'service_id',                               'Service ID',                               12],
                                ['attribute_name',              'attribute_data.attribute.name',            'Attribute Name',                           40],
                                ['attribute_value',             'attribute_data.value',                     'Attribute Value',                          52],
                             ],

                'CmrDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['id',                          'cmr_id',                                   'CMR ID',                                    8],
                                ['id_url',                      'cmr_id',                                   'CMR ID/URL',                               55],
                                ['backout',                     'back_out_plan',                            'Backout Plan',                             50],
                                ['change_type',                 'change_type.name',                         'Change Type',                              30],
                                ['closed',                      'closed_datetime',                          'CRM Closed Datetime',                      21],
                                ['cmr_service',                 'cmr_to_service.service.full_name',         'Device Service',                           30],
                                ['cmr_type',                    'type',                                     'CMR Type',                                 10],
                                ['cmr_state',                   'cmr_state_id',                             'CMR State ID',                             15],
                                ['completion_notes',            'completion_notes',                         'Completion Notes',                         40],
                                ['completion_reason',           'completion_reason',                        'Completion Reason',                        50],
                                ['completion_status',           'completion_status',                        'Completion Status',                        24],
                                ['completion_user',             'completion_user_id.full_name',             'Completion User',                          30],
                                ['created_by_user',             'created_by_user.full_name',                'Created By User',                          30],
                                ['creation_time',               'creation_datetime',                        'Creation Time',                            21],
                                ['cso',                         'cso_id',                                   'CSO ID',                                   20],
                                ['deadline',                    'approval_deadline',                        'Approval Deadline',                        21],
                                ['implementation',              'implementation_plan',                      'Implementation Plan',                      60],
                                ['incident',                    'cso_id',                                   'CSO ID',                                   20],
                                ['executor',                    'change_executor_user.full_name',           'Change Executor',                          30],
                                ['function',                    'function.name',                            'Function Name',                            30],
                                ['justification',               'business_justification',                   'Business Justification',                   60],
                                ['priority',                    'priority',                                 'Priority',                                 10],
                                ['rejection_reason',            'rejection_reason',                         'Rejection Reason',                         30],
                                ['status',                      'cmr_state.status',                         'CRM Status',                               21],
                                ['summary',                     'summary',                                  'Summary',                                  60],
                                ['testing',                     'testing_validation',                       'Testing Description',                      40],
                                ['ticket',                      'ticket_number',                            'Ticket Number',                            15],
                                ['ticket_type',                 'ticket_type',                              'Ticket Type',                              25],
                                ['start_date',                  'maintenance_window.start_date',            'Start Date',                               21],
                                ['end_date',                    'maintenance_window.end_date',              'End Date',                                 21],
                                ['duration',                    'maintenance_window.end_date',              'Duration',                                 13],
                                ['risk',                        'cmr_to_service.risk_label.value',          'Risk',                                      8],
                                ['impact',                      'cmr_to_service.impact_label.value',        'Impact',                                   10],
                                ['type',                        'maintenance_type',                         'Maintenance Type',                         20],
                             ],

                'FpsslImplementationDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['ssl_hostname',                'ssl_hostname',                             'SSL Hostname',                             40],
                                ['ip_address.ip_address',       'ip_address.ip_address',                    'IP Address(es)',                           17],
                                ['fpssl_id',                    'fpssl_implementation_id',                  'FPSSL ID',                                 10],
                                ['f5',                          'ip_address.lb_device.name',                'F5 LB Name(s)',                            25],
                                ['avi',                         'ip_address.lb_device_group.name',          'AVI LB Name(s)',                           20],
                             ],

                'DnsAdvertisementMapDao':
                             [
                                # ALIAS                         # CMDB Name                                 # Print Header Title               # Print Width
                                ['name',                        'name',                                     'Map Name',                                30],
                                ['mapid',                       'dns_advertisement_map_id',                 'Map ID',                                   8],
                                ['description',                 'description',                              'Description',                             30],
                                ['sor_id',                      'source_of_record_id',                      'SOR ID',                                   8],
                                ['key_id',                      'source_of_record_key_id',                  'SOR Key ID',                              12],
                                ['site',                        'dns_advertisement_map_record.advertised_in_site', 'Advertising Site',                 30],
                                ['record',                      'dns_advertisement_map_record.record_site', 'Destination Site Advertised',             30],
                             ]
}


cidr_data = {
                '30':'255.255.255.252',
                '29':'255.255.255.248',
                '28':'255.255.255.240',
                '27':'255.255.255.224',
                '26':'255.255.255.192',
                '25':'255.255.255.128',
                '24':'255.255.255.0',
                '23':'255.255.254.0',
                '22':'255.255.252.0',
                '21':'255.255.248.0',
                '20':'255.255.240.0',
                '19':'255.255.224.0',
                '18':'255.255.192.0',
                '17':'255.255.128.0',
                '16':'255.255.0.0',
                '15':'255.254.0.0',
                '14':'255.252.0.0',
                '13':'255.248.0.0',
                '12':'255.240.0.0',
                '11':'255.224.0.0',
                '10':'255.192.0.0',
                '9' :'255.128.0.0',
                '8' :'255.0.0.0',
                '7' :'254.0.0.0',
                '6' :'252.0.0.0',
                '5' :'248.0.0.0',
                '4' :'240.0.0.0',
                '3' :'224.0.0.0',
                '2' :'192.0.0.0',
                '1' :'128.0.0.0',
                '0' :'0.0.0.0'
            }



##############################################################################
#
# textScreenOutput(denaliVariables)
#

def textScreenOutput(denaliVariables):
    for target in denaliVariables["outputTarget"]:
        if target.type in ["txt_screen", "txt_file"]:
            return True

    return False



##############################################################################
#
# obtainBasicDeviceInformation(denaliVariables, device, device_id?)
#

def obtainBasicDeviceInformation(denaliVariables, device, deviceType):

    PID = os.getpid()
    current_time = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    fileName  = '/tmp/denali-tmp-%s-%s.newline' % (PID, current_time)
    denaliVariables["tmpFilesCreated"].append(fileName)
    scriptLoc = denaliVariables["denaliLocation"]

    authenticationParm = denali_arguments.returnLoginCLIParameter(denaliVariables)

    if authenticationParm == False:
        # punt?  How did we get this far then?  Manual authentication?
        return False
    else:

        try:
            os.remove(fileName)
        except:
            pass

        authenticationParm = authenticationParm[0] + '=' + authenticationParm[1]

        if deviceType == False:     # device name submitted
            denali_call="%s %s --sql=\"DeviceDao:SELECT model,device_id,cage_location,rack_name WHERE name = '%s'\" -o %s --noheaders" % (scriptLoc, authenticationParm, device, fileName)
        else:                       # device_id submitted
            denali_call="%s %s --sql=\"DeviceDao:SELECT model,name,cage_location,rack_name WHERE device_id = '%s'\" -o %s --noheaders" % (scriptLoc, authenticationParm, device, fileName)

        os.system(denali_call)

        try:
            data = open(fileName, 'r')
        except:
            return

        model     = data.readline().strip()
        deviceSQL = data.readline().strip()
        location  = data.readline().strip()
        rack      = data.readline().strip()
        data.close()

        try:
            os.remove(fileName)
        except:
            pass

        if deviceType == False:
            print "  Model            :  %s" % model
            print "  Data Center      :  %s" % location
            print "  Rack Name        :  %s" % rack
            print "CMDB Site          :  %s" % deviceSQL
        else:
            print "Device Name        :  %s" % deviceSQL
            print "  Model            :  %s" % model
            print "  Data Center      :  %s" % location
            print "  Rack Name        :  %s" % rack
            print "CMDB Site          :  https://skms.adobe.com/cmdb.device/view/?device_id=%s" % device



##############################################################################
#
# searchPowerIDInformation(denaliVariables, powerID)
#

def searchPowerIDInformation(denaliVariables, powerID):

    denaliVariables["addColumn"] = True
    powerFields = denaliVariables["userAliases"]

    if "_POWER" in powerFields:
        POWER_FIELDS = powerFields['_POWER']
    else:
        POWER_FIELDS = "host_power_supply,device_power_connection.connected_to_device_power_connection.device.name,power_supply_port,device_state,device_service"

    powerList = compileIDRange(powerID.split(','))

    for pID in powerList:

        if textScreenOutput(denaliVariables) == True and denaliVariables["showHeaders"] == True:
            print
            print "Power Device ID    :  %s" % pID

            rCode = obtainBasicDeviceInformation(denaliVariables, pID, True)
            if rCode == False:
                pass

        sqlQuery = "DeviceDao:SELECT name,%s WHERE name IN (DeviceDao:SELECT device_power_connection.connected_to_device_power_connection.device.name WHERE device_id = '%s' ORDER BY name)" % (POWER_FIELDS, pID)

        select = "device_power_connection.connected_to_device_power_connection.device.name,device_power_connection.model_power_connection.name"
        where  = "device_id"

        denaliVariables["addColumnData"] = denali_utility.getDenaliResponse(denaliVariables, select, where, pID, False)

        if constructSQLQuery(denaliVariables, sqlQuery, True) == False:
            # if the query is false, print that result and move to the next one
            print
            print "The query for power device (%s) did not complete successfully." % pID
            print

        if denaliVariables["showsql"] == True:
            denali_utility.showSQLQuery(sqlQuery, denaliVariables)

    return True



##############################################################################
#
# searchPowerNameInformation(denaliVariables, powerName)
#

def searchPowerNameInformation(denaliVariables, powerName):

    denaliVariables["addColumn"] = True
    powerFields = denaliVariables["userAliases"]

    if "_POWER" in powerFields:
        POWER_FIELDS = powerFields['_POWER']
    else:
        POWER_FIELDS = "host_power_supply,device_power_connection.connected_to_device_power_connection.device.name,power_supply_port,device_state,device_service"

    powerList = powerName.split(',')

    for pName in powerList:

        if textScreenOutput(denaliVariables) and denaliVariables["showHeaders"] == True:
            print
            print "Power Device Name  :  %s" % pName

            rCode = obtainBasicDeviceInformation(denaliVariables, pName, False)
            if rCode == False:
                pass

        sqlQuery = "DeviceDao:SELECT name,%s WHERE name IN (DeviceDao:SELECT device_power_connection.connected_to_device_power_connection.device.name WHERE name = '%s')" % (POWER_FIELDS, pName)

        select = "device_power_connection.connected_to_device_power_connection.device.name,device_power_connection.model_power_connection.name"
        where  = "name"

        denaliVariables["addColumnData"] = denali_utility.getDenaliResponse(denaliVariables, select, where, pName, False)

        if constructSQLQuery(denaliVariables, sqlQuery, True) == False:
            # if the query is false, print that result and move to the next one
            print
            print "The query for power device (%s) did not complete successfully." % pName
            print

        if denaliVariables["showsql"] == True:
            denali_utility.showSQLQuery(sqlQuery, denaliVariables)

    return True


##############################################################################
#
# compileIDRange(rackArgument)
#

def compileIDRange(idList):

    finalIDRange  = []
    standAloneIDs = []
    rangeIDs      = []

    # multiple ranges supplied?
    for device_id in idList:
        if device_id.count('..') == 0:
            # we have a single, stand-alone device_id (not paired/ranged)
            standAloneIDs.append(device_id)
        else:
            rangeIDs.append(device_id)


    # add the stand-alone server(s) to the list
    if len(standAloneIDs) > 0:
        for device_id in standAloneIDs:
            # search for 'sets' of data
            if '[' in device_id and ']' in device_id:
                # found a 'set' query in the device_id name
                start = device_id.find('[')
                end   = device_id.find(']')
                if (end - start) > 11:
                    print "Perhaps a different method is needed to query"
                    print "for device IDd with a %d character set." % (end - start)
                    print "The code allows for 10 characters or less in"
                    print "a single set."
                    print
                    continue
                else:
                    if start == 0:
                        beginning = ''
                    else:
                        beginning = device_id[:start]

                    middle_chars = device_id[(start + 1):end]
                    ending       = device_id[(end + 1):]

                    for (count, char) in enumerate(middle_chars):
                        new_device_id = beginning + char + ending
                        finalIDRange.append(new_device_id)
            else:
                finalIDRange.append(device_id)

    # process through the serverPaired list
    for device_id in rangeIDs:
        # search for wildcards -- they aren't supported in ranges
        if '*' in device_id or '?' in device_id or '_' in device_id:
            print
            print "Device ID syntax submitted: %s" % device_id
            print
            print "Wildcard characters (*,?, etc.), are not supported in a range request."
            print "Please re-enter the range without wildcard characters."
            print
            return False

        countDots = device_id.count('..')

        if countDots > 0:
            deviceIDList = device_id.split('..')
            device_id1 = deviceIDList[0]
            device_id2 = deviceIDList[1]

            rValue = generateIDRange(device_id1, device_id2)
            if rValue != False:
                #print "rValue = %s" % rValue
                finalIDRange.extend(rValue)

    return finalIDRange



##############################################################################
#
# generateIDRange(device_id1, device_id2)
#

def generateIDRange(device_id1, device_id2):

    idRange = []

    start = int(device_id1)
    stop  = int(device_id2) + 1    # add 1 to the 'stop' because a range doesn't include the stop number.

    if int(device_id1) > int(device_id2):
        step = -1
    elif int(device_id2) > int(device_id1):
        step = 1
    else:
        step = 1

    # build the id range
    for number in range(start, stop, step):
        idRange.append(str(number))

    return idRange



##############################################################################
#
# searchRackInformation(denaliVariables, rackArgument)
#

def searchRackIDInformation(denaliVariables, rackArgument):

    rackFields = denaliVariables["userAliases"]

    if "_RACK" in rackFields:
        RACK_FIELDS = rackFields['_RACK']
    else:
        RACK_FIELDS = "rack_number,name,ru_size,rack_facing,device_state,device_service,environment"

    rackList = compileIDRange(rackArgument.split(','))

    if rackList != False:
        for rackID in rackList:

            if textScreenOutput(denaliVariables) and denaliVariables["showHeaders"] == True:
                print
                print "Rack ID   :  %s" % rackID
                print "CMDB Site :  https://skms.adobe.com/cmdb.rack/view/?rack_id=%s" % rackID

            sqlQuery = "DeviceDao:SELECT %s WHERE rack_id='%s' ORDER BY rack_unit DESC,name" % (RACK_FIELDS, rackID)

            if constructSQLQuery(denaliVariables, sqlQuery, True) == False:
                # if the query is false, print that result and move to the next one
                print
                print "The query for rack ID %s did not complete successfully."
                print

            if denaliVariables["showsql"] == True:
                denali_utility.showSQLQuery(sqlQuery, denaliVariables)

    else:
        print "Rack list/range has incorrect syntax (%s)" % rackArgument
        return False

    return True



##############################################################################
#
# searchRackNameInformation(denaliVariables, rackArgument)
#

def searchRackNameInformation(denaliVariables, rackArgument):

    rackFields = denaliVariables["userAliases"]

    if "_RACK" in rackFields:
        RACK_FIELDS = rackFields['_RACK']
    else:
        RACK_FIELDS = "rack_number,name,ru_size,rack_facing,device_state,device_service,environment"

    rackList = rackArgument.split(',')

    for rackName in rackList:
        # separate the data center from the rack name
        dataCenterLocation = rackName.find(':')
        dataCenter = rackName[:dataCenterLocation]
        rack = rackName[(dataCenterLocation + 1):]

        if textScreenOutput(denaliVariables) == True and denaliVariables["showHeaders"] == True:
            print
            print "Rack Name   :  %s" % rack

        sqlQuery = "DeviceDao:SELECT %s WHERE rack.cage.location.name='%s' AND rack.name='%s' ORDER BY rack_unit DESC,name" % (RACK_FIELDS, dataCenter, rack)

        if constructSQLQuery(denaliVariables, sqlQuery, True) == False:
            print
            print "The query for rack name %s:%s did not complete successfully."
            print

        if denaliVariables["showsql"] == True:
            denali_utility.showSQLQuery(sqlQuery, denaliVariables)

    return True



##############################################################################
#
# searchSwitchInformation(denaliVariables, switchArgument)
#

def searchSwitchNameInformation(denaliVariables, switchArgument):

#
#  fields=name,device_interface.name,
#         device_interface.connected_to_device_interface.name,
#         device_interface.connected_to_device_interface.device_id,
#         device_interface.connected_to_device_interface.device.name
#

    switchFields = denaliVariables["userAliases"]

    if "_SWITCH" in switchFields:
        SWITCH_FIELDS = switchFields['_SWITCH']
    else:
        SWITCH_FIELDS = "name,switch_port_name,connected_to_device_interface.device.name,vlan_number,vlan,device_state,device_service"

    switchList = switchArgument.split(',')

    for switch in switchList:

        if textScreenOutput(denaliVariables) == True and denaliVariables["showHeaders"] == True:
            print
            print "Switch Device Name :  %s" % switch

            obtainBasicDeviceInformation(denaliVariables, switch, False)

        sqlQuery = "DeviceDao:SELECT %s WHERE name IN (DeviceDao:SELECT connected_to_device_interface.device.name WHERE name = '%s') ORDER BY connected_to_device_interface.name" % (SWITCH_FIELDS, switch)

        if constructSQLQuery(denaliVariables,sqlQuery, True) == False:
            print
            print "SQL query for switch (%s) failed to execute properly." % switch
            print "Please check the name and try again."
            print

        if denaliVariables["showsql"] == True:
            denali_utility.showSQLQuery(sqlQuery, denaliVariables)

    return True



##############################################################################
#
# searchSwitchIDInformation(denaliVariables, switchArgument)
#

def searchSwitchIDInformation(denaliVariables, switchArgument):

    switchFields = denaliVariables["userAliases"]

    if "_SWITCH" in switchFields:
        SWITCH_FIELDS = switchFields['_SWITCH']
    else:
        SWITCH_FIELDS = "name,switch_port_name,connected_to_device_interface.device.name,vlan_number,vlan,device_state,device_service"

    switchList = compileIDRange(switchArgument.split(','))

    for switch in switchList:

        if textScreenOutput(denaliVariables) == True and denaliVariables["showHeaders"] == True:
            print
            print "Switch Device ID   :  %s" % switch

            obtainBasicDeviceInformation(denaliVariables, switch, True)

        sqlQuery = "DeviceDao:SELECT %s WHERE name IN (DeviceDao:SELECT connected_to_device_interface.device.name WHERE device_id = '%s') ORDER BY connected_to_device_interface.name" % (SWITCH_FIELDS, switch)

        if constructSQLQuery(denaliVariables,sqlQuery, True) == False:
            print
            print "SQL query for switch (%s) failed to execute properly." % switch
            print "Please check the name and try again."
            print

        if denaliVariables["showsql"] == True:
            denali_utility.showSQLQuery(sqlQuery, denaliVariables)

    return True



##############################################################################
#
# printColumnHeaders(displayColumns)
#

def printColumnHeaders(displayColumns):

    column_name_pos    = 2          # the column that stores the Name to print (not the CMDB name)
    column_print_width = 3          # the column that stores the print width

    print "|",
    for column in displayColumns:
        print "%s" % str(column[column_name_pos]).ljust(column[column_print_width] - 1) + '|',

    headerLine = '|'

    for column in displayColumns:
        headerLine += "%s" % ('=' * (column[column_print_width]) + '|')

    print
    print headerLine



##############################################################################
#
# replaceAliasedNames(denaliVariables, fieldToUse)
#

def replaceAliasedNames(denaliVariables, fieldToUse):

    cmdb_name_pos = 1
    dao           = denaliVariables['searchCategory']

    # Catch this ... just in case an actual field name is passed in
    try:
        fields = denaliVariables[fieldToUse]
    except KeyError:
        fields = fieldToUse

    modFields = ''

    #print "dao    = %s" % dao
    #print "fields = %s" % fields

    # if the fields variable is empty, return 'False'
    if fields == '':
        return ''

    # place the fields in question in a List for processing
    if ',' in fields:
        # multiple items in the field variable
        selectedColumns = fields.split(',')
    else:
        # single item in the field variable
        selectedColumns = [fields]

    if dao in cmdb_defs:
        for column in selectedColumns:
            if ':' in column:
                # Hand sort column direction data (column:sort direction)
                location   = column.find(':')   # find the colon
                columnName = column[:location]  # separate the column name,
                sortData   = column[location:]  # from the sort direction data
            else:
                location   = 0                  # with no colon, fill out the
                columnName = column             # data here to avoid problems
                sortData   = ''                 # with the code below

            #print "column name = %s" % columnName

            for listObject in cmdb_defs[dao]:
                #print "listobj = %s" % listObject
                if columnName in listObject:
                    if location == 0:
                        modFields += (listObject[cmdb_name_pos] + ',')
                    else:
                        modFields += (listObject[cmdb_name_pos] + sortData + ',')
                        location = 0
                    break
            else:
                # didn't find it -- assume the submitted name is correct
                modFields += (str(column) + ',')
    else:
        # submitted dao not found, just add all of the fields "as is"
        for field in selectedColumns:
            modFields += (field + ',')

    #print "modFields = %s" % modFields

    # strip off the ending comma, if it exists
    if modFields[-1:] == ',':
        return modFields[:-1]
    else:
        return modFields



##############################################################################
#
# returnAllAliasedNames(denaliVariables, field_classifier, single=False)
#
#   This function searches a specific dao for all alias and cmdb reference
#   names for a specific field and returns that in a List.
#
#   Example:  DeviceDao, service
#       This will return the following List:
#       ['service', 'device_service', 'device_service.full_name']
#
#   The first two are aliases for the 3rd one.  All are returned because they
#   identify the same column from the database to display.
#
#   single=False
#       This flag allows a call to be made to this function to swap a single
#       aliased name in CMDB for the full CMDB-ified database name.
#

def returnAllAliasedNames(denaliVariables, field_classifier, single=False):

    alias_set_one = set()
    alias_set_two = set()

    for column in cmdb_defs[denaliVariables['searchCategory']]:
        if field_classifier == column[0]:
            alias_set_one.update(column[0])
            alias_set_one.update(column[1])
            if single == True:
                return column[1]

        if field_classifier == column[1]:
            alias_set_one.update(column[0])
            alias_set_one.update(column[1])
            if single == True:
                return column[1]

    for column in cmdb_defs[denaliVariables['searchCategory']]:
        for alias in alias_set_one:
            if alias in column:
                alias_set_two.update(column[0])
                alias_set_two.update(column[1])

    full_set = alias_set_one.union(alias_set_two)

    return list(full_set)



##############################################################################
#
# determineColumnOrder(denaliVariables)
#

def determineColumnOrder(denaliVariables, limitAddition=True):

    if denaliVariables["debug"] == True:
        print "\n++Entered determineColumnOrder\n"

    # Make sure a limitData specified column is added to the field list if it
    # is not alredy a part of the field list.  Check all aliased names to make
    # sure and not miss it.
    # MRASEREQ-41219
    if 'definition' in denaliVariables['limitData'] and limitAddition == True:
        field_classifier = denaliVariables['limitData']['definition']
        field_classifier = field_classifier.split(':')[1]
        fields_to_print  = denaliVariables['fields'].split(',')

        # find the alias(es) as well
        field_list = returnAllAliasedNames(denaliVariables, field_classifier)

        if len(field_list):
            for check_field in field_list:
                if check_field in fields_to_print:
                    break
            else:
                denaliVariables['fields'] += ',' +  field_classifier

    dao            = denaliVariables["searchCategory"]
    selectFields   = denaliVariables["fields"]
    methodFields   = denaliVariables["methodData"]
    methodData     = ''
    modFields      = ''
    displayColumns = []

    if denaliVariables["debug"] == True:
        print "mod fields    (b) = %s" % selectFields
        print "method fields (b) = %s" % methodFields

    if denaliVariables["method"] == "count":
        # if "count" is selected, then kill any fields entered
        # and generate them manually from the "--count" switch
        colonLoc = methodFields.find(':')
        selectFields = methodFields[(colonLoc + 1):]
        denaliVariables["fields"] = selectFields
    elif denaliVariables["method"] == "getAttributes":
        denaliVariables["methodData"] = ''
        methodFields = ''

    # get the columns ready for checking aliased names
    selectColumns  = selectFields.split(',')

    # Function in a function specifically for including default values
    def includeDefaultValues(field_value):
        default_field_length = 20

        length = len(field_value)
        if length >= default_field_length:
            default_field_length = (length + 2)

        # If the name is being updated -- make it wider,  Instead of the default 20 characters,
        # grab the Host Name default length and add 10 characters to it.
        if dao == 'DeviceDao' and field_value.strip() == "name" and default_field_length == 20:
            default_field_length = cmdb_defs['DeviceDao'][0][-1] + 10

        return ([field_value, field_value, field_value, default_field_length])

    if dao in cmdb_defs:
        for field in selectColumns:
            for (index, listObject) in enumerate(cmdb_defs[dao]):
                if field == listObject[cmdb_alias_name]:
                    if denaliVariables['aliasHeaders'] == True:
                        column_data = list(cmdb_defs[dao][index])
                        column_data[2] = column_data[0]
                    else:
                        column_data = cmdb_defs[dao][index]
                    #displayColumns.append(cmdb_defs[dao][index])
                    displayColumns.append(column_data)
                    modFields += (listObject[cmdb_name_pos] + ',')
                    break
            else:
                # the field didn't match an alias name -- see if it matches a CMDB name
                for (index, listObject) in enumerate(cmdb_defs[dao]):
                    if field in listObject:
                        if denaliVariables['aliasHeaders'] == True:
                            column_data = list(cmdb_defs[dao][index])
                            column_data[2] = column_data[0]
                        else:
                            column_data = cmdb_defs[dao][index]
                        #displayColumns.append(cmdb_defs[dao][index])
                        displayColumns.append(column_data)
                        modFields += (listObject[cmdb_name_pos] + ',')
                        break
                else:
                    # not found anywhere -- make it a default value
                    displayColumns.append(includeDefaultValues(field))
                    modFields += (field + ',')

    else:
        # dao not defined in cmdb_defs -- assume the fields were
        # typed in correctly (and can be found in CMDB); therefore,
        # give of the submitted fields a default set of options so
        # they can be searched for and displayed/output if wanted.
        for field in selectColumns:
            displayColumns.append(includeDefaultValues(field))
            modFields += (field + ',')

    # arrange the method data for adjustment (method type == "count" for instance)
    if methodFields != '':
        if ':' in methodFields:
            colon = True
            methodFields = methodFields.replace(':', ',')
        else:
            colon = False

        methodFields = methodFields.split(',')

        if dao in cmdb_defs:
            for (count, field) in enumerate(methodFields):
                for (index, listObject) in enumerate(cmdb_defs[dao]):
                    if field in listObject:
                        if (count == 0):
                            colData = cmdb_defs[dao][index]
                            #colWidth = colData[3]
                            if colData[2].find("(count)") == -1:
                                colData[2] += " (count)"
                            if (len(colData[2]) + 2) > colData[3]:
                                colData[3] = len(colData[2]) + 2
                            if denaliVariables['aliasHeaders'] == True:
                                colData[2] = colData[0]
                            displayColumns.append(colData)
                        methodData += (listObject[cmdb_name_pos] + ',')
                        break
                else:
                    # didn't find it
                    methodData += (field + ',')
        else:
            # dao not defined
            for field in methodFields:
                methodData += (field + ',')

        if colon == True:
            methodData = methodData.replace(',', ':', 1)

        denaliVariables["methodData"] = methodData[:-1]

    if denaliVariables["debug"] == True:
        print "mod fields    (a) = %s" % modFields[:-1]
        print "method fields (a) = %s" % methodData[:-1]
        print "disp columns  (a) = %s" % displayColumns
        print

    return (modFields[:-1], displayColumns)



##############################################################################
#
# specialColumnHandling(denaliVariables, data, columnAlias)
#

def specialColumnHandling(denaliVariables, data, columnAlias):

    # catch the obvious problems -- if there's no data, just return
    if len(data) == 0:
        return data

    # Insert a set of colons (:) for the MAC Address
    if (columnAlias == "mac" or columnAlias == "secondary_mac_address") and len(data) > 10:
        data = data[:2] + ':' + data[2:4] + ':' + data[4:6] + ':' + \
        data[6:8] + ':' + data[8:10] + ':' + data[10:]
        return data

    # MAC address Cisco format
    if (columnAlias == "mac_cisco" or columnAlias == "secondary_mac_cisco") and len(data) > 10:
        data = data[:4] + '.' + data[4:8] + '.' + data[8:]
        return data

    # MAC address dash format
    if (columnAlias == "mac_dash" or columnAlias == "secondary_mac_dash") and len(data) > 10:
        data = data[:2] + '-' + data[2:4] + '-' + data[4:6] + '-' + \
        data[6:8] + '-' + data[8:10] + '-' + data[10:]
        return data

    # Modify the rack position output to be user friendly
    if columnAlias == "rack_facing":
        if data == "0":
            return ""
        if data == "1":
            return "Front"
        elif data == "2":
            return "Back"

    # Descript blade servers in a rack setting
    if columnAlias == "rack_unit":
        if data == "0":
            # we have a blade unit or power unit
            data = "---"

    # replace the device id with a URL to the CMDB entry
    if columnAlias == "device_id_url":
        if data != '':
            data = "https://skms.adobe.com/cmdb.device/view/?device_id=%s" % data

    # replace the device service id with a URL to the CMDB entry
    if columnAlias == "device_service_id_url":
        # only print the URL if there is associated data
        if data != '':
            data = "https://skms.adobe.com/cmdb.device_service/view/?device_service_id=%s" % data

    # replace the device role id with a URL to the CMDB entry
    if columnAlias == "device_role_id_url":
        # only print the URL if there is associated data
        if data != '':
            data = "https://skms.adobe.com/cmdb.device_role/view/?device_role_id=%s" % data

    if columnAlias == "rack_id_url":
        if data != '':
            if str(data) == "0":
                data = "Not available"
            else:
                data = "https://skms.adobe.com/cmdb.rack/view/?rack_id=%s" % data

    if columnAlias == "virtual_cluster_group_url":
        if data != '':
            data = "https://skms.adobe.com/cmdb.device_group/view/?device_group_id=%s" % data

    # oncallqueuedao
    # alternate escalation
    if columnAlias == "alternate_escalation":
        if data == "1":  return "None"
        if data == "2":  return "Last Person On-Call"
        if data == "3":  return "Next Person On-Call"
        if data == "4":  return "Alternate Queue"
        if data == "5":  return "Alternate User"
        if data == "6":  return "Other"

    if columnAlias == "enable_rotation":
        if data == "0":  return "Not Enabled"
        if data == "1":  return "Enabled"

    if columnAlias == "queue_type":
        if data == "1":  return "Standard"
        if data == "2":  return "Follow The Sun"

    if columnAlias == "phone_ext":
        if len(data) > 0:
            return ('x' + data)

    if columnAlias == "location_status":
        if data == "1":   return "In Rack (Mounted)"
        if data == "2":   return "In Rack (Not Mounted)"
        if data == "3":   return "In Enclosure"
        if data == "4":   return "In Cage"
        if data == "5":   return "In Location"
        if data == "6":   return "In Transit"
        if data == "7":   return "Out For Repair"
        if data == "8":   return "On Virtual Host"
        if data == "9":   return "In Public Cloud"
        if data == "10":  return "In Virtual Cluster"
        if data == "100": return "Other"

    if columnAlias == "is_virtual_host":
        if data == "0":  return "Virtual Host - No"
        if data == "1":  return "Virtual Host - Yes"

    if columnAlias == "virtual_guest_toggle":
        if data == "0":  return "Not a Virtual Guest"
        if data == "1":  return "Virtual Guest (host assigned)"
        if data == "2":  return "Virtual Guest (in cluster)"

    if columnAlias == "location":
        # the number of locations can change and at that point denali will be
        # behind.  to avoid IndexErrors, just print "unknown" for now until
        # the location list (at the top of this file) can be updated.
        if data != '':
            try:
                return denali_location.dc_location[int(data)]
            except IndexError:
                return "Unknown"

    if columnAlias == "location_id":
        if data != '':
            try:
                return data + " (" + denali_location.dc_location[int(data)] + ")"
            except:
                print "data = %s" % data

    if columnAlias == "fpssl":
        if data != '':
            if data == "0":  return "No"
            if data == "1":  return "Yes"

    if columnAlias == "group_type":
        if data != '':
            if data == "1":  return "Static"
            if data == "2":  return "Dynamic"
            if data == "3":  return "SAN Array"
            if data == "4":  return "NAS Cluster"
            if data == "5":  return "Virtual Cluster"
            if data == "6":  return "Service Cluster"

    if columnAlias == "jira_url":
        if data != '':
            if data.find(',') != -1:
                jira_tickets = data.split(',')
                data = ''
                for ticket in jira_tickets:
                    if len(data) == 0:
                        data = "https://jira.corp.adobe.com/browse/%s" % ticket
                    else:
                        data += " https://jira.corp.adobe.com/browse/%s" % ticket
            else:
                data = "https://jira.corp.adobe.com/browse/%s" % data

    # if the ip_block_prefix is asked for, print the subnet mask instead of
    # the CIDR notation
    if columnAlias == "subnet":
        # there are times when the address/subnet isn't filled out
        if data.find('/') == -1:
            return data
        ip_block = data.split('/')
        return ip_block[0] + '/' + cidr_data[ip_block[1]]

    if columnAlias == "ip_utilization":
        return (str(round(float(data) * 100,1)) + '%')

    if denaliVariables["searchCategory"] == "OrderDao":
        if columnAlias == "status":
            if data == "50":  return "Step 1: Pending PR (50)"
            if data == "60":  return "Step 2: Pending PR Approval (60)"
            if data == "70":  return "Step 3: Pending Vendor Confirmation (70)"
            if data == "90":  return "Step 4: Pending Shipment Info (90)"
            if data == "120": return "Step 5: Pending Delivery (120)"
            if data == "130": return "Step 5: Pending Item Completion (130)"
            if data == "140": return "Step 6: Pending Confirmation (140)"
            if data == "150": return "Complete (150)"
            if data == "160": return "Canceled (160)"

    if (denaliVariables['searchCategory'] == 'EnvironmentDao' or
       denaliVariables['searchCategory'] == 'DeviceServiceDao' or
       denaliVariables['searchCategory'] == 'DeviceRoleDao'):
        if columnAlias == 'active':
            if data == '0' : return 'Inactive'
            if data == '1' : return 'Active'

        if columnAlias == 'alerts':
            if data == '0' : return 'No'
            if data == '1' : return 'Yes'

        if columnAlias == 'monitored':
            if data == '0' : return 'No'
            if data == '1' : return 'Yes'

        if columnAlias == 'node_type':
            if data == '0' : return 'Child'
            if data == '1' : return 'Parent'

    if denaliVariables['searchCategory'] == 'CmrDao':
        if columnAlias == "id_url":
            return "https://skms.adobe.com/sst.cm.cmr/view/?cmr_id=%s" % data

        if columnAlias == "start_date":
            denaliVariables['cmrData'][0] = data

        if columnAlias == "end_date":
            denaliVariables['cmrData'][1] = data

        if columnAlias == "duration":
            start_time = denaliVariables['cmrData'][0]
            if start_time == '':
                return 'Unknown ST'
            end_time   = denaliVariables['cmrData'][1]
            if end_time == '':
                end_time = data
            return denali_utility.getDeltaTimeDifference(start_time, end_time)

        if columnAlias == 'completion_status':
            if data == '0':  return "CMR Not Started"
            if data == '1':  return "Completed Successfully"
            if data == '2':  return "Completed Unexpected"
            if data == '3':  return "Canceled No Resources"
            if data == '4':  return "Canceled Not Needed"
            if data == '5':  return "Canceled Back Out Plan"
            if data == '6':  return "Completed To Plan"
            if data == '7':  return "Completed Not To Plan"

        if columnAlias == 'type':
            if data == '1':  return "Maintenance Window"
            if data == '2':  return "Internal Change"

        if columnAlias == 'window_announced':
            if data == '1':  return "Yes"
            if data == '2':  return "No"

        if columnAlias == 'priority':
            if data == '1':  return "Normal"
            if data == '2':  return "Urgent"

        # 2 = pending, 3 = on-going, 4 = rejected, 5 = completed, 6 = canceled
        if columnAlias == 'cmr_state':
            if data == '2':  return "(2) Pending"
            if data == '3':  return "(3) On-Going"
            if data == '4':  return "(4) Rejected"
            if data == '5':  return "(5) Completed"
            if data == '6':  return "(6) Canceled"

        if columnAlias == 'ticket_type':
            if data == '1':  return "RT (Deprecated)"
            if data == '2':  return "Bugzilla (Deprecated)"
            if data == '3':  return "RightNow"
            if data == '4':  return "JIRA (TechOps)"
            if data == '5':  return "Access Management"
            if data == '6':  return "JIRA (Engineering)"

        if columnAlias == 'cmr_type':
            if data == '1':  return "Request"
            if data == '2':  return "Model"
            if data == '3':  return "CSO"

    return data



##############################################################################
#
# gatherSearchedData(responseDictionary, denaliVariables)
#

def gatherSearchedData(queryDictionary, denaliVariables):

    cmdb_name_pos = 1
    columnData    = denaliVariables["columnData"]
    printData     = ''


    if denaliVariables["debug"] == True:
        print "response dictionary = %s" % queryDictionary
        print "print column widths = %s" % columnData


    # Step #1:  Build the rows of data (to print) into a List
    for serverData in queryDictionary['data']['results']:
        # create an empty List with "None" in all positions
        tempList = list(None for index in columnData)

        for attribute in serverData:
            for (cIndex, column) in enumerate(columnData):
                if attribute == column[cmdb_name_pos]:
                    # found the attribute position, put it in the List to
                    # print later
                    tempList[cIndex] = serverData[attribute]
                    break
        else:
            # create a List of Lists containing the server data gathered
            for (count, data) in enumerate(tempList):

                # I prefer to see an empty column, rather than 'None' for any
                # non-existant data
                if data == None:
                    data = ''

                # remove all unicode "trappings" from the response
                data = unicode(data).replace("{u'", "")
                data = unicode(data).replace("'}", "")
                data = unicode(data).replace("[u'", "")
                data = unicode(data).replace("', u'", ",")
                data = unicode(data).replace("']", "")
                data = unicode(data).replace("[]", "")
                data = unicode(data).replace(": u'", ": '")

                tempList[count] = unicode(data)

            # after adjusting the column widths (above 'for' loop), add the completed
            # data to the data element that will be output (to screen/file)
            printData += "'" + str(tempList) + "','"
            printData = printData.replace(",", "','")
            printData = printData.replace("[u","")
            printData = printData.replace("]", "")
            while printData.find("''") != -1:
                printData = printData.replace("''", "'")


    if denaliVariables["debug"] == True:
        print "printData = %s" % printData[:-2]
        print "printData = %s" % str(printData)[:-2]

    return printData[:-2]



##############################################################################
#
# generateColumnDataOverflow(data, neededData)
#

def generateColumnDataOverflow(data, neededData):
    # Width of "gutter" between columns in characters.
    GUTTER = 2

    overflowData = {}
    columnData   = []

    columnWidth         = neededData["columnWidth"]
    columnEnd           = neededData["columnEnd"]
    columnNumber        = neededData["columnNumber"]
    columnDifference    = neededData["columnDifference"]

    column_meta = (['columnNumber',     columnNumber,
                    'columnWidth',      columnWidth,
                    'columnEnd',        columnEnd,
                    'columnDifference', columnDifference])

    textWidth = columnWidth - GUTTER

    columnData = splitLine(data, textWidth)

    # Apply padding to each string in the split text.
    format_str = '{{0: <{0}}}'.format(textWidth)
    columnData = [format_str.format(d.encode('ascii', 'ignore')) for d in columnData]

    overflowData[columnNumber] = [column_meta] + columnData
    return overflowData


##############################################################################
#
# splitLine(line, width, chars, secondary):
#
def splitLine(line, width, chars=('/', ',', ' '), secondary=('.', '-', '_')):
    """ Splits a line to fit a specific width, preferentially splitting
        on one set of characters and then a fallback set.
    """
    width = max(1, width)  # Ensure that we can't have a nonsensical width.

    if len(line) <= width:
        return [line,]

    # Find the ideal split. Split on a char in chars first, then on secondary.
    split = max([line.rfind(c, 0, width) for c in chars])
    if split == -1:
        split = max([line.rfind(c, 0, width) for c in secondary])

    # Only split on the separator if we can include it in the desired width.
    # Otherwise let it fall through to 'ugly' split. (i.e. don't start a line
    # with the split char.)
    if split > 0:
        split += 1  # Include the separator on the line.
        if split < width:
            return [line[:split]] + splitLine(line[split:], width, chars, secondary)

    # No natural split char found, make an ugly split!
    return [line[:width]] + splitLine(line[width:], width, chars, secondary)


##############################################################################
#
# zeroPadNumbers(inputString)
#

def zeroPadNumbers(inputString):

    spaces      = inputString.count(' ')
    inputString = inputString.strip()
    inputList   = inputString.split(',')

    # I've seen up to 3 itmes for a port definition:
    #   Example: 100/1/3
    # The code should handle this type of data (unknown number of '/')

    count = 0

    fixedString = ''
    for data in inputList:
        if '/' in data:

            splitData = data.split('/')

            for (index, item) in enumerate(splitData):
                if len(item) == 1:
                    item = '0' + item
                    splitData[index] = item
                    count += 1

            for item in splitData:
                if fixedString == '':
                    fixedString = item
                else:
                    fixedString += '/' + item

            fixedString = fixedString.replace(',/', ',')

        elif len(data) == 1:
            fixedString = '0' + data
            count += 1
        else:
            fixedString = data

        fixedString += ','

    spaces = spaces - count

    if fixedString[-1] == ',':
        fixedString = fixedString[:-1] + (' ' * spaces)
    else:
        fixedString = fixedString + (' ' * spaces)


    return fixedString



##############################################################################
#
# handleUnsortedColumns(columnData, readyData, denaliVariables, sort_column)
#

def handleUnsortedColumns(columnData, readyData, denaliVariables, sort_column):

    #
    # This is a special purpose function that operates when the --switch/id,
    # and --power/id switches are given to denali.
    #
    # The data is gathered in different queries and must be sorted specifically
    # after it is combined in columns.  That's what this function does.  It takes
    # the already gathered (pre-sorted) data and resorts it by the power port or
    # switch port (by default).  It also honors all of the original (no)wrapping
    # parameters entered.
    #

    printData = []

    #cmdb_alias_name    = 0
    #column_print_width = 3

    #SORT_COLUMN = 1
    sortColumn = ''
    maxColumn = ''

    # determine the number of columns presented
    numberOfColumns = len(readyData[0])

    # determine which column is which so sorting can happen
    for (index, columnInfo) in enumerate(columnData):
        if columnInfo[cmdb_alias_name] == sort_column:
            SWITCH_COLUMN = index
            break
    else:
        # There is no switch port column; therefore, no re-sort is
        # required.  Exit back out and print the data as normal,
        # with no adjustments
        return (readyData, False)

    if sortColumn == '':
        sortColumn = SWITCH_COLUMN
    else:
        sortColumn = SWITCH_COLUMN


    columnWidthList   = []
    columnHolder      = {}
    zippedList        = []
    overflowPrintData = {}

    for index in range(numberOfColumns):
        columnWidthList.append(columnData[index][column_print_width])
        columnHolder['c' + str(index)] = []

    for listSet in readyData:

        for index in range(numberOfColumns):
            if index == sortColumn:
                columnHolder['c' + str(index)].append(zeroPadNumbers(listSet[index]))
            else:
                columnHolder['c' + str(index)].append(listSet[index])

    for index in range(numberOfColumns):
        if index == sortColumn:
            zippedList = [columnHolder['c' + str(index)]]
            break

    for index in range(numberOfColumns):
        if index != sortColumn:
            zippedList.append(columnHolder['c' + str(index)])


    # use '*' to allow a variable length argument list work
    # zip up the columns
    zipped = zip(*zippedList)
    # sort them by the first column (e.g., default is switch/power ports)
    zipped.sort()
    # take the lists out of the 'zip' format
    zipLists = zip(*zipped)


    # put the columns back in their proper order
    fixedColumns = []

    if sortColumn != 0:
        for (index, zList) in enumerate(zipLists):
            if index == sortColumn:
                fixedColumns.append(list(zipLists[0]))
            elif index < sortColumn:
                fixedColumns.append(list(zipLists[(index+1)]))
            else:
                fixedColumns.append(list(zList))

    # determine the column with the most data (longest length of items)
    # this is typically the column with the host name
    for (index, columnInfo) in enumerate(columnData):
        if columnInfo[cmdb_alias_name] == "name":
            maxColumn = index
            break
    else:
        maxCount = 0
        for index in range(numberOfColumns):
            if len(fixedColumns[index]) > maxCount:
                maxColumn = index

    # put the data back in the proper format for pretty print to use it.
    readyData         = []

    for row in range(len(fixedColumns[maxColumn])):
        columnEndingPoint = 0
        for column in range(numberOfColumns):
            data = fixedColumns[column][row].strip()
            columnDataWidth = len(data)
            columnPrintWidth = columnData[column][column_print_width]
            columnEndingPoint += (columnPrintWidth + 1)

            if denaliVariables["textTruncate"] == True:
                cutLocation = (columnPrintWidth - 2)

                if columnDataWidth >= columnPrintWidth:
                    data = data[:cutLocation]

            elif denaliVariables["textWrap"] == True:

                if columnDataWidth >= columnPrintWidth:
                    # create a temporary variable passing dictionary
                    neededData = { "columnWidth"        : columnPrintWidth,
                                   "columnEnd"          : columnEndingPoint,
                                   "columnNumber"       : column,
                                   "columnDifference"   : -1
                                 }

                    if row in overflowPrintData:
                        tempOverFlow = generateColumnDataOverflow(data, neededData)
                        if tempOverFlow != False:
                            overflowPrintData[row].update(tempOverFlow)

                    else:
                        overflowPrintData[row] = generateColumnDataOverflow(data, neededData)

            data = unicode(data).ljust(columnPrintWidth)

            readyData.append(data)
        printData.append(readyData)
        readyData = []

    return (printData, overflowPrintData)



##############################################################################
#
# createColumnDataWithSecrets(denaliVariables, secretColumns)
#

def createColumnDataWithSecrets(denaliVariables, secretColumns):

    # generic column data structure creator function call
    # this will return with, among other items, the following (if the SECRETS
    # alias was used:
    #   ['SECRETS', 'SECRETS', 'SECRETS', 20]
    # If this isn't found, tack it on at the end

    (modifiedFields, denaliVariables["columnData"]) = determineColumnOrder(denaliVariables)

    # locate the index for the SECRETS column placeholder
    for (secretIndex, column) in enumerate(denaliVariables["columnData"]):
        # make triple-sure
        if column[0] == "SECRETS" and column[1] == "SECRETS" and column[2] == "SECRETS":
            break
    else:
        # it wasn't found -- put it at the end
        secretIndex = len(denaliVariables["columnData"])

        # insert the SECRETS column -- if the user forgot
        secretColumn = ['SECRETS', 'SECRETS', 'SECRETS', 20]
        denaliVariables["columnData"].insert(secretIndex, secretColumn)

    # insert the secret columns into the existing column data structure
    for (index, sColumn) in enumerate(secretColumns):
        denaliVariables["columnData"].insert((secretIndex + index), sColumn)

    # remove the placeholder secret column
    denaliVariables["columnData"].pop(secretIndex + index + 1)

    if denaliVariables["debug"] == True:
        print "finialized column data = %s" % denaliVariables["columnData"]

    return True



##############################################################################
#
# processGetSecretsResponse(queryDictionary, denaliVariables)
#

def processGetSecretsResponse(queryDictionary, denaliVariables):

    #
    # secret store column definitions
    #   device_service   == previously defined in CMDB as alias "device_service"
    #   environment_name == previously defined in CMDB as alias "environment"
    #   environment_type == previously defined in CMDB as alias "environment_name"
    #
    #   New column definitions:
    #       (1) users
    #           [ "user_secrets", "user_secrets", "%User Name% Secrets", 35]
    #
    #       (2) secrets
    #           [ "secret_users", "secret_users", "%Secret Name% Users", 35]
    #
    #       (3) secret_names
    #           List only the secret names (no user affiliation shown)
    #           [ "secret_names", "secret_name",  "Secret Names",        35]
    #
    #   Any %<variable>% means that it will be substituted with the user/secret
    #   as the column title
    #
    #   The denaliVariables["columnData"] information needs to be filled out in
    #   a manual way here in this function because these specific pieces of data
    #   cannot be specifically queried against (which is why these definitions
    #   aren't at the beginning of denali_search.py).
    #
    #   The column width is currently set to 35 because some secret names close
    #   in on 25 characters in length, and if multiple are shown, the wrap would
    #   be ugly -- thus, 10 more characters to make the potential wrap nicers.
    #   This may be adjusted later after some testing.
    #


    #
    # Variable Definitions
    #

    NO_USER      = "<EMPTY_USER>"
    COLUMN_WIDTH = 35
    printData    = []
    rowData      = []

    user_column         = ["user_secrets", "user_secrets", "",              COLUMN_WIDTH]
    secret_names_column = ["secret_names", "secret_names", "Secret Names",  COLUMN_WIDTH]

    #print "queryDictionary = %s" % queryDictionary

    # get the common data items
    device_service   = queryDictionary["device_service_name_arr"]
    environment_name = queryDictionary["environment_name"]
    environment_type = queryDictionary["environment_type"]

    # get the secret store data items
    users        = queryDictionary["users"]
    secrets      = queryDictionary["secrets"]
    secret_names = queryDictionary["secret_names"]


    # build the column data variable
    #   order is based on the denaliVariables["fields"] variable
    #   if the SECRETS alias is used, then integrate that in as well.

    # build the secret names column(s)
    secretColumns = []

    for name in secret_names:
        column = ["secret_users", "secret_users", "Secret: %s" % name, COLUMN_WIDTH]
        secretColumns.append(column)

    if len(secretColumns) != 0:
        ccode = createColumnDataWithSecrets(denaliVariables, secretColumns)
        if ccode == False:
            return False
    else:
        # empty secret names list
        print "Denali message:  No secret names are found for secret store name [%s] in Device Service [%s]." % (denaliVariables["getSecretsStore"], ','.join(device_service))
        return False

    # spin through each name in the user array -- replace empty names
    # with the NO_USER variable
    for (index, secretName) in enumerate(secrets):
        for (uIndex, username) in enumerate(secretName["users"]):
            if len(username) == 0:
                secrets[index]["users"][uIndex] = NO_USER


    # Put the data in the correct column
    #
    # This seems so different from the normal method used previously
    # in denali -- mainly because the return data from SKMS in dictionary
    # format is _so_ different from the previous dictionaries the code
    # has worked with.  Therefore, a customized method to retrieve and
    # display the data is required.
    for (index, column) in enumerate(denaliVariables["columnData"]):
        rowData.append('')
        if column[0] == "name":     # hostname
            rowData[index] = denaliVariables["getSecretsHost"]
        elif column[0] == "device_service":
            rowData[index] = ','.join(device_service)
        elif column[0] == "environment":
            rowData[index] = environment_name
        elif column[0] == "environment_name":
            rowData[index] = environment_type
        elif column[0] == "secret_users":
            # determine which secret name this is, and put the correct data in the column
            secretNameColumn = column[2]
            secretNameColumn = secretNameColumn.split(':')
            secretNameColumn = secretNameColumn[1].strip()
            for secretNameData in secrets:
                if secretNameData["secret_name"] == secretNameColumn:
                    rowData[index] = ','.join(secretNameData["users"])
                    break

    if denaliVariables["debug"] == True:
        print "getSecrets: columnData = %s" % denaliVariables["columnData"]
        print "getSecrets: dictionary = %s" % queryDictionary
        print "getSecrets: rowData    = %s" % rowData

    printData.append(rowData)

    return printData



##############################################################################
#
# restructureQueryDictionary(denaliVariables, queryDictionary["data"]["results"])
#
#   This function is called from generateOutputData and is meant to take a single
#   array entry (with multiple items from different columns) and make them into
#   individual data items (a row for each).  For now, when the DeviceGroupDao is
#   searched against, this is the only the time the call is made here.  It will
#   take the Device Group Name and duplicate it however many times is necessary
#   so that each device assigned to the device group can have a distinct row.
#

def restructureQueryDictionary(denaliVariables, queryDictionary):

    resultantList = []

    for device_index in range(len(queryDictionary)):

        # determine the row count to create
        arrayCount   = []
        arrayColumns = []

        for key_name in queryDictionary[device_index].keys():
            for columnName in denaliVariables["columnData"]:
                if columnName[1] == key_name:
                    if type(queryDictionary[device_index][key_name]) == list:
                        length = len(queryDictionary[device_index][key_name])
                        arrayCount.append(length)
                        arrayColumns.append(key_name)

        # determine if the array counts are identical (they should be)
        #
        # TO DO:
        # if they aren't, remove the count and column name from the list(s)
        # this also means if there are multiple arrays (they may have different
        # counts if they aren't from the same DAO -- be careful
        #

        if len(arrayCount) > 1:
            initialCount = arrayCount[0]

            success = False
            for number in arrayCount:
                if number == initialCount:
                    continue
                else:
                    break
            else:
                success = True
        else:
            success = False

        if success == False:
            # if the numbers aren't identical -- return the original
            # dictionary so it can be printed ... as is.
            return queryDictionary

        baseDict = {}

        # create the non-array members of the dictionary -- the "base" dictionary
        for key_name in queryDictionary[device_index].keys():
            for columnName in denaliVariables["columnData"]:
                if columnName[1] == key_name:
                    if type(queryDictionary[device_index][key_name]) != list:
                        baseDict.update({key_name:queryDictionary[device_index][key_name]})

        # for each baseDict, add on individual array members and put the new
        # baseDict into an array
        for index in range(arrayCount[0]):
            for column_name in arrayColumns:
                baseDict.update({column_name:queryDictionary[device_index][column_name][index]})

            # without this "copy" all entries are identical -- meaning, each server in the list
            # looks identical to the last -- so 64 identical entries for each host (which is wrong)
            resultantList.append(baseDict.copy())


    return resultantList



##############################################################################
#
# wrapColumnData(denaliVariables, existingData)
#

def wrapColumnData(denaliVariables, existingData):

    printData          = []
    readyData          = []
    overflowPrintData  = {}
    column_print_width = 3
    columnData = denaliVariables["columnData"]
    #numberOfColumns = len(existingData[0])

    #print "cd = %s" % columnData
    #print "ed = %s" % existingData
    for row in range(len(existingData)):
        columnEndingPoint = 0

        #for column in range(numberOfColumns):
        for column in range(len(existingData[row])):

            data = existingData[row][column]
            if data is None:
                data = ''
            data.encode('ascii', 'ignore')
            data = data.strip()
            columnDataWidth = len(data)
            columnPrintWidth = columnData[column][column_print_width]
            columnEndingPoint += (columnPrintWidth + 1)

            if denaliVariables["textTruncate"] == True:
                cutLocation = (columnPrintWidth - 2)

                if columnDataWidth >= columnPrintWidth:
                    data = data[:cutLocation]

            elif denaliVariables["textWrap"] == True:

                if columnDataWidth >= columnPrintWidth:
                    # create a temporary variable passing dictionary
                    neededData = { "columnWidth"        : columnPrintWidth,
                                   "columnEnd"          : columnEndingPoint,
                                   "columnNumber"       : column,
                                   "columnDifference"   : -1
                                 }

                    if row in overflowPrintData:
                        tempOverFlow = generateColumnDataOverflow(data, neededData)
                        if tempOverFlow != False:
                            overflowPrintData[row].update(tempOverFlow)

                    else:
                        overflowPrintData[row] = generateColumnDataOverflow(data, neededData)

            data = unicode(data).ljust(columnPrintWidth)
            readyData.append(data)

        printData.append(readyData)
        readyData = []

    return (printData, overflowPrintData)



##############################################################################
#
# calculateOverflowNumbers(rowNumber, overflowPrintData)
#

def calculateOverflowNumbers(rowNumber, overflowPrintData):

    # overflowPrintData investigation:
    #
    # With a single column containing overflow data, the logic doesn't need any more
    # tweaking.  However, if there are multiple columns on the same row that have
    # overflow data, more logic is needed.

    #
    # currentColumnData definitions (word description and value):
    # [0] = columnNumber        [1] value
    # [2] = columnWidth         [3] value
    # [4] = columnEnd           [5] value
    # [6] = columnDifference    [7] value
    #

    overflowColumns = len(overflowPrintData)

    if overflowColumns > 1:

        keys = sorted(overflowPrintData.keys())
        tempColumnData = []
        for column in keys:
            if len(tempColumnData) == 0:
                tempColumnData    = overflowPrintData[column][0]
                tempColumnNumber  = column
            else:
                currentColumnData = overflowPrintData[column][0]
                tempColumnEnd     = tempColumnData[5]
                #columnNumber      = currentColumnData[1]
                columnStart       = (currentColumnData[5] - currentColumnData[3]) - tempColumnEnd

                columnDifference  = (column - 1) - tempColumnNumber

                # should never be less than zero, but check anyway
                if columnDifference < 0:
                    columnDifference = 0

                currentColumnData[7] = (columnStart + columnDifference)

                # reset the temp variable to be correct -- to prepare for another
                # potential overflow column
                tempColumnData   = overflowPrintData[column][0]
                tempColumnNumber = column



##############################################################################
#
# monitorPrintRowColored(denaliVariables, printRow, originator='pretty')
#

def monitorPrintRowColored(denaliVariables, printRow, originator='pretty'):

    # list of monitoring commands that show the 'details' output
    detail_list = [ 'details', 'all', 'mismatch', 'simple' ]

    OK          = getattr(colors.fg, denaliVariables['mon_ok'])         # lightgreen
    CRITICAL    = getattr(colors.fg, denaliVariables['mon_critical'])   # red
    WARNING     = getattr(colors.fg, denaliVariables['mon_warning'])    # yellow
    UNKNOWN     = getattr(colors.fg, denaliVariables['mon_unknown'])    # darkgrey
    NOTFOUND    = getattr(colors.fg, denaliVariables['mon_notfound'])   # blue

    if denaliVariables['monitoring_default'] in detail_list:
        if originator == 'pretty' or (originator == 'overflow' and denaliVariables['monitoring_color'] is None):
            left_status_location = -1
            for search_monitor in ['CRITICAL', 'WARNING', 'UNKNOWN', 'OK']:
                status_location = printRow.find(search_monitor)

                if left_status_location == -1:
                    left_status_location = status_location
                elif status_location < left_status_location and status_location != -1:
                    left_status_location = status_location

            if left_status_location > -1:
                status_string = printRow[left_status_location:(left_status_location + 9)].strip()
                if status_string == "CRITICAL" or status_string.startswith('CRITICAL:'):
                    denaliVariables['monitoring_color'] = CRITICAL
                    print colors.bold + CRITICAL + printRow.encode("UTF-8") + colors.reset
                elif status_string == "WARNING" or status_string.startswith('WARNING :'):
                    denaliVariables['monitoring_color'] = WARNING
                    print colors.bold + WARNING + printRow.encode("UTF-8") + colors.reset
                elif status_string == "UNKNOWN" or status_string.startswith('UNKNOWN :'):
                    denaliVariables['monitoring_color'] = UNKNOWN
                    print colors.bold + UNKNOWN + printRow.encode("UTF-8") + colors.reset
                elif status_string == "OK":
                    denaliVariables['monitoring_color'] = OK
                    print colors.bold + OK + printRow.encode("UTF-8") + colors.reset
                else:
                    denaliVariables['monitoring_color'] = colors.reset
                    print printRow.encode("UTF-8")
            else:
                denaliVariables['monitoring_color'] = colors.reset
                print printRow.encode("UTF-8")
        else:
            print colors.bold + denaliVariables["monitoring_color"] + printRow.encode("UTF-8") + colors.reset

    elif denaliVariables['monitoring_default'] == 'summary':
        if printRow.strip()[0][0] == '(':
            # multiple downtime events?  Color is bold gray
            # kind of a hack-y way to determine if the next line is a wrap showing
            # a different maintenance event
            print_color = colors.bold + UNKNOWN
        else:
            splitRow = printRow.split()

            if int(splitRow[denaliVariables['monitoring_columns']['crit']]) > 0:
                print_color = colors.bold + CRITICAL
            elif int(splitRow[denaliVariables['monitoring_columns']['warn']]) > 0:
                print_color = colors.bold + WARNING
            elif int(splitRow[denaliVariables['monitoring_columns']['unk']]) > 0:
                print_color = colors.bold + UNKNOWN
            elif int(splitRow[denaliVariables['monitoring_columns']['ok']]) > 0:
                print_color = colors.bold + OK
            else:
                print_color = colors.bold + NOTFOUND
                #print_color = colors.reset

        print print_color + printRow.encode("UTF-8") + colors.reset

    else:
        print printRow.encode("UTF-8")



##############################################################################
#
# sortByDataCenter(denaliVariables, queryDictionary)
#
#   This function sorts the hosts by data center first, and then by hostname.
#   With the normal 'name' sort from MySQL, the hosts in each data center will
#   typically not be by each other in the final listing on-screen/file, because
#   MySQL doesn't understand this specific sort that is wanted.
#

def sortByDataCenter(denaliVariables, queryDictionary):

    sort_dictionary = {}
    new_query_data  = []

    results = queryDictionary['data']['results']
    for (index, item) in enumerate(results):
        if item['name'].find('.') != -1:
            data_center = item['name'].split('.')[-1]
        else:
            data_center = 'z'

        hostname = item['name'] + ':' + str(index)
        if data_center.upper() in denali_location.dc_location or data_center == 'sbx1':
            if data_center not in sort_dictionary:
                # add it
                sort_dictionary.update({data_center:[hostname]})
            else:
                # augment it
                sort_dictionary[data_center].append(hostname)
        else:
            # handle 'other' data centers: ut1.omniture.com, etc.
            if data_center != 'z':
                data_center = item['name'].split('.',1)
                data_center = data_center[1].split('.')[0]
            if data_center.upper() in denali_location.dc_location:
                if data_center not in sort_dictionary:
                    # add it
                    sort_dictionary.update({data_center:[hostname]})
                else:
                    # augment it
                    sort_dictionary[data_center].append(hostname)
            else:
                # sort any hosts/devices in this category to 'z' -- at the bottom
                if 'z' not in sort_dictionary:
                    # add it
                    sort_dictionary.update({'z':[hostname]})
                else:
                    # augment it
                    sort_dictionary['z'].append(hostname)

    dc_locations = sort_dictionary.keys()
    dc_locations.sort()

    for location in dc_locations:
        # this 'name' sort isn't needed ... it is already sorted.
        #sort_dictionary[location].sort()

        # put the sorted list in the new query data list
        for host_data in sort_dictionary[location]:
            host_index = int(host_data.split(':')[1])
            new_query_data.append(results[host_index])

    # reassign it back to the queryDictionary as a data center sorted list now
    queryDictionary['data']['results'] = new_query_data

    return queryDictionary



##############################################################################
#
# determineAttributeColumnSizeValues(denaliVariables, queryDictionary)
#
# attributes requested, pre-populate the data ... to help performance/efficiency
# collect the sql search criteria for attributes (what was requested)
# each returned variable is divided into 3 parts (in a List)
#   1. True/False : Whether or not the request is a wildcard search
#   2. Actual request : The request (wildcard and all)
#   3. Modified request : The request without the wildcard (if applicable)
#
#   Example:
#   --attribute_name="MONGO* OR CLUSTER_NAME"
#
#   The above query, results in this return:
#   attr_name = [[True, 'MONGO*', 'MONGO'], [False, 'CLUSTER_NAME', 'CLUSTER_NAME']]

def determineAttributeColumnSizeValues(denaliVariables, queryDictionary):

    showAllAttributes      = False

    wildcard_name_list     = []
    nonwildcard_name_list  = []
    completed_name_list    = []

    wildcard_value_list    = []
    nonwildcard_value_list = []
    completed_value_list   = []

    length_dictionary      = {
                                'stacked': {'max_name_length':0, 'max_value_length':0},
                                'columns': {},
                             }

    (attr_name, attr_value, attr_inheritance) = denali_utility.getSQLAttributeSearch(denaliVariables["sqlParmsOriginal"])

    # if no search criteria was entered -- show all of the attributes
    if len(attr_name) == 0 and len(attr_value) == 0 and len(attr_inheritance) == 0:
        showAllAttributes = True

    # wildcarded names/values?
    for name in attr_name:
        if name[0] == True:
            wildcard_name_list.append(name[2])
        else:
            nonwildcard_name_list.append(name[1])

    for value in attr_value:
        if value[0] == True:
            wildcard_value_list.append(value[2])
        else:
            nonwildcard_value_list.append(value[1])

    for (index, host) in enumerate(queryDictionary['data']['results']):
        name_list_orig  = queryDictionary['data']['results'][index]['attribute_data.attribute.name']
        value_list_orig = queryDictionary['data']['results'][index]['attribute_data.value']

        if showAllAttributes == True:
            # the length_dictionary still needs to be filled out, even if no
            # attribute names/values were specified
            for name in name_list_orig:
                if len(name) > length_dictionary['stacked']['max_name_length']:
                    length_dictionary['stacked']['max_name_length'] = len(name)
                if name not in length_dictionary['columns']:
                    length_dictionary['columns'].update({name:len(name)})

            for (wIndex, value) in enumerate(value_list_orig):
                if len(value) > length_dictionary['stacked']['max_value_length']:
                    length_dictionary['stacked']['max_value_length'] = len(value)
                if len(value) > length_dictionary['columns'][name_list_orig[wIndex]]:
                    length_dictionary['columns'][name_list_orig[wIndex]] = len(value)

        else:
            # get all name wildcard matches
            if len(wildcard_name_list):
                for wild_name in wildcard_name_list:
                    for (wIndex, name) in enumerate(name_list_orig):
                        # substring search ... quick and dirty
                        if wild_name in name:
                            # for the name, bring along the value as well

                            if len(name) > length_dictionary['stacked']['max_name_length']:
                                length_dictionary['stacked']['max_name_length'] = len(name)
                            if len(value_list_orig[wIndex]) > length_dictionary['stacked']['max_value_length']:
                                length_dictionary['stacked']['max_value_length'] = len(value_list_orig[wIndex])

                            # add to the 'columns' key in the length_dictionary
                            if name not in length_dictionary['columns']:
                                length_dictionary['columns'].update({name:len(name)})
                            if len(value_list_orig[wIndex]) > length_dictionary['columns'][name]:
                                length_dictionary['columns'][name] = len(value_list_orig[wIndex])

            # get all name non-wildcard matches
            if len(nonwildcard_name_list):
                for nonwild_name in nonwildcard_name_list:
                    if nonwild_name in name_list_orig:
                        # for the name, bring along the value as well
                        wIndex = name_list_orig.index(nonwild_name)

                        if len(nonwild_name) > length_dictionary['stacked']['max_name_length']:
                            length_dictionary['stacked']['max_name_length'] = len(nonwild_name)
                        if len(value_list_orig[wIndex]) > length_dictionary['stacked']['max_value_length']:
                            length_dictionary['stacked']['max_value_length'] = len(value_list_orig[wIndex])

                        # add to the 'columns' key in the length_dictionary
                        if nonwild_name not in length_dictionary['columns']:
                            length_dictionary['columns'].update({nonwild_name:len(nonwild_name)})
                        if len(value_list_orig[wIndex]) > length_dictionary['columns'][nonwild_name]:
                            length_dictionary['columns'][nonwild_name] = len(value_list_orig[wIndex])

            # get all value wildcard matches
            if len(wildcard_value_list):
                for wild_value in wildcard_value_list:
                    for (wIndex, value) in enumerate(value_list_orig):
                        if wild_value in value:

                            if len(value) > length_dictionary['stacked']['max_value_length']:
                                length_dictionary['stacked']['max_value_length'] = len(value)
                            if len(name_list_orig[wIndex]) > length_dictionary['stacked']['max_name_length']:
                                length_dictionary['stacked']['max_name_length'] = len(name_list_orig[wIndex])

                            # add to the 'columns' key in the length_dictionary
                            if name_list_orig[wIndex] not in length_dictionary['columns']:
                                length_dictionary['columns'].update({name_list_orig[wIndex]:len(name_list_orig[wIndex])})
                            if len(value) > length_dictionary['columns'][name_list_orig[wIndex]]:
                                length_dictionary['columns'][name_list_orig[wIndex]] = len(value)

            # get all value non-wildcard matches
            if len(nonwildcard_value_list):
                for nonwild_value in nonwildcard_value_list:
                    if nonwild_value in value_list_orig:
                        wIndex = value_list_orig.index(nonwild_value)
                        if len(nonwild_value) > length_dictionary['stacked']['max_value_length']:
                            length_dictionary['stacked']['max_value_length'] = len(nonwild_value)
                        if len(name_list_orig[wIndex]) > length_dictionary['stacked']['max_name_length']:
                            length_dictionary['stacked']['max_name_length'] = len(name_list_orig[wIndex])

                        # add to the 'columns' key in the length_dictionary
                        if name_list_orig[wIndex] not in length_dictionary['columns']:
                            length_dictionary['columns'].update({name_list_orig[wIndex]:len(name_list_orig[wIndex])})
                        if len(value) > length_dictionary['columns'][name_list_orig[wIndex]]:
                            length_dictionary['columns'][name_list_orig[wIndex]] = len(value)

            if not len(completed_value_list):
                completed_value_list = value_list_orig

    # store this dictionary for possible use with non-stacked attribute displays
    denaliVariables['attributeColumnSizes'] = dict(length_dictionary)

    return length_dictionary



##############################################################################
#
# autoColumnResize(denaliVariables, queryDictionary)
#
#   This function inspects the data from the dictionary returned by SKMS and
#   auto-resizes all columns to fit the size of the maximum string found in
#   the response.
#
#   For the first revision, all of the resizing is done "down".  This means if
#   the found maximum size is less than the configured size, then the column
#   will be resized down to meet the maximum found size.  If the size is
#   greater, it is ignored and the maximum configured size is used.
#
#   The +2 is for a single space at the beginning and end of the text to aid
#   in readability.
#

def autoColumnResize(denaliVariables, queryDictionary):

    CURRENT_SETTING  = 0
    MAXIMUM_VALUE    = 1
    COLUMN_NAME_SIZE = 2
    columnData       = denaliVariables['columnData']
    column_sizes     = []
    resize_all       = False
    GUTTER_SIZE      = 2

    # Collect current values and insert them into column_sizes
    for column in columnData:
        current   = column[-1]
        colString = len(column[-2])
        column_sizes.append([current,0,colString])

    # if attributes are involved, special logic/searching needs to happen
    if denaliVariables['attributes'] == True:
        attribute_column_sizes = determineAttributeColumnSizeValues(denaliVariables, queryDictionary)

    # Each serverData instance represents the data for a single device only
    # so each column/data-element must be gone through one at a time.
    # Because this is iterated through on a column-by-column basis, it makes
    # it easy to put the number in the column_sizes List/array structure.
    for (rowNumber, serverData) in enumerate(queryDictionary["data"]["results"]):
        for (columnIndex, column) in enumerate(columnData):
            if column[1] in serverData:
                if type(serverData[column[1]]) is list:
                    if len(serverData[column[1]]):
                        # handle attribute display auto-resizing
                        if column[0] == 'attribute_name':
                            string_length = attribute_column_sizes['stacked']['max_name_length']
                        elif column[0] == 'attribute_value':
                            string_length = attribute_column_sizes['stacked']['max_value_length']
                        else:
                            string_length = len(serverData[column[1]][0])
                    else:
                        string_length = 0
                else:
                    string_length = len(str(serverData[column[1]].encode("UTF-8")))
            else:
                string_length = 0

            if string_length > column_sizes[columnIndex][MAXIMUM_VALUE]:
                column_sizes[columnIndex][MAXIMUM_VALUE] = string_length

    # Now review the adjusted column sizes and replace the columnData numbers
    # with these new numbers -- if appropriate.
    #
    # Checks that must pass before the column width is adjusted up:
    #   1.  The found maximum for the column is greater than the column title
    #
    #   This check isn't implemented yet -- still working on when it should be used
    #   2.  The found maximum for the column is greater than the defined column size
    #
    # Checks that must pass before the column width is adjusted down:
    #   1.  The found maximum for the column is less than the configured maximum
    #   2.  The found maximum for the column is greater than (or equal to) column title
    for (index, column) in enumerate(column_sizes):
        if resize_all == True or len(denaliVariables['externalModule']):
            # resize the column "up"
            if ((column[MAXIMUM_VALUE] + GUTTER_SIZE) > (column[COLUMN_NAME_SIZE] + GUTTER_SIZE)):
                columnData[index][-1] = (column[MAXIMUM_VALUE] + GUTTER_SIZE)
        else:
            # resize the column "down"
            if (column[MAXIMUM_VALUE] + GUTTER_SIZE) < column[CURRENT_SETTING]:
                if (column[MAXIMUM_VALUE] + GUTTER_SIZE) >= (column[COLUMN_NAME_SIZE] + GUTTER_SIZE):
                    # column text less than defined column width, greater than column header
                    # set to text size
                    columnData[index][-1] = (column[MAXIMUM_VALUE] + GUTTER_SIZE)
                elif (column[MAXIMUM_VALUE] + GUTTER_SIZE):
                    # column text less than defined column width, less than column header
                    # set to column header size
                    columnData[index][-1] = (column[COLUMN_NAME_SIZE] + GUTTER_SIZE)



##############################################################################
#
# generateOutputData(queryDictionary, denaliVariables)
#
#   Generate all of the data to be output (to screen and/or file)
#

def generateOutputData(queryDictionary, denaliVariables):

    if denaliVariables['data_center_sort'] == True:
        queryDictionary = sortByDataCenter(denaliVariables, queryDictionary)

    printData         = []
    overflowPrintData = {}
    denali_utility.addElapsedTimingData(denaliVariables, 'generateOutputData_start', time.time())
    #print "response length = %d" % len(queryDictionary['data']['results'])
    method     = denaliVariables["method"]
    methodData = {}
    columnData = denaliVariables["columnData"]

    name_check  = []
    value_check = []

    if denaliVariables["debug"] == True:
        print "\n++Entered generateOutputData\n"

    if method == "search" or method == "count" or method == "getCurrentOnCallInfo":
        if queryDictionary == False:
            if denaliVariables["showInfoMessages"] == True:
                print "No devices found for the query submitted (3)."
            denali_utility.addElapsedTimingData(denaliVariables, 'generateOutputData_stop', time.time())
            cleanUp(denaliVariables)
            exit(1)

        if (
            "data" in queryDictionary and "results" in queryDictionary["data"] and
            isinstance(queryDictionary["data"]["results"], list)):

            # auto resize of columns
            #
            # This function will investigate each of the fields to be printed, and will resize the column size
            # "down" to meet the maximum size.  "UP" sizing will be enabled later, with provisions.
            if denaliVariables['autoColumnResize'] == True:
                autoColumnResize(denaliVariables, queryDictionary)

            # if DeviceGroupDao is used -- put each device (in a group) on a separate line
            if denaliVariables["searchCategory"] == "DeviceGroupDao":
                # only do the restructuring if no attributes were requested
                if denaliVariables['fields'].find('attribute_name') == -1 and denaliVariables['fields'].find('attribute_value') == -1:
                    denali_utility.addTimingData(denaliVariables, 'restructureQueryDictionary_start', time.time())
                    queryDictionary["data"]["results"] = restructureQueryDictionary(denaliVariables, queryDictionary["data"]["results"])
                    denali_utility.addTimingData(denaliVariables, 'restructureQueryDictionary_stop', time.time())

            for (rowNumber, serverData) in enumerate(queryDictionary["data"]["results"]):
                #print "columnData = %s" % columnData
                # create an empty List with "None" in all positions
                tempList = list(None for index in columnData)

                # holding variables for attribute values if they exist
                nameList    = []
                valueList   = []
                inheritList = []

                ##
                ## New code (if I can figure out how to use it correctly)
                ## This will improve the performance of the function by not
                ## having to search through each data item and column looking
                ## for a match
                ##

                # make a columnData dictionary, for faster lookups (cycling through one by
                # one is not very efficient
                columnDataDict = {}

                for (index, column) in enumerate(columnData):
                    columnDataDict.update({column[cmdb_name_pos]:index})

                #print "columnDataDict = %s" % columnDataDict

                ##
                ## End new code
                ##

                # move the data from the Dictionary to a List -- in rows with columns
                #print "\ncolumnData = %s\n" % columnData
                #print "serverData = %s" % serverData
                for attribute in serverData:
                    #print "looking at skms response key = %s" % attribute
                    for (cIndex, column) in enumerate(columnData):
                        #print "index = %d   ::   looking at column : %s" % (cIndex, column)
                        if attribute == column[cmdb_name_pos] or (attribute.startswith("attr") and column[cmdb_name_pos].startswith("attr_")):
                            # Check the value in the returned data against what is stored in the
                            # columnData store ... if it matches, put the data in the tempList.
                            #print "column found / being processed = %s\n" % attribute
                            if attribute.startswith("attr_") or attribute.startswith("attribute_"):
                            #    print "!!!attr_start_processing"
                            #if (attribute == "attribute_data.attribute.name" or attribute == "attribute_data.value" or
                            #    attribute == "attribute_data.inherited_from_attribute.value"):
                                tempList[cIndex] = ''

                                if denali_utility.singleAttributeColumn(denaliVariables) == True:
                                    # Single attribute column (name or inheritance only) asked for display.
                                    # attribute_values aren't stored the same way in the dictionary.
                                    #
                                    # My guess is that attribute_name would be the only column asked to be
                                    # displayed in this manner -- but maybe I'm wrong.
                                    # 2/2/2018:  yep, I'm wrong.  Request for attribute_value column just
                                    #            made.  change made in denali_arguments | parseArgumentList()
                                    #            to determine if this is the case and automatically "help"
                                    #            the user so the output looks correct.

                                    # Retrieve the column data and sort it
                                    tempList[cIndex] = serverData[attribute]

                                    # It was suggested to me that sorting this list makes the appearance better.
                                    # If there are problems, they will be dealt with in a bug report.
                                    tempList[cIndex].sort()
                                else:
                                    # Multiple attribute columns asked to display (name/value are the most common)
                                    if "attribute_data" in serverData:
                                        for (index, attribute_data) in enumerate(serverData["attribute_data"]):
                                            if attribute == "attribute_data.attribute.name":
                                                if "attribute" in attribute_data and "name" in attribute_data["attribute"]:
                                                    nameList.append(attribute_data["attribute"]["name"])

                                            if attribute == "attribute_data.value":
                                                if "value" in attribute_data:
                                                    valueList.append(attribute_data["value"])

                                            if attribute == "attribute_data.inherited_from_attribute.value":
                                                if "inherited_from_attribute" in attribute_data and "value" in attribute_data["inherited_from_attribute"]:
                                                    inheritList.append(attribute_data["inherited_from_attribute"]["value"])
                                            elif attribute == "attribute_data.overrides_attribute_data_id":
                                                # repurpose the inheritList to hold the inherit data ID
                                                if "overrides_attribute_data_id" in attribute_data:
                                                    inheritList.append(attribute_data["overrides_attribute_data_id"])
                                            elif attribute == "attribute_data.inherited_attribute_data_id":
                                                if "inherited_attribute_data_id" in attribute_data:
                                                    inheritList.append(attribute_data["inherited_attribute_data_id"])
                                    else:
                                        # attribute_data key not found -- DeviceGroupDao? so attribute_data.value in serverData?  check...
                                        # only add attributes/values for those that are searched for
                                        #print "dvsql parms = %s" % denaliVariables["sqlParmsOriginal"]

                                        if len(denaliVariables["sqlParmsOriginal"]) > 0:
                                            for param in denaliVariables["sqlParmsOriginal"]:
                                                if param[0] == "--attribute_data.attribute.name" and len(name_check) == 0:
                                                    name_check.extend(param[1].split())
                                                if param[0] == "--attribute_data.value" and param[1] and len(value_check) == 0:
                                                    value_check.extend(param[1].split())

                                        #print "name_check = %s" % name_check
                                        #print "value_check = %s" % value_check

                                        if "attribute_data.attribute.name" in serverData:
                                            if len(name_check):
                                                #print "1"
                                                if serverData["attribute_data.attribute.name"] in name_check[0]:
                                                    #print "2"
                                                    nameList.append(serverData["attribute_data.attribute.name"])

                                        if "attribute_data.value" in serverData:
                                            if len(value_check):
                                                #print "1"
                                                if serverData["attribute_data.value"] in value_check[0]:
                                                    #print "2"
                                                    valueList.append(serverData["attribute_data.value"])

                                        if "attribute_data.inherited_from_attribute.value" in serverData:
                                            inheritList.append(serverData["inherited_from_attribute"]["value"])
                                        elif "attribute_data.overrides_attribute_data_id" in serverData:
                                            inheritList.append(serverData["overrides_attributed_data_id"])
                                        elif "attribute_data.inherited_attribute_data_id" in serverData:
                                            inheritList.append(serverData["inherited_attribute_data_id"])

                            else:
                                if type(serverData[attribute]) is list:
                                    # Probably not the most "pythonic" thing to do here.
                                    # If a list is detected, just join the contents to avoid
                                    # issues with a list data object later.
                                    serverData[attribute] = ','.join(serverData[attribute])

                                tempList[cIndex] = serverData[attribute]

                            break
                        else:
                            #print "column doesn't match skms key"
                            pass

                else:
                    # process rows with attribute data contained within
                    # create a List of Lists containing the server data gathered
                    columnEndingPoint = 0

                    # check for attribute processing ... if the name or value list has a length > 0
                    # it means that we have a row with attribute columns
                    if len(nameList) > 0 or len(valueList) > 0:
                        # send off the 3 Lists and sort them, returning a dictionary with key values
                        #       "attributeName", "attributeValue", "attributeInheritance"
                        attrLists = denali_utility.sortAttributeColumns(denaliVariables, nameList, valueList, inheritList)

                        # code to catch if displaying attribut-ed columns will work correctly.
                        if denaliVariables["attributesStacked"] == False:
                            if len(nameList) == 0 or len(valueList) == 0:
                                # both the name and value are required for a column-ized attribute display
                                denaliVariables["attributesStacked"] = True

                        if denaliVariables["attributesStacked"] == True:
                            # run the default attribute display (all attributes in single column displays)
                            tempList = denali_utility.insertStackedAttributeColumns(denaliVariables, attrLists, tempList)
                            if tempList == False:
                                denali_utility.addElapsedTimingData(denaliVariables, 'generateOutputData_stop', time.time())
                                return False

                        else:
                            # run the optional attribute display (each attribute in a separate column)
                            tempList = denali_utility.insertAttributeColumns(denaliVariables, attrLists, tempList)
                            if tempList == False:
                                denali_utility.addElapsedTimingData(denaliVariables, 'generateOutputData_stop', time.time())
                                return False

                        # perform specialColumnHandling for rows with attributes
                        # tempList is a List within a List ---> [['db2255.oak1','5','On Duty - Standby','2.4']]
                        for (columnNumber, rowData) in enumerate(tempList[0]):
                            if rowData == None: rowData = ''
                            rowData = denali_utility.stripUnicodeTrappings(rowData)
                            rowData = specialColumnHandling(denaliVariables, rowData, columnData[columnNumber][cmdb_alias_name])
                            tempList[0][columnNumber] = rowData

                        printData.extend(tempList)

                    else:
                        # process rows without attribute data
                        for (columnNumber, data) in enumerate(tempList):
                            if data == None: data = ''
                            data = denali_utility.stripUnicodeTrappings(data)
                            data = specialColumnHandling(denaliVariables, data, columnData[columnNumber][cmdb_alias_name])
                            tempList[columnNumber] = data

                        printData.append(tempList)

                        if rowNumber in overflowPrintData:
                            calculateOverflowNumbers(rowNumber, overflowPrintData[rowNumber])

            # Regular data processing finished
            (printData, overflowPrintData) = wrapColumnData(denaliVariables, printData)

    elif method == "getSecrets":
        printData = processGetSecretsResponse(queryDictionary, denaliVariables)
        if printData == False:
            # problem getting the data from the dictionary
            denali_utility.addElapsedTimingData(denaliVariables, 'generateOutputData_stop', time.time())
            return (False, False)

        # wrap the column data -- if requested
        (printData, overflowPrintData) = wrapColumnData(denaliVariables, printData)
        if printData == False:
            # problem wrapping the data
            denali_utility.addElapsedTimingData(denaliVariables, 'generateOutputData_stop', time.time())
            return (False, False)

    # specific handling of the --power/id parameter to manually inject a column,
    # into an already collected set of data
    if denaliVariables["addColumn"] == True:
        denaliVariables["addColumn"] = False

        # where the column is inserted (after the first)
        insertColumn = 1
        # column header/width data
        newColumnData = ["power_slot","device_power_connection.model_power_connection.name","Port", 6]

        printData = denali_utility.keyColumnInsert(printData, denaliVariables, insertColumn, newColumnData)
        (printData, overflowPrintData) = handleUnsortedColumns(columnData, printData, denaliVariables, "power_slot")

    # specific handling of the --switch parameter to manually sort the columns
    # and then print the data
    if denaliVariables["sortColumnsFirst"] == True:
        denaliVariables["sortColumnsFirst"] = False

        (printData, overflowPrintData) = handleUnsortedColumns(columnData, printData, denaliVariables, "switch_port_name")

    # if the --validate switch was used, put the not-found-hosts in the printData
    if denaliVariables["validateData"] == True:
        # only show these devices after they are "found"
        if len(denaliVariables["devicesNotFound"]) > 0:
            if denaliVariables["authSuccessful"] == True:
                # append the DNF data to the end of the printData List
                for row in denaliVariables["dnfPrintList"]:
                    printData.append(row)
            else:
                print "Authentication unsuccessful, not printing DNF data"

    denali_utility.addElapsedTimingData(denaliVariables, 'generateOutputData_stop', time.time())
    return (printData, overflowPrintData)



##############################################################################
#
# printOverflowData(denaliVariables, PAD_DEBUG, printRow, overflowDataCopy, row, target, outFile)
#

def printOverflowData(denaliVariables, PAD_DEBUG, printRow, overflowDataCopy, row, target, outFile):

    NO_CHANGES = getattr(colors.fg, denaliVariables["updateColorNo"])
    CHANGES    = getattr(colors.fg, denaliVariables["updateColorYes"])

    OK         = getattr(colors.fg, "lightgreen")
    CRITICAL   = getattr(colors.fg, "red")
    WARNING    = getattr(colors.fg, "yellow")
    UNKNOWN    = getattr(colors.fg, "darkgrey")

    printGreen = False
    printRed   = False

    if "file" in target.type:
        output = u'%s\n' % printRow
        outFile.write(output.encode("UTF-8"))
        #outFile.write(printRow + '\n')

    # print the first row of the overflow data set (i.e., with the hostname)
    if "screen" in target.type:
        if printRow.strip()[0] == '=':
            # print the row green
            printRow = printRow.replace('=', ' ')
            print colors.bold + NO_CHANGES + printRow + colors.reset
            printGreen = True
        elif printRow.strip()[0] == '+':
            # print the row red
            printRow = printRow.replace('+', ' ')
            print colors.bold + CHANGES + printRow + colors.reset
            printRed = True
        elif denaliVariables["monitoring"] == True and denaliVariables["nocolors"] == False:
            # no 'overflow' for 3rd parm as this is needed to search for the status_string
            monitorPrintRowColored(denaliVariables, printRow)
        else:
            # normal print -- standard white
            print printRow.encode("UTF-8")

    # make the overflow "row(s)" of data ready to print
    while row in overflowDataCopy:

        if PAD_DEBUG == True:
            data = "_"
        else:
            data = " "

        # gather the sorted keys (of columns) for this row
        keys = sorted(overflowDataCopy[row].keys())

        prevCEnd   = 0
        prevCWidth = 0
        prevC      = 0
        dataLength = 0

        for (index, overflowColumn) in enumerate(keys):
            frontPadding = ''
            #backPadding  = ''
            width        = overflowDataCopy[row][overflowColumn][0][3]
            end          = overflowDataCopy[row][overflowColumn][0][5]
            #columnDiff   = overflowDataCopy[row][overflowColumn][0][7]


            # get the data (removing it from the column data)
            subData = overflowDataCopy[row][overflowColumn].pop(1).strip()

            # remove hidden characters in the overflow data
            subData = subData.replace('\t', " ")
            subData = subData.replace('\r', " ")
            subData = subData.replace('\n', " ")

            dataLength += len(subData)

            if PAD_DEBUG == True:
                print "pend = %d  ::  pwidth = %d  ::  length = %d  ::  width = %d  ::  end = %d  ::  start = %d" % \
                      (prevCEnd, prevCWidth, len(subData), width, end, (end - width))

            # column padding
            if len(subData) < width:
                if PAD_DEBUG == True:
                    print "column padding :: width-len = %d-%d=%d" % (width, len(subData), (width - len(subData)))
                    char = '.'
                else:
                    char = ' '

                difference = (width - len(subData))
                columnPadding = (char * difference)
                subData = subData + columnPadding

            else:
                if PAD_DEBUG == True:
                    print "no column padding :: width-len = %d-%d=%d" % (width, len(subData), (width - len(subData)))

            #front padding
            column_start = (end - width)

            if column_start > 0:
                if PAD_DEBUG == True:
                    char = '~'
                else:
                    char = ' '

                difference = (column_start - prevCEnd)
                frontPadding = (char * difference)
                subData = frontPadding + subData

            dataLength += len(subData)
            data += subData

            # if the column control data is all that is left, remove the column
            if len(overflowDataCopy[row][overflowColumn]) == 1:
                del overflowDataCopy[row][overflowColumn]

            # if the row is empty, remove it from the dictionary
            if len(overflowDataCopy[row]) == 0:
                del overflowDataCopy[row]

            #Set the previous column ending point
            prevCEnd = end
            prevCWidth = width
            #prevC = overflowColumn

        if "file" in target.type:
            output = u'%s\n' % data
            outFile.write(output.encode("UTF-8"))
            #outFile.write(data + '\n')

        # print other overflow rows (i.e., without the hostname)
        if "screen" in target.type:
            if printGreen == True:
                # print the row green
                data = data.replace('=', ' ')
                print colors.bold + NO_CHANGES + data.encode("UTF-8") + colors.reset
            elif printRed == True:
                # print the row red
                data = data.replace('+', ' ')
                print colors.bold + CHANGES + data.encode("UTF-8") + colors.reset
            elif denaliVariables["monitoring"] == True and denaliVariables["nocolors"] == False:
                monitorPrintRowColored(denaliVariables, data, 'overflow')
            else:
                # normal print -- standard white
                print data.encode("UTF-8")



##############################################################################
#
# limitSegregation(denaliVariables, printData, overflowData)
#
#   MRASEREQ-41219:
#   The purpose of this function to to remove line items that aren't desired
#   to be output because of a specific limit request made.
#
#   Example: --limit=2:device_service
#
#   This means that only show the first two devices of each device service
#   in the query response.  All other devices, remove.
#

def limitSegregation(denaliVariables, printData, overflowData):

    new_printData    = []
    new_overflowData = {}
    columnData       = denaliVariables['columnData']
    limitData        = denaliVariables['limitData']
    data_counter     = 0

    #print "pd = %s" % printData
    #print "od = %s" % overflowData
    #print "column data = %s" % columnData
    #print "(b) limit data  = %s" % limitData

    # find the identifying column in columnData from the limitData supplied
    column_counter    = int(limitData['definition'].split(':')[0])
    column_identifier = limitData['definition'].split(':')[1]

    #print "cc = %s" % column_counter
    #print "ci = %s" % column_identifier

    for (index, column) in enumerate(columnData):
        if column[0] == column_identifier or column[1] == column_identifier:
            column_match = index
            break
    else:
        # no match found -- assume invalid entry, just return existing data
        return printData, overflowData

    for (index, row) in enumerate(printData):
        row_data = row[column_match].strip()
        if row_data not in limitData:
            limitData.update({row[column_match].strip():1})
            new_printData.append(row)
            if len(overflowData) > 0 and index in overflowData:
                new_overflowData.update({data_counter:overflowData[index]})
            data_counter += 1
        else:
            count = limitData[row_data]
            if count < column_counter:
                count += 1
                limitData[row_data] = count
                new_printData.append(row)
                if len(overflowData) > 0 and index in overflowData:
                    new_overflowData.update({data_counter:overflowData[index]})
                data_counter += 1

    # store the total device count in denaliVariables['limitData']
    # so the --summary code can find/use it.
    summary = denaliVariables['limitData'].get('summary',0)
    denaliVariables['limitData']['summary'] = summary + len(new_printData)

    #print "(a) limit data  = %s" % limitData
    #print "npd = %s" % new_printData
    #print "nod = %s" % new_overflowData

    return new_printData, new_overflowData



##############################################################################
#
# prettyPrintData(printData, overflowData, queryDictionary, denaliVariables)
#

def prettyPrintData(printData, overflowData, queryDictionary, denaliVariables):

    #cmdb_alias_name     = 0
    #cmdb_name_pos       = 1          # the column that stores the cmdb reference name
                                      # (the name the API expects to see)
    #column_name_pos     = 2          # the column that stores the Name to print (not the CMDB name)
    #column_print_width  = 3          # the column that stores the column print width

    denali_utility.addElapsedTimingData(denaliVariables, 'prettyPrintData_start', time.time())

    if denaliVariables["debug"] == True:
        print "\n++Entered prettyPrintData\n"

    #PAD_DEBUG           = True
    PAD_DEBUG           = False
    outFile             = ''

    NO_CHANGES   = getattr(colors.fg, denaliVariables["updateColorNo"])
    CHANGES      = getattr(colors.fg, denaliVariables["updateColorYes"])
    HOSTNAME     = getattr(colors.fg, "red")
    CATEGORY     = getattr(colors.fg, "blue")

    method       = denaliVariables["method"]
    outputTarget = denaliVariables["outputTarget"]
    headers      = denaliVariables["showHeaders"]
    columnData   = denaliVariables["columnData"]

    #print "cd  = %s" % columnData
    #print "qd  = %s" % queryDictionary
    #print "pd  = %s" % printData
    #print "ofd = %s" % overflowData

    # MRASEREQ-41219
    if 'definition' in denaliVariables["limitData"] and denaliVariables['commandFunction'] == '':
        # checking commandFunction because if limitData is used and a command is used (ping), then
        # printing here will fail; the normal method works -- the data has already been massaged
        # by this point, so there's no need to do it again.
        (printData, overflowData) = limitSegregation(denaliVariables, printData, overflowData)

    # repurpose the "methodData" variable to contain the count of the
    # number of categories found, or "False" if none are found.
    if method == "count":
        count = len(printData)
        if count > 0:
            denaliVariables['methodData'] = len(printData)
        else:
            # MRASEREQ-40928
            # Using 'count' with 'json' output produces an error message:
            #   "The query returned with no information from the database."
            # It is possible 'prettyPrint' is called multiple times, with the first time being
            # successful (a correct count), and the second time not.  In this instance, the second
            # time overwrites the first and causes an error message -- unless this 'if' statement
            # is here.
            if denaliVariables['methodData'] == '':
                denaliVariables["methodData"] = False

    if method == "search" or method == "count" or method == "getAttributes" or method == "getSecrets":

        if PAD_DEBUG == True:
            num = 17
            for count in range(num):
                if count == 0:
                    print (' ' * 10) + str(count + 1),
                elif count < 10:
                    print (' ' * 8) + str(count + 1),
                else:
                    print (' ' * 7) + str(count + 1),

            print
            print "0123456789" * num

        for target in outputTarget:
            if "txt_" in target.type:
                if "file" in target.type:
                    if not target.append:
                        outFile = open(target.filename, 'w')      # open new file for writing
                    else:
                        # open existing file for appended writes.  This happens when CMDB sends
                        # back more than 1000 rows of data, and this code has to loop through
                        # the pages of data -- so, the file is appended to.
                        #   9/3/2015 -- CMDB now allows up to 5000 rows sent back.
                        outFile = open(target.filename, 'a')

                # print the headers if requested
                if headers == True and not target.append and len(printData) > 0:
                    if "screen" in target.type:
                        if denaliVariables["listToggle"] == False:
                            # only print the headers if the --list is not used (i.e., false)
                            printColumnHeaders(columnData)
                    if "file" in target.type:
                        # unicode not needed for the header
                        outFile.write('| ')
                        for column in columnData:
                            outFile.write('%s' % str(column[column_name_pos]).ljust(column[column_print_width] - 1) + '| ')

                        # new line
                        outFile.write('\n')
                        headerLine = '|'

                        for column in columnData:
                            headerLine += '%s' % ('=' * (column[column_print_width]) + '|')

                        outFile.write(headerLine)
                        outFile.write('\n')

                # make a copy of the overflow dictionary
                overflowDataCopy = copy.deepcopy(overflowData)

                # print formatted results to the screen
                for (row, printLine) in enumerate(printData):
                    printRow  = "  "    # leading spaces for the row indentation
                    overFlow  = False   # default setting for the state variable

                    # data for a list view -- if needed
                    printList = printLine

                    for (column, dataItem) in enumerate(printLine):

                        # Check for the existence of overflow data for this column
                        # on this specific row.
                        #
                        # If it exists:
                        #  (1) add column data from, the overflow dictionary for
                        #      the first set of data from this row to print.
                        #      --> pop(0) the data from the column(s)
                        #  (2) set a "state" variable identifying that this row
                        #      has overflow data to print (before the next row is
                        #      allowed to print
                        #
                        # If overflow data does not exist, add the data as normal.
                        #

                        if row in overflowDataCopy and column in overflowDataCopy[row]:

                            # set the state variable
                            overFlow = True

                            # add the overflowdata to the row to print, with a 3 space buffer
                            # to allow for the next column data to be properly aligned
                            printRow = printRow  + overflowDataCopy[row][column].pop(1) + "   "

                        else:
                            # normal data add
                            printRow = printRow  + dataItem + " "

                    # I found data in cmdb that is returned with a "\r\n" in it.
                    #       TeamDao: team_id = '12' -- the "description" for that team.
                    #                "TechOps SiteCatalyst SysEng\r\n"
                    # This code replaces a newline, return, or tab control character with a space
                    # to keep the column starting points lined up for the screen/file
                    printRow = printRow.replace('\t', " ")
                    printRow = printRow.replace('\r', " ")
                    printRow = printRow.replace('\n', " ")

                    # search for commas in the row -- replace with ' / '
                    #printRow = printRow.replace(',', ' / ')

                    #
                    # check the overflow state variable
                    # if set:
                    #   (1) turn off the overflow state variable
                    #   (2) print the rest of the overflow data for this row
                    #
                    # if not set, print data as normal and move to the next
                    # row for compilation of the column data
                    #

                    if overFlow == True and denaliVariables["listToggle"] == False:
                        # 'un'-set the state variable
                        overFlow = False

                        # print the over flow data
                        printOverflowData(denaliVariables, PAD_DEBUG, printRow, overflowDataCopy, row, target, outFile)

                    else:
                        if "screen" in target.type:
                            # see if the user requested the updateMethod(s)
                            if denaliVariables["updateMethod"] != '':
                                # verify that the print row has data before dereferencing it
                                if len(printRow.strip()) > 0:
                                    if printRow.strip()[0] == '=':
                                        # print the row green
                                        printRow = printRow.replace('=', ' ')
                                        print colors.bold + NO_CHANGES + printRow + colors.reset
                                    elif printRow.strip()[0] == '+':
                                        # print the row red
                                        printRow = printRow.replace('+', ' ')
                                        print colors.bold + CHANGES + printRow + colors.reset
                                    else:
                                        # normal print -- standard white
                                        print printRow.encode("UTF-8")
                                else:
                                    # normal print -- standard white
                                    print printRow.encode("UTF-8")
                            elif denaliVariables["monitoring"] == True and denaliVariables["nocolors"] == False:
                                monitorPrintRowColored(denaliVariables, printRow)
                            else:
                                # normal print -- standard white
                                if denaliVariables["listToggle"] == False:
                                    # default row-style of print (rows and columns)
                                    print printRow.encode("UTF-8")
                                else:
                                    # "list-style" of print
                                    # find the largest column header -- make all headers this length (plus padding)
                                    categoryLength = 0
                                    for column in columnData:
                                        if len(column[2]) > categoryLength:
                                            categoryLength = len(column[2])
                                    categoryLength += 2     # padding

                                    for (index, printListRow) in enumerate(printList):
                                        if columnData[index][2] == "Host Name":
                                            if denaliVariables["nocolors"] == False:
                                                category = colors.bold + HOSTNAME + columnData[index][2].ljust(categoryLength+2) + colors.reset
                                            else:
                                                category = columnData[index][2].ljust(categoryLength+2)
                                        else:
                                            if denaliVariables["nocolors"] == False:
                                                category = "  " + colors.bold + CATEGORY + columnData[index][2].ljust(categoryLength) + colors.reset
                                            else:
                                                category = "  " + columnData[index][2].ljust(categoryLength)

                                        # remove any funny characters
                                        printListRow = printListRow.strip()
                                        printListRow = printListRow.replace('\t', " ")
                                        printListRow = printListRow.replace('\r', " ")
                                        printListRow = printListRow.replace('\n', " ")

                                        print "  %s :: %s " % (category, printListRow.encode("UTF-8"))
                                    # line/space between each device/record
                                    print

                        if "file" in target.type:
                            output = u'%s\n' % printRow
                            outFile.write(output.encode("UTF-8"))
                            #outFile.write(printRow + '\n')

                if "file" in target.type:
                    outFile.close()

            elif "csv_" in target.type or "space_" in target.type or "newline_" in target.type or "comma_" in target.type:
                # only print something if it exists (including headers)
                if len(printData) != 0:
                    denali.outputGenericFormat(denaliVariables, printData, target, columnData, headers)

            elif "json_" in target.type:
                denali.outputJSONFormat(denaliVariables, queryDictionary, target)

            elif "update_" in target.type or "yaml_" in target.type:
                denali.outputYAMLFormat(denaliVariables, queryDictionary, target)

            else:
                # printing nothing ... nowhere
                pass

    denali_utility.addElapsedTimingData(denaliVariables, 'prettyPrintData_stop', time.time())



##############################################################################
#
# executeWebAPIQuery(denaliVariables, queryData)
#
#  This function executes the actual SQL-like query and obtains the returned
#  data in the form of a dictionary.
#
#  If the query fails, return "False" to the caller.
#

def executeWebAPIQuery(denaliVariables, queryData):

    if denaliVariables["debug"] == True:
        print "\n++Entered executeWebAPIQuery\n"

    api          = denaliVariables["api"]
    category     = denaliVariables["searchCategory"]
    method       = denaliVariables["method"]
    request_type = "Normal"

    if method == "getAttributes":
        parameterDictionary = {"devices"        : denaliVariables["serverList"],
                               "attribute_names": denaliVariables["attributeNames"]}

    elif method == "getCurrentOnCallInfo":
        if len(queryData) != 0:
            parameterDictionary = {"on_call_queue_list": queryData}
        else:
            parameterDictionary = {}

    elif method == "getSecrets":
        if denaliVariables["debug"] == True:
            print "device_key         : %s" % denaliVariables["serverList"][0]
            print "secret_store_key   : %s" % denaliVariables["getSecretsStore"]

        parameterDictionary = {"device_key"         : denaliVariables["serverList"][0],
                               "secret_store_key"   : denaliVariables["getSecretsStore"]}

        # assign the first host in serverList as the getSecretsHost
        denaliVariables["getSecretsHost"] = denaliVariables["serverList"][0]

    else:
        # Put the built query into dictionary format for the API to use
        parameterDictionary = {"query": queryData}

    if denaliVariables["debug"] == True:
        print
        print "api                : %s" % api
        print "category           : %s" % category
        print "method             : %s" % method
        print "parameterDictionary: %s" % parameterDictionary

    try:
        generic_time = time.time()
        denaliVariables["analyticsSTime"] = generic_time
        denaliVariables['time']['skms_start'].append(generic_time)
        ccode = api.send_request(category, method, parameterDictionary)

        if ccode == True:
            if method == "search" or method == "count":
                response_dict = api.get_response_dictionary()
            elif method == "getAttributes":
                response_dict = api.get_data_dictionary()
            elif method == "getCurrentOnCallInfo":
                response_dict = api.get_data_dictionary()
            else:
                response_dict = api.get_data_dictionary()
            denaliVariables['time']['skms_stop'].append(time.time())

            if denaliVariables["analytics"] == True:
                if "status" in response_dict and "data" in response_dict and "paging_info" in response_dict["data"]:
                    # item count returned in the current display page (each page will have a count; each is a separate DB query)
                    item_count = response_dict["data"]["paging_info"]["items_per_page"]
                    if item_count == denaliVariables["maxSKMSRowReturn"]:   # 5000 currently
                        # just in case ...
                        # count the rows manually because a wildcard will put '5000' in the items_per_page
                        if "results" in response_dict["data"]:
                            item_count = len(response_dict["data"]["results"])
                else:
                    item_count = 0

                elapsed_time = time.time() - denaliVariables["analyticsSTime"]
                retValue = denali_analytics.createProcessForAnalyticsData(denaliVariables, request_type, queryData, category, method, item_count, elapsed_time)
                denaliVariables["analyticsSTime"] = 0.00

            return response_dict
        else:
            denaliVariables['time']['skms_stop'].append(time.time())
            if denaliVariables["analytics"] == True:
                elapsed_time = time.time() - denaliVariables["analyticsSTime"]
                retValue = denali_analytics.createProcessForAnalyticsData(denaliVariables, request_type, queryData, category, method, 0, elapsed_time)
                denaliVariables["analyticsSTime"] = 0.00

            if denaliVariables['debug'] == True:
                print "\nSKMS ERROR:"
                print "   STATUS  : " + api.get_response_status()
                print "   TYPE    : " + str(api.get_error_type())
                print "   MESSAGE : " + api.get_error_message()

            return False
    except KeyError:
        print "Denali Error: Incorrect SKMS username and/or password entered."
        cleanUp(denaliVariables)
        exit(1)
    except:
        print "Problem accessing SKMS API."
        cleanUp(denaliVariables)
        exit(1)



##############################################################################
#
# executeSQLQuery(denaliVariables, sqlQuery, index, numOfQueries, outputDataFlag)
#

def executeSQLQuery(denaliVariables, sqlQuery, index, numOfQueries, outputDataFlag):

    if denaliVariables["debug"] == True:
        print "\n++Entered executeSQLQuery\n"

    subData     = ''
    next_page   = True
    page_number = 0
    commandSent = False

    for arg_parameter in denaliVariables["cliParameters"]:
        if arg_parameter[0] == "-c" or arg_parameter[0] == "--command":
            commandSent = True

    while next_page == True:
        page_number += 1

        # Set the file append mode for output files based on the page_number.
        # page_numbers >= 2 will set append mode to True.
        for item in denaliVariables['outputTarget']:
            if outputDataFlag == False:
                pass
            else:
                item.append = page_number > 1

        responseDictionary = executeWebAPIQuery(denaliVariables, sqlQuery)

        #print "rd = %s" % responseDictionary
        # custom module requested the dictionary data to be returned
        # typically for manipulation before printing
        # History and Batch mode use this
        if outputDataFlag == False:
            return (responseDictionary, False)

        if denaliVariables["debug"] == True:
            print "\nresponseDictionary = %s" % responseDictionary

        if responseDictionary != False:
            method = denaliVariables["method"]
            if method == "search":
                # check the item count -- need another page?
                (pageInfo, item_count) = checkItemCount(denaliVariables, responseDictionary)
            elif method == "count" or method == "getAttributes":
                pageInfo = False
                item_count = "count"
            elif method == "getSecrets":
                pageInfo = False
                (pageInfo, item_count) = checkItemCount(denaliVariables, responseDictionary)

                # insert the host name used for the query in the responseDictionary
                responseDictionary.update({"hostname":denaliVariables["getSecretsHost"]})

            if (index + 1) == numOfQueries:
                # if jira was queried -- remove all "Closed" tickets (added jira_closed for MRASEREQ-40937)
                if denaliVariables["fields"].find("jira_issue") != -1 and denaliVariables["jira_closed"] == False:
                    responseDictionary = denali_utility.removeClosedJIRA(denaliVariables, responseDictionary)

                (printData, overflowData) = generateOutputData(responseDictionary, denaliVariables)
                if printData == False:
                    # problem creating printData -- error message should already have been
                    # printed in context with the problem.  Just exit here.
                    return (False, False)

                # Be careful here -- this is the main printing routing being controlled by a "command" variable
                # setting.  If this is incorrectly done, nothing will print.
                #
                # If a "-c" or "--command" was submitted (the "commandSent" check just above), then also check
                # and see if the user requested combined data (--combine) or not.
                # If False, then print only the command information.
                # If True, then combine the command information with CMDB search data.
                if commandSent == False:
                    # normal path for outputting data
                    if denaliVariables["monitoring"] == False:
                        prettyPrintData(printData, overflowData, responseDictionary, denaliVariables)
                    else:
                        # pull out the host names and put them in denaliVariables["serverList"]
                        if denaliVariables["debug"] == True:
                            print "Monitoring debug:  repopulate serverList after search"
                        denali_utility.repopulateHostList(denaliVariables, printData, responseDictionary)
                else:
                    # command request submitted
                    denali_utility.repopulateHostList(denaliVariables, printData, responseDictionary)

                '''
                if (commandSent == True and denaliVariables["combine"] == True) or (commandSent == False):
                    # output the information
                    (printData, overflowData) = generateOutputData(responseDictionary, denaliVariables)
                    if printData == False:
                        # problem creating printData -- error message should already have been
                        # printed in context with the problem.  Just exit here.
                        return (False, False)
                    if denaliVariables["monitoring"] == False:
                        prettyPrintData(printData, overflowData, responseDictionary, denaliVariables)
                    else:
                        # pull out the host names and put them in denaliVariables["serverList"]
                        if denaliVariables["debug"] == True:
                            print "Monitoring debug:  repopulate serverList after search"
                        denali_utility.repopulateHostList(denaliVariables, printData)
                '''

            else:
                # sub-query data handling
                # don't print sub-query data
                # just gather the data for later use
                subData = gatherSearchedData(responseDictionary, denaliVariables)

            # clean up the data --- remove 'nones' (return as a dictionary)
            responseDictionary = clearUpNones(responseDictionary)

            if pageInfo != False:      # new pages to query for
                sqlQuery = modifyQueryPageSetting(sqlQuery, pageInfo)

                # if json activated for output type -- otherwise, don't store the data
                for target in denaliVariables["outputTarget"]:
                    if target.type.startswith("json"):
                        if not denaliVariables["jsonResponseDict"]:
                            denaliVariables["jsonResponseDict"]["results"] = responseDictionary["data"]["results"]
                        else:
                            denaliVariables["jsonResponseDict"]["results"].extend(responseDictionary["data"]["results"])
                        break
            else:
                next_page = False

                # output the information
                for target in denaliVariables["outputTarget"]:
                    if target.type.startswith("json"):
                        # Retrieve and output the last page of json data if it exists from the "last" query
                        if not denaliVariables["jsonResponseDict"]:
                            responseDictionary = responseDictionary["data"]
                        else:
                            denaliVariables["jsonResponseDict"]["results"].extend(responseDictionary["data"]["results"])
                            responseDictionary = denaliVariables["jsonResponseDict"]
                        denaliVariables["jsonPageOutput"] = True

                        (printData, overflowData) = generateOutputData(responseDictionary, denaliVariables)
                        if printData == False:
                            # problem creating printData -- error message should already have been
                            # printed in context with the problem.  Just exit here.
                            return (False, False)
                        prettyPrintData(printData, overflowData, responseDictionary, denaliVariables)
                        break

        else:
            next_page = False
            return False, False

    return (subData, item_count)



##############################################################################
#
# removeStartEndCharacter(string, character)
#

def removeStartEndCharacter(string, character):

    if string[0] == character:
        string = string[1:]

    if string[-1] == character:
        string = string[:-1]

    return string



##############################################################################
#
# modifyQueryPageSetting(sqlQuery, pageInfo):
#

def modifyQueryPageSetting(sqlQuery, pageInfo):

    sqlQuery = sqlQuery[:(sqlQuery.find("PAGE") - 1)]
    sqlQuery = sqlQuery + pageInfo

    return sqlQuery



##############################################################################
#
# checkItemCount(denaliVariables, response):
#

def checkItemCount(denaliVariables, response):

    # default setting
    item_count = 0

    if ('status' in response and 'data' in response and 'results' in response['data']):

        # final page in this list
        last_page      = response['data']['paging_info']['last_page']

        # current page with data gathered
        current_page   = response['data']['paging_info']['current_page']

        # items generated/displayed on this page
        items_per_page = response['data']['paging_info']['items_per_page']

        # total number of items in the overall query
        item_count     = response['data']['paging_info']['item_count']

        #print "last_page      = %d" % last_page
        #print "current_page   = %d" % current_page
        #print "items_per_page = %d" % items_per_page
        #print "item_count     = %d" % item_count

        if current_page > last_page:    # why would this happen?
            return (False, item_count)


        # determine what the settings for a new page are
        if current_page < last_page:
            if denaliVariables["limitCount"] != 0:
                # determine if the limitCount has been reached
                # if so, stop the output
                if (items_per_page * current_page) >= denaliVariables["limitCount"]:
                    return (False, item_count)

            current_page += 1
            PAGE = " PAGE %d, %d" % (current_page, items_per_page)
            return (PAGE, item_count)
        else:
            return (False, item_count)
    else:
        return (False, item_count)



##############################################################################
#
# findMatchingParenthesis(sqlQuery)
#

def findMatchingParenthesis(sqlQuery):

    openList  = []
    closeList = []
    parenList = []

    # print out all matching sets of parenthesis in this string
    for (index, character) in enumerate(sqlQuery):
        if character == '(':
            openList.append(index)
        if character == ')':
            closeList.append(index)

    # If we grabbed too many parenthesis -- give them back
    if len(closeList) > len(openList):
        closeParenNumber = len(closeList) - len(openList)
    else:
        closeParenNumber = 0

    #print "Input String     = %s" % sqlQuery
    #print "Open Paren List  = %s" % openList
    #print "Close Paren List = %s" % closeList


    while openList:
        for (oIndex, openP) in enumerate(openList):
            if openP < closeList[0] and sqlQuery[(openP + 1)] == '|':
                #match = openP
                index = oIndex

        #print "found a match: %d(@%d) : %d " % (openList[index], index, closeList[0])
        parenList.append([openList[index],(closeList[0] + 1)])
        openList.pop(index)
        closeList.pop(0)

    #print "Matched Paren List = %s" % parenList

    #for (count, pair) in enumerate(parenList):
    #    print "#%d = %s" % (count, sqlQuery[pair[0]:(pair[1] + 1)])


    return (parenList, closeParenNumber)



##############################################################################
#
# separateSQLQueries(sqlQuery)
#

def separateSQLQueries(sqlQuery, denaliVariables):

    daoList    = []
    sqlQueries = []

    if denaliVariables["debug"] == True:
        print "\n++Entered separateSQLQueries\n"

    # separate the Dao from the query
    count = sqlQuery.count(':')

    # separate out the Daos from the query
    for dao in range(count):

        location = sqlQuery.find(':')

        if sqlQuery[(location - 3):location].lower() == 'dao':
            if (location - 35) <= 0:
                subString = sqlQuery[:(location + 1)].strip()
                sqlQuery = sqlQuery.replace(':', '|', 1)
                sqlQuery = sqlQuery.replace(subString[:-1], '', 1)

            else:
                subString = sqlQuery[(location - 35):(location + 1)]
                subString = subString[(subString.find('(') + 1):]
                sqlQuery = sqlQuery.replace(':', '|', 1)
                sqlQuery = sqlQuery.replace(subString[:-1], '', 1)

            daoList.append(subString[:-1])

    #print
    #print "Beginning SQL Query = %s" % sqlQuery
    #print

    # separate out the sql queries (delimited with '|')
    for sql in range(count):

        # MRASETEAM-41020
        if denaliVariables['debug'] == True:
            # separate out the queries by parenthesis
            if sqlQuery.count('(') != sqlQuery.count(')'):
                # Got caught here when an on-call group included an opening parenthesis, but not
                # a closing one.  The text was valid, but stopped the search because this check
                # only counted all parentheses combinations (whether or not they were included
                # inside of quotations is not a factor here).  Because of this, the text with a
                # missing parenthesis caused the above equality to be NOT EQUAL, and the below
                # messages to print.  Ug.  This specific check is now moved behind the global
                # 'debug' variable -- to ensure it doesn't interfere again.
                #
                # Commit 8010523 2015-07-07 Update denali code push -- 3rd overall commit to Denali
                #
                # This was written initially to catch syntax errors that the code would create
                # for a search query.  I haven't seen this specific check fire for a legitimate
                # reason in well over a year.  I believe it safe to put behind the 'debug' variable.
                print "Denali: Possible syntax error - Opening and closing parenthesis do not match."
                print "        There are %d opening and %d closing." % (sqlQuery.count('('), sqlQuery.count(')'))
                cleanUp(denaliVariables)
                exit(1)

        selectLocation = sqlQuery.rfind("|SELECT")

        if selectLocation == 0:                 # there's only one query left
            sqlQueries.append(sqlQuery[1:])     # append it to the List (minus the '|')

        else:                                   # nested sub-queries in the string
            if sqlQuery[(selectLocation - 1)] != '(':
                # now what?
                print "Embedded SQL query SELECT statement is not enclosed within parenthesis."
                print "Stopping code execution."
                cleanUp(denaliVariables)
                exit(1)

            # Normal code-path for separating the queries

            # grab the opening parenthesis with the marker
            #selectLocation -= 1


            # This code statement (the next one listed) pulls all of the characters from the
            # parenthesis marker to the end of the string -- this is not always how a query
            # statement will be put together.  It may have remnants from another query
            # behind this string segment that have nothing to do with the segment being
            # pulled; however, for now we'll assume this "easy" type of sql statement is
            # entered, and handle the more difficult case if/when it appears.
            subQuery = sqlQuery[selectLocation-1:]

            #print "sub-query = %s" % subQuery

            # append the sub-query to the List for later use
            if subQuery[-1] == ')':
                sqlQueries.append(subQuery[2:-1])  # 2 = remove "(|"  -1 = remove ")"
            else:
                # remove excess, and attach to outer query
                loc = subQuery.rfind(')')
                #extraQueryStatement = subQuery[(loc + 1):]
                subQuery = subQuery[:(loc + 1)]
                sqlQueries.append(subQuery[2:-1])

            (parenList, closeNumber) = findMatchingParenthesis(subQuery)

            if closeNumber > 0:
                # string to represent
                parClose = (')' * closeNumber)
            else:
                parClose = ''

            # remove the "SELECT" string from the main query string
            sqlQuery = sqlQuery.replace(subQuery[:],'([#])') + parClose

            #print "subQuery = %s" % subQuery
            #print "sqlQuery = %s" % sqlQuery

            #for (index, pair) in enumerate(parenList):
            #    print "#%d :: %s" % (index, subQuery[pair[0]:pair[1]])

    # the inner-most query should be run first, followed by the next inner-most
    # and so on until the final outer-most query.  The compiled Lists are in
    # reverse order from how they should be run, so reverse both of them.
    daoList.reverse()
    #sqlQueries.reverse()

    subQueries = []
    for (index, query) in enumerate(daoList):
        subQueries.append([query, sqlQueries[index]])

    return subQueries



##############################################################################
#
# clearUpNones(r_dictionary)
#

def clearUpNones(r_dictionary):
    # change the dictionary to a string
    stringEdit = str(r_dictionary)
    stringEdit = stringEdit.replace("None", "\"None\"")

    # change the string back to a dictionary (json object)
    jsonObject = ast.literal_eval(stringEdit)

    return jsonObject



##############################################################################
#
# constructSQLQuery(denaliVariables, sqlQuery, outputDataFlag)
#

def constructSQLQuery(denaliVariables, sqlQuery, outputDataFlag):

    if denaliVariables["debug"] == True:
        print "\n++Entered constructSQLQuery\n"

    # remove any ", " or " , " entries in the query and replace with ","
    sqlQuery = sqlQuery.replace(', ', ',')
    sqlQuery = sqlQuery.replace(' , ', ',')

    subQueries = separateSQLQueries(sqlQuery, denaliVariables)

    # At this point the queries should be properly separated and in one List.
    # Loop through all of them collecting results and pass them on to the next
    # query in the List -- along the way building the SQL query "properly",
    # I hope.

    subData = ''

    for (index, query) in enumerate(subQueries):

        numOfQueries = len(subQueries)

        # pull out the dao first
        denaliVariables["searchCategory"] = query[0]
        sqlQuery = query[1]

        findSELECT = sqlQuery.find("SELECT")
        findWHERE  = sqlQuery.find("WHERE")
        where  = sqlQuery[findWHERE:].strip()
        denaliVariables["fields"] = sqlQuery[(findSELECT + 7):(findWHERE - 1)].strip()

        (modFields, denaliVariables["columnData"]) = determineColumnOrder(denaliVariables)

        sqlQuery = "SELECT " + modFields + " " + where

        if "[#]" in sqlQuery:
            sqlQuery = sqlQuery.replace("[#]", subData)

        # Add a PAGE itentifier at the end, if needed
        if "PAGE" not in sqlQuery:
            PAGE = " PAGE 1, %d" % denaliVariables["maxSKMSRowReturn"]
            sqlQuery += PAGE

        (subData, itemCount) = executeSQLQuery(denaliVariables, sqlQuery, index, numOfQueries, outputDataFlag)

        # outputData is default True -- meaning all data returned from the query is output to the
        # defined targets.  If set to False, that means a dynamic module called this function and
        # has requested the output to be returned to the function, instead of pushed to the screen
        # or a file format.
        if outputDataFlag == False:
            return subData

    if denaliVariables["summary"] == True:
        print
        print " Total Items Displayed: %d" % itemCount

    if denaliVariables["showsql"] == True:
        denali_utility.showSQLQuery(sqlQuery, denaliVariables)



##############################################################################
#
# buildSqlParmQuery(denaliVariables)
#
#   This function builds the SQL sent into SKMS for the query.
#

def buildSqlParmQuery(denaliVariables):

    sqlParmQuery = ''
    conjunctions = []
    historySQL   = []
    daoDateData  = {}       # MRASEREQ-41538

    if denaliVariables["debug"] == True:
        print "\n++Entered buildSqlParmQuery\n"

    #print "current sql parameters = %s" % denaliVariables["sqlParameters"]

    if denaliVariables["method"] == "getAttributes":
        attribute_names        = ''
        attribute_values       = ''
        attribute_inheritances = ''
        attr_store             = ''
        for parameterSet in denaliVariables["sqlParameters"]:
            # identify the parameter to write into
            parameter = parameterSet[0]
            value     = parameterSet[1]

            for parameter in parameterSet:
                if parameter   == "attribute_name":
                    attr_store = "attribute_name"
                elif parameter == "attribute_value":
                    attr_store = "attribute_value"
                elif parameter == "attribute_inheritance":
                    attr_store = "attribute_inheritance"
                else:
                    # store the value for the parameter(s)
                    if attr_store == "attribute_name":
                        if attribute_names == '':
                            attribute_names = parameter
                        else:
                            attribute_names = ',' + parameter
                    elif attr_store == "attribute_value":
                        if attribute_values == '':
                            attribute_values = parameter
                        else:
                            attribute_values = ',' +  parameter
                    elif attr_store == "attribute_inheritance":
                        if attribute_inheritances == '':
                            attribute_inheritances = parameter
                        else:
                            attribute_inheritances = ',' + parameter

        denaliVariables["attributeNames"] = attribute_names.split(',')
        sqlParmQuery = ''
        return sqlParmQuery

    # MRASEREQ-41538:  work out any DAO date ranges before the main loop
    dao_date_ranges = ['maintenance_window.start_date']
    for parameter in denaliVariables['sqlParameters']:
        # Check for DAO start date with 'day', 'week', 'month', or 'year' in it -- translate appropriately
        if parameter[0] in dao_date_ranges:
            if len(daoDateData) == 0:
                # save parameter[0], because the 'for' loop will advance and that will cause the substitution
                # in the daoTimeMethodMassage function to completely mess up.
                daoDateData.update({'date1':parameter[1],'parm0':parameter[0]})
            else:
                daoDateData.update({'date2':parameter[1]})

    # MRASEREQ-41538
    if len(daoDateData):
        # date_element is used by the historydao, but probably not here ...
        (ccode, date_element) = denali_utility.daoTimeMethodMassage(denaliVariables, daoDateData, daoDateData['parm0'])
        if ccode == False:
            return False

    for parameter in denaliVariables["sqlParameters"]:

        # first check if this is a history sql parameter.
        # if so, ciphon it off and work on the rest
        if parameter[0].startswith("hist_"):
            # remove the "hist_" identifier
            historySQL.append([parameter[0][5:],parameter[1]])
            continue

        # Feature request:  If the sql parameter is the MAC Address, then automatically
        # remove all colons and periods from the search field.  With the colons or periods
        # included SKMS will not return any matches; without them, it returns the correct
        # matches -- this is just a simplification/helper piece of code.
        if parameter[0].startswith("mac_addr"):
            parameter[1] = parameter[1].replace(":", "")
            parameter[1] = parameter[1].replace(".", "")

        # Check for AND:, OR:, NOT: tags at the beginning of the statement.
        # Inclusion of these indicate the relationship with a previous sql
        # statement.  This follow-on statement will be "and-ed", "or-ed",
        # or "AND with !=" to it.

        eqOperator = " ="
        tie_word   = "AND"

        # Cannot assume the first colon in the statement is preceded by AND, OR, or NOT
        if ':' in parameter[1]:
            tie_word = parameter[1][:parameter[1].find(':')]
            if tie_word.lower() == 'and' or tie_word.lower() == 'or' or tie_word.lower() == 'not':
                parameter[1] = parameter[1][(parameter[1].find(':') + 1):]

                if tie_word != "NOT" and tie_word != "AND" and tie_word != "OR":
                    sqlParmQuery += ' ' + "AND" + " ("

                elif tie_word == "NOT":
                    sqlParmQuery += ' ' + "AND" + " ("
                    eqOperator = " !="

                else:
                    sqlParmQuery += ' ' + tie_word + " ("
            else:
                # Reset the tie word -- there's a colon in the search statement without
                # 'and', 'or', or 'not' immediately preceding.
                tie_word = "AND"
                sqlParmQuery += ' ' + tie_word + " ("
        else:
            sqlParmQuery += ' ' + tie_word + " ("

        # count up the logical operators
        andCount  = parameter[1].count(" AND ")
        andCount += parameter[1].count(" and ")
        orCount   = parameter[1].count(" OR ")
        orCount  += parameter[1].count(" or ")
        notCount  = parameter[1].count(" NOT ")
        notCount += parameter[1].count(" not ")

        if '*' in parameter[1] or '%' in parameter[1] or '?' in parameter[1] or '_' in parameter[1]:
            parameter[1] = parameter[1].replace('*', '%')
            parameter[1] = parameter[1].replace('?', '_')

            if tie_word == "NOT":
                eqOperator = " NOT LIKE"
            else:
                eqOperator = " LIKE"

        # Typically used for date search/narrowing
        #   the >= / <= feel "hacky".  Because the text separates on the equal
        #   sign, the '-' was used as a substitute
        #   Example:  --hist_datetime=">2014-01"  <-- all dates > Jan 2014
        #                                             this includes Jan 1 2014
        if parameter[1].startswith(">-"):
            eqOperator = " >="
            parameter[1] = parameter[1][2:]
        elif parameter[1].startswith("<-"):
            eqOperator = " <="
            parameter[1] = parameter[1][2:]
        elif len(parameter[1]) > 0 and parameter[1][0] == '>':
            eqOperator = " >"
            parameter[1] = parameter[1][1:]
        elif len(parameter[1]) > 0 and parameter[1][0] == '<':
            eqOperator = " <"
            parameter[1] = parameter[1][1:]

        if andCount > 0:
            parameter[1] = parameter[1].replace(" AND ", "','")
            wildList    = parameter[1].split(',')

            inOperation  = ''
            andOperation = ''
            inOp         = False
            andOp        = False

            for statement in wildList:
                # remove all single quotes -- I'll add them later
                statement = statement.replace("'", "")
                if '%' in statement or '_' in statement:
                    if tie_word == "NOT":
                        eqOperator = "NOT LIKE"
                    else:
                        eqOperator = "LIKE"

                    if andOperation == "":
                        andOperation = "%s '%s'" % (eqOperator, statement)
                    else:
                        andOperation += " AND %s %s '%s'" % (parameter[0], eqOperator, statement)

                    eqOperator = ""
                    andOp = True
                else:
                    if tie_word == "NOT":
                        eqOperator = " !="
                    else:
                        eqOperator = "="

                    if inOperation == "":
                        inOperation = "%s '%s'" % (eqOperator, statement)
                    else:
                        inOperation += " AND %s %s '%s'" % (parameter[0], eqOperator, statement)

                    eqOperator = ""
                    inOp = True

            # Alphabetical choice: The "IN" operation comes before the "OR" operation
            if inOp == True and andOp == True:
                parameter[1] = inOperation + (" AND %s " % parameter[0]) + andOperation

            elif inOp == True and andOp == False:
                parameter[1] = inOperation

            elif inOp == False and andOp == True:
                parameter[1] = andOperation

        if orCount > 0:
            # All OR statements will be converted to "IN" operations
            # unless they have a wildcard, in which case they will
            # be put in a "LIKE" operation.
            parameter[1] = parameter[1].replace(" OR ", "','")

            wildList    = parameter[1].split(',')
            inOperation = ''
            orOperation = ''
            inOp        = False
            orOp        = False

            for statement in wildList:
                # remove all single quotes -- I'll add them later
                statement = statement.replace("'", "")
                if '%' in statement or '_' in statement:
                    if tie_word == "NOT":
                        eqOperator = "NOT LIKE"
                    else:
                        eqOperator = "LIKE"

                    if orOperation == "":
                        orOperation = "%s '%s'" % (eqOperator, statement)
                    else:
                        orOperation += " OR %s %s '%s'" % (parameter[0], eqOperator, statement)
                    orOp = True
                else:
                    if inOperation == "":
                        inOperation = "'" + statement + "'"
                    else:
                        inOperation += ",'" + statement + "'"
                    inOp = True

            # fix the inOperation string for use
            if inOp == True:
                inOperation = '(' + inOperation + ')'

            # Alphabetical choice: The "IN" operation comes before the "OR" operation
            if inOp == True and orOp == True:
                parameter[1] = inOperation + (" OR %s " % parameter[0]) + orOperation
                if tie_word == "NOT":
                    eqOperator = " NOT IN"
                else:
                    eqOperator = " IN"

            elif inOp == True and orOp == False:
                parameter[1] = inOperation
                if tie_word == "NOT":
                    eqOperator = " NOT IN"
                else:
                    eqOperator = " IN"

            elif inOp == False and orOp == True:
                parameter[1] = orOperation
                eqOperator = ''

        if notCount == 1:
            for index in range(notCount):
                conjunctions.append(parameter[1].find(" NOT "))
                parameter[1] = parameter[1].replace(" NOT ", "' AND %s %s" % (parameter[0], eqOperator + '\''), 1)

        if orCount == 0 and andCount == 0 and notCount == 0:
            parameter[1] = "'" + parameter[1] + "'"

        # add the "WHERE" criteria to the query string
        sqlParmQuery += "%s%s %s)" % (parameter[0], eqOperator, parameter[1])

    # Prior code did a 'replace' on all '( and )' to be make sure the quotation mark was on
    # the inside of the parenthesis.  At the time it was written, it served as a catch-all
    # at the end of the function to make sure the sql parameter query was properly formatted;
    # which would prevent weird bugs from happening in the function.
    #
    # That "replace" code has been removed because it caused a problem with device services
    # ending with a parenthesis.  Because the removed code has been around for a few years
    # without modification, sufficient testing to make sure it doesn't introduce a new issue
    # or two is unlikely to happen.  So ... the new code will print a message on the screen
    # whenever one of the cases that the prior code would have automatically fixed is found.
    # The hope is that with this it can help illuminate the edge-cases for this type of code
    # to be used, and thus perhaps included again -- with certain coditions of execution.
    #
    # This code was committed with the very first commit for this function definition, and
    # hasn't been modified since ... until now.  Commit 80105235
    #
    ##### make sure the single quotes are _inside_ of the parenthesis
    #####   sqlParmQuery = sqlParmQuery.replace("'(", "('")
    #####   sqlParmQuery = sqlParmQuery.replace(")'", "')")

    if len(historySQL) > 0:
        denaliVariables["historySQLQuery"] = historySQL

    #print "modified sql parameters = %s" % denaliVariables["sqlParameters"]

    return (sqlParmQuery)



##############################################################################
#
# buildGenericQuery(denaliVariables, whereQuery)
#

def buildGenericQuery(denaliVariables, whereQuery='name'):

    if denaliVariables["debug"] == True:
        print "\n++Entered buildGenericQuery\n"

    if denaliVariables['searchCategory'] == 'DeviceGroupDao':
        queryList = denaliVariables['groupList']
    else:
        queryList = denaliVariables["serverList"]

    SQLSEARCHMODS = denaliVariables["sqlParameters"]

    # get the sort information
    ORDER_BY = denaliVariables["sqlSort"]

    # sometimes the search modifications are not filled out (if called from a dynamic module)
    # fix it so it doesn't cause everything else to halt processing.
    if len(SQLSEARCHMODS) == 0:
        SQLSEARCHMODS = ''

    (modifiedFields, denaliVariables["columnData"]) = determineColumnOrder(denaliVariables)

    # build the sql-like query parameters
    SELECT = "SELECT "

    if denaliVariables["fields"] != '':
        SELECT += modifiedFields

    LIKE     = "LIKE "
    IN       = "IN ("

    if whereQuery == 'name' and denaliVariables["searchCategory"] == "DeviceDao":
        DEFAULTS = " AND device_state.full_name != 'Decommissioned'"
    else:
        DEFAULTS = ''

    if len(queryList) > 0:
        for item in queryList:
            # MRASETEAM-41020
            #if '*' in item or '?' in item or '_' in item or '%' in item:
            # Removed '_' as a wildcard character (used in SQL) as there are database items that
            # use it in their text -- forcing a LIKE statement where an IN should be used.
            if '*' in item or '?' in item or '%' in item:
                wildcard = True
                WHERE = " WHERE (%s " % whereQuery
                break
            else:
                wildcard = False
                WHERE = " WHERE %s " % whereQuery

        for item in queryList:
            if wildcard == True:
                # the LIKE method for querying must be used to accomodate wildcard searching
                item = item.replace('*', '%')
                item = item.replace('?', '_')

                LIKE += "'%s' OR %s LIKE " % (item, whereQuery)

            else:
                # normal (non-wildcard) name query
                IN += "'%s'," % item

        if wildcard == True:
            # Remove the " or name LIKE " string from the end of the constructed query
            string = " OR %s LIKE " % whereQuery
            remove = len(string)
            LIKE = LIKE[:-remove]

            if denaliVariables["limitCount"] == 0:
                PAGE = " PAGE 1, %d" % denaliVariables["maxSKMSRowReturn"]
            else:
                if denaliVariables["limitCount"] <= denaliVariables["maxSKMSRowReturn"]:
                    PAGE = " PAGE 1, %d" % denaliVariables["limitCount"]
                else:
                    PAGE = " PAGE 1, %d" % denaliVariables["maxSKMSRowReturn"]

            if denaliVariables["defaults"] == True:
                if denaliVariables["debug"] == True:
                    print "SELECT   = %s" % SELECT
                    print "WHERE    = %s" % WHERE
                    print "LIKE     = %s" % LIKE
                    print "DEFAULTS = %s" % DEFAULTS
                    print "SQLMODS  = %s" % SQLSEARCHMODS
                    print "ORDER_BY = %s" % ORDER_BY
                    print "PAGE     = %s" % PAGE
                query = SELECT + WHERE + LIKE + ')' + DEFAULTS + SQLSEARCHMODS + ORDER_BY + PAGE
            else:
                if denaliVariables["debug"] == True:
                    print "SELECT   = %s" % SELECT
                    print "WHERE    = %s" % WHERE
                    print "LIKE     = %s" % LIKE
                    print "SQLMODS  = %s" % SQLSEARCHMODS
                    print "ORDER_BY = %s" % ORDER_BY
                    print "PAGE     = %s" % PAGE
                query = SELECT + WHERE + LIKE + ')' + SQLSEARCHMODS + ORDER_BY + PAGE
        else:
            IN = IN[:-1] + ')'
            PAGE = " PAGE 1, %d" % len(queryList)

            if denaliVariables["defaults"] == True:
                if denaliVariables["debug"] == True:
                    print "SELECT   = %s" % SELECT
                    print "WHERE    = %s" % WHERE
                    print "IN       = %s" % IN
                    print "DEFAULTS = %s" % DEFAULTS
                    print "SQLMODS  = %s" % SQLSEARCHMODS
                    print "ORDER_BY = %s" % ORDER_BY
                    print "PAGE     = %s" % PAGE
                query = SELECT + WHERE + IN + DEFAULTS + SQLSEARCHMODS + ORDER_BY + PAGE
            else:
                if denaliVariables["debug"] == True:
                    print "SELECT   = %s" % SELECT
                    print "WHERE    = %s" % WHERE
                    print "IN       = %s" % IN
                    print "SQLMODS  = %s" % SQLSEARCHMODS
                    print "ORDER_BY = %s" % ORDER_BY
                    print "PAGE     = %s" % PAGE
                query = SELECT + WHERE + IN + SQLSEARCHMODS + ORDER_BY + PAGE
    else:
        # there is no server list -- probably a non "DeviceDao" request
        if SQLSEARCHMODS != '':
            WHERE = SQLSEARCHMODS.replace(" AND", " WHERE", 1)

            if denaliVariables["limitCount"] == 0:
                PAGE = " PAGE 1, %d" % denaliVariables["maxSKMSRowReturn"]
            else:
                if denaliVariables["limitCount"] <= denaliVariables["maxSKMSRowReturn"]:
                    PAGE = " PAGE 1, %d" % denaliVariables["limitCount"]
                else:
                    PAGE = " PAGE 1, %d" % denaliVariables["maxSKMSRowReturn"]

            if denaliVariables["defaults"] == True:
                query = SELECT + WHERE + DEFAULTS + ORDER_BY + PAGE
            else:
                query = SELECT + WHERE + ORDER_BY + PAGE
        else:
            field_to_show = denaliVariables["fields"].split(',')[0]
            if len(field_to_show) <= 2 or field_to_show == '':
                field_to_show = "name"
            print "Denali Syntax Error:  Execution must stop"
            print "  Searching parameters are not specific enough to conduct a search."
            print "  A \"WHERE\" clause cannot be found."
            print "  Example of what is needed:  --%s=\"*<search_criteria>*\"" % field_to_show
            print "  Submit the query again."
            print
            return (False, False)

        wildcard = False

    return (query, wildcard)



##############################################################################
#
# buildHostQuery(denaliVariables)
#

def buildHostQuery(denaliVariables):

    if denaliVariables["debug"] == True:
        print "\n++Entered buildHostQuery\n"

    serverList    = denaliVariables["serverList"]
    SQLSEARCHMODS = denaliVariables["sqlParameters"]

    # set the default state -- so a walk through the host list
    # change this to true (if there is a wildcard-ed host).
    wildcard = False

    # sometimes the search modifications are not filled out (if called from a dynamic module)
    # fix it so it doesn't cause everything else to halt processing.
    if len(SQLSEARCHMODS) == 0:
        SQLSEARCHMODS = ''

    (modifiedFields, denaliVariables["columnData"]) = determineColumnOrder(denaliVariables)
    denaliVariables["fields"] = modifiedFields

    # build the sql-like query parameters
    SELECT = "SELECT "

    # default setting (to stop python problems with empty search return)
    WHERE  = "WHERE "

    if denaliVariables["fields"] != '':
        SELECT += modifiedFields

    if denaliVariables["method"] == "count":
        countData = denaliVariables["methodData"]

        # divide the data into the column to count and GROUP BY(s)
        loc = countData.find(':')
        if loc == -1:
            # no GROUP BY statement(s)
            countColumn = countData                 # COUNT(countColumn)
            groupBY     = ''                        # GROUP BY is empty
        else:
            countColumn = countData[:loc]           # COUNT(countColumn)
            groupBY     = countData[(loc + 1):]     # GROUP BY takes the rest (minus the ':')
                                                    # This can have multiple columns; for instance,
                                                    #    GROUP BY device_service,device_state

        # Use the "count(%s) AS %s" syntax; otherwise the column header is entitled "cnt",
        # and this messes up the printing because it won't be found
        #COUNT    = "COUNT(%s)"   % countColumn
        COUNT    = "COUNT(%s) AS %s"   % (countColumn, countColumn)
        GROUP_BY = " GROUP BY %s"      % groupBY

        # replace the existing countColumn with this one
        #  step 1: count how many there are.
        number = SELECT.count(countColumn)

        #  step 2: if >= 1, then pick the best match and replace it
        if number >= 1:
            # potential multiple choices for the count column are found in the SELECT statement.
            # pick the "one" that is isolated.

            # copy the string (remove the "SELECT" phrase)
            copySELECT = SELECT[7:]
            copySELECT = copySELECT.split(',')

            for (index, column) in enumerate(copySELECT):
                if countColumn == column:
                    copySELECT[index] = COUNT

                    SELECT = "SELECT "
                    for field in copySELECT:
                        SELECT += field + ","
                        SELECT = SELECT[:-1]
            else:
                SELECT += ',' + COUNT

        else:
            # The "counted" column wasn't entered with --fields as an option
            # Put it in at the end of the fields parameter.
            SELECT += ',' + COUNT

    else:
        # make it empty if there is nothing to input here
        GROUP_BY = ''

    LIKE     = "LIKE "
    IN       = "IN ("
    DEFAULTS = " AND device_state.full_name != 'Decommissioned'"

    for server in serverList:
        # MRASETEAM-41020
        #if '*' in server or '?' in server or '_' in server or '%' in server:
        if '*' in server or '?' in server or '%' in server:
            wildcard = True
            WHERE = " WHERE (name "
            break
        else:
            wildcard = False
            WHERE = " WHERE name "

    for server in serverList:
        if wildcard == True:
            # the LIKE method for querying must be used to accomodate wildcard searching
            server = server.replace('*', '%')
            server = server.replace('?', '_')

            LIKE += "'%s' OR name LIKE " % server

        else:
            # normal (non-wildcard) name query
            IN += "'%s'," % server

    # get the sort information
    ORDER_BY = denaliVariables["sqlSort"]

    if wildcard == True:
        # Remove the " or name LIKE " string from the end of the constructed query
        remove = len(" OR name LIKE ")
        LIKE = LIKE[:-remove]

        if denaliVariables["limitCount"] == 0:
            PAGE = " PAGE 1, %d" % denaliVariables["maxSKMSRowReturn"]
        else:
            if denaliVariables["limitCount"] <= denaliVariables["maxSKMSRowReturn"]:
                PAGE = " PAGE 1, %d" % denaliVariables["limitCount"]
            else:
                PAGE = " PAGE 1, %d" % denaliVariables["maxSKMSRowReturn"]

        if denaliVariables["defaults"] == True:
            if denaliVariables["debug"] == True:
                print "SELECT   = %s" % SELECT
                print "WHERE    = %s" % WHERE
                print "LIKE     = %s" % LIKE
                print "DEFAULTS = %s" % DEFAULTS
                print "SQLMODS  = %s" % SQLSEARCHMODS
                print "GROUP_BY = %s" % GROUP_BY
                print "ORDER_BY = %s" % ORDER_BY
                print "PAGE     = %s" % PAGE
            query = SELECT + WHERE + LIKE + ')' + DEFAULTS + SQLSEARCHMODS + GROUP_BY + ORDER_BY + PAGE
        else:
            if denaliVariables["debug"] == True:
                print "SELECT   = %s" % SELECT
                print "WHERE    = %s" % WHERE
                print "LIKE     = %s" % LIKE
                print "SQLMODS  = %s" % SQLSEARCHMODS
                print "GROUP_BY = %s" % GROUP_BY
                print "ORDER_BY = %s" % ORDER_BY
                print "PAGE     = %s" % PAGE
            query = SELECT + WHERE + LIKE + ')' + SQLSEARCHMODS + GROUP_BY + ORDER_BY + PAGE

    else:
        IN = IN[:-1] + ')'

        if denaliVariables["limitCount"] == 0:
            PAGE = " PAGE 1, %d" % len(serverList)
        else:
            if len(serverList) <= denaliVariables["limitCount"]:
                PAGE = " PAGE 1, %d" % len(serverList)
            else:
                if denaliVariables["limitCount"] < denaliVariables["maxSKMSRowReturn"]:
                    if denaliVariables["historyList"] == True:
                        PAGE = " PAGE 1, %d" % denaliVariables["maxSKMSRowReturn"]
                    else:
                        PAGE = " PAGE 1, %d" % denaliVariables["limitCount"]
                else:
                    PAGE = " PAGE 1, %d" % denaliVariables["maxSKMSRowReturn"]

        if denaliVariables["defaults"] == True:
            if denaliVariables["debug"] == True:
                print "SELECT   = %s" % SELECT
                print "WHERE    = %s" % WHERE
                print "IN       = %s" % IN
                print "DEFAULTS = %s" % DEFAULTS
                print "SQLMODS  = %s" % SQLSEARCHMODS
                print "GROUP_BY = %s" % GROUP_BY
                print "ORDER_BY = %s" % ORDER_BY
                print "PAGE     = %s" % PAGE
            query = SELECT + WHERE + IN + DEFAULTS + SQLSEARCHMODS + GROUP_BY + ORDER_BY + PAGE
        else:
            if denaliVariables["debug"] == True:
                print "SELECT   = %s" % SELECT
                print "WHERE    = %s" % WHERE
                print "IN       = %s" % IN
                print "SQLMODS  = %s" % SQLSEARCHMODS
                print "GROUP_BY = %s" % GROUP_BY
                print "ORDER_BY = %s" % ORDER_BY
                print "PAGE     = %s" % PAGE
            query = SELECT + WHERE + IN + SQLSEARCHMODS + GROUP_BY + ORDER_BY + PAGE

    return (query, wildcard)



##############################################################################
#
# returnDataCenterID(dc_name)
#

def returnDataCenterID(dc_name):

    if dc_name.upper() in denali_location.dc_location:
        return str(denali_location.dc_location.index(dc_name.upper()))
    else:
        return False



##############################################################################
#
# locationWildcardSearch(denaliVariables, site_location)
#

def locationWildcardSearch(denaliVariables, site_location):

    if denaliVariables["debug"] == True:
        print "Wildcard location expression entered  : %s" % site_location

    # execute the search
    match_list  = fnmatch.filter(denali_location.dc_location, site_location.upper())

    if denaliVariables["debug"] == True:
        print "Wildcard locations found              : %s" % match_list

    # assume all matches are valid and replace them with their
    # correct location_id
    for (index, match) in enumerate(match_list):
        match_list[index] = returnDataCenterID(match)

    match_count = len(match_list)
    sequence    = range(1, (match_count * 2), 2)

    # put an "OR" between each wildcard match
    for count in range(match_count - 1):
        index = sequence[count]
        match_list.insert(index, "OR")

    match_string = ' '.join(match_list)

    if denaliVariables["debug"] == True:
        print "Wildcard location expression generated: %s" % match_string

    return [match_string]



##############################################################################
#
# checkForValidLocation(sql_location):
#
#   Validate that the list returned is correct and can be processed by
#   the sql parser.
#

def checkForValidLocation(sql_location):

    location_list     = []
    operator_list     = []
    sql_location_list = []

    if len(sql_location) == 0:
        # all possible locations were stripped because they were/are invalid.
        return False
    else:
        # 1 or more "locations" in the list
        valid_locations = 0
        for location in sql_location:
            if location.isdigit():
                break
        else:
            # all possible locations were stripped because they were/are invalid.
            return False

    # remove all or's, and's, not's from the beginning/end of the list
    while sql_location[0].isalpha():
        sql_location.pop(0)
    while sql_location[-1].isalpha():
        sql_location.pop(-1)

    for (index, list_item) in enumerate(sql_location):
        if (index % 2) == 0:
            location_list.append(list_item)
        else:
            operator_list.append(list_item)

    # remove any extraneous locations -- must be a number
    for location in location_list:
        if location.isdigit():
            sql_location_list.append(location)

    # intersperse the remaining operators between each
    # location
    location_count = len(sql_location_list)
    if location_count == 0:
        return False
    elif location_count == 1:
        return sql_location_list[0]
    else:
        sequence = range(1, (location_count * 2), 2)
        for count in range(location_count - 1):
            index = sequence[count]
            sql_location_list.insert(index, operator_list[count])

    sql_location_list = ' '.join(sql_location_list)

    return sql_location_list



##############################################################################
#
# locationDataReturn(denaliVariables, sql_location):
#
#   Allow multiple locations to be specified (and translated) if input.
#   The return from this function is in the form of the following:
#       87 OR 5 OR 69
#   The above represents the following: --location="or1 or da2 or sin2"
#   Site locations are translated into the location_id number(s) and then
#   included in an SQL-like string (which is what is actually returned) for
#   inclusion in the search query submitted to SKMS.
#

def locationDataReturn(denaliVariables, sql_location):

    site_location       = sql_location.split()
    site_list           = []
    wildcard_match_list = []
    not_the_locations   = False

    if denaliVariables["debug"] == True:
        print "Initial location submission           : %s" % sql_location

    for site in site_location:
        # check for initial "NOT:" -- potentially
        if site.lower().startswith("not:"):
            site = site.split(':',1)[1]
            not_the_locations = True

        if (site.lower() == "or" or
            site.lower() == "and" or
            site.lower() == "not"):
            # Don't put or,and,not at the beginning, and don't put two
            # or's, and's, or not's back to back
            # With a really interesting query, there is a possibility
            # that an and/or/not gets dropped.  If that's the case, then
            # it means the query is probably complicated and could benefit
            # from being submitted manually.
            if (len(site_list) > 0 and (site_list[-1] != 'OR'  and
                                        site_list[-1] != 'AND' and
                                        site_list[-1] != 'NOT')):
                site_list.append(site.upper())
            continue

        # handle wildcard location submission
        if site.find('*') != -1 or site.find('?') != -1 or site.find('%') != -1:
            matches = locationWildcardSearch(denaliVariables, site)
            wildcard_match_list.append(matches)
            continue

        if site[0].isalpha():
            site_found = returnDataCenterID(site)
            if site_found == False:
                print "Denali syntax error:  Specified location [%s] does not exist." % site
            else:
                site_list.append(site_found)
        elif site.isdigit():
            site_list.append(site)
        else:
            # Don't know what this is (input that will be ignored)
            # Because this doesn't start with a character or isn't a full
            # number, ignore it.
            print "Denali syntax error:  Specified location [%s] does not exist." % site

    # combine wildcard matches with regular ones for validation
    wildcard_matches = ''
    for wildcard_string in wildcard_match_list:
        if len(wildcard_matches) == 0:
            wildcard_matches  = ' '.join(wildcard_string)
        else:
            wildcard_matches += " OR " + ' '.join(wildcard_string)

    wildcard_matches = wildcard_matches.split()

    # join the lists
    site_list_combined = site_list
    if denaliVariables["debug"] == True:
        if len(site_list_combined) > 0:
            print "Site list before join                 : %s" % site_list_combined
        if len(wildcard_matches) > 0:
            print "Wildcard list before join             : %s" % wildcard_matches

    if len(wildcard_matches) > 0 and len(site_list_combined) > 0:
        # make sure that to 'ORs' aren't put back-to-back
        if wildcard_matches[0] != 'OR' and site_list_combined[-1] != 'OR':
            site_list_combined.append('OR')
        site_list_combined.extend(wildcard_matches)
    elif len(wildcard_matches) > 0:
        site_list_combined.extend(wildcard_matches)
    else:
        # site_list_combined > 0
        pass

    # the look up is done, now make sure there are valid locations
    # left over and not just "or's" or "and's", etc.
    if denaliVariables["debug"] == True:
        print "Site List before validation           : %s" % site_list_combined
    new_sql_location = checkForValidLocation(site_list_combined)

    if denaliVariables["debug"] == True:
        print "Final location_id submission          : %s" % new_sql_location
    if new_sql_location == False:
        print "Denali syntax error:  Specified location [%s] is problematic; execution stopped." % sql_location
        return False
    if not_the_locations == True:
        new_sql_location = "NOT:" + new_sql_location

    return new_sql_location



##############################################################################
#
# constructSimpleQuery(denaliVariables)
#

def constructSimpleQuery(denaliVariables):

    # SELECT name, device_state.full_name WHERE name LIKE '<something>'
    #   SELECT == name of the column(s) from the db/table to retrieve
    #   WHERE  == filter for the SELECT clause (search on known values)
    #       WHERE name = 'server1' OR name = 'server2' ...
    #           WHERE supports =, <>, !=, <, <=, !<, >, >=, !>, BETWEEN, IS NULL
    #               WHERE name <> 'server1'
    #           WHERE support AND, OR, NOT, and parenthesis for order of execution
    #               WHERE name = ('server1' NOT name = 'server2') AND name='server3'
    #       WHERE name IN ('server1', 'server2' ...)
    #   LIKE   == filter condition with wildcards, etc.
    #       % = wildcard character (any character, any number of times, including
    #           zero times)
    #           LIKE '%server1%' or LIKE 'serv%r2' ...
    #       _ = wildcard character (single character match, never zero) -- check
    #           '?' if '_' doesn't work.
    #      [] = wildcard for a set of characters to match (only one)
    #           LIKE '[JM]%'  --  data retrieved must begin with a 'J' or 'M'
    #           LIKE '[^JM]%' --  same, but that do NOT begin with 'J' or 'M'
    #               May need to use '!' instead of '^' for some DBMS
    #
    # Wildcard searches take far longer to process than any other search types.
    # If a search can be done without wildcards, do it.
    #
    # As a general rule filtering data at the application layer is strongly
    # discouraged.  Allow the database to do this for you, sending only what
    # you need (i.e., build the query correctly so as to save you time).
    # This will allow the application to scale better.

    # Default SQL query for what we are looking for:
    #
    #  SELECT name,device_state.full_name,device_service.full_name
    #  WHERE  device_state.full_name IN ('On Duty - In Service',
    #                                    'On Duty - Standby')
    #          AND
    #             environment.parent_environment.parent_environment.name = 'SiteCatalyst'
    #          AND
    #             (device_service.parent_device_service.full_name = 'SiteCatalyst'
    #          OR
    #             device_service.parent_device_service.parent_device_service.full_name = 'SiteCatalyst')
    #
    #   This query shows the following:
    #       (1) hostname (name)
    #       (2) host state (device_state.full_name)
    #       (3) host device service
    #
    #   It searches through all hosts that have the parent environment and parent service
    #   of "SiteCatalyst".  This returns 25,000+ host names.

    if denaliVariables["debug"] == True:
        print "\n++Entered constructSimpleQuery\n"

    serverList = denaliVariables["serverList"]

    # if somehow an empty fields list got through, put just the host name
    # as the column to print
    if denaliVariables["fields"] == '':
        denaliVariables["fields"] = "name"

    if len(denaliVariables["sqlParameters"]) > 0:

        # build a temporary list to send in to the validator
        tempObjects  = []
        tempValues   = []
        tempCombined = []

        # validate the SQL parameters are valid (object name/value combination)
        for parm in denaliVariables["sqlParameters"]:
            if parm[0].startswith("--"):
                tempObjects.append(parm[0])

                if len(parm) > 1:
                    tempValues.append(parm[1])
                else:
                    print "Denali Syntax Error: SQL parameter value is empty for [\"%s\"]" % parm[0]
                    print "                     Parameter is dropped from sql modifier list."
                    # if the corresponding object isn't removed, then it creates a scenario where the
                    # entirety of the CMDB is searched through (all objects) -- which is like _not_
                    # what the user asked for.  In this case, it just removes a single modifier and
                    # does the query without it.
                    tempObjects.pop()
            else:
                # MRASEREQ-41586 -- modified 10/23/2017 to fix accidental entire db scan
                print "Denali Syntax Error: SQL parameter name entered without double dash [\"%s\"]" % parm[0]
                cleanUp(denaliVariables)
                exit(1)

        # This is not a perfect check.  It makes sure there are objects and that the
        # number of sql objects matches the number of sql object values.  These could
        # be empty if there are syntax errors passed through the command line.
        #
        # The downside here is that a carefully crafted command line with multiple
        # syntax errors in it could cause unexpected data returns ("wait, I didn't ask
        # for that -- why did that show up?").  That's why the above messages will be
        # displayed when these types of errors are identified (hope the user pays close
        # attention).
        if len(tempObjects) > 0 and (len(tempObjects) == len(tempValues)):
            # load the tempObject list into the variable definition
            denaliVariables["sqlParameters"] = tempObjects

            # send it off to be validated and un-aliased
            denaliVariables["sqlParameters"] = (denali_arguments.validateSQLParameters(denaliVariables)).split(',')

            # reshuffle the objects and values together into the List of Lists
            for (index, parm) in enumerate(denaliVariables["sqlParameters"]):
                if parm == "location_id":
                    tempValues[index] = locationDataReturn(denaliVariables, tempValues[index])
                    if tempValues[index] == False:
                        return False

                tempCombined.append([parm, tempValues[index]])

            # assign the fixed up list back to the denaliVariables location
            denaliVariables["sqlParameters"] = tempCombined
            denaliVariables["sqlParameters"] = buildSqlParmQuery(denaliVariables)
        else:
            denaliVariables["sqlParameters"] = ''
    else:
        denaliVariables["sqlParameters"] = ''

    if (str(denaliVariables["method"]) == "search" or
        str(denaliVariables["method"]) == "count"  or
        str(denaliVariables["method"]) == "getAttributes" or
        str(denaliVariables["method"]) == "getSecrets"):

        # for queries that have a defined host list
        if len(serverList) > 0:
            (sqlQuery, wildcard) = buildHostQuery(denaliVariables)
        else:
            # build query in a more "generic" manner (for eventual portability)
            (sqlQuery, wildcard) = buildGenericQuery(denaliVariables)

        #print "sqlquery = %s" % sqlQuery
        #exit()

        if sqlQuery == False and wildcard == False:
            # found a problem in the query construction
            # print an error, cleanup, and then exit
            if len(serverList) > 0:
                print "Error: Problem in query construction -- with the \"count\" parameter."
            cleanUp(denaliVariables)
            exit(1)

        # the SQL query statement is constructed; submit it to the web API for processing

        ## 0 = index (for number of subqueries; which is zero for a "simple" run)
        ## 1 = number of queries run; which is 1 because this is the only query to run
        ## True/False = print (true) or don't print (false) the query data.  If False,
        ##   then return the dictionary in subdata.  If true, subdata is empty.
        ## subData is used for multi-query data (which a typical "simple" query doesn't use)
        if denaliVariables["historyList"] == True or denaliVariables['batchDevices'] == True:
            (subData, itemCount) = executeSQLQuery(denaliVariables, sqlQuery, 0, 1, False)
        else:
            (subData, itemCount) = executeSQLQuery(denaliVariables, sqlQuery, 0, 1, True)

        # If device history was requested, executeSQLQuery will check and return the subData
        # without printing (just the dictionary, unmodified).  At this point the code checks
        # to see this (again), and then branches off to massage the data to get the history.
        # Yes, this violates the "true" passed in
        if denaliVariables["historyList"] == True:
            # handle printing CMDB history for device(s)
            itemCount = denali_history.deviceHistoryRequest(denaliVariables, subData)
        elif denaliVariables['batchDevices'] == True:
            # handle batched data
            itemCount = denali_utility.batchedDeviceRequest(denaliVariables, subData)

        if denaliVariables["method"] == "count" or denaliVariables["method"] == "getSecrets":
            itemCount = denaliVariables["methodData"]

        # query processing is finished -- determine if anything was printed
        if itemCount != False:
            if itemCount > 0:
                if denaliVariables["summary"] == True:
                    denali_utility.printSummaryInformation(denaliVariables, itemCount, wildcard)
            elif itemCount == "count":      # count method used
                pass
        else:
            if denaliVariables["method"] == "search":
                if len(denaliVariables["serverList"]) > denaliVariables["maxSKMSRowReturn"]:
                    print "SKMS Error:  Device/Record count submitted > %d.  SKMS failed the query." % denaliVariables["maxSKMSRowReturn"]
                else:
                    if denaliVariables["searchCategory"] == "DeviceDao":
                        if ((denaliVariables["historyList"] == False) or
                            (denaliVariables["historyList"] == True and denaliVariables["historyCount"] == 0)):
                            if ((denaliVariables["validateData"] == True and len(denaliVariables["devicesNotFound"]) > 0) or
                                denaliVariables["commOptions"] == "completed"):
                                # keep this "if-branch" just in case it is needed in the future
                                pass
                            elif denaliVariables['monitoring'] == True:
                                # an entity or entities were searched for and not found
                                # pass this to the monitoring code to look for (fpssl, etc.)
                                pass
                            else:
                                if denaliVariables["showInfoMessages"] == True:
                                    print "No devices found for the query submitted (4)."
                    else:
                        if denaliVariables["showInfoMessages"] == True:
                            print "No records found for the query submitted (4)."
            elif denaliVariables["method"] == "count" or denaliVariables["method"] == "getSecrets":
                print "The query returned with no information from the database."

            if denaliVariables["showsql"] == True:
                denali_utility.showSQLQuery(sqlQuery,denaliVariables)

            api = denaliVariables["api"]
            error_type = str(api.get_error_type())

            # if there's a permission error -- automatically print the error
            if error_type == "permission":
                print "\nSKMS ERROR:"
                print "   STATUS  : "  + api.get_response_status()
                print "   TYPE    : "  + str(api.get_error_type())
                if api.get_error_message() == "This account does not have permission to call this method.":
                    print "   MESSAGE : " + "This account does not have permission to call the %s() method." % denaliVariables["method"]
                else:
                    print "   MESSAGE : " + api.get_error_message()

            if denaliVariables["debug"] == True and error_type != "permission":
                print "\nSKMS ERROR:"
                print "   STATUS  : "  + api.get_response_status()
                print "   TYPE    : "  + str(api.get_error_type())
                print "   MESSAGE : "  + api.get_error_message()

            # do not return a '1' when valid SKMS hosts aren't found _and_ the "--validate" switch is used
            if denaliVariables["validateData"] == False and denaliVariables['monitoring'] == False:
                # Add --fields timing to prevent python stack when the '--time' switch
                # is used and no devices are found.
                denali_utility.addElapsedTimingData(denaliVariables, '--fields_stop', time.time())
                denali_utility.addElapsedTimingData(denaliVariables, 'process_arguments_stop', time.time())
                cleanUp(denaliVariables)
                exit(1)

        if denaliVariables["showsql"] == True:
            denali_utility.showSQLQuery(sqlQuery, denaliVariables)

        return True

    else:
        print
        print "Method specified, \"%s\", is currently not supported." % denaliVariables["method"]
        print "Only the \"search\", \"count\", \"getAttributes\", and \"getSecrets\" methods are supported."
        print "Execution must stop."
        print
        return False



##############################################################################
#
# cleanUp(denaliVariables)
#

def cleanUp(denaliVariables):

    # get rid of any temp files created/used during the denali run
    for tmpFile in denaliVariables["tmpFilesCreated"]:
        # make sure the file exists before trying to delete it
        if os.path.isfile(tmpFile) == True:
            if denaliVariables["debug"] == True:
                print "\nRemoving temp file: %s" % tmpFile
            try:
                os.remove(tmpFile)
            except:
                if denaliVariables["debug"] == True:
                    print "   FAILURE"
            else:
                if denaliVariables["debug"] == True:
                    print "   SUCCESS"

    denaliVariables['time']['denali_stop'].append(time.time())

    if denaliVariables['time_display'] == True:
        denali_utility.printTimingInformation(denaliVariables)



##############################################################################
##############################################################################
##############################################################################


if __name__ == '__main__':
    # do nothing
    pass
