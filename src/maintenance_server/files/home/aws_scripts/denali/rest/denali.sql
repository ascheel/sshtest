CREATE TABLE `analytics` (
    `id` int(10) unsigned NOT NULL auto_increment,
    `timestamp` timestamp NOT NULL default CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `timezone` varchar(7) default NULL,
    `version` varchar(30) NOT NULL default '',
    `host_ip` varchar(15) NOT NULL default '0.0.0.0',
    `query_type` enum('Anomoly Authentication','Attribute Comparison','Authentication','Normal','Update') NOT NULL default 'Normal',
    `username` varchar(50) NOT NULL default '',
    `dao` varchar(30) NOT NULL default '',
    `method` varchar(20) NOT NULL default '',
    `rows` int(5) unsigned NOT NULL default '0',
    `fields` varchar(1000) NOT NULL default '',
    `ext_module` varchar(20) NULL default NULL,
    `search_time` float NOT NULL default '0',
    `sql_query` mediumtext NOT NULL,
    PRIMARY KEY  ('id'),
    KEY `timestamp_idx` (`timestamp`)
) ENGINE=MyISAM CHARSET=latin1;